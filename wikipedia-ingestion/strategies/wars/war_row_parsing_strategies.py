"""Strategy pattern for parsing different war table row structures."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Optional

from strategies.wars.war_event import WarEvent


class WarRowParserStrategy(ABC):
    """Abstract base class for war table row parsing strategies."""

    @abstractmethod
    def can_parse(self, cell_texts: list[str]) -> bool:
        """Determine if this strategy can parse the given row.

        Args:
            cell_texts: The text content of each cell in the row

        Returns:
            True if this strategy can handle this row structure
        """
        pass

    @abstractmethod
    def parse_row(self, cell_texts: list[str], source_url: str, source_title: str) -> Optional[WarEvent]:
        """Parse the row into a WarEvent.

        Args:
            cell_texts: The text content of each cell in the row
            source_url: Source URL for attribution
            source_title: Source page title

        Returns:
            WarEvent instance or None if parsing failed
        """
        pass

    def _parse_belligerents(self, text: str) -> list[str]:
        """Parse belligerents from text."""
        if not text:
            return []

        # Split on common separators
        separators = [r'\s+vs\.?\s+', r'\s+v\.?\s+', r'\s+versus\s+', r'\s*;\s*', r'\s*,\s*']
        for sep in separators:
            parts = re.split(sep, text, flags=re.IGNORECASE)
            if len(parts) > 1:
                return [part.strip() for part in parts if part.strip()]

        # If no separators found, treat as single belligerent
        return [text.strip()]
    
    def _clean_war_name(self, name: str) -> str:
        """Clean up war name text."""
        if not name:
            return ""

        # Remove extra whitespace
        name = re.sub(r'\s+', ' ', name.strip())

        # Remove citation markers like [1], [2], etc.
        name = re.sub(r'\[\d+\]', '', name)

        return name


class MergedDateCellsStrategy(WarRowParserStrategy):
    """Strategy for tables with merged date cells (colspan='2' for date ranges)."""

    def can_parse(self, cell_texts: list[str]) -> bool:
        """Check if first cell contains a date range (merged cells)."""
        if len(cell_texts) < 2:
            return False

        first_cell = cell_texts[0]
        # Look for explicit range patterns like "2300–2200" or "2300-2200"
        return bool(re.search(r'\d{1,4}\s*[-–]\s*\d{1,4}', first_cell))

    def parse_row(self, cell_texts: list[str], source_url: str, source_title: str) -> Optional[WarEvent]:
        """Parse row with merged date cells."""
        if len(cell_texts) < 2:
            return None

        # Parse range from first cell
        start_year, end_year = self._parse_year_range_from_text(cell_texts[0])
        if start_year is None:
            return None

        war_name = cell_texts[1] if len(cell_texts) > 1 else ""
        belligerents_start_idx = 2

        # Clean up the war name
        war_name = self._clean_war_name(war_name)

        # Extract belligerents
        belligerents = []
        if len(cell_texts) > belligerents_start_idx:
            belligerents_text = cell_texts[belligerents_start_idx]
            belligerents = self._parse_belligerents(belligerents_text)

        # Extract notes (remaining columns)
        notes = ""
        if len(cell_texts) > belligerents_start_idx + 1:
            notes = " ".join(cell_texts[belligerents_start_idx + 1:]).strip()

        return WarEvent(
            start_year=start_year,
            end_year=end_year if end_year is not None else start_year,
            title=war_name,
            belligerents=belligerents,
            notes=notes,
            source_url=source_url,
            source_title=source_title
        )

    def _parse_year_range_from_text(self, text: str) -> tuple[int | None, int | None]:
        """Parse start and end years from text that may contain a range."""
        if not text or text.lower() in ['ongoing', 'present', 'current']:
            return None, None

        # Handle BC/AD markers
        is_bc = 'bc' in text.lower()
        text = re.sub(r'\s*bc\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*ad\s*', '', text, flags=re.IGNORECASE)

        # Look for range patterns like "3400–3100" or "3400-3100"
        range_match = re.search(r'(\d{1,4})\s*[-–]\s*(\d{1,4})', text)
        if range_match:
            start_num = int(range_match.group(1))
            end_num = int(range_match.group(2))
            start_year = -start_num if is_bc else start_num
            end_year = -end_num if is_bc else end_num
            return start_year, end_year

        # Single year
        match = re.search(r'\d{3,4}', text)
        if match:
            year = int(match.group())
            year = -year if is_bc else year
            return year, year

        return None, None

    def _clean_war_name(self, name: str) -> str:
        """Clean up war name text."""
        if not name:
            return ""

        # Remove extra whitespace
        name = re.sub(r'\s+', ' ', name.strip())

        # Remove citation markers like [1], [2], etc.
        name = re.sub(r'\[\d+\]', '', name)

        return name

    def _parse_belligerents(self, text: str) -> list[str]:
        """Parse belligerents from text."""
        if not text:
            return []

        # Split on common separators
        separators = [r'\s+vs\.?\s+', r'\s+v\.?\s+', r'\s+versus\s+', r'\s*;\s*', r'\s*,\s*']
        for sep in separators:
            parts = re.split(sep, text, flags=re.IGNORECASE)
            if len(parts) > 1:
                return [part.strip() for part in parts if part.strip()]

        # If no separators found, treat as single belligerent
        return [text.strip()]


class SingleDateSeparateColumnsStrategy(WarRowParserStrategy):
    """Strategy for tables with separate columns: date | war_name | belligerents."""

    def _get_date_expression(self) -> str:
        """Return regex expression for date length (3 or 4 digits)."""
        return r'\d{3,4}'

    def can_parse(self, cell_texts: list[str]) -> bool:
        """Check if this looks like separate date columns."""
        if len(cell_texts) < 3:
            return False

        # First cell should contain a date (but not a range)
        first_cell = cell_texts[0]
        has_date = bool(re.search(self._get_date_expression(), first_cell)) and ('BC' in first_cell or 'AD' in first_cell or 'c.' in first_cell)

        # Second cell should NOT be a date (should be the war name)
        second_cell = cell_texts[1] if len(cell_texts) > 1 else ""
        second_is_date = bool(re.search(self._get_date_expression(), second_cell)) and ('BC' in second_cell or 'AD' in second_cell)
        return has_date and not second_is_date

    def parse_row(self, cell_texts: list[str], source_url: str, source_title: str) -> Optional[WarEvent]:
        """Parse row with separate date columns."""
        if len(cell_texts) < 3:
            return None

        # Parse date from first cell
        start_year = self._parse_year_from_text(cell_texts[0])
        if start_year is None:
            return None

        war_name = cell_texts[1]
        belligerents_start_idx = 2

        # Clean up the war name
        war_name = self._clean_war_name(war_name)

        # Extract belligerents
        belligerents = []
        if len(cell_texts) > belligerents_start_idx:
            belligerents_text = cell_texts[belligerents_start_idx]
            belligerents = self._parse_belligerents(belligerents_text)

        # Extract notes (remaining columns)
        notes = ""
        if len(cell_texts) > belligerents_start_idx + 1:
            notes = " ".join(cell_texts[belligerents_start_idx + 1:]).strip()

        return WarEvent(
            start_year=start_year,
            end_year=start_year,  # Same as start
            title=war_name,
            belligerents=belligerents,
            notes=notes,
            source_url=source_url,
            source_title=source_title
        )

    def _parse_year_from_text(self, text: str) -> int | None:
        """Parse a year from text, handling various formats."""
        if not text or text.lower() in ['ongoing', 'present', 'current']:
            return None

        # Extract numeric year, handling ranges and BC/AD
        text = text.strip()

        # Handle BC years
        is_bc = 'bc' in text.lower()
        text = re.sub(r'\s*bc\s*', '', text, flags=re.IGNORECASE)

        # Handle AD years
        text = re.sub(r'\s*ad\s*', '', text, flags=re.IGNORECASE)

        # Extract first number found
        match = re.search(r'\d+', text)
        if match:
            year = int(match.group())
            return -year if is_bc else year

        return None

    def _clean_war_name(self, name: str) -> str:
        """Clean up war name text."""
        if not name:
            return ""

        # Remove extra whitespace
        name = re.sub(r'\s+', ' ', name.strip())

        # Remove citation markers like [1], [2], etc.
        name = re.sub(r'\[\d+\]', '', name)

        return name

    def _parse_belligerents(self, text: str) -> list[str]:
        """Parse belligerents from text."""
        if not text:
            return []

        # Split on common separators
        separators = [r'\s+vs\.?\s+', r'\s+v\.?\s+', r'\s+versus\s+', r'\s*;\s*', r'\s*,\s*']
        for sep in separators:
            parts = re.split(sep, text, flags=re.IGNORECASE)
            if len(parts) > 1:
                return [part.strip() for part in parts if part.strip()]

        # If no separators found, treat as single belligerent
        return [text.strip()]

class TwoDigitSingleDateSeparateColumnsStrategy(SingleDateSeparateColumnsStrategy):
    """Strategy for tables with separate columns: date (2 digits) | war_name | belligerents."""

    def _get_date_expression(self) -> str:
        """Return regex expression for date length (2 digits)."""
        return r'\d{2}'

class TwoDateColumnsStrategy(WarRowParserStrategy):
    """Strategy for tables with: start_date | end_date | war_name | belligerents."""

    def can_parse(self, cell_texts: list[str]) -> bool:
        """Check if first two cells are dates."""
        if len(cell_texts) < 4:
            return False

        # First two cells should be dates
        first_is_date = self._cell_is_date(cell_texts[0])
        second_is_date = self._cell_is_date(cell_texts[1])

        return first_is_date and second_is_date

    def _get_date_expression(self) -> str:
        """Return regex expression for date length (3 or 4 digits)."""
        return r'\d{3,4}'

    def _cell_is_date(self, cell_text: str) -> bool:
        """Check if a cell contains date-like content."""
        return bool(re.search(self._get_date_expression(), cell_text)) and ('BC' in cell_text or 'AD' in cell_text or 'c.' in cell_text)

    def parse_row(self, cell_texts: list[str], source_url: str, source_title: str) -> Optional[WarEvent]:
        """Parse row with two date columns."""
        if len(cell_texts) < 4:
            return None

        # Parse start and end years
        start_year = self._parse_year_from_text(cell_texts[0])
        end_year = self._parse_year_from_text(cell_texts[1])

        if start_year is None:
            return None

        war_name = cell_texts[2] if len(cell_texts) > 2 else ""
        belligerents_start_idx = 3

        # Clean up the war name
        war_name = self._clean_war_name(war_name)

        # Extract belligerents
        belligerents = []
        if len(cell_texts) > belligerents_start_idx:
            belligerents_text = cell_texts[belligerents_start_idx]
            belligerents = self._parse_belligerents(belligerents_text)

        # Extract notes (remaining columns)
        notes = ""
        if len(cell_texts) > belligerents_start_idx + 1:
            notes = " ".join(cell_texts[belligerents_start_idx + 1:]).strip()

        return WarEvent(
            start_year=start_year,
            end_year=end_year if end_year is not None else start_year,
            title=war_name,
            belligerents=belligerents,
            notes=notes,
            source_url=source_url,
            source_title=source_title
        )

    def _parse_year_from_text(self, text: str) -> int | None:
        """Parse a year from text, handling various formats."""
        if not text or text.lower() in ['ongoing', 'present', 'current']:
            return None

        # Extract numeric year, handling ranges and BC/AD
        text = text.strip()

        # Handle BC years
        is_bc = 'bc' in text.lower()
        text = re.sub(r'\s*bc\s*', '', text, flags=re.IGNORECASE)

        # Handle AD years
        text = re.sub(r'\s*ad\s*', '', text, flags=re.IGNORECASE)

        # Extract first number found
        match = re.search(r'\d+', text)
        if match:
            year = int(match.group())
            return -year if is_bc else year

        return None

    def _clean_war_name(self, name: str) -> str:
        """Clean up war name text."""
        if not name:
            return ""

        # Remove extra whitespace
        name = re.sub(r'\s+', ' ', name.strip())

        # Remove citation markers like [1], [2], etc.
        name = re.sub(r'\[\d+\]', '', name)

        return name

    def _parse_belligerents(self, text: str) -> list[str]:
        """Parse belligerents from text."""
        if not text:
            return []

        # Split on common separators
        separators = [r'\s+vs\.?\s+', r'\s+v\.?\s+', r'\s+versus\s+', r'\s*;\s*', r'\s*,\s*']
        for sep in separators:
            parts = re.split(sep, text, flags=re.IGNORECASE)
            if len(parts) > 1:
                return [part.strip() for part in parts if part.strip()]

        # If no separators found, treat as single belligerent
        return [text.strip()]

class Post1000ADTwoDateColumnsStrategy(TwoDateColumnsStrategy):
    def _cell_is_date(self, cell_text: str) -> bool:
        """Check if a cell contains date-like content."""
        return bool(re.search(self._get_date_expression(), cell_text))

class TwoDigitTwoDateColumnsStrategy(TwoDateColumnsStrategy):
    """Strategy for tables with: start_date (2 digits) | end_date (2 digits) | war_name | belligerents."""

    def _get_date_expression(self) -> str:
        """Return regex expression for date length (2 digits)."""
        return r'\d{2}'

class OneDigitTwoDateColumnsStrategy(TwoDateColumnsStrategy):
    """Strategy for tables with: start_date (1 digit) | end_date (1 digit) | war_name | belligerents."""

    def _get_date_expression(self) -> str:
        """Return regex expression for date length (1 digit)."""
        return r'\d{1,2}' 
# Strategy for ['Late 24th century BC', 'Formation of the Akkadian Empire[25]', 'Akkad Kish (after being conquered)']
class CenturyDescriptorStrategy(WarRowParserStrategy):
    """Strategy for rows with century descriptors instead of specific years."""

    def can_parse(self, cell_texts: list[str]) -> bool:
        """Check if first cell contains a century descriptor."""
        if len(cell_texts) < 2:
            return False

        first_cell = cell_texts[0]
        # Look for patterns like "Late 24th century BC"
        return bool(re.search(r'(Early|Mid|Late)?\s*\d{1,2}(st|nd|rd|th)?\s*century\s*(BC|AD)?', first_cell, re.IGNORECASE))

    def parse_row(self, cell_texts: list[str], source_url: str, source_title: str) -> Optional[WarEvent]:
        """Parse row with century descriptor."""
        if len(cell_texts) < 2:
            return None

        # Parse century from first cell
        start_year, end_year = self._parse_century_from_text(cell_texts[0])
        if start_year is None:
            return None

        war_name = cell_texts[1] if len(cell_texts) > 1 else ""
        belligerents_start_idx = 2

        # Clean up the war name
        war_name = self._clean_war_name(war_name)

        # Extract belligerents
        belligerents = []
        if len(cell_texts) > belligerents_start_idx:
            belligerents_text = cell_texts[belligerents_start_idx]
            belligerents = self._parse_belligerents(belligerents_text)

        # Extract notes (remaining columns)
        notes = ""
        if len(cell_texts) > belligerents_start_idx + 1:
            notes = " ".join(cell_texts[belligerents_start_idx + 1:]).strip()

        return WarEvent(
            start_year=start_year,
            end_year=end_year if end_year is not None else start_year,
            title=war_name,
            belligerents=belligerents,
            notes=notes,
            source_url=source_url,
            source_title=source_title
        )

    def _parse_century_from_text(self, text: str) -> tuple[int | None, int | None]:
        """Parse start and end years from century descriptor."""
        match = re.search(r'(Early|Mid|Late)?\s*(\d{1,2})(st|nd|rd|th)?\s*century\s*(BC|AD)?', text, re.IGNORECASE)
        if not match:
            return None, None
        period = match.group(1)
        century_num = int(match.group(2))
        era = match.group(4)
        is_bc = era and era.lower() == 'bc'
        # Calculate start and end years of the century

        if is_bc:
            start_year, end_year = self._calculate_bc_century_years(century_num, period)
        else:
            start_year, end_year = self._calculate_ad_century_years(century_num, period)

        return start_year, end_year
    
    def _calculate_ad_century_years(self, century: int, period: str | None) -> tuple[int, int]:
        """Calculate AD century start and end years."""
        start_year = (century - 1) * 100 + 1
        end_year = century * 100
        if period:
            period = period.lower()
            if period == 'early':
                end_year = start_year + 33
            elif period == 'mid':
                start_year += 34
                end_year = start_year + 32
            elif period == 'late':
                start_year += 67
        return start_year, end_year
    
    def _calculate_bc_century_years(self, century: int, period: str | None) -> tuple[int, int]:
        """Calculate BC century start and end years."""

        """"
            2nd century BC:
                start_year = -200 
                end_year = -101
            1st century BC:
                start_year = -100
                end_year = -1

            Early 2nd century BC:
                start_year = -200
                end_year = -167
            Mid 2nd century BC:
                start_year = -166
                end_year = -134
            Late 2nd century BC:
                start_year = -133
                end_year = -101
        """
        start_year = -((century - 1) * 100 + 1)
        end_year = -(century * 100)
        
        if period:
            period = period.lower()
            if period == 'early':
                end_year = start_year + 33
            elif period == 'mid':
                start_year += 34
                end_year = start_year + 32
            elif period == 'late':
                start_year += 67
        return start_year, end_year
    
# Parenthetical "between" ranges like (Between 753 and 716 BC) 
class ParentheticalBetweenRangeStrategy(WarRowParserStrategy):
    """Strategy for rows with parenthetical 'between' date ranges."""

    def can_parse(self, cell_texts: list[str]) -> bool:
        """Check if first cell contains a parenthetical 'between' range."""
        if len(cell_texts) < 2:
            return False

        first_cell = cell_texts[0]
        # Look for patterns like "(Between 753 and 716 BC)"
        return bool(re.search(r'\(Between\s+\d{1,4}\s+and\s+\d{1,4}\s*(BC|AD)?\)', first_cell, re.IGNORECASE))

    def parse_row(self, cell_texts: list[str], source_url: str, source_title: str) -> Optional[WarEvent]:
        """Parse row with parenthetical 'between' range."""
        if len(cell_texts) < 2:
            return None

        # Parse range from first cell
        start_year, end_year = self._parse_between_range_from_text(cell_texts[0])
        if start_year is None:
            return None

        war_name = cell_texts[1] if len(cell_texts) > 1 else ""
        belligerents_start_idx = 2

        # Clean up the war name
        war_name = self._clean_war_name(war_name)

        # Extract belligerents
        belligerents = []
        if len(cell_texts) > belligerents_start_idx:
            belligerents_text = cell_texts[belligerents_start_idx]
            belligerents = self._parse_belligerents(belligerents_text)

        # Extract notes (remaining columns)
        notes = ""
        if len(cell_texts) > belligerents_start_idx + 1:
            notes = " ".join(cell_texts[belligerents_start_idx + 1:]).strip()

        return WarEvent(
            start_year=start_year,
            end_year=end_year if end_year is not None else start_year,
            title=war_name,
            belligerents=belligerents,
            notes=notes,
            source_url=source_url,
            source_title=source_title
        )
    
    def _parse_between_range_from_text(self, text: str) -> tuple[int | None, int | None]:
        """Parse start and end years from parenthetical 'between' range."""
        match = re.search(r'\(Between\s+(\d{1,4})\s+and\s+(\d{1,4})\s*(BC|AD)?\)', text, re.IGNORECASE)
        if not match:
            return None, None

        start_num = int(match.group(1))
        end_num = int(match.group(2))
        era = match.group(3)
        is_bc = era and era.lower() == 'bc'

        start_year = -start_num if is_bc else start_num
        end_year = -end_num if is_bc else end_num

        return start_year, end_year