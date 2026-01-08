"""List-of-years ingestion strategy.

This is the current default ingestion pipeline.

It discovers year pages from Wikipedia's `List_of_years` page, then extracts
bullets from the per-year "Events" section.

This module owns the HTML parsing logic for year pages.

IMPORTANT NOTE ON WIKIPEDIA URL REDIRECTS:
==========================================
Wikipedia uses different URL formats for year pages across different eras:
  - BC years: /wiki/100_BC
  - Early AD years (roughly 1-500): /wiki/AD_100
  - Later AD years (roughly 501+): /wiki/504 (simple numeric format)

Some URLs may redirect to others. For example, /wiki/AD_504 redirects to /wiki/504.

LIMITATION: We do NOT follow HTTP redirects during page discovery. We only discover 
pages based on the actual href links present in the "List of years" HTML. This means:
  - If the List of years links to /wiki/504, we discover and process it
  - If the List of years links to /wiki/AD_504 (which redirects), we discover AD_504
  - We use URL canonicalization for duplicate detection, but don't fetch redirects
  
This approach keeps discovery fast and simple, but means we rely on Wikipedia's 
"List of years" page having correct links for all years in our configured range.
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

    if norm in {"unknown dates", "date unknown", "unknown date", "unknown", "year unknown"}:
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


def _is_heading_generic(h3_text: str | None) -> bool:
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
        "year unknown",
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
            current_h3 = None if _is_heading_generic(h3_text) else (h3_text or None)
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


def _parse_year(year_str: str | None) -> dict | None:
    """
    Parse a year string in format '#### AD/BC' (e.g., '150 BC', '1962 AD', '1962').
    Returns dict with {year: int, is_bc: bool} or None if invalid/not specified.
    """
    if not year_str:
        return None
    
    year_str = year_str.strip()
    if not year_str:
        return None
    
    # Match patterns like "150 BC", "1962 AD", "1962", "150 BCE", "1962 CE"
    pattern = r"^(\d{1,4})\s*(AD|BC|BCE|CE)?$"
    match = re.match(pattern, year_str, re.IGNORECASE)
    
    if not match:
        return None
    
    year = int(match.group(1))
    era = match.group(2)
    
    # Determine if BC/BCE (default to AD if no era specified)
    is_bc = bool(era and era.upper() in {"BC", "BCE"})
    
    return {"year": year, "is_bc": is_bc}


def _should_include_page(page_year: int, page_is_bc: bool, min_year: dict | None, max_year: dict | None) -> bool:
    """
    Determine if a page should be included based on min/max year thresholds.
    
    "Ingest from X to Y" means start at X chronologically and stop when we encounter a year AFTER Y:
    - min='100 BC', max='150 BC': Include 200 BC? No. 100 BC? Yes. 99 BC? Yes. 50 BC? Yes. 150 BC? Yes. 149 BC? No.
    - min='100 BC', max='50 AD': Include all from 100 BC through 1 BC, then 1 AD through 50 AD
    - min='10 AD', max='50 AD': Skip all BC, start at 1 AD? No. 10 AD? Yes. 11 AD? Yes. 50 AD? Yes. 51 AD? No.
    
    BC years: 200 BC comes BEFORE 100 BC chronologically (higher numbers = earlier in time).
    """
    # Check minimum year (earliest to start ingesting)
    if min_year is not None:
        min_year_num = min_year["year"]
        min_is_bc = min_year["is_bc"]
        
        if page_is_bc and min_is_bc:
            # Both BC: page must be <= min_year (closer to present)
            # 100 BC min: include 100, 99, 98... exclude 101, 102...
            if page_year > min_year_num:
                return False
        elif not page_is_bc and not min_is_bc:
            # Both AD: page must be >= min_year
            if page_year < min_year_num:
                return False
        elif page_is_bc and not min_is_bc:
            # Page is BC but min is AD: exclude all BC pages (AD comes after BC)
            return False
        # else: page is AD and min is BC: include (AD comes after BC)
    
    # Check maximum year (latest to stop ingesting)
    if max_year is not None:
        max_year_num = max_year["year"]
        max_is_bc = max_year["is_bc"]
        
        if page_is_bc and max_is_bc:
            # Both BC: Higher BC numbers are EARLIER in time (200 BC comes before 100 BC)
            # Include if page year >= max year (page comes before or at the cutoff)
            if page_year < max_year_num:
                return False
        elif not page_is_bc and not max_is_bc:
            # Both AD: include if page year <= max year
            if page_year > max_year_num:
                return False
        elif page_is_bc and not max_is_bc:
            # Page is BC, max is AD: include all BC pages (all BC comes before any AD)
            pass
        else:
            # Page is AD, max is BC: exclude all AD pages
            return False
    
    return True


def _discover_yearish_links_from_list_of_years(html: str, *, limit: int | None = 200, min_year: dict | None = None, max_year: dict | None = None) -> list[dict]:
    """
    Discover year page links from Wikipedia's List of years.
    
    Args:
        html: HTML content of the List of years page
        limit: Optional limit on number of candidates to discover
        min_year: Optional min year dict to determine earliest year to discover
        max_year: Optional max year dict to determine if AD pages should be discovered
    
    Note on Wikipedia URL formats:
        Wikipedia uses different URL formats for year pages in different eras:
        - BC years: /wiki/100_BC
        - Early AD years (1-500): /wiki/AD_100
        - Later AD years (501+): /wiki/504 (simple numeric format)
        
        IMPORTANT: We do NOT follow redirects. Some URLs like /wiki/AD_504 may redirect
        to /wiki/504, but we only discover pages based on the links present in the 
        "List of years" HTML. This means if Wikipedia links to /wiki/504, we discover it,
        but if they link to /wiki/AD_504 which redirects to /wiki/504, we treat them
        as the same page (duplicate detection by final URL).
    """
    soup = BeautifulSoup(html, "lxml")
    candidates: list[dict] = []
    seen_urls: set[str] = set()

    bc_re = re.compile(r"^/wiki/(\d{1,4})_BC$")
    ad_prefix_re = re.compile(r"^/wiki/AD_(\d{1,4})$")
    # Match simple numeric year URLs (e.g., /wiki/504) - interpret as AD years
    # These are used by Wikipedia for years after ~500 AD
    numeric_year_re = re.compile(r"^/wiki/(\d{1,4})$")
    
    # Discover AD pages if:
    # - No max_year specified (default to discovering all)
    # - max_year is AD
    # - min_year is AD (need to discover AD even if max is BC)
    include_ad = (max_year is None or not max_year.get("is_bc", False) or 
                  (min_year is not None and not min_year.get("is_bc", False)))

    for a in soup.select('a[href^="/wiki/"]'):
        href = a.get("href") or ""
        m_bc = bc_re.match(href)
        # Try both AD URL formats: /wiki/AD_### and /wiki/### (numeric only)
        m_ad_prefix = ad_prefix_re.match(href) if include_ad else None
        m_numeric = numeric_year_re.match(href) if include_ad else None
        m_ad = m_ad_prefix or m_numeric
        
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




def _discover_and_filter_pages() -> tuple[list[dict], dict[str, int], dict[str, list[dict]]]:
    """Discover and filter year pages based on min/max year configuration.
    
    Returns:
        tuple of (filtered_pages, exclusions_agg_counts, exclusions_agg_samples)
    """
    exclusions_agg_counts: dict[str, int] = {}
    exclusions_agg_samples: dict[str, list[dict]] = {}

    # Load the List of years index page
    (index_pair, index_err) = _get_html(LIST_OF_YEARS_URL, context="list_of_years")
    index_html, _index_url = index_pair
    if index_err or not index_html.strip():
        log_error(f"Failed to load List_of_years page: {index_err}")
        return [], exclusions_agg_counts, exclusions_agg_samples

    # Parse min/max year configuration (e.g., "150 BC", "1962 AD", "1962")
    min_year_str = os.getenv("WIKI_MIN_YEAR")
    max_year_str = os.getenv("WIKI_MAX_YEAR")
    min_year = _parse_year(min_year_str)
    max_year = _parse_year(max_year_str)
    
    # Discover year pages (pass min/max to control AD discovery)
    pages = _discover_yearish_links_from_list_of_years(index_html, limit=None, min_year=min_year, max_year=max_year)
    
    # Filter pages based on min/max year thresholds
    if min_year or max_year:
        pages = [
            p for p in pages
            if _should_include_page(
                p.get("scope", {}).get("start_year", 0),
                p.get("scope", {}).get("is_bc", False),
                min_year,
                max_year
            )
        ]

    min_desc = f"from {min_year_str}" if min_year_str else "from earliest"
    max_desc = f"to {max_year_str}" if max_year_str else "to latest"
    log_info(f"Discovered {len(pages)} year/decade pages ({min_desc} {max_desc})")
    log_info(f"Full pages list: {pages}")

    return pages, exclusions_agg_counts, exclusions_agg_samples


def _process_event_item(
    item: dict,
    scope: dict,
    scope_is_bc: bool,
    page_assume_is_bc: bool | None,
    canonical_url: str,
    pageid: int | None,
    title: str
) -> dict | None:
    """Process a single event item and return an event dict ready for insertion.
    
    Args:
        item: Extracted event item with text and context
        scope: Page scope (start_year, end_year, precision, is_bc)
        scope_is_bc: Whether the scope is BC
        page_assume_is_bc: Inferred BC/AD era from page HTML
        canonical_url: Canonical Wikipedia URL
        pageid: Wikipedia page ID
        title: Page title
        
    Returns:
        Event dict ready for insert_event(), or None if item should be skipped
    """
    b = item["text"]
    tag = (item.get("tag") or "").strip() or None
    month_bucket = (item.get("month_bucket") or "").strip() or None

    bullet_text = (b or "").strip()
    #is_circa = bool(re.match(r"^\s*(c\.|ca\.|circa)\b", bullet_text, flags=re.IGNORECASE))

    from strategies.list_of_years.list_of_years_span_parser import YearsParseOrchestrator
    bullet_span = YearsParseOrchestrator.parse_span_from_bullet(
        bullet_text, scope["start_year"], assume_is_bc=page_assume_is_bc
    )
    
    # Initialize all date components to None/defaults to prevent leaking from previous iterations
    effective_start_year = scope["start_year"]
    effective_start_month = None
    effective_start_day = None
    effective_end_year = scope["end_year"]
    effective_end_month = None
    effective_end_day = None
    effective_is_bc = bool(page_assume_is_bc) if page_assume_is_bc is not None else scope_is_bc
    precision = scope["precision"]
    span_match_notes = ""

    if bullet_span is not None:
        precision = bullet_span.precision
        effective_start_year = bullet_span.start_year
        effective_start_month = bullet_span.start_month
        effective_start_day = bullet_span.start_day
        effective_end_year = bullet_span.end_year
        effective_end_month = bullet_span.end_month
        effective_end_day = bullet_span.end_day
        effective_is_bc = bullet_span.is_bc
        span_match_notes = bullet_span.match_type

    category_value = tag or None

    # Compute weight from bullet_span if available, otherwise compute from effective dates
    weight = 0
    if bullet_span is not None and hasattr(bullet_span, 'weight'):
        weight = bullet_span.weight
    
    # Extract precision value
    precision_value = None
    if bullet_span is not None and hasattr(bullet_span, 'precision'):
        precision_value = bullet_span.precision

    event = {
        "title": b[:500],
        "description": b[:500],
        "url": canonical_url,
        "start_year": effective_start_year,
        "start_month": effective_start_month,
        "start_day": effective_start_day,
        "end_year": effective_end_year,
        "end_month": effective_end_month,
        "end_day": effective_end_day,
        "is_bc_start": effective_is_bc,
        "is_bc_end": effective_is_bc,
        "weight": weight,
        "precision": precision_value,
        "pageid": pageid,
        "category": category_value,
        "_debug_extraction": {
            "method": "list_of_years_events_and_trends",
            "matches": [],
            "snippet": b[:300],
            "weight_days": weight,
            "precision": precision_value,
            "events_heading": item.get("events_heading"),
            "h3_context": {"tag": tag, "month_bucket": month_bucket},
            "scope": scope,
            "bullet_span": bullet_span,
            "source_page": {"title": title, "url": canonical_url},
            "span_match_notes": span_match_notes,
        },
    }

    return event


@dataclass
class ProcessedYearPage:
    """Result of processing a single year page.
    
    Attributes:
        extracted_items: List of event items extracted from the page
        scope: Page scope dict (start_year, end_year, precision, is_bc)
        canonical_url: Canonical Wikipedia URL for the page
        pageid: Wikipedia page ID (or None if unavailable)
        title: Page title
        page_assume_is_bc: Inferred BC/AD era from page HTML
        scope_is_bc: Whether the scope indicates BC
    """
    extracted_items: list[dict]
    scope: dict
    canonical_url: str
    pageid: int | None
    title: str
    page_assume_is_bc: bool | None
    scope_is_bc: bool


def _process_year_page(
    page: dict,
    visited_page_keys: set[tuple],
    exclusions_agg_counts: dict[str, int],
    exclusions_agg_samples: dict[str, list[dict]]
) -> ProcessedYearPage | None:
    """Process a single year page and extract event items.
    
    Args:
        page: Page info dict with title, url, scope
        visited_page_keys: Set of already-visited page keys for deduplication
        exclusions_agg_counts: Aggregate exclusion counts (updated in place)
        exclusions_agg_samples: Aggregate exclusion samples (updated in place)
        
    Returns:
        ProcessedYearPage with extracted data, or None if page should be skipped
    """
    title = page["title"]
    url = page["url"]
    scope = page["scope"]
    scope_is_bc = bool(scope.get("is_bc", False))

    log_info(
        f"Processing page: {title} ({scope['precision']} {scope['start_year']}..{scope['end_year']}{' BC' if scope_is_bc else ''})"
    )

    # Load the page HTML
    (page_pair, page_err) = _get_html(url, context=f"year_page={title}")
    if page_err:
        log_error(f"Failed to load year page {title}: {page_err}")
        return None
    html, redirected_url = page_pair
    if not html.strip():
        log_error(f"Loaded empty HTML for year page {title} (url={redirected_url})")
        return None

    # Extract title from HTML to refine scope
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

    # Recompute scope from actual page title if available
    actual_scope = _parse_scope_from_title(actual_title) if actual_title else None
    if actual_scope is not None:
        if actual_scope != page["scope"]:
            log_info(
                f"Recomputed page scope from HTML title: discovered={page['scope']} actual_title={actual_title!r} actual_scope={actual_scope}"
            )
        scope = actual_scope
        scope_is_bc = bool(scope.get("is_bc", False))

    # Resolve page identity and check for duplicates
    identity = _resolve_page_identity(redirected_url)
    canonical_url = identity["canonical_url"] if identity else _canonicalize_wikipedia_url(redirected_url)
    pageid = identity["pageid"] if identity else None

    visited_key = ("pageid", pageid) if pageid is not None else ("url", canonical_url)
    if visited_key in visited_page_keys:
        log_info(f"Skipping duplicate page: {canonical_url}")
        return None
    visited_page_keys.add(visited_key)

    # Extract events from the page
    extracted_items, extraction_report = _extract_events_section_items_with_report(html)
    if not extracted_items:
        log_info("No Events bullets found (skipping)")
        return None

    # Merge extraction exclusions into aggregate tracking
    _merge_exclusions(exclusions_agg_counts, exclusions_agg_samples, extraction_report)

    # Log extraction exclusions for debugging
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

    # Infer BC/AD era from page HTML
    page_assume_is_bc = _infer_page_era_from_html(html, scope_is_bc=scope_is_bc)

    return ProcessedYearPage(
        extracted_items=extracted_items,
        scope=scope,
        canonical_url=canonical_url,
        pageid=pageid,
        title=title,
        page_assume_is_bc=page_assume_is_bc,
        scope_is_bc=scope_is_bc
    )


def ingest_wikipedia_list_of_years(conn=None) -> None:
    """Main entry point for ingesting events from Wikipedia's List of years.
    
    This function orchestrates a pipeline:
    1. Discover and filter year pages based on min/max year configuration
    2. Process each page to extract event items
    3. Process each event item to build event dicts
    4. Write events to JSON artifact file for later database insertion
    
    Args:
        conn: Database connection (DEPRECATED - kept for backward compatibility, not used)
    """
    log_info("Starting Wikipedia list-of-years ingestion...")

    # Pipeline Stage 1: Discover and filter pages
    pages, exclusions_agg_counts, exclusions_agg_samples = _discover_and_filter_pages()
    if not pages:
        _write_exclusions_report(exclusions_agg_counts, exclusions_agg_samples)
        return

    # Initialize tracking state
    visited_page_keys: set[tuple] = set()
    seen_event_keys: set[tuple] = set()
    all_events: list[dict] = []
    log_info("Visited-page set initialized (count=0)")

    # Pipeline Stage 2 & 3: Process pages and events
    for page in pages:
        # Process the year page
        page_result = _process_year_page(page, visited_page_keys, exclusions_agg_counts, exclusions_agg_samples)
        if page_result is None:
            continue

        # Process each event item from this page
        for item in page_result.extracted_items:
            # Build the event dict
            event = _process_event_item(
                item,
                page_result.scope,
                page_result.scope_is_bc,
                page_result.page_assume_is_bc,
                page_result.canonical_url,
                page_result.pageid,
                page_result.title
            )
            if event is None:
                continue

            # Deduplicate events
            normalized_title = re.sub(r"\s+", " ", event["title"].strip().lower())
            event_key = (
                normalized_title,
                int(event["start_year"]),
                int(event["end_year"]),
                bool(event["is_bc_start"]),
            )
            if event_key in seen_event_keys:
                continue
            seen_event_keys.add(event_key)

            # Add to events list (category is part of the event dict)
            all_events.append(event)

    # Pipeline Stage 4: Write JSON artifact
    artifact_path = Path(LOGS_DIR) / f"events_list_of_years_{RUN_ID}.json"
    artifact_data = {
        "strategy": "list_of_years",
        "run_id": RUN_ID,
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "event_count": len(all_events),
        "metadata": {
            "pages_processed": len(visited_page_keys),
            "exclusions": exclusions_agg_counts
        },
        "events": all_events
    }
    
    try:
        artifact_path.write_text(
            json.dumps(artifact_data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )
        log_info(f"Wrote {len(all_events)} events to artifact: {artifact_path}")
    except Exception as e:
        log_error(f"Failed to write artifact file: {e}")
        raise
    
    _write_exclusions_report(exclusions_agg_counts, exclusions_agg_samples)

