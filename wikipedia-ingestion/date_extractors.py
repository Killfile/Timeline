from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Sequence


@dataclass(frozen=True)
class ExtractionResult:
    method: str
    start_year: Optional[int]
    end_year: Optional[int]
    is_bc_start: bool
    is_bc_end: bool
    confidence: float
    matches: List[Dict[str, Any]]
    snippet: str
    notes: List[str]


class DateExtractor(Protocol):
    method: str

    def extract(self, *, text: str, snippet_len: int = 300) -> ExtractionResult:
        ...


_YEAR_TOKEN_RE = re.compile(r"(?<!\d)(\d{1,4})(?!\d)\s*(BC|BCE|AD|CE)?", re.IGNORECASE)


def _normalize_era(era: str | None) -> str:
    if not era:
        return ""
    e = era.strip().upper()
    # Normalize variants
    if e == "BCE":
        return "BC"
    if e == "CE":
        return "AD"
    return e


def _make_snippet(text: str, snippet_len: int) -> str:
    return (text or "").replace("\n", " ")[:snippet_len]


class RegexFirstLastExtractor:
    """V1 behavior (kept for comparison): pick first and last year-ish token from intro."""

    method = "v1_regex_intro_years_first_last"

    def extract(self, *, text: str, snippet_len: int = 300) -> ExtractionResult:
        years = _YEAR_TOKEN_RE.findall(text or "")
        start_year = None
        end_year = None
        is_bc_start = False
        is_bc_end = False
        notes: List[str] = []

        if years:
            s_y, s_era = years[0]
            start_year = int(s_y)
            is_bc_start = _normalize_era(s_era) == "BC"

            if len(years) > 1:
                e_y, e_era = years[-1]
                end_year = int(e_y)
                is_bc_end = _normalize_era(e_era) == "BC"

        matches = [
            {"year": int(y), "era": _normalize_era(era)} for (y, era) in years[:50]
        ]

        # Confidence is intentionally low because this method is noisy.
        confidence = 0.2 if start_year is not None else 0.0
        if len(matches) == 0:
            notes.append("no-year-tokens-found")

        return ExtractionResult(
            method=self.method,
            start_year=start_year,
            end_year=end_year,
            is_bc_start=is_bc_start,
            is_bc_end=is_bc_end,
            confidence=confidence,
            matches=matches,
            snippet=_make_snippet(text, snippet_len),
            notes=notes,
        )


