"""Tests for wars strategy parsing corner cases."""

import pytest
from bs4 import BeautifulSoup
from pathlib import Path

from strategies.wars.wars_strategy import WarsStrategy


class TestWarsStrategyParsing:
    """Test corner cases in wars strategy table parsing."""

    def test_mari_ebla_war_parsing(self):
        """Test that single date cells are correctly distinguished from merged date cells.

        This test documents a bug fix where single dates like 'c. 2300 BC' were incorrectly
        treated as merged date cells because they contain 'BC' and digits. The old logic
        would misidentify the date cell as a merged cell, causing the war name to be
        parsed as the date and the belligerents to become the war name.

        Fixed by changing the merged date detection to only trigger on explicit range
        patterns (containing '–' or '-' between two numbers) rather than any date-like text.
        """
        # Create a mock table row with the problematic structure
        html = """
        <table>
        <tr>
            <td>c. 2300 BC</td>
            <td>Mari-Ebla War</td>
            <td>Mari Ebla Nagar Emar Kish Armi</td>
        </tr>
        </table>
        """

        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        rows = table.find_all('tr')

        # Get the cells from the first data row
        cells = rows[0].find_all(['td', 'th'])

        # Create strategy instance
        strategy = WarsStrategy(run_id='test', output_dir=Path('.'))

        # Parse the row
        war = strategy._parse_war_row(cells, "test_url", "test_title")

        # Verify correct parsing
        assert war is not None
        assert war.start_year == -2300  # BC year
        assert war.end_year == -2300
        assert war.title == "Mari-Ebla War"
        # Note: The belligerents parsing may split on spaces or other patterns
        # The exact parsing depends on the _parse_belligerents implementation
        assert len(war.belligerents) > 0

    def test_merged_date_cells_detection(self):
        """Test that actual merged date cells (with ranges) are correctly detected."""
        # Test cases that should be treated as merged date cells
        merged_cases = [
            "2300–2200 BC",
            "2300-2200 BC",
            "100–50 BC",
            "2300–2200",
        ]

        # Test cases that should NOT be treated as merged date cells
        separate_cases = [
            "c. 2300 BC",
            "2300 BC",
            "100 AD",
            "circa 2300 BC",
        ]

        strategy = WarsStrategy(run_id='test', output_dir=Path('.'))

        for case in merged_cases:
            # Should be handled by MergedDateCellsStrategy
            cell_texts = [case, "Test War", "Test Belligerents"]
            parser = strategy.parser_factory.get_parser(cell_texts)
            assert parser is not None, f"Should find parser for merged case: {case}"
            assert parser.__class__.__name__ == 'MergedDateCellsStrategy', f"Should use MergedDateCellsStrategy for: {case}"

        for case in separate_cases:
            # Should be handled by SingleDateSeparateColumnsStrategy
            cell_texts = [case, "Test War", "Test Belligerents"]
            parser = strategy.parser_factory.get_parser(cell_texts)
            assert parser is not None, f"Should find parser for separate case: {case}"
            assert parser.__class__.__name__ == 'SingleDateSeparateColumnsStrategy', f"Should use SingleDateSeparateColumnsStrategy for: {case}"