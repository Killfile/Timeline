"""Unit tests for client detection utility."""

import pytest
from api.auth.client_detection import parse_user_agent, get_client_summary, ClientInfo


class TestParseUserAgent:
    """Tests for parse_user_agent function."""

    def test_chrome_browser(self) -> None:
        """Test Chrome browser detection."""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        result = parse_user_agent(ua)
        
        assert result.client_type == "browser"
        assert result.confidence > 0.8
        assert "Chrome" in result.details

    def test_safari_browser(self) -> None:
        """Test Safari browser detection."""
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
        result = parse_user_agent(ua)
        
        assert result.client_type == "browser"
        assert result.confidence > 0.8
        assert "Safari" in result.details

    def test_firefox_browser(self) -> None:
        """Test Firefox browser detection."""
        ua = "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0"
        result = parse_user_agent(ua)
        
        assert result.client_type == "browser"
        assert result.confidence > 0.8
        assert "Firefox" in result.details

    def test_edge_browser(self) -> None:
        """Test Edge browser detection."""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0"
        result = parse_user_agent(ua)
        
        assert result.client_type == "browser"
        assert result.confidence > 0.8
        assert "Edge" in result.details

    def test_opera_browser(self) -> None:
        """Test Opera browser detection."""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 OPR/106.0.0.0"
        result = parse_user_agent(ua)
        
        assert result.client_type == "browser"
        assert result.confidence > 0.7
        assert "Opera" in result.details

    def test_curl_cli(self) -> None:
        """Test curl command-line tool detection."""
        ua = "curl/8.4.0"
        result = parse_user_agent(ua)
        
        assert result.client_type == "cli"
        assert result.confidence > 0.9
        assert "curl" in result.details.lower()

    def test_wget_cli(self) -> None:
        """Test wget command-line tool detection."""
        ua = "Wget/1.21.3"
        result = parse_user_agent(ua)
        
        assert result.client_type == "cli"
        assert result.confidence > 0.9
        assert "wget" in result.details.lower()

    def test_httpie_cli(self) -> None:
        """Test HTTPie command-line tool detection."""
        ua = "HTTPie/3.2.2"
        result = parse_user_agent(ua)
        
        assert result.client_type == "cli"
        assert result.confidence > 0.9
        assert "HTTPie" in result.details

    def test_python_requests_cli(self) -> None:
        """Test Python requests library detection."""
        ua = "python-requests/2.31.0"
        result = parse_user_agent(ua)
        
        assert result.client_type == "cli"
        assert result.confidence > 0.8
        assert "python-requests" in result.details.lower()

    def test_postman_cli(self) -> None:
        """Test Postman detection."""
        ua = "PostmanRuntime/7.36.1"
        result = parse_user_agent(ua)
        
        assert result.client_type == "cli"
        assert result.confidence > 0.8
        assert "Postman" in result.details

    def test_googlebot(self) -> None:
        """Test Googlebot detection."""
        ua = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        result = parse_user_agent(ua)
        
        assert result.client_type == "bot"
        assert result.confidence > 0.9
        assert "bot" in result.details.lower()

    def test_generic_crawler(self) -> None:
        """Test generic crawler detection."""
        ua = "MyCrawler/1.0 (compatible; +http://example.com/crawler)"
        result = parse_user_agent(ua)
        
        assert result.client_type == "bot"
        assert result.confidence > 0.7
        assert "crawler" in result.details.lower()

    def test_spider_bot(self) -> None:
        """Test spider bot detection."""
        ua = "MySpider/1.0"
        result = parse_user_agent(ua)
        
        assert result.client_type == "bot"
        assert result.confidence > 0.7
        assert "spider" in result.details.lower()

    def test_unknown_user_agent(self) -> None:
        """Test unknown user agent."""
        ua = "SomeRandomClient/1.0"
        result = parse_user_agent(ua)
        
        assert result.client_type == "unknown"
        assert result.confidence < 0.5
        assert result.details == "Unknown user-agent"

    def test_empty_user_agent(self) -> None:
        """Test empty user agent string."""
        result = parse_user_agent("")
        
        assert result.client_type == "unknown"
        assert result.confidence == 0.0
        assert result.details == "No user-agent provided"

    def test_none_user_agent(self) -> None:
        """Test None user agent."""
        result = parse_user_agent(None)
        
        assert result.client_type == "unknown"
        assert result.confidence == 0.0
        assert result.details == "No user-agent provided"

    def test_case_insensitive_matching(self) -> None:
        """Test that user-agent matching is case-insensitive."""
        ua = "CURL/8.4.0"
        result = parse_user_agent(ua)
        
        assert result.client_type == "cli"
        assert "curl" in result.details.lower()


class TestGetClientSummary:
    """Tests for get_client_summary function."""

    def test_browser_summary(self) -> None:
        """Test summary for browser client."""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36"
        info = parse_user_agent(ua)
        summary = get_client_summary(info)
        
        assert summary["client_type"] == "browser"
        assert summary["confidence"] == info.confidence
        assert summary["details"] == info.details
        assert isinstance(summary, dict)

    def test_cli_summary(self) -> None:
        """Test summary for CLI client."""
        ua = "curl/8.4.0"
        info = parse_user_agent(ua)
        summary = get_client_summary(info)
        
        assert summary["client_type"] == "cli"
        assert summary["confidence"] == info.confidence
        assert summary["details"] == info.details

    def test_bot_summary(self) -> None:
        """Test summary for bot client."""
        ua = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        info = parse_user_agent(ua)
        summary = get_client_summary(info)
        
        assert summary["client_type"] == "bot"
        assert summary["confidence"] == info.confidence
        assert summary["details"] == info.details

    def test_unknown_summary(self) -> None:
        """Test summary for unknown client."""
        ua = "SomeRandomClient/1.0"
        info = parse_user_agent(ua)
        summary = get_client_summary(info)
        
        assert summary["client_type"] == "unknown"
        assert summary["confidence"] < 0.5
        assert summary["details"] == "Unknown user-agent"
