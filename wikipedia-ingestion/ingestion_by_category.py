"""Legacy category-based ingestion strategy.

This strategy crawls a fixed set of Wikipedia categories using the MediaWiki API,
then extracts introductory text and tries to parse a date span from it.

The new default ingestion strategy is list-of-years, but we keep this around for
comparison and as a fallback.
"""

from __future__ import annotations

import json
import time

from .date_extractors import choose_best_result, pick_extractor_strategies
from .ingestion_common import WIKIPEDIA_API, _get_json, insert_event


def fetch_historical_events_by_category(category: str) -> list[dict]:
    """Fetch historical events from Wikipedia by category."""
    events: list[dict] = []

    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": 5000,
        "format": "json",
    }

    try:
        category_title = category.replace(" ", "_")
        params["cmtitle"] = f"Category:{category_title}"

        data = _get_json(WIKIPEDIA_API, params=params, timeout=30, context=f"category={category}")
        if not data:
            return events

        if "query" in data and "categorymembers" in data["query"]:
            for member in data["query"]["categorymembers"]:
                events.append({"title": member["title"], "pageid": member["pageid"]})

        print(f"Fetched {len(events)} events from category: {category}")

    except Exception as e:
        print(f"Error fetching category {category}: {e}", flush=True)

    return events


def extract_event_details(pageid: int) -> dict | None:
    """Extract event details including dates from a Wikipedia page."""
    params = {
        "action": "query",
        "pageids": pageid,
        "prop": "extracts|info",
        "exintro": True,
        "explaintext": True,
        "inprop": "url",
        "format": "json",
    }

    try:
        data = _get_json(WIKIPEDIA_API, params=params, timeout=30, context=f"pageid={pageid}")
        if not data:
            return None

        if "query" in data and "pages" in data["query"]:
            page = data["query"]["pages"][str(pageid)]

            extract = page.get("extract", "")
            url = page.get("fullurl", "")

            results = []
            for extractor in pick_extractor_strategies(prefer_v2=True):
                results.append(extractor.extract(text=extract or ""))
                if results[-1].start_year is not None:
                    break

            best = choose_best_result(results)

            # Observability log: structured-ish for easy grepping.
            print(
                "EXTRACTION "
                + json.dumps(
                    {
                        "pageid": pageid,
                        "url": url,
                        "selected_method": best.method,
                        "chosen_start_year": best.start_year,
                        "chosen_is_bc_start": best.is_bc_start,
                        "chosen_end_year": best.end_year,
                        "chosen_is_bc_end": best.is_bc_end,
                        "confidence": best.confidence,
                        "has_candidates": len(best.matches) > 0,
                        "snippet": best.snippet,
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )

            return {
                "description": extract[:500] if extract else None,
                "url": url,
                "start_year": best.start_year,
                "end_year": best.end_year,
                "is_bc_start": best.is_bc_start,
                "is_bc_end": best.is_bc_end,
                "_debug_extraction": {
                    "method": best.method,
                    "matches": best.matches,
                    "snippet": best.snippet,
                    "confidence": best.confidence,
                    "weight_days": (
                        None
                        if best.start_year is None
                        else (365 if best.end_year is None else max(1, abs(int(best.end_year) - int(best.start_year))) * 365)
                    ),
                    "all_results": [
                        {
                            "method": r.method,
                            "start_year": r.start_year,
                            "end_year": r.end_year,
                            "is_bc_start": r.is_bc_start,
                            "is_bc_end": r.is_bc_end,
                            "confidence": r.confidence,
                            "notes": r.notes,
                        }
                        for r in results
                    ],
                },
            }

    except Exception as e:
        print(f"Error extracting details for page {pageid}: {e}", flush=True)

    return None


def ingest_wikipedia_by_category(conn) -> None:
    """Legacy ingestion pipeline: crawl Wikipedia categories and ingest pages."""
    print("Starting Wikipedia category-based ingestion...", flush=True)

    categories = [
        "Ancient history",
        "Medieval history",
        "Modern history",
        "World War I",
        "World War II",
        "Renaissance",
        "Industrial Revolution",
        "Cold War",
        "Space exploration",
        "Scientific discoveries",
    ]

    total_inserted = 0

    for category in categories:
        print(f"\nProcessing category: {category}", flush=True)
        events = fetch_historical_events_by_category(category)

        for event in events:
            time.sleep(0.5)

            print(f"Processing: {event['title']}", flush=True)
            details = extract_event_details(event["pageid"])

            if details:
                event.update(details)
                if insert_event(conn, event, category):
                    total_inserted += 1
                    print(f"✓ Inserted: {event['title']}", flush=True)

        time.sleep(2)

    print(f"\n{'=' * 50}", flush=True)
    print(f"Ingestion complete! Total events inserted: {total_inserted}", flush=True)
    print(f"{'=' * 50}", flush=True)
