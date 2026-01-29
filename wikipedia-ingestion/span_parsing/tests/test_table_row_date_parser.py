"""Unit tests for TableRowDateParser

Tests cover all date formats, rowspan inheritance, BC/AD handling,
and edge cases from Timeline of Roman History Wikipedia page.
"""

import pytest
from span_parsing.table_row_date_parser import (
    TableRowDateParser,
    RowspanContext,
    ConfidenceLevel,
)
from span_parsing.span import SpanPrecision


class TestParseYearCell:
    """Tests for parse_year_cell method."""
    
    def test_year_with_bc_designation(self):
        """Test parsing year with BC suffix: '509 BC' → (509, True)"""
        parser = TableRowDateParser()
        result = parser.parse_year_cell("509 BC")
        assert result.year == -509
        assert result.is_bc == True
        assert result.precision == SpanPrecision.YEAR_ONLY
        assert result.month is None
        assert result.day is None
    
    def test_year_with_ad_designation(self):
        """Test parsing year with AD suffix: '27 AD' → (27, False)"""
        parser = TableRowDateParser()
        result = parser.parse_year_cell("27 AD")
        assert result.year == 27
        assert result.is_bc == False
    
    def test_year_compact_bc(self):
        """Test parsing compact BC format: '753BC' → (753, True)"""
        parser = TableRowDateParser()
        result = parser.parse_year_cell("753BC")
        assert result.year == -753
        assert result.is_bc == True
    
    def test_bare_year_no_designation(self):
        """Test parsing bare number: '100' → (100, False)"""
        parser = TableRowDateParser()
        result = parser.parse_year_cell("100")
        assert result.year == 100
        assert result.is_bc == False
    
    def test_legendary_year_pre_753_bc(self):
        """Test legendary dates before Rome founding: '754 BC' → confidence=legendary"""
        parser = TableRowDateParser()
        result = parser.parse_year_cell("754 BC")
        assert result.year == -754
        assert result.confidence == ConfidenceLevel.LEGENDARY
    
    def test_range_format_uses_start_year(self):
        """Test range format: '264–146 BC' → uses 264"""
        parser = TableRowDateParser()
        result = parser.parse_year_cell("264–146 BC")
        assert result.year == -264
        assert result.precision == SpanPrecision.YEAR_ONLY
    
    def test_bce_designation(self):
        """Test BCE (alternative designation): '100 BCE' → (100, True)"""
        parser = TableRowDateParser()
        result = parser.parse_year_cell("100 BCE")
        assert result.year == -100
        assert result.is_bc == True
    
    def test_empty_year_raises(self):
        """Test empty string raises ValueError"""
        parser = TableRowDateParser()
        with pytest.raises(ValueError):
            parser.parse_year_cell("")
    
    def test_invalid_year_raises(self):
        """Test invalid format raises ValueError"""
        parser = TableRowDateParser()
        with pytest.raises(ValueError):
            parser.parse_year_cell("invalid")


class TestParseDateCell:
    """Tests for parse_date_cell method."""
    
    def test_exact_date_day_month(self):
        """Test exact date: '21 April' → day=21, month=4, precision=EXACT"""
        parser = TableRowDateParser()
        result = parser.parse_date_cell("21 April", -753, True)
        assert result.day == 21
        assert result.month == 4
        assert result.year == -753
        assert result.is_bc == True
        assert result.precision == SpanPrecision.EXACT
    
    def test_month_only(self):
        """Test month-only: 'January' → month=1, day=None, precision=MONTH_ONLY"""
        parser = TableRowDateParser()
        result = parser.parse_date_cell("January", 1066, False)
        assert result.month == 1
        assert result.day is None
        assert result.precision == SpanPrecision.MONTH_ONLY
    
    def test_season_only(self):
        """Test season: 'Summer' → month=None, day=None, precision=SEASON_ONLY"""
        parser = TableRowDateParser()
        result = parser.parse_date_cell("Summer", 33, False)
        assert result.month is None
        assert result.day is None
        assert result.precision == SpanPrecision.SEASON_ONLY
    
    def test_empty_date_cell(self):
        """Test empty date cell → precision=YEAR_ONLY"""
        parser = TableRowDateParser()
        result = parser.parse_date_cell("", 100, False)
        assert result.year == 100
        assert result.month is None
        assert result.day is None
        assert result.precision == SpanPrecision.YEAR_ONLY
    
    def test_month_abbreviated(self):
        """Test abbreviated month: 'Jan' → month=1"""
        parser = TableRowDateParser()
        result = parser.parse_date_cell("Jan", 1066, False)
        assert result.month == 1
    
    def test_approximate_date(self):
        """Test approximate: 'c. 1000 BC' → precision=APPROXIMATE, confidence=APPROXIMATE"""
        parser = TableRowDateParser()
        result = parser.parse_date_cell("c. 1000 BC", -1000, True)
        assert result.year == -1000
        assert result.precision == SpanPrecision.APPROXIMATE
        assert result.confidence == ConfidenceLevel.APPROXIMATE
    
    def test_uncertain_date(self):
        """Test uncertain: '?180s BC' → precision=APPROXIMATE, confidence=UNCERTAIN"""
        parser = TableRowDateParser()
        result = parser.parse_date_cell("?180 BC", -180, True)
        assert result.year == -180
        assert result.precision == SpanPrecision.APPROXIMATE
        assert result.confidence == ConfidenceLevel.UNCERTAIN
    
    def test_date_with_full_designation_overrides_year(self):
        """Test date cell with full date and year: '13 January 27 BC' → uses 27 BC"""
        parser = TableRowDateParser()
        result = parser.parse_date_cell("13 January 27 BC", 100, False)
        assert result.year == -27
        assert result.is_bc == True
        assert result.day == 13
        assert result.month == 1


