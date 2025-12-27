from span_parsing import SpanParser


def test_circa_bullet_returns_none_so_page_scope_can_apply():
    assert SpanParser.parse_span_from_bullet("c. 1000 BC— Iron Age starts.", 1000, assume_is_bc=True) is None


def test_year_only_bullet_parses_single_year_span():
    span = SpanParser.parse_span_from_bullet("1506 BC — Cecrops dies.", 1506, assume_is_bc=True)
    assert span is not None
    assert span.start_year == 1506
    assert span.end_year == 1506
    assert span.is_bc is True
