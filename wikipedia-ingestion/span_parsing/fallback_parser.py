from span_parsing.span import Span
from span_parsing.strategy import SpanParserStrategy

class FallbackSpanParser(SpanParserStrategy):
    """Fallback parser that returns a default span when no other parser matches.
    
    This parser creates a span with the page year and era context.
    """
    
    def parse(self, text: str, page_year: int, page_bc: bool) -> Span | None:
        """Return a default span using the page year and era context.
        
        Args:
            text: The text to parse (not used in this parser)
            page_year: The year from the Wikipedia page context
            page_bc: Whether the page context is BC/BCE
            
        Returns:
            A Span object representing the page year context
        """
        span = Span(
            start_year=page_year,
            end_year=page_year,
            start_month=1,
            start_day=1,
            end_month=12,
            end_day=31,
            is_bc=page_bc,
            precision="year",
            match_type="Fallback parser using page context"
        )
        return self._return_none_if_invalid(span)

    def compute_weight_days(self, span: Span) -> int | None:
        return 1 # Fallback span has a weight of 1 day since we are just guessing
