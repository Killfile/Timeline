from pathlib import Path

from ingest_wikipedia import _extract_events_section_items


FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_extract_flat_events_and_trends_section_only():
    html = _load("year_flat_events_and_trends.html")
    items = _extract_events_section_items(html)

    assert [i["text"] for i in items] == [
        "1506 BC — Cecrops dies.",
        "c. 1504 BC — Example event.",
    ]

    assert all(i["tag"] is None for i in items)
    assert all(i["month_bucket"] is None for i in items)


def test_extract_h3_as_tag_when_not_months():
    html = _load("year_by_place_h3.html")
    items = _extract_events_section_items(html)

    assert [i["text"] for i in items] == [
        "March 15 — Caesar is assassinated.",
        "Consuls: Caesar and Antony.",
    ]

    assert items[0]["tag"] == "By place"
    assert items[0]["month_bucket"] is None

    assert items[1]["tag"] == "Rome"
    assert items[1]["month_bucket"] is None


def test_extract_h3_as_month_bucket_not_tag():
    html = _load("year_month_h3.html")
    items = _extract_events_section_items(html)

    assert [i["text"] for i in items] == [
        "January 1 — An event happens.",
        "February 2 — Another event.",
        "Something with unknown date.",
    ]

    assert items[0]["tag"] is None
    assert items[0]["month_bucket"] == "January"

    assert items[1]["tag"] is None
    assert items[1]["month_bucket"] == "January—March"

    assert items[2]["tag"] is None
    assert items[2]["month_bucket"] == "Unknown dates"
