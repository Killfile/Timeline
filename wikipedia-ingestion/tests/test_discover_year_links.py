"""Test the URL pattern matching for year page discovery."""

import pytest
from strategies.list_of_years.list_of_years_strategy import ListOfYearsStrategy


class TestDiscoverYearishLinks:
    """Tests for ListOfYearsStrategy._discover_yearish_links_from_list_of_years function."""

    def test_discovers_ad_prefix_format(self):
        """Should discover year pages with AD_ prefix format (e.g., /wiki/AD_100)."""
        html = '''
        <html>
            <body>
                <a href="/wiki/AD_100">AD 100</a>
                <a href="/wiki/AD_250">AD 250</a>
            </body>
        </html>
        '''
        result = ListOfYearsStrategy._discover_yearish_links_from_list_of_years(html, limit=None)
        assert len(result) == 2
        assert result[0]["title"] == "AD 100"
        assert result[0]["url"] == "https://en.wikipedia.org/wiki/AD_100"
        assert result[0]["scope"]["start_year"] == 100
        assert result[0]["scope"]["is_bc"] is False
        assert result[1]["title"] == "AD 250"

    def test_discovers_numeric_format(self):
        """Should discover year pages with simple numeric format (e.g., /wiki/504)."""
        html = '''
        <html>
            <body>
                <a href="/wiki/504">504</a>
                <a href="/wiki/600">600</a>
                <a href="/wiki/999">999</a>
            </body>
        </html>
        '''
        result = ListOfYearsStrategy._discover_yearish_links_from_list_of_years(html, limit=None)
        assert len(result) == 3
        assert result[0]["title"] == "AD 504"
        assert result[0]["url"] == "https://en.wikipedia.org/wiki/504"
        assert result[0]["scope"]["start_year"] == 504
        assert result[0]["scope"]["is_bc"] is False
        assert result[1]["title"] == "AD 600"
        assert result[2]["title"] == "AD 999"

    def test_discovers_bc_format(self):
        """Should discover BC year pages with _BC suffix (e.g., /wiki/100_BC)."""
        html = '''
        <html>
            <body>
                <a href="/wiki/10_BC">10 BC</a>
                <a href="/wiki/100_BC">100 BC</a>
            </body>
        </html>
        '''
        result = ListOfYearsStrategy._discover_yearish_links_from_list_of_years(html, limit=None)
        assert len(result) == 2
        assert result[0]["title"] == "10 BC"
        assert result[0]["url"] == "https://en.wikipedia.org/wiki/10_BC"
        assert result[0]["scope"]["is_bc"] is True
        assert result[1]["title"] == "100 BC"

    def test_mixed_formats(self):
        """Should discover all three URL formats in the same HTML."""
        html = '''
        <html>
            <body>
                <a href="/wiki/10_BC">10 BC</a>
                <a href="/wiki/AD_100">AD 100</a>
                <a href="/wiki/500">500</a>
                <a href="/wiki/AD_250">AD 250</a>
                <a href="/wiki/700">700</a>
            </body>
        </html>
        '''
        result = ListOfYearsStrategy._discover_yearish_links_from_list_of_years(html, limit=None)
        assert len(result) == 5
        years = [r["scope"]["start_year"] for r in result]
        assert 10 in years  # BC
        assert 100 in years  # AD prefix
        assert 250 in years  # AD prefix
        assert 500 in years  # numeric
        assert 700 in years  # numeric

    def test_ignores_non_year_links(self):
        """Should ignore links that don't match year patterns."""
        html = '''
        <html>
            <body>
                <a href="/wiki/Main_Page">Main Page</a>
                <a href="/wiki/500">500</a>
                <a href="/wiki/History">History</a>
                <a href="/wiki/1990s">1990s</a>
            </body>
        </html>
        '''
        result = ListOfYearsStrategy._discover_yearish_links_from_list_of_years(html, limit=None)
        assert len(result) == 1
        assert result[0]["title"] == "AD 500"

    def test_deduplicates_by_url(self):
        """Should deduplicate pages with the same URL."""
        html = '''
        <html>
            <body>
                <a href="/wiki/500">500</a>
                <a href="/wiki/500">Year 500</a>
                <a href="/wiki/AD_100">AD 100</a>
            </body>
        </html>
        '''
        result = ListOfYearsStrategy._discover_yearish_links_from_list_of_years(html, limit=None)
        assert len(result) == 2
        assert result[0]["scope"]["start_year"] == 500
        assert result[1]["scope"]["start_year"] == 100

    def test_respects_limit(self):
        """Should stop discovering after reaching the limit."""
        html = '''
        <html>
            <body>
                <a href="/wiki/500">500</a>
                <a href="/wiki/501">501</a>
                <a href="/wiki/502">502</a>
                <a href="/wiki/503">503</a>
                <a href="/wiki/504">504</a>
            </body>
        </html>
        '''
        result = ListOfYearsStrategy._discover_yearish_links_from_list_of_years(html, limit=3)
        assert len(result) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
