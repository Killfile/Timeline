import ingest_wikipedia as ingest


class _FakeConn:
    """Fake psycopg2 connection to test transaction handling.

        Mimics minimal psycopg2 connection pieces used by insert_event under
        autocommit.
    """

    def __init__(self, cursor):
        self._cursor = cursor
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self._cursor

    def rollback(self):
        self.rollbacks += 1


class _FakeCursor:
    def __init__(self):
        self.execute_calls = []
        self._fetchone_queue = []
        self._raise_first = True

    def queue_fetchone(self, value):
        self._fetchone_queue.append(value)

    def execute(self, sql, params=None):
        self.execute_calls.append((sql, params))
        # First execute call simulates a statement failure.
        if self._raise_first:
            self._raise_first = False
            raise RuntimeError("boom")

    def fetchone(self):
        return self._fetchone_queue.pop(0) if self._fetchone_queue else None

    def close(self):
        return None


def test_insert_event_rolls_back_then_allows_next_insert(monkeypatch):
    # Ensure we don't require real psycopg2 in this unit test.
    monkeypatch.setattr(ingest, "_require_psycopg2", lambda: None)

    fake_cursor = _FakeCursor()
    fake_cursor.queue_fetchone((123,))
    fake_conn = _FakeConn(fake_cursor)

    event = {
        "title": "885 BC— Zimri king of Israel assassinates",
        "description": "x",
        "start_year": 885,
        "end_year": 885,
        "is_bc_start": True,
        "is_bc_end": True,
        "url": "https://en.wikipedia.org/wiki/885_BC",
        "pageid": 1,
        "_debug_extraction": {"method": "test", "matches": [], "snippet": "x"},
    }

    # First insert fails (boom) and must rollback.
    assert ingest.insert_event(fake_conn, event, category="year") is False
    # insert_event does a defensive rollback at start plus one on error.
    assert fake_conn.rollbacks == 2

    # Second insert should succeed, proving we don't remain in a poisoned state.
    assert ingest.insert_event(fake_conn, event, category="year") is True