class HeuristicV2Extractor:
    """V2: heuristics to avoid common false positives and prefer plausible years.

    Heuristics:
    - ignore tokens that are likely measurements: 'mm', 'cm', 'm', 'km', 'meters', 'ft', '%'
    - ignore 1-2 digit numbers unless explicitly marked BC/AD
    - prefer years in [5000 BC .. current_year+10] (loose)
    - boost years near keywords like 'in', 'born', 'died', 'founded', 'reigned', 'during'
    """

    method = "v2_heuristic_context_scored"

    _MEASUREMENT_RE = re.compile(
        r"\b(mm|cm|m|km|meter|meters|metre|metres|ft|feet|%|kg|g)\b",
        re.IGNORECASE,
    )
    _KEYWORDS = (
        "in ",
        "c. ",
        "circa ",
        "born ",
        "died ",
        "founded ",
        "established ",
        "reigned ",
        "during ",
        "from ",
        "to ",
        "between ",
    )

    def __init__(self, *, current_year: int = 2025):
        self._current_year = current_year

    def extract(self, *, text: str, snippet_len: int = 300) -> ExtractionResult:
        raw_text = text or ""
        snippet = _make_snippet(raw_text, snippet_len)

        notes: List[str] = []
        candidates: List[Dict[str, Any]] = []

        for m in _YEAR_TOKEN_RE.finditer(raw_text):
            year_str = m.group(1)
            era = _normalize_era(m.group(2))
            year = int(year_str)

            # Determine BC only if explicitly present.
            is_bc = era == "BC"

            span_start, span_end = m.span()
            window_start = max(0, span_start - 25)
            window_end = min(len(raw_text), span_end + 25)
            context_window = raw_text[window_start:window_end].lower()

            # Filter likely measurement numbers (e.g., '1,670 meters' will produce '1' and '670'
            # but the context contains 'meters')
            if self._MEASUREMENT_RE.search(context_window):
                candidates.append(
                    {
                        "year": year,
                        "era": era,
                        "kept": False,
                        "reason": "measurement-context",
                        "context": context_window,
                    }
                )
                continue

            # Filter tiny numbers unless explicitly marked.
            if year < 100 and era == "":
                candidates.append(
                    {
                        "year": year,
                        "era": era,
                        "kept": False,
                        "reason": "too-small-unmarked",
                        "context": context_window,
                    }
                )
                continue

            # Plausibility range.
            # Allow 1..(current+10) AD and 1..5000 BC.
            if (not is_bc and year > (self._current_year + 10)):
                candidates.append(
                    {
                        "year": year,
                        "era": era,
                        "kept": False,
                        "reason": "too-far-future",
                        "context": context_window,
                    }
                )
                continue
            if is_bc and year > 5000:
                candidates.append(
                    {
                        "year": year,
                        "era": era,
                        "kept": False,
                        "reason": "too-far-past",
                        "context": context_window,
                    }
                )
                continue

            # Score based on context.
            score = 1.0
            if any(k in context_window for k in self._KEYWORDS):
                score += 1.0
            # Prefer 3-4 digit years
            if year >= 1000:
                score += 0.5
            # Penalize very ancient unmarked years (e.g. '500' often appears in counts)
            if year < 500 and era == "":
                score -= 0.2

            candidates.append(
                {
                    "year": year,
                    "era": era,
                    "is_bc": is_bc,
                    "kept": True,
                    "score": score,
                    "context": context_window,
                }
            )

        kept = [c for c in candidates if c.get("kept")]
        kept_sorted = sorted(kept, key=lambda c: c.get("score", 0.0), reverse=True)

        start_year: Optional[int] = None
        end_year: Optional[int] = None
        is_bc_start = False
        is_bc_end = False
        confidence = 0.0

        if kept_sorted:
            # Primary pick
            best = kept_sorted[0]
            start_year = int(best["year"])
            is_bc_start = bool(best.get("is_bc"))
            confidence = min(1.0, 0.3 + 0.2 * float(best.get("score", 1.0)))

            # If there are multiple kept years, choose a plausible end as the max year in same era.
            same_era = [c for c in kept if bool(c.get("is_bc")) == is_bc_start]
            if len(same_era) >= 2:
                # Choose range based on sorted by numeric year.
                numeric = sorted((int(c["year"]) for c in same_era))
                end_year = numeric[-1]
                is_bc_end = is_bc_start

        if not kept_sorted:
            notes.append("no-plausible-year-candidates")

        # Trim matches for storage/logging
        matches = candidates[:50]
        return ExtractionResult(
            method=self.method,
            start_year=start_year,
            end_year=end_year,
            is_bc_start=is_bc_start,
            is_bc_end=is_bc_end,
            confidence=confidence,
            matches=matches,
            snippet=snippet,
            notes=notes,
        )


def pick_extractor_strategies(*, prefer_v2: bool = True) -> Sequence[DateExtractor]:
    """Strategy selector.

    - By default, run v2 first and fall back to v1 if v2 yields no start year.
    - If prefer_v2 is False, run v1 only (useful for comparison runs).
    """

    v1 = RegexFirstLastExtractor()
    v2 = HeuristicV2Extractor()
    return (v2, v1) if prefer_v2 else (v1,)


def choose_best_result(results: Sequence[ExtractionResult]) -> ExtractionResult:
    """Choose the best extraction result from multiple strategies."""
    if not results:
        return ExtractionResult(
            method="none",
            start_year=None,
            end_year=None,
            is_bc_start=False,
            is_bc_end=False,
            confidence=0.0,
            matches=[],
            snippet="",
            notes=["no-results"],
        )

    # Prefer any result with a start_year, then higher confidence.
    with_year = [r for r in results if r.start_year is not None]
    if with_year:
        return sorted(with_year, key=lambda r: r.confidence, reverse=True)[0]
    return results[0]
