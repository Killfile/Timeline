"""Factory for creating war row parsing strategies."""

from typing import Optional

from .war_row_parsing_strategies import (
    CenturyDescriptorStrategy,
    MergedDateCellsStrategy,
    OneDigitTwoDateColumnsStrategy,
    ParentheticalBetweenRangeStrategy,
    Post1000ADTwoDateColumnsStrategy,
    SingleDateSeparateColumnsStrategy,
    TwoDateColumnsStrategy,
    TwoDigitSingleDateSeparateColumnsStrategy,
    TwoDigitTwoDateColumnsStrategy,
    WarRowParserStrategy,
)


class WarRowParserFactory:
    """Factory for selecting the appropriate war row parsing strategy."""

    def __init__(self):
        """Initialize with available strategies."""
        self.strategies = [
            ParentheticalBetweenRangeStrategy(),
            MergedDateCellsStrategy(),
            SingleDateSeparateColumnsStrategy(),
            TwoDateColumnsStrategy(),
            CenturyDescriptorStrategy(),
            TwoDigitSingleDateSeparateColumnsStrategy(),
            TwoDigitTwoDateColumnsStrategy(),
            Post1000ADTwoDateColumnsStrategy(),
            OneDigitTwoDateColumnsStrategy(),
        ]

    def get_parser(self, cell_texts: list[str]) -> Optional[WarRowParserStrategy]:
        """Get the appropriate parser for the given row structure.

        Args:
            cell_texts: The text content of each cell in the row

        Returns:
            The strategy that can parse this row, or None if no strategy matches
        """
        for strategy in self.strategies:
            if strategy.can_parse(cell_texts):
                return strategy
        return None