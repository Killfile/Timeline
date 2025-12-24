import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ingest_wikipedia import _parse_span_from_bullet


def test_parse_span_from_bullet_bc_range():
    span = _parse_span_from_bullet("500 BC – 490 BC — Something happens")
    assert span is not None
    assert span["start_year"] == 490
    assert span["end_year"] == 500
    assert span["is_bc"] is True


def test_parse_span_from_bullet_ad_range():
    span = _parse_span_from_bullet("1991–1993 — Something happens")
    assert span is not None
    assert span["start_year"] == 1991
    assert span["end_year"] == 1993
    assert span["is_bc"] is False
