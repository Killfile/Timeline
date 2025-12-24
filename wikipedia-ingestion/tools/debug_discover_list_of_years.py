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
    bc_only = os.getenv("WIKI_LIST_OF_YEARS_BC_ONLY", "").strip().lower() in {"1", "true", "yes"}
    res = ingest._get_html(ingest.LIST_OF_YEARS_URL, context="debug_list_of_years")
    if not res:
        print("Failed to fetch List_of_years")
        return
    html, _ = res

    pages = ingest._discover_yearish_links_from_list_of_years(html, limit=None)
    print(f"Discovered total yearish pages: {len(pages)}")

    bc_pages = [p for p in pages if bool(p.get('scope', {}).get('is_bc', False))]
    ad_pages = [p for p in pages if not bool(p.get('scope', {}).get('is_bc', False))]
    print(f"BC pages: {len(bc_pages)} | non-BC pages: {len(ad_pages)}")

    show = bc_pages if bc_only else pages
    for p in show[:30]:
        scope = p["scope"]
        bc = " BC" if scope.get("is_bc") else ""
        print(f"- {p['title']!r} -> {scope['precision']} {scope['start_year']}..{scope['end_year']}{bc}")


if __name__ == "__main__":
    main()
