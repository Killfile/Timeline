"""Shared utilities for ingestion strategies.

This module is intentionally strategy-agnostic. It contains:
- per-run logging setup (INFO/ERROR loggers + run id)
- database connection helpers + insert function
- HTTP helpers for MediaWiki API and HTML fetches
- Wikipedia URL canonicalization and identity resolution

Both the list-of-years and category-based strategies import from here.

NOTE: Some HTML parsing helpers remain in the list-of-years strategy module
because they are specific to year/decade pages.
"""

from __future__ import annotations

import json
import logging
import os
import time
import hashlib
from event_key import compute_event_key
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse


import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Wikipedia API endpoint
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_BASE = "https://en.wikipedia.org"
LIST_OF_YEARS_URL = "https://en.wikipedia.org/wiki/List_of_years"


class HttpCache:
    """Cache for HTTP responses to avoid redundant fetches."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, url: str) -> str:
        """Generate a cache key from the URL."""
        return hashlib.sha256(url.encode('utf-8')).hexdigest()

    def _load_from_cache(self, cache_key: str) -> tuple[str, str] | None:
        """Load cached response if it exists."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with cache_file.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data['text'], data['final_url']
            except (json.JSONDecodeError, KeyError):
                # Invalid cache file, ignore and fetch fresh
                pass
        return None

    def _save_to_cache(self, cache_key: str, text: str, final_url: str) -> None:
        """Save response to cache."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        data = {'text': text, 'final_url': final_url}
        try:
            with cache_file.open('w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception:
            # If caching fails, don't fail the request
            pass

    def get(self, url: str, *, timeout: int = 30, context: str = "") -> tuple[tuple[str, str], str | None]:
        """Fetch from cache or remote.

        Returns:
          ((html, final_url), None) on success (cached or fresh)
          (("", url), error_string) on failure
        """
        cache_key = self._get_cache_key(url)
        cached = self._load_from_cache(cache_key)
        if cached:
            print(f"🤑 Cache hit for URL{f' ({context})' if context else ''}: {url}", flush=True)
            text, final_url = cached
            return ((text, final_url), None)

        # Cache miss: fetch from remote
        try:
            resp = WIKI_SESSION.get(url, timeout=timeout)
            final_url = _canonicalize_wikipedia_url(resp.url or url)

            content_type = (resp.headers.get("Content-Type") or "").lower()
            text = resp.text or ""
            snippet = text.replace("\n", " ").strip()[:300]

            if resp.status_code != 200:
                msg = (
                    f"HTTP {resp.status_code} fetching HTML"
                    f"{f' ({context})' if context else ''}"
                    f" ct={content_type!r} url={final_url} snippet={snippet!r}"
                )
                print(msg, flush=True)
                return (("", final_url), msg)

            if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                msg = (
                    f"Unexpected content-type fetching HTML"
                    f"{f' ({context})' if context else ''}"
                    f" ct={content_type!r} url={final_url} snippet={snippet!r}"
                )
                print(msg, flush=True)
                return (("", final_url), msg)

            # Success: cache the response
            self._save_to_cache(cache_key, text, final_url)
            return ((text, final_url), None)
        except requests.RequestException as e:
            msg = f"Request error{f' ({context})' if context else ''}: {e}"
            print(msg, flush=True)
            return (("", url), msg)


# Cache directory for HTTP responses
CACHE_DIR = Path(__file__).resolve().parent / "cache"
HTTP_CACHE = HttpCache(CACHE_DIR)


def _setup_run_logging() -> tuple[logging.Logger, logging.Logger, str, str]:
    """Create per-run file loggers for ingestion."""
    # Default to a *writable* location when running locally.
    # The container can (and should) override this via INGEST_LOG_DIR.
    default_logs_dir = str(Path(__file__).resolve().parent / "logs")
    logs_dir = Path(os.getenv("INGEST_LOG_DIR", default_logs_dir))
    logs_dir.mkdir(parents=True, exist_ok=True)

    run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    info_path = logs_dir / f"ingest_{run_id}.info.log"
    err_path = logs_dir / f"ingest_{run_id}.error.log"

    fmt = logging.Formatter("%(asctime)sZ\t%(levelname)s\t%(message)s")

    info_logger = logging.getLogger(f"ingest.info.{run_id}")
    info_logger.setLevel(logging.INFO)
    info_logger.propagate = False
    ih = logging.FileHandler(info_path, encoding="utf-8")
    ih.setFormatter(fmt)
    info_logger.addHandler(ih)

    err_logger = logging.getLogger(f"ingest.error.{run_id}")
    err_logger.setLevel(logging.ERROR)
    err_logger.propagate = False
    eh = logging.FileHandler(err_path, encoding="utf-8")
    eh.setFormatter(fmt)
    err_logger.addHandler(eh)

    # Also keep a very small amount of info on stdout for humans.
    print(f"Ingestion logs: {info_path} (info), {err_path} (error)", flush=True)
    return info_logger, err_logger, str(logs_dir), run_id


INFO_LOG, ERROR_LOG, LOGS_DIR, RUN_ID = _setup_run_logging()


def log_info(msg: str) -> None:
    print(f"ℹ️ {msg}", flush=True)
    INFO_LOG.info(msg)


def log_error(msg: str) -> None:
    print(f"❌ {msg}", flush=True)
    ERROR_LOG.error(msg)


def _build_wikipedia_session() -> requests.Session:
    """Create a requests session with retries and a proper User-Agent."""
    session = requests.Session()

    retries = Retry(
        total=5,
        connect=5,
        read=5,
        status=5,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
        respect_retry_after_header=False,  # Avoid parsing issues with decimal Retry-After values
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    ua = os.getenv(
        "WIKIPEDIA_USER_AGENT",
        "TimelineIngestionBot/1.0 (https://localhost; admin@example.com) requests",
    )
    session.headers.update({"User-Agent": ua})
    return session


WIKI_SESSION = _build_wikipedia_session()


def _get_json(url: str, *, params: dict, timeout: int = 30, context: str = "") -> dict | None:
    """GET JSON with good diagnostics when the response isn't JSON."""
    try:
        resp = WIKI_SESSION.get(url, params=params, timeout=timeout)

        try:
            data = resp.json()
        except ValueError:
            snippet = (resp.text or "").replace("\n", " ").strip()[:300]
            print(
                f"HTTP {resp.status_code} non-JSON response{f' ({context})' if context else ''}: {snippet}",
                flush=True,
            )
            return None

        if isinstance(data, dict) and data.get("error"):
            print(
                f"Wikipedia API error{f' ({context})' if context else ''}: {data['error']}",
                flush=True,
            )
            return None

        return data
    except requests.RequestException as e:
        print(f"Request error{f' ({context})' if context else ''}: {e}", flush=True)
        return None




