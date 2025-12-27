from pathlib import Path

from ingest_wikipedia import _infer_page_era_from_html
from span_parsing import SpanParser


FIXTURES = Path(__file__).parent / "fixtures"


def test_infer_page_era_from_html_prefers_bc_in_h1():
    html = (FIXTURES / "era_bc_headline.html").read_text(encoding="utf-8")
    assert _infer_page_era_from_html(html, scope_is_bc=None) is True


def test_infer_page_era_from_html_prefers_ad_in_h1():
    html = (FIXTURES / "era_ad_headline.html").read_text(encoding="utf-8")
    assert _infer_page_era_from_html(html, scope_is_bc=None) is False


def test_parse_span_inherits_bc_from_page_context_for_year_only():
    # Bullet contains a naked year; should follow assumed page era.
    span = SpanParser.parse_span_from_bullet("970 — Something happened", 970, assume_is_bc=True)
    assert span is not None
    assert span.start_year == 970
    assert span.end_year == 970
    assert span.is_bc is True


def test_parse_span_defaults_ad_when_no_context_for_year_only():
    span = SpanParser.parse_span_from_bullet("970 — Something happened", 970, assume_is_bc=None)
    assert span is not None
    assert span.is_bc is False


def test_parse_span_explicit_era_overrides_page_context():
    span = SpanParser.parse_span_from_bullet("970 BC — Something happened", 970, assume_is_bc=False)
    assert span is not None
    assert span.start_year == 970
    assert span.is_bc is True


def test_parse_range_inherits_bc_when_no_era_markers_present():
    span = SpanParser.parse_span_from_bullet("970–968 — Something happened", 970, assume_is_bc=True)
    assert span is not None
    assert span.start_year == 970
    assert span.end_year == 968
    assert span.is_bc is True

