"""Tests for YearRangeParser BC/BCE handling."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from span_parsing.year_range_parser import YearRangeParser
from span_parsing.span import SpanPrecision


class TestYearRangeParser:
    """Ensure BC markers on second value apply to the start year."""

    def setup_method(self):
        self.parser = YearRangeParser()

    @pytest.mark.parametrize(
        "text, expected_start, expected_end",
        [
            ("2500-1500 BCE", 2500, 1500),
            ("2500–1500 BCE", 2500, 1500),
            ("4000–2000 BCE", 4000, 2000),
        ],
    )
    def test_bc_marker_on_second_year_applies_to_start(self, text, expected_start, expected_end):
        span = self.parser.parse(text, page_year=0, page_bc=False)
        assert span is not None
        assert span.start_year == expected_start
        assert span.end_year == expected_end
        assert span.start_year_is_bc is True
        assert span.end_year_is_bc is True
        assert span.precision == SpanPrecision.YEAR_ONLY

    def test_ad_marker_keeps_bc_off_start_even_if_end_bc(self):
        span = self.parser.parse("500 AD - 400 BCE", page_year=0, page_bc=False)
        # Mixed AD→BC ranges should be rejected as invalid
        assert span is None

    def test_page_bc_context_still_sets_both_bc(self):
        span = self.parser.parse("1200-1100", page_year=0, page_bc=True)
        assert span is not None
        assert span.start_year == 1200
        assert span.end_year == 1100
        assert span.start_year_is_bc is True
        assert span.end_year_is_bc is True

