import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from requests.exceptions import RequestException

from ingestion_common import HttpCache


@pytest.fixture
def temp_cache_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def cache(temp_cache_dir):
    return HttpCache(temp_cache_dir)


def test_get_cache_key(cache):
    url = "https://example.com"
    key1 = cache._get_cache_key(url)
    key2 = cache._get_cache_key(url)
    assert key1 == key2
    assert isinstance(key1, str)
    assert len(key1) == 64  # SHA256 hex


def test_load_from_cache_miss(cache):
    assert cache._load_from_cache("nonexistent") is None


def test_load_from_cache_invalid(cache, temp_cache_dir):
    cache_file = temp_cache_dir / "invalid.json"
    cache_file.write_text("invalid json")
    assert cache._load_from_cache("invalid") is None


def test_load_from_cache_hit(cache, temp_cache_dir):
    data = {"text": "<html></html>", "final_url": "https://example.com/final"}
    cache_file = temp_cache_dir / "test.json"
    with cache_file.open('w') as f:
        json.dump(data, f)
    result = cache._load_from_cache("test")
    assert result == ("<html></html>", "https://example.com/final")


def test_save_to_cache(cache, temp_cache_dir):
    cache._save_to_cache("test", "<html></html>", "https://example.com/final")
    cache_file = temp_cache_dir / "test.json"
    assert cache_file.exists()
    with cache_file.open('r') as f:
        data = json.load(f)
    assert data == {"text": "<html></html>", "final_url": "https://example.com/final"}


@patch('ingestion_common.WIKI_SESSION')
@patch('ingestion_common._canonicalize_wikipedia_url')
def test_get_cache_hit(mock_canonicalize, mock_session, cache):
    # Setup cache
    cache._save_to_cache(cache._get_cache_key("https://example.com"), "<html></html>", "https://example.com/final")
    
    result, error = cache.get("https://example.com")
    assert error is None
    assert result == ("<html></html>", "https://example.com/final")
    # Should not call session
    mock_session.get.assert_not_called()


@patch('ingestion_common.WIKI_SESSION')
@patch('ingestion_common._canonicalize_wikipedia_url')
def test_get_cache_miss_success(mock_canonicalize, mock_session, cache):
    mock_canonicalize.return_value = "https://example.com/final"
    
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "text/html"}
    mock_resp.text = "<html></html>"
    mock_resp.url = "https://example.com/final"
    mock_session.get.return_value = mock_resp
    
    result, error = cache.get("https://example.com")
    assert error is None
    assert result == ("<html></html>", "https://example.com/final")
    
    # Check cache was saved
    cache_key = cache._get_cache_key("https://example.com")
    cached = cache._load_from_cache(cache_key)
    assert cached == ("<html></html>", "https://example.com/final")


@patch('ingestion_common.WIKI_SESSION')
@patch('ingestion_common._canonicalize_wikipedia_url')
def test_get_cache_miss_failure_status(mock_canonicalize, mock_session, cache):
    mock_canonicalize.return_value = "https://example.com"
    
    mock_resp = Mock()
    mock_resp.status_code = 404
    mock_resp.headers = {"Content-Type": "text/html"}
    mock_resp.text = "Not found"
    mock_resp.url = "https://example.com"
    mock_session.get.return_value = mock_resp
    
    result, error = cache.get("https://example.com")
    assert result == ("", "https://example.com")
    assert "HTTP 404" in error


@patch('ingestion_common.WIKI_SESSION')
@patch('ingestion_common._canonicalize_wikipedia_url')
def test_get_cache_miss_failure_content_type(mock_canonicalize, mock_session, cache):
    mock_canonicalize.return_value = "https://example.com"
    
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "application/json"}
    mock_resp.text = '{"error": "not html"}'
    mock_resp.url = "https://example.com"
    mock_session.get.return_value = mock_resp
    
    result, error = cache.get("https://example.com")
    assert result == ("", "https://example.com")
    assert "Unexpected content-type" in error


@patch('ingestion_common.WIKI_SESSION')
@patch('ingestion_common._canonicalize_wikipedia_url')
def test_get_cache_miss_exception(mock_canonicalize, mock_session, cache):
    mock_canonicalize.return_value = "https://example.com"
    mock_session.get.side_effect = RequestException("Network error")
    
    result, error = cache.get("https://example.com")
    assert result == ("", "https://example.com")
    assert "Request error" in error