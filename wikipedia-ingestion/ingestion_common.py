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
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# psycopg2 is only required for DB IO (not for HTML parsing/unit tests).
try:
    import psycopg2  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    psycopg2 = None


def _require_psycopg2():
    if psycopg2 is None:  # pragma: no cover
        raise RuntimeError(
            "psycopg2 is required for database operations. "
            "For local unit tests you can run pytest inside the Docker container, "
            "or install wikipedia-ingestion/requirements.txt in your host environment."
        )


# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "database"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "timeline_history"),
    "user": os.getenv("DB_USER", "timeline_user"),
    "password": os.getenv("DB_PASSWORD", "timeline_pass"),
}

# Wikipedia API endpoint
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_BASE = "https://en.wikipedia.org"
LIST_OF_YEARS_URL = "https://en.wikipedia.org/wiki/List_of_years"


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


def connect_db():
    """Connect to the database with retry logic."""
    _require_psycopg2()
    max_retries = 5
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            conn.autocommit = True
            log_info(f"Successfully connected to database at {DB_CONFIG['host']}")
            return conn
        except psycopg2.OperationalError:
            if attempt < max_retries - 1:
                log_error(
                    f"DB connection attempt {attempt + 1} failed. Retrying in {retry_delay} seconds..."
                )
                time.sleep(retry_delay)
            else:
                log_error(f"Failed to connect to database after {max_retries} attempts")
                raise


def clear_previously_ingested(conn) -> None:
    """Clear previously ingested events."""
    _require_psycopg2()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN;")
        cur.execute("TRUNCATE TABLE event_date_extraction_debug RESTART IDENTITY;")
        cur.execute("TRUNCATE TABLE historical_events RESTART IDENTITY CASCADE;")
        cur.execute("COMMIT;")
        log_info("Cleared historical_events + event_date_extraction_debug")
    except Exception:
        cur.execute("ROLLBACK;")
        raise
    finally:
        cur.close()


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


def _get_html(url: str, *, timeout: int = 30, context: str = "") -> tuple[tuple[str, str], str | None]:
    """Fetch HTML.

    Returns:
      ((html, final_url), None) on success
      (("", url), error_string) on failure
    """
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

        return ((text, final_url), None)
    except requests.RequestException as e:
        msg = f"Request error{f' ({context})' if context else ''}: {e}"
        print(msg, flush=True)
        return (("", url), msg)


def insert_event(conn, event: dict, category: str | None):
    """Insert an event into the database."""
    _require_psycopg2()
    title = (event.get("title") or "").strip()
    if not title or len(title) < 3:
        return False

    def _compute_weight_days(e: dict) -> int | None:
        """Approximate event span length in days.

        Contract:
        - Uses year-level granularity only (no months/days yet).
        - 1 year => 365 days.
        - If start/end missing or invalid, returns None.
        """
        try:
            s = e.get("start_year")
            end = e.get("end_year")
            if s is None or end is None:
                return None
            s_i = int(s)
            e_i = int(end)
            # Some ingestion paths store year-as-exclusive-end (e.g. scope year => end = start+1).
            # In that model, end-start is already "span in years".
            span_years = abs(e_i - s_i)
            # Treat single-year point spans (end==start) as 1 year.
            if span_years == 0:
                span_years = 1
            return int(span_years) * 365
        except Exception:
            return None

    # Ensure weight is present; allow caller override.
    if event.get("weight") is None:
        event["weight"] = _compute_weight_days(event)

    try:
        conn.rollback()
    except Exception:
        pass

    insert_sql = """
        INSERT INTO historical_events
            (title, description, start_year, end_year, is_bc_start, is_bc_end, weight, category, wikipedia_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT ON CONSTRAINT uq_historical_events_identity DO NOTHING
        RETURNING id
    """

    insert_params = (
        event["title"],
        event.get("description"),
        event.get("start_year"),
        event.get("end_year"),
        event.get("is_bc_start", False),
        event.get("is_bc_end", False),
        event.get("weight"),
        category,
        event.get("url"),
    )

    if not hasattr(insert_event, "_seen_first_db_error"):
        insert_event._seen_first_db_error = False  # type: ignore[attr-defined]
    if not hasattr(insert_event, "_aborted_count"):
        insert_event._aborted_count = 0  # type: ignore[attr-defined]

    cursor = None
    try:
        cursor = conn.cursor()
        try:
            cursor.execute(insert_sql, insert_params)
        except psycopg2.errors.UndefinedObject:
            cursor.execute(
                """
                INSERT INTO historical_events
                    (title, description, start_year, end_year, is_bc_start, is_bc_end, weight, category, wikipedia_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                insert_params,
            )

        row = cursor.fetchone()
        event_id = row[0] if row else None
        if event_id is None:
            return False

        debug = event.get("_debug_extraction")
        if debug:
            # Record weight for UI debugging.
            debug_weight = debug.get("weight_days")
            if debug_weight is None:
                debug_weight = event.get("weight")

            cursor.execute(
                """
                INSERT INTO event_date_extraction_debug
                    (historical_event_id, pageid, title, category, wikipedia_url,
                     extraction_method, extracted_year_matches,
                     chosen_start_year, chosen_is_bc_start, chosen_end_year, chosen_is_bc_end,
                     chosen_weight_days,
                     extract_snippet)
                VALUES (%s, %s, %s, %s, %s,
                        %s, %s,
                        %s, %s, %s, %s,
                        %s,
                        %s)
                """,
                (
                    event_id,
                    event.get("pageid"),
                    event.get("title"),
                    category,
                    event.get("url"),
                    debug.get("method", "unknown"),
                    json.dumps(debug.get("matches", [])),
                    event.get("start_year"),
                    event.get("is_bc_start", False),
                    event.get("end_year"),
                    event.get("is_bc_end", False),
                    debug_weight,
                    debug.get("snippet"),
                ),
            )

        return True

    except Exception as e:
        details = ""
        if psycopg2 is not None and isinstance(e, psycopg2.Error):
            pgerror = getattr(e, "pgerror", None)
            diag = getattr(e, "diag", None)
            d_msg = getattr(diag, "message_primary", None) if diag else None
            d_detail = getattr(diag, "message_detail", None) if diag else None
            details = (
                f" pgerror={pgerror!r}" + (f" diag={d_msg!r}" if d_msg else "") + (f" detail={d_detail!r}" if d_detail else "")
            )

        msg = "Error inserting event: " + str(e) + details + f" title={event.get('title')!r}"

        if psycopg2 is not None and isinstance(e, psycopg2.Error) and "current transaction is aborted" in str(e).lower():
            insert_event._aborted_count += 1  # type: ignore[attr-defined]
            if insert_event._aborted_count % 50 == 1:  # type: ignore[attr-defined]
                log_error(msg + f" (aborted_count={insert_event._aborted_count})")
        else:
            if not insert_event._seen_first_db_error:  # type: ignore[attr-defined]
                insert_event._seen_first_db_error = True  # type: ignore[attr-defined]
                log_error("FIRST_DB_ERROR " + msg)
            else:
                log_error(msg)

        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        try:
            if cursor is not None:
                cursor.close()
        except Exception:
            pass