def _canonicalize_wikipedia_url(url: str) -> str:
    if not url:
        return url
    return url.split("#", 1)[0]


def _wikipedia_title_from_url(url: str) -> str | None:
    if not url:
        return None
    try:
        parsed = urlparse(url)
        path = parsed.path or ""
        if not path.startswith("/wiki/"):
            return None
        title = unquote(path[len("/wiki/") :])
        return title or None
    except Exception:
        return None


def _resolve_page_identity(url: str, *, timeout: int = 30) -> dict | None:
    """Resolve a Wikipedia URL to a stable identity via MediaWiki API."""
    title = _wikipedia_title_from_url(url)
    if not title:
        return None

    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "redirects": 1,
        "prop": "info",
        "inprop": "url",
    }
    data = _get_json(WIKIPEDIA_API, params=params, timeout=timeout, context=f"resolve={title}")
    if not data:
        return None

    pages = (data.get("query") or {}).get("pages")
    if not isinstance(pages, dict) or not pages:
        return None

    page = next(iter(pages.values()))
    pageid = page.get("pageid")
    fullurl = page.get("fullurl")
    if not isinstance(pageid, int) or pageid <= 0:
        return None
    canonical_url = _canonicalize_wikipedia_url(fullurl or url)
    return {"pageid": pageid, "canonical_url": canonical_url}

def _get_from_remote(url: str, *, timeout: int = 30, context: str = "") -> tuple[tuple[str, str], str | None]:
    """Fetch HTML with caching.

    Checks cache first; if miss, fetches from remote and caches success.
    Returns:
      ((html, final_url), None) on success (cached or fresh)
      (("", url), error_string) on failure
    """
    return HTTP_CACHE.get(url, timeout=timeout, context=context)

def get_html(url: str, *, timeout: int = 30, context: str = "") -> tuple[tuple[str, str], str | None]:
    """Fetch HTML.

    Returns:
      ((html, final_url), None) on success
      (("", url), error_string) on failure
    """
    return_value = _get_from_remote(url, timeout=timeout, context=context)
    return return_value