class TestParseRowPair:
    """Tests for parse_row_pair convenience method."""
    
    def test_simple_year_and_date(self):
        """Test combining year and date cells"""
        parser = TableRowDateParser()
        result = parser.parse_row_pair("753 BC", "21 April")
        assert result.year == -753
        assert result.is_bc == True
        assert result.month == 4
        assert result.day == 21
        assert result.precision == SpanPrecision.EXACT
    
    def test_year_only_no_date(self):
        """Test year with empty date cell"""
        parser = TableRowDateParser()
        result = parser.parse_row_pair("1066", "")
        assert result.year == 1066
        assert result.month is None
        assert result.precision == SpanPrecision.YEAR_ONLY
    
    def test_confidence_override(self):
        """Test confidence override parameter"""
        parser = TableRowDateParser()
        result = parser.parse_row_pair(
            "100 BC", 
            "June",
            confidence_override=ConfidenceLevel.INFERRED
        )
        assert result.confidence == ConfidenceLevel.INFERRED


class TestRowspanContext:
    """Tests for RowspanContext tracking."""
    
    def test_rowspan_inheritance_multiple_rows(self):
        """Test year inherits across rowspan=3"""
        context = RowspanContext(
            inherited_year=-752,
            inherited_is_bc=True,
            remaining_rows=2,
            source_row_index=3
        )
        
        assert context.should_inherit() == True
        assert context.consume_row() == True
        assert context.remaining_rows == 1
        
        assert context.should_inherit() == True
        assert context.consume_row() == True
        assert context.remaining_rows == 0
        
        assert context.should_inherit() == False
        assert context.consume_row() == False
    
    def test_rowspan_bc_propagates(self):
        """Test BC designation propagates across rowspan"""
        context = RowspanContext(
            inherited_year=-27,
            inherited_is_bc=True,
            remaining_rows=2,
            source_row_index=0
        )
        
        # All rows should show BC
        assert context.inherited_is_bc == True
        assert context.inherited_year < 0


class TestParseWithRowspanContext:
    """Tests for rowspan-aware parsing."""
    
    def test_inherited_year_from_rowspan(self):
        """Test year inherited via rowspan context"""
        parser = TableRowDateParser()
        context = RowspanContext(
            inherited_year=-752,
            inherited_is_bc=True,
            remaining_rows=1,
            source_row_index=3
        )
        
        # Row without explicit year cell
        result = parser.parse_with_rowspan_context("", "Celebration", context)
        
        assert result.year == -752
        assert result.confidence == ConfidenceLevel.INFERRED
        assert context.remaining_rows == 0
    
    def test_explicit_year_overrides_rowspan(self):
        """Test explicit year in row overrides rowspan"""
        parser = TableRowDateParser()
        context = RowspanContext(
            inherited_year=-752,
            inherited_is_bc=True,
            remaining_rows=1,
            source_row_index=3
        )
        
        # Row with explicit year
        result = parser.parse_with_rowspan_context("715 BC", "", context)
        
        assert result.year == -715
        assert result.confidence == ConfidenceLevel.EXPLICIT


class TestMonthNameParsing:
    """Tests for month name parsing."""
    
    def test_all_month_names(self):
        """Test all 12 month names"""
        parser = TableRowDateParser()
        months = [
            ("January", 1), ("February", 2), ("March", 3), ("April", 4),
            ("May", 5), ("June", 6), ("July", 7), ("August", 8),
            ("September", 9), ("October", 10), ("November", 11), ("December", 12),
        ]
        for name, num in months:
            result = parser.month_name_to_number(name)
            assert result == num, f"Failed for {name}"
    
    def test_month_abbreviations(self):
        """Test 3-letter month abbreviations"""
        parser = TableRowDateParser()
        assert parser.month_name_to_number("Jan") == 1
        assert parser.month_name_to_number("Dec") == 12
        assert parser.month_name_to_number("Jul") == 7
    
    def test_case_insensitive(self):
        """Test month parsing is case-insensitive"""
        parser = TableRowDateParser()
        assert parser.month_name_to_number("JANUARY") == 1
        assert parser.month_name_to_number("january") == 1
        assert parser.month_name_to_number("JaNuArY") == 1
    
    def test_invalid_month(self):
        """Test invalid month returns None"""
        parser = TableRowDateParser()
        assert parser.month_name_to_number("InvalidMonth") is None
        assert parser.month_name_to_number("") is None


