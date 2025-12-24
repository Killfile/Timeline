"""List-of-years ingestion strategy.

This is the current default ingestion pipeline.

It discovers year pages from Wikipedia's `List_of_years` page, then extracts
bullets from the per-year "Events" section.

This module owns the HTML parsing logic for year pages.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

try:
    from .ingestion_common import (
        LIST_OF_YEARS_URL,
        LOGS_DIR,
        RUN_ID,
        WIKIPEDIA_BASE,
        _canonicalize_wikipedia_url,
        _get_html,
        _resolve_page_identity,
        insert_event,
        log_error,
        log_info,
    )
except ImportError:  # pragma: no cover
    from ingestion_common import (
        LIST_OF_YEARS_URL,
        LOGS_DIR,
        RUN_ID,
        WIKIPEDIA_BASE,
        _canonicalize_wikipedia_url,
        _get_html,
        _resolve_page_identity,
        insert_event,
        log_error,
        log_info,
    )


_DASH_RE = re.compile(r"[\u2012\u2013\u2014\u2212-]")

_MONTHS = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)


# ===== Data Classes =====
# Structured types replacing dict returns for better type safety


@dataclass
class PageScope:
    """Date scope for a year/decade/century page."""
    precision: str  # "year", "decade", or "century"
    start_year: int
    end_year: int
    is_bc: bool


@dataclass
class BulletSpan:
    """Parsed date span from event bullet text."""
    precision: str
    start_year: int
    end_year: int
    is_bc: bool


@dataclass
class EventItem:
    """Structured event bullet extracted from HTML."""
    text: str
    tag: Optional[str] = None
    month_bucket: Optional[str] = None
    events_heading: Optional[str] = None


@dataclass
class ExclusionReport:
    """Report of excluded bullets during extraction."""
    excluded_counts: dict[str, int] = field(default_factory=dict)
    excluded_samples: dict[str, list[dict]] = field(default_factory=dict)


@dataclass
class PageDiscovery:
    """Discovered year/decade page metadata."""
    title: str
    url: str
    scope: dict  # Will be PageScope once dict consumers are updated


# ===== Pure Parsing Functions =====
# Functions that don't perform IO and can be tested independently


def _bump_excluded(
    excluded_counts: dict[str, int],
    excluded_samples: dict[str, list[dict]],
    reason: str,
    *,
    text: Optional[str] = None,
    events_heading: Optional[str] = None,
    h3: Optional[str] = None,
) -> None:
    """Add an exclusion reason to the tracking dictionaries.
    
    Args:
        excluded_counts: Count dictionary to update
        excluded_samples: Sample dictionary to update
        reason: Exclusion reason key
        text: Optional bullet text
        events_heading: Optional heading text
        h3: Optional h3 context
    """
    excluded_counts[reason] = excluded_counts.get(reason, 0) + 1
    if text:
        bucket = excluded_samples.setdefault(reason, [])
        if len(bucket) < 8:
            bucket.append({
                "text": text[:200],
                "events_heading": events_heading,
                "h3": h3
            })


def _element_should_be_excluded(el, content_root) -> bool:
    """Check if element is in excluded navigation/metadata sections.
    
    Args:
        el: BeautifulSoup element
        content_root: The main content container element
        
    Returns:
        True if element should be excluded from extraction
    """
    if el is None:
        return True
    if content_root is not None and not (el is content_root or content_root in el.parents):
        return True

    for anc in el.parents:
        if not hasattr(anc, "name"):
            continue
        anc_id = (anc.get("id") or "").strip()
        if anc_id in {"mw-normal-catlinks", "mw-hidden-catlinks", "catlinks", "footer"}:
            return True

        classes = set((anc.get("class") or []))
        if classes.intersection(
            {
                "navbox",
                "navbox-inner",
                "vertical-navbox",
                "metadata",
                "mbox-small",
                "ambox",
                "hatnote",
                "mw-footer",
                "mw-portlet",
            }
        ):
            return True

    return False


def _merge_exclusions(
    exclusions_agg_counts: dict[str, int],
    exclusions_agg_samples: dict[str, list[dict]],
    report: Optional[dict],
) -> None:
    """Merge extraction report exclusions into aggregate dictionaries.
    
    Args:
        exclusions_agg_counts: Aggregate counts to update
        exclusions_agg_samples: Aggregate samples to update
        report: Extraction report dict with excluded_counts and excluded_samples
    """
    if not report:
        return
    counts = report.get("excluded_counts") or {}
    samples = report.get("excluded_samples") or {}
    for k, v in counts.items():
        exclusions_agg_counts[k] = exclusions_agg_counts.get(k, 0) + int(v)
    for reason, slist in (samples or {}).items():
        bucket = exclusions_agg_samples.setdefault(reason, [])
        for s in slist:
            if len(bucket) >= 25:
                break
            bucket.append(s)


def _write_exclusions_report(
    exclusions_agg_counts: dict[str, int],
    exclusions_agg_samples: dict[str, list[dict]],
) -> None:
    """Write exclusions report to JSON file.
    
    Args:
        exclusions_agg_counts: Aggregate exclusion counts
        exclusions_agg_samples: Aggregate exclusion samples
    """
    try:
        out_path = Path(LOGS_DIR) / f"exclusions_{RUN_ID}.json"
        payload = {
            "run_id": RUN_ID,
            "generated_at_utc": datetime.utcnow().isoformat() + "Z",
            "excluded_counts": exclusions_agg_counts,
            "excluded_samples": exclusions_agg_samples,
        }
        out_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )
        log_info(f"Wrote exclusions report: {out_path}")
    except Exception as e:
        log_info(f"Failed to write exclusions report: {e}")


def _parse_scope_from_title(title: str) -> dict | None:
    """Infer the date scope from a year/decade/century page title."""
    t = (title or "").strip()
    t_norm = re.sub(r"\s+", " ", t)

    is_bc = bool(re.search(r"\b(BC|BCE)\b", t_norm, flags=re.IGNORECASE))
    is_ad = bool(re.search(r"\b(AD|CE)\b", t_norm, flags=re.IGNORECASE))

    core = re.sub(r"\b(BC|BCE|AD|CE)\b", "", t_norm, flags=re.IGNORECASE)
    core = re.sub(r"\s+", " ", core).strip()

    m = re.match(r"^(\d{1,4})$", core)
    if m:
        y = int(m.group(1))
        if is_bc:
            return {"precision": "year", "start_year": y, "end_year": y, "is_bc": True}
        return {"precision": "year", "start_year": y, "end_year": y, "is_bc": False}

    m = re.match(r"^(\d{1,4})s$", core)
    if m:
        start = int(m.group(1))
        is_bc_only = bool(is_bc and not is_ad)
        return {
            "precision": "decade",
            "start_year": start,
            "end_year": start + 9,
            "is_bc": is_bc_only,
        }

    m = re.match(r"^(\d{1,2})(st|nd|rd|th) century$", core, flags=re.IGNORECASE)
    if m:
        c = int(m.group(1))
        if is_bc and not is_ad:
            start = c * 100
            end = (c - 1) * 100 + 1
            return {"precision": "century", "start_year": start, "end_year": end, "is_bc": True}
        start = (c - 1) * 100
        end = start + 99
        return {"precision": "century", "start_year": start, "end_year": end, "is_bc": False}

    return None


def _extract_events_and_trends_bullets(html: str) -> list[str]:
    return [i["text"] for i in _extract_events_section_items(html)]


def _get_tag_and_month_from_h3_context(h3_text: str | None) -> tuple[str | None, str | None]:
    """Classify h3 heading as a tag or month bucket.
    
    Args:
        h3_text: The h3 heading text
        
    Returns:
        Tuple of (tag, month_bucket). Tag is the category label, month_bucket
        is the month name if this is a month heading.
    """
    if not h3_text:
        return None, None

    raw = re.sub(r"\s+", " ", h3_text).strip()
    if not raw:
        return None, None

    norm = _DASH_RE.sub("-", raw.lower())

    if norm in {"unknown dates", "date unknown", "unknown date", "unknown"}:
        return None, raw

    months_pattern = r"(?:" + "|".join(_MONTHS) + r")"
    if re.fullmatch(months_pattern, norm, flags=re.IGNORECASE):
        return None, raw
    if re.fullmatch(months_pattern + r"\s*-\s*" + months_pattern, norm, flags=re.IGNORECASE):
        return None, raw

    # Compatibility with existing tests and earlier behavior:
    # a standalone "By place" heading is treated as a tag (not a grouping header).
    # More generic group headings like "By place/topic/subject" are ignored elsewhere.
    if norm in {"by place", "by topic", "by subject"}:
        return raw, None

    return raw, None


def _is_grouping_category_heading(h3_text: str | None) -> bool:
    """Return True for generic group headings that should not be treated as tags.
    
    Args:
        h3_text: The h3 heading text
        
    Returns:
        True if this is a generic grouping header like "By place/topic"
    """

    if not h3_text:
        return False
    raw = re.sub(r"\s+", " ", h3_text).strip().lower()
    raw = _DASH_RE.sub("-", raw)
    # Ignore the broad group headings, not the concrete category labels.
    return raw in {
        "by place/topic",
        "by place/topic/subject",
        "by topic/subject",
    }


def _find_events_h2_heading(soup: BeautifulSoup):
    """Find the Events or Events and trends h2 heading.
    
    Args:
        soup: BeautifulSoup parsed HTML
        
    Returns:
        The h2 element or None if not found
    """
    for h in soup.find_all(["h2"]):
        txt = h.get_text(" ", strip=True)
        if not txt:
            continue
        low = txt.lower()
        if low == "events" or "events and trends" in low:
            return h
    return None


def _extract_events_section_items_with_report(html: str) -> tuple[list[dict], dict]:
    """Extract structured items from the year page Events section.
    
    Args:
        html: Raw HTML content from Wikipedia page
        
    Returns:
        Tuple of (event items list, exclusion report dict)
    """
    soup = BeautifulSoup(html, "lxml")
    content_root = soup.select_one("#mw-content-text") or soup
    events_h2 = _find_events_h2_heading(soup)
    if events_h2 is None:
        return [], {"excluded_counts": {}, "excluded_samples": {}}

    events_heading = events_h2.get_text(" ", strip=True)
    current_h3: str | None = None
    current_h4: str | None = None
    items: list[dict] = []

    excluded_counts: dict[str, int] = {}
    excluded_samples: dict[str, list[dict]] = {}

    for node in events_h2.find_all_next():
        if node == events_h2:
            continue
        if node.name == "h2":
            break

        if node.name == "h3":
            h3_text = node.get_text(" ", strip=True)
            current_h3 = None if _is_grouping_category_heading(h3_text) else (h3_text or None)
            current_h4 = None
            continue

        if node.name == "h4":
            current_h4 = node.get_text(" ", strip=True) or None
            continue

        if node.name != "ul":
            continue

        if _element_should_be_excluded(node, content_root):
            _bump_excluded(excluded_counts, excluded_samples, "chrome_ul", events_heading=events_heading, h3=current_h3)
            continue

        tag, month_bucket = _get_tag_and_month_from_h3_context(current_h3)
        if current_h4:
            tag = current_h4

        for li in node.find_all("li", recursive=False):
            if _element_should_be_excluded(li, content_root):
                _bump_excluded(excluded_counts, excluded_samples, "chrome_li", events_heading=events_heading, h3=current_h3)
                continue
            text = li.get_text(" ", strip=True)
            if not text:
                _bump_excluded(excluded_counts, excluded_samples, "empty_li", events_heading=events_heading, h3=current_h3)
                continue
            if text.startswith("Category:"):
                _bump_excluded(excluded_counts, excluded_samples, "category_prefix", text=text, events_heading=events_heading, h3=current_h3)
                continue
            if len(text) < 3:
                _bump_excluded(excluded_counts, excluded_samples, "too_short", text=text, events_heading=events_heading, h3=current_h3)
                continue
            if text in {"v", "t", "e"}:
                _bump_excluded(excluded_counts, excluded_samples, "vtelinks", text=text, events_heading=events_heading, h3=current_h3)
                continue

            log_info(f"Found event bullet: {text[:100]!r} (tag={tag!r}, month_bucket={month_bucket!r})")
            items.append(
                {
                    "text": text,
                    "tag": tag,
                    "month_bucket": month_bucket,
                    "events_heading": events_heading,
                }
            )

    return items, {"excluded_counts": excluded_counts, "excluded_samples": excluded_samples}


def _extract_events_section_items(html: str) -> list[dict]:
    items, _report = _extract_events_section_items_with_report(html)
    return items


def _discover_yearish_links_from_list_of_years(html: str, *, limit: int | None = 200) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    candidates: list[dict] = []
    seen_urls: set[str] = set()

    bc_re = re.compile(r"^/wiki/(\d{1,4})_BC$")
    ad_re = re.compile(r"^/wiki/AD_(\d{1,4})$")
    include_ad = os.getenv("WIKI_LIST_OF_YEARS_INCLUDE_AD", "").strip().lower() in {"1", "true", "yes"}

    for a in soup.select('a[href^="/wiki/"]'):
        href = a.get("href") or ""
        m_bc = bc_re.match(href)
        m_ad = ad_re.match(href) if include_ad else None
        if not (m_bc or m_ad):
            continue

        year = int((m_bc or m_ad).group(1))
        is_bc = bool(m_bc)

        url = urljoin(WIKIPEDIA_BASE, href)
        if url in seen_urls:
            continue
        seen_urls.add(url)

        title = f"{year} BC" if is_bc else f"AD {year}"
        scope = {"precision": "year", "start_year": year, "end_year": year, "is_bc": is_bc}

        candidates.append({"title": title, "url": url, "scope": scope})
        if limit is not None and len(candidates) >= limit:
            break

    return candidates


def _infer_page_era_from_html(html: str, *, scope_is_bc: bool | None) -> bool | None:
    title_text = ""
    h1_text = ""
    try:
        soup = BeautifulSoup(html, "lxml")
        title_tag = soup.find("title")
        if title_tag:
            title_text = title_tag.get_text(" ", strip=True)
        h1_tag = soup.find("h1")
        if h1_tag:
            h1_text = h1_tag.get_text(" ", strip=True)
    except Exception:
        title_text = ""
        h1_text = ""

    combined = f"{title_text} {h1_text}".strip()
    combined = re.sub(r"\s+", " ", combined)
    if combined:
        if re.search(r"\b(BCE?)\b", combined, flags=re.IGNORECASE):
            return True
        if re.search(r"\d\s*s\s*(BC|BCE)\b", combined, flags=re.IGNORECASE):
            return True
        if re.search(r"\b(AD|CE)\b", combined, flags=re.IGNORECASE):
            return False

    return scope_is_bc


def _parse_span_from_bullet(text: str, *, assume_is_bc: bool | None = None) -> dict | None:
    if not text:
        return None
    t = text.strip()

    lead = re.sub(r"^\s+", "", t)
    if re.match(r"^(c\s*\.|ca\s*\.|circa)(\s|$)", lead, flags=re.IGNORECASE):
        return None

    t_norm = _DASH_RE.sub("-", t)

    m = re.search(
        r"(?<!\d)(\d{1,4})\s*(BC|BCE|AD|CE)?\s*-\s*(\d{1,4})\s*(BC|BCE|AD|CE)?",
        t_norm,
        flags=re.IGNORECASE,
    )
    if m:
        s_y = int(m.group(1))
        s_era = (m.group(2) or "").upper()
        e_y = int(m.group(3))
        e_era = (m.group(4) or "").upper()

        is_bc = ("BC" in s_era) or ("BC" in e_era) or ("BCE" in s_era) or ("BCE" in e_era)
        is_ad = ("AD" in s_era) or ("AD" in e_era) or ("CE" in s_era) or ("CE" in e_era)
        if is_bc and is_ad:
            return None

        if not is_bc and not is_ad and assume_is_bc is not None:
            is_bc = bool(assume_is_bc)

        start_year = min(s_y, e_y)
        end_year = max(s_y, e_y)
        return {"start_year": start_year, "end_year": end_year, "is_bc": bool(is_bc and not is_ad), "precision": "year"}

    m = re.search(r"(?<!\d)(\d{1,4})\s*(BC|BCE|AD|CE)\b", t_norm, flags=re.IGNORECASE)
    if m:
        y = int(m.group(1))
        era = (m.group(2) or "").upper()
        is_bc = era in {"BC", "BCE"}
        return {"start_year": y, "end_year": y, "is_bc": is_bc, "precision": "year"}

    m = re.search(r"(?<!\d)(\d{3,4})(?!\d)", t_norm)
    if m:
        y = int(m.group(1))
        return {"start_year": y, "end_year": y, "is_bc": bool(assume_is_bc) if assume_is_bc is not None else False, "precision": "year"}

    return None


def ingest_wikipedia_list_of_years(conn) -> None:
    """Main entry point for ingesting events from Wikipedia's List of years.
    
    Args:
        conn: Database connection for inserting events
    """
    log_info("Starting Wikipedia list-of-years ingestion...")

    exclusions_agg_counts: dict[str, int] = {}
    exclusions_agg_samples: dict[str, list[dict]] = {}

    (index_pair, index_err) = _get_html(LIST_OF_YEARS_URL, context="list_of_years")
    index_html, _index_url = index_pair
    if index_err or not index_html.strip():
        log_error(f"Failed to load List_of_years page: {index_err}")
        _write_exclusions_report(exclusions_agg_counts, exclusions_agg_samples)
        return

    raw_limit = os.getenv("WIKI_LIST_OF_YEARS_PAGE_LIMIT")
    page_limit = int(raw_limit) if raw_limit else 1000

    bc_only = os.getenv("WIKI_LIST_OF_YEARS_BC_ONLY", "").strip().lower() in {"1", "true", "yes"}
    if bc_only and not raw_limit:
        page_limit = None

    pages = _discover_yearish_links_from_list_of_years(index_html, limit=page_limit)
    if bc_only:
        pages = [p for p in pages if bool(p.get("scope", {}).get("is_bc", False))]

    log_info(f"Discovered {len(pages)} year/decade pages (limit={page_limit}, env={raw_limit!r}, bc_only={bc_only})")
    log_info(f"Full pages list: {pages}")

    total_inserted = 0
    visited_page_keys: set[tuple] = set()
    seen_event_keys: set[tuple] = set()

    log_info("Visited-page set initialized (count=0)")

    for p in pages:
        title = p["title"]
        url = p["url"]
        scope = p["scope"]
        scope_is_bc = bool(scope.get("is_bc", False))

        log_info(
            f"Processing page: {title} ({scope['precision']} {scope['start_year']}..{scope['end_year']}{' BC' if scope_is_bc else ''})"
        )

        (page_pair, page_err) = _get_html(url, context=f"year_page={title}")
        if page_err:
            log_error(f"Failed to load year page {title}: {page_err}")
            continue
        html, redirected_url = page_pair
        if not html.strip():
            log_error(f"Loaded empty HTML for year page {title} (url={redirected_url})")
            continue

        try:
            soup = BeautifulSoup(html, "lxml")
            h1_tag = soup.find("h1")
            h1_text = h1_tag.get_text(" ", strip=True) if h1_tag else ""
            title_tag = soup.find("title")
            title_text = title_tag.get_text(" ", strip=True) if title_tag else ""
        except Exception:
            h1_text = ""
            title_text = ""

        actual_title = (h1_text or "").strip()
        if not actual_title:
            actual_title = re.split(r"\s+-\s+", (title_text or "").strip(), maxsplit=1)[0].strip()

        actual_scope = _parse_scope_from_title(actual_title) if actual_title else None
        if actual_scope is not None:
            if actual_scope != p["scope"]:
                log_info(
                    f"Recomputed page scope from HTML title: discovered={p['scope']} actual_title={actual_title!r} actual_scope={actual_scope}"
                )
            scope = actual_scope
            scope_is_bc = bool(scope.get("is_bc", False))

        identity = _resolve_page_identity(redirected_url)
        canonical_url = identity["canonical_url"] if identity else _canonicalize_wikipedia_url(redirected_url)
        pageid = identity["pageid"] if identity else None

        visited_key = ("pageid", pageid) if pageid is not None else ("url", canonical_url)
        if visited_key in visited_page_keys:
            continue
        visited_page_keys.add(visited_key)

        extracted_items, extraction_report = _extract_events_section_items_with_report(html)
        if not extracted_items:
            log_info("No Events bullets found (skipping)")
            continue

        _merge_exclusions(exclusions_agg_counts, exclusions_agg_samples, extraction_report)

        try:
            excluded_counts = (extraction_report or {}).get("excluded_counts") or {}
            excluded_samples = (extraction_report or {}).get("excluded_samples") or {}
            if excluded_counts:
                log_info(f"Extraction exclusions for {canonical_url}: counts={excluded_counts}")
                for reason, samples in excluded_samples.items():
                    for s in samples[:3]:
                        log_info(f"  excluded[{reason}] {s.get('text')!r} (h3={s.get('h3')!r})")
        except Exception:
            pass

        time.sleep(0.3)

        page_assume_is_bc = _infer_page_era_from_html(html, scope_is_bc=scope_is_bc)

        for item in extracted_items:
            b = item["text"]

            tag = (item.get("tag") or "").strip() or None
            month_bucket = (item.get("month_bucket") or "").strip() or None

            bullet_text = (b or "").strip()
            is_circa = bool(re.match(r"^\s*(c\.|ca\.|circa)\b", bullet_text, flags=re.IGNORECASE))

            bullet_span = None if is_circa else _parse_span_from_bullet(bullet_text, assume_is_bc=page_assume_is_bc)
            effective_start_year = scope["start_year"]
            effective_end_year = scope["end_year"]
            effective_is_bc = bool(page_assume_is_bc) if page_assume_is_bc is not None else scope_is_bc
            precision = scope["precision"]

            if bullet_span is not None:
                precision = bullet_span.get("precision", precision)
                effective_start_year = bullet_span["start_year"]
                effective_end_year = bullet_span["end_year"]
                effective_is_bc = bool(bullet_span.get("is_bc", False))

            if precision == "year":
                effective_end_year = int(effective_start_year) + 1

            if is_circa:
                effective_start_year = scope["start_year"]
                effective_end_year = scope["end_year"]
                effective_is_bc = bool(page_assume_is_bc) if page_assume_is_bc is not None else scope_is_bc
                precision = scope["precision"]

            has_any_year_number = bool(re.search(r"(?<!\d)\d{1,4}(?!\d)", bullet_text))
            if not has_any_year_number:
                effective_start_year = scope["start_year"]
                effective_end_year = scope["end_year"]
                effective_is_bc = bool(page_assume_is_bc) if page_assume_is_bc is not None else scope_is_bc
                precision = scope["precision"]

            category_value = tag or None

            normalized_title = re.sub(r"\s+", " ", (b or "").strip().lower())
            event_key = (
                normalized_title,
                int(effective_start_year),
                int(effective_end_year),
                bool(effective_is_bc),
            )
            if event_key in seen_event_keys:
                continue
            seen_event_keys.add(event_key)

            event = {
                "title": b[:500],
                "description": b[:500],
                "url": canonical_url,
                "start_year": effective_start_year,
                "end_year": effective_end_year,
                "is_bc_start": effective_is_bc,
                "is_bc_end": effective_is_bc,
                "pageid": pageid,
                "_debug_extraction": {
                    "method": "list_of_years_events_and_trends",
                    "matches": [],
                    "snippet": b[:300],
                    "weight_days": None,  # set below
                    "events_heading": item.get("events_heading"),
                    "h3_context": {"tag": tag, "month_bucket": month_bucket},
                    "scope": scope,
                    "bullet_span": bullet_span,
                    "source_page": {"title": title, "url": canonical_url},
                },
            }

            # Keep debug payload explicit so the UI can show how weight was derived.
            try:
                span_years = abs(int(effective_end_year) - int(effective_start_year))
                if span_years == 0:
                    span_years = 1
                event["_debug_extraction"]["weight_days"] = int(span_years) * 365
            except Exception:
                event["_debug_extraction"]["weight_days"] = None

            if insert_event(conn, event, category=category_value):
                total_inserted += 1

    log_info(f"Inserted {total_inserted} events from list-of-years")
    _write_exclusions_report(exclusions_agg_counts, exclusions_agg_samples)
