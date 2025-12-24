import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from date_extractors import HeuristicV2Extractor, RegexFirstLastExtractor


def test_v2_ignores_measurements_like_meters():
    text = "The mountain is 1,670 meters high and was first climbed in 1954."
    # NOTE: regex tokenization sees '1' and '670' and '1954'
    v2 = HeuristicV2Extractor(current_year=2025)
    res = v2.extract(text=text)
    assert res.start_year == 1954


def test_v2_allows_bc_marked_years():
    text = "The city was founded in 753 BC and became powerful by 509 BC."
    v2 = HeuristicV2Extractor(current_year=2025)
    res = v2.extract(text=text)
    assert res.start_year == 753
    assert res.is_bc_start is True


def test_v1_is_noisy_on_measurements():
    text = "The mountain is 1,670 meters high and was first climbed in 1954."
    v1 = RegexFirstLastExtractor()
    res = v1.extract(text=text)
    # v1 typically picks first token (1) as start
    assert res.start_year in {1, 1670}
