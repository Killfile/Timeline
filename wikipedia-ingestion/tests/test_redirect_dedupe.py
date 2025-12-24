import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import ingest_wikipedia as ingest


def test_canonicalize_wikipedia_url_strips_fragment() -> None:
    assert (
        ingest._canonicalize_wikipedia_url("https://en.wikipedia.org/wiki/980s_BC#Events")
        == "https://en.wikipedia.org/wiki/980s_BC"
    )


def test_redirect_alias_dedupes_when_resolved() -> None:
    """Simulate a redirect alias by checking we dedupe on canonical final URL.

    We don't hit the network in unit tests; instead we mimic what `_get_html` returns:
    a tuple of (html, canonical_url).
    """

    visited: set[tuple] = set()

    def visited_key_for(url: str) -> tuple:
        identity = ingest._resolve_page_identity(url)
        canonical_url = identity["canonical_url"] if identity else ingest._canonicalize_wikipedia_url(url)
        pageid = identity["pageid"] if identity else None
        return ("pageid", pageid) if pageid is not None else ("url", canonical_url)

    # Simulate a redirect alias by stubbing `_resolve_page_identity`.
    real = ingest._resolve_page_identity
    try:
        def stub(u: str):
            # Both 986_BC and 980s_BC resolve to the same pageid.
            if u.endswith("/wiki/986_BC") or u.endswith("/wiki/980s_BC"):
                return {"pageid": 12345, "canonical_url": "https://en.wikipedia.org/wiki/980s_BC"}
            return None

        ingest._resolve_page_identity = stub  # type: ignore[assignment]

        key1 = visited_key_for("https://en.wikipedia.org/wiki/986_BC")
        assert key1 == ("pageid", 12345)
        visited.add(key1)

        key2 = visited_key_for("https://en.wikipedia.org/wiki/980s_BC")
        assert key2 == ("pageid", 12345)
        assert key2 in visited
    finally:
        ingest._resolve_page_identity = real  # type: ignore[assignment]
