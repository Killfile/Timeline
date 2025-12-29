"""Debug helper to inspect which yearish links are discovered from Wikipedia's List_of_years.

This script is intentionally lightweight and prints a small summary so we can
quickly validate discovery filtering logic (e.g., BC-only).

Run inside the ingestion container where dependencies exist.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# When running as /app/tools/..., ensure we can import /app/ingest_wikipedia.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ingest_wikipedia as ingest  # noqa: E402


def main() -> None:
    min_year_str = os.getenv("WIKI_MIN_YEAR")
    max_year_str = os.getenv("WIKI_MAX_YEAR")
    min_year = ingest._parse_year(min_year_str)
    max_year = ingest._parse_year(max_year_str)
    
    res = ingest._get_html(ingest.LIST_OF_YEARS_URL, context="debug_list_of_years")
    if not res:
        print("Failed to fetch List_of_years")
        return
    html, _ = res

    pages = ingest._discover_yearish_links_from_list_of_years(html, limit=None, min_year=min_year, max_year=max_year)
    print(f"Discovered total yearish pages: {len(pages)}")

    # Filter by min/max year if specified
    if min_year or max_year:
        filtered_pages = [
            p for p in pages
            if ingest._should_include_page(
                p.get("scope", {}).get("start_year", 0),
                p.get("scope", {}).get("is_bc", False),
                min_year,
                max_year
            )
        ]
        min_desc = f"from {min_year_str}" if min_year_str else "from earliest"
        max_desc = f"to {max_year_str}" if max_year_str else "to latest"
        print(f"After filtering ({min_desc} {max_desc}): {len(filtered_pages)} pages")
        show = filtered_pages
    else:
        print("No year range filter applied")
        show = pages

    bc_pages = [p for p in show if bool(p.get('scope', {}).get('is_bc', False))]
    ad_pages = [p for p in show if not bool(p.get('scope', {}).get('is_bc', False))]
    print(f"BC pages: {len(bc_pages)} | AD pages: {len(ad_pages)}")

    for p in show[:30]:
        scope = p["scope"]
        bc = " BC" if scope.get("is_bc") else ""
        print(f"- {p['title']!r} -> {scope['precision']} {scope['start_year']}..{scope['end_year']}{bc}")


if __name__ == "__main__":
    main()
