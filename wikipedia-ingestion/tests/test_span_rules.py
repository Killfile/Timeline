from span_parsing.orchestrators.years_parse_orchestrator import YearsParseOrchestrator


def test_circa_bullet_now_parses_correctly():
    """Test that circa bullets are now parsed instead of returning None."""
    span = YearsParseOrchestrator.parse_span_from_bullet("c. 1000 BC— Iron Age starts.", 1000, assume_is_bc=True)
    assert span is not None
    assert span.start_year == 1000
    assert span.is_bc is True
    assert "circa" in span.match_type.lower()


def test_year_only_bullet_parses_single_year_span():
    span = YearsParseOrchestrator.parse_span_from_bullet("1506 BC — Cecrops dies.", 1506, assume_is_bc=True)
    assert span is not None
    assert span.start_year == 1506
    assert span.end_year == 1506
    assert span.is_bc is True