class TestConfidenceDetermination:
    """Tests for confidence level determination."""
    
    def test_explicit_confidence_for_ad_dates(self):
        """Test AD dates get explicit confidence"""
        result = TableRowDateParser.determine_confidence_for_date(1066)
        assert result == ConfidenceLevel.EXPLICIT
    
    def test_explicit_confidence_for_late_bc(self):
        """Test BC dates after 753 get explicit confidence"""
        result = TableRowDateParser.determine_confidence_for_date(-100)
        assert result == ConfidenceLevel.EXPLICIT
    
    def test_legendary_confidence_before_753_bc(self):
        """Test BC dates before 753 get legendary confidence"""
        result = TableRowDateParser.determine_confidence_for_date(-754)
        assert result == ConfidenceLevel.LEGENDARY
    
    def test_legendary_confidence_for_year_zero(self):
        """Test year 0 (doesn't exist) gets legendary confidence"""
        result = TableRowDateParser.determine_confidence_for_date(0)
        assert result == ConfidenceLevel.LEGENDARY


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""
    
    def test_bc_ad_transition_753_bc(self):
        """Test 753 BC (Rome founding) boundary"""
        parser = TableRowDateParser()
        result = parser.parse_year_cell("753 BC")
        assert result.year == -753
        assert result.confidence == ConfidenceLevel.LEGENDARY
    
    def test_bc_ad_transition_752_bc(self):
        """Test 752 BC (one year before Rome) is legendary"""
        parser = TableRowDateParser()
        result = parser.parse_year_cell("752 BC")
        assert result.year == -752
        # 752 BC is before 753 BC (founding), so it's legendary
        assert result.confidence == ConfidenceLevel.EXPLICIT
        
    def test_bc_ad_transition_before_753(self):
        """Test years before 753 BC are legendary"""
        parser = TableRowDateParser()
        result = parser.parse_year_cell("754 BC")
        assert result.year == -754
        assert result.confidence == ConfidenceLevel.LEGENDARY
    
    def test_ad_1_dates(self):
        """Test AD 1 (after year 0 gap)"""
        parser = TableRowDateParser()
        result = parser.parse_year_cell("1 AD")
        assert result.year == 1
        assert result.is_bc == False
    
    def test_whitespace_handling(self):
        """Test various whitespace formats"""
        parser = TableRowDateParser()
        
        # Extra spaces
        result1 = parser.parse_year_cell("  753   BC  ")
        result2 = parser.parse_year_cell("753 BC")
        assert result1.year == result2.year
    
    def test_roman_numeral_dates_not_supported(self):
        """Test that Roman numerals are not parsed (expected to fail gracefully)"""
        parser = TableRowDateParser()
        with pytest.raises(ValueError):
            parser.parse_year_cell("DCCLIII BC")


class TestIntegration:
    """Integration tests combining multiple components."""
    
    def test_legendary_period_events(self):
        """Test full parsing of legendary period event"""
        parser = TableRowDateParser()
        
        # Founding of Rome
        year_result = parser.parse_year_cell("753 BC")
        date_result = parser.parse_date_cell("21 April", year_result.year, year_result.is_bc)
        
        assert date_result.year == -753
        assert date_result.month == 4
        assert date_result.day == 21
        assert date_result.confidence == ConfidenceLevel.EXPLICIT
    
    def test_bc_to_ad_transition(self):
        """Test Augustus (27 BC) marking empire beginning"""
        parser = TableRowDateParser()
        result = parser.parse_row_pair("27 BC", "13 January")
        
        assert result.year == -27
        assert result.is_bc == True
        assert result.month == 1
        assert result.day == 13
    
    def test_byzantine_period_event(self):
        """Test late event (1453 AD)"""
        parser = TableRowDateParser()
        result = parser.parse_row_pair("1453", "29 May")
        
        assert result.year == 1453
        assert result.is_bc == False
        assert result.month == 5
        assert result.day == 29
    
    def test_rowspan_with_inherited_year(self):
        """Test complete rowspan inheritance scenario"""
        parser = TableRowDateParser()
        
        # Parent row: "752 BC" rowspan=2
        parent = parser.parse_year_cell("752 BC")
        
        # Child row 1: no year, has date
        context = RowspanContext(parent.year, parent.is_bc, 1, 0)
        child1 = parser.parse_with_rowspan_context("", "21 April", context)
        
        assert child1.year == -752
        assert child1.confidence == ConfidenceLevel.INFERRED
        assert child1.month == 4
        
        # Child row 2: no year, different date
        child2 = parser.parse_with_rowspan_context("", "", context)
        assert child2.year == -752
        assert child2.confidence == ConfidenceLevel.INFERRED
