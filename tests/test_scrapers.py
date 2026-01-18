"""Tests for keiba.scrapers module."""

import time
from unittest.mock import Mock, patch

import pytest
from bs4 import BeautifulSoup

from keiba.scrapers.base import BaseScraper


class TestBaseScraperInit:
    """BaseScraper初期化のテスト"""

    def test_default_delay(self):
        """デフォルトのdelay値は1.0秒"""
        scraper = BaseScraper()
        assert scraper.delay == 1.0

    def test_custom_delay(self):
        """カスタムdelay値を設定できる"""
        scraper = BaseScraper(delay=2.5)
        assert scraper.delay == 2.5

    def test_last_request_time_initially_none(self):
        """初期状態では_last_request_timeはNone"""
        scraper = BaseScraper()
        assert scraper._last_request_time is None

    def test_has_default_user_agent(self):
        """DEFAULT_USER_AGENTクラス属性が存在する"""
        assert hasattr(BaseScraper, "DEFAULT_USER_AGENT")
        assert "Mozilla" in BaseScraper.DEFAULT_USER_AGENT


class TestBaseScraperFetch:
    """BaseScraper.fetch()のテスト"""

    @patch("keiba.scrapers.base.requests.get")
    def test_fetch_returns_html_text(self, mock_get):
        """fetch()はHTMLテキストを返す"""
        mock_response = Mock()
        mock_response.text = "<html><body>Test</body></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=0)
        html = scraper.fetch("https://example.com")

        assert html == "<html><body>Test</body></html>"

    @patch("keiba.scrapers.base.requests.get")
    def test_fetch_uses_user_agent(self, mock_get):
        """fetch()はUser-Agentヘッダーを設定する"""
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=0)
        scraper.fetch("https://example.com")

        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert "headers" in call_kwargs
        assert "User-Agent" in call_kwargs["headers"]
        assert call_kwargs["headers"]["User-Agent"] == BaseScraper.DEFAULT_USER_AGENT

    @patch("keiba.scrapers.base.requests.get")
    def test_fetch_updates_last_request_time(self, mock_get):
        """fetch()は_last_request_timeを更新する"""
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=0)
        assert scraper._last_request_time is None

        scraper.fetch("https://example.com")

        assert scraper._last_request_time is not None
        assert isinstance(scraper._last_request_time, float)

    @patch("keiba.scrapers.base.requests.get")
    @patch("keiba.scrapers.base.time.sleep")
    def test_fetch_applies_delay_on_second_request(self, mock_sleep, mock_get):
        """2回目のリクエストではdelayが適用される"""
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=1.0)

        # 1回目のリクエスト - sleepなし
        scraper.fetch("https://example.com/page1")
        assert mock_sleep.call_count == 0

        # _last_request_timeを直前に設定してdelayが必要な状況を作る
        scraper._last_request_time = time.time()

        # 2回目のリクエスト - sleepあり
        scraper.fetch("https://example.com/page2")
        assert mock_sleep.call_count == 1

    @patch("keiba.scrapers.base.requests.get")
    @patch("keiba.scrapers.base.time.sleep")
    def test_fetch_no_delay_if_enough_time_passed(self, mock_sleep, mock_get):
        """十分な時間が経過していればdelayは適用されない"""
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=1.0)
        # 2秒前にリクエストしたことにする
        scraper._last_request_time = time.time() - 2.0

        scraper.fetch("https://example.com")

        # 十分な時間が経過しているのでsleepは呼ばれない
        mock_sleep.assert_not_called()

    @patch("keiba.scrapers.base.requests.get")
    def test_fetch_calls_raise_for_status(self, mock_get):
        """fetch()はraise_for_status()を呼び出す"""
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=0)
        scraper.fetch("https://example.com")

        mock_response.raise_for_status.assert_called_once()


class TestBaseScraperGetSoup:
    """BaseScraper.get_soup()のテスト"""

    def test_get_soup_returns_beautifulsoup(self):
        """get_soup()はBeautifulSoupオブジェクトを返す"""
        scraper = BaseScraper()
        html = "<html><body><p>Test</p></body></html>"

        soup = scraper.get_soup(html)

        assert isinstance(soup, BeautifulSoup)

    def test_get_soup_parses_html_correctly(self):
        """get_soup()はHTMLを正しくパースする"""
        scraper = BaseScraper()
        html = "<html><body><p class='test'>Hello World</p></body></html>"

        soup = scraper.get_soup(html)

        p_tag = soup.find("p", class_="test")
        assert p_tag is not None
        assert p_tag.text == "Hello World"

    def test_get_soup_uses_lxml_parser(self):
        """get_soup()はlxmlパーサーを使用する"""
        scraper = BaseScraper()
        # lxmlは不正なHTMLも適切に処理する
        html = "<p>Unclosed paragraph"

        soup = scraper.get_soup(html)

        # lxmlパーサーは適切にパースできる
        assert soup.find("p") is not None


class TestBaseScraperParse:
    """BaseScraper.parse()のテスト"""

    def test_parse_raises_not_implemented(self):
        """parse()はNotImplementedErrorを発生させる"""
        scraper = BaseScraper()
        soup = BeautifulSoup("<html></html>", "lxml")

        with pytest.raises(NotImplementedError):
            scraper.parse(soup)


class TestBaseScraperSubclass:
    """BaseScraperのサブクラス化テスト"""

    def test_subclass_can_implement_parse(self):
        """サブクラスでparse()を実装できる"""

        class MyScraper(BaseScraper):
            def parse(self, soup: BeautifulSoup) -> dict:
                title = soup.find("title")
                return {"title": title.text if title else None}

        scraper = MyScraper()
        html = "<html><head><title>Test Page</title></head></html>"
        soup = scraper.get_soup(html)
        result = scraper.parse(soup)

        assert result == {"title": "Test Page"}
