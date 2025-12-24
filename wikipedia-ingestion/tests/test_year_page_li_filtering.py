import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ingest_wikipedia import _extract_events_and_trends_bullets


def test_extract_events_filters_category_items() -> None:
    html = """
    <html><body>
      <h2><span class=\"mw-headline\">Events and trends</span></h2>
      <ul>
        <li>Category:Foo</li>
        <li>921 BC — A transit of Venus occurs.</li>
      </ul>
      <h2><span class=\"mw-headline\">Births</span></h2>
      <ul>
        <li>Not part of events</li>
      </ul>
    </body></html>
    """

    bullets = _extract_events_and_trends_bullets(html)
    assert bullets == ["921 BC — A transit of Venus occurs."]

def test_extract_events_excludes_footer_and_categories_by_structure():
    """Non-event boilerplate often appears in page chrome (categories + footer).

    The extractor should exclude those based on DOM location, not text matching.
    """
    from ingest_wikipedia import _extract_events_section_items

    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "fixtures",
        "year_events_with_footer_and_categories.html",
    )
    with open(fixture_path, "r", encoding="utf-8") as f:
        html = f.read()

    items = _extract_events_section_items(html)
    texts = [i["text"] for i in items]

    # Only the Events list bullets should be included.
    assert "1000 BC— Early Horizon period starts in the Andes." in texts
    assert "c. 1000 BC— Iron Age starts." in texts

    # Chrome items must be excluded.
    assert "BC year stubs" not in texts
    assert "Legal & safety contacts" not in texts
