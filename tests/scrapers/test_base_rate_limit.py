"""Tests for BaseScraper rate limiting behavior."""

import time
from unittest.mock import Mock, patch

import pytest
import requests

from keiba.scrapers.base import BaseScraper


class TestBaseScraperRateLimitOnError:
    """HTTPエラー発生時のレート制限動作テスト"""

    def setup_method(self):
        """各テスト前にグローバルタイマーをリセット"""
        BaseScraper._global_last_request_time = None

    @patch("keiba.scrapers.base.requests.Session.get")
    def test_delay_applied_after_http_error(self, mock_get):
        """HTTPエラー後も_last_request_timeが更新される"""
        # HTTPエラーを発生させるモックレスポンス
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=1.0)

        # 初期状態では_last_request_timeはNone
        assert scraper._last_request_time is None

        # HTTPエラーが発生しても_last_request_timeが更新されることを確認
        with pytest.raises(requests.HTTPError):
            scraper.fetch("https://example.com/error")

        # HTTPエラー後も_last_request_timeが更新されている
        assert scraper._last_request_time is not None
        assert isinstance(scraper._last_request_time, float)


class TestBaseScraperMinimumDelay:
    """リクエスト間隔の最小delay確認テスト"""

    def setup_method(self):
        """各テスト前にグローバルタイマーをリセット"""
        BaseScraper._global_last_request_time = None

    @patch("keiba.scrapers.base.requests.Session.get")
    @patch("keiba.scrapers.base.time.sleep")
    def test_minimum_delay_between_requests(self, mock_sleep, mock_get):
        """リクエスト間隔がdelay秒以上空く"""
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=2.0)

        # 1回目のリクエスト - sleepなし
        scraper.fetch("https://example.com/page1")
        assert mock_sleep.call_count == 0

        # 直後にグローバルタイマーを少し前に設定（0.5秒前）
        BaseScraper._global_last_request_time = time.time() - 0.5

        # 2回目のリクエスト - 残り1.5秒分sleep
        scraper.fetch("https://example.com/page2")

        # sleepが呼ばれ、残り時間分待機したことを確認
        assert mock_sleep.call_count == 1
        sleep_duration = mock_sleep.call_args[0][0]
        # 約1.5秒のsleepが呼ばれる（誤差を考慮して1.4〜1.6秒）
        assert 1.4 <= sleep_duration <= 1.6


class TestBaseScraperGlobalRateLimit:
    """複数インスタンス間でのグローバルレート制限テスト"""

    def setup_method(self):
        """各テスト前にグローバルタイマーをリセット"""
        # グローバルタイマーをリセット
        BaseScraper._global_last_request_time = None

    @patch("keiba.scrapers.base.requests.Session.get")
    @patch("keiba.scrapers.base.time.sleep")
    def test_global_delay_between_different_instances(self, mock_sleep, mock_get):
        """異なるインスタンス間でもグローバルにdelay秒以上の間隔が空く"""
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # 2つの異なるスクレイパーインスタンス
        scraper1 = BaseScraper(delay=1.0)
        scraper2 = BaseScraper(delay=1.0)

        # scraper1で1回目のリクエスト - グローバルタイマーが初期化される
        scraper1.fetch("https://example.com/page1")
        assert mock_sleep.call_count == 0

        # グローバルタイマーを0.3秒前に設定（残り0.7秒必要）
        BaseScraper._global_last_request_time = time.time() - 0.3

        # scraper2で2回目のリクエスト - グローバルタイマーに基づいて待機
        scraper2.fetch("https://example.com/page2")

        # sleepが呼ばれ、残り時間分待機したことを確認
        assert mock_sleep.call_count == 1
        sleep_duration = mock_sleep.call_args[0][0]
        # 約0.7秒のsleepが呼ばれる（誤差を考慮して0.6〜0.8秒）
        assert 0.6 <= sleep_duration <= 0.8

    @patch("keiba.scrapers.base.requests.Session.get")
    def test_global_timer_updated_on_http_error(self, mock_get):
        """HTTPエラー時もグローバルタイマーが更新される"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("503 Service Unavailable")
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=1.0)

        # 初期状態ではグローバルタイマーはNone
        assert BaseScraper._global_last_request_time is None

        # HTTPエラーが発生してもグローバルタイマーが更新されることを確認
        with pytest.raises(requests.HTTPError):
            scraper.fetch("https://example.com/error")

        # HTTPエラー後もグローバルタイマーが更新されている
        assert BaseScraper._global_last_request_time is not None
        assert isinstance(BaseScraper._global_last_request_time, float)

    @patch("keiba.scrapers.base.requests.Session.get")
    @patch("keiba.scrapers.base.time.sleep")
    def test_first_request_after_global_timer_reset_has_no_delay(self, mock_sleep, mock_get):
        """グローバルタイマーリセット後の初回リクエストは遅延なし"""
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # グローバルタイマーを明示的にNoneに設定
        BaseScraper._global_last_request_time = None

        scraper = BaseScraper(delay=1.0)

        # 初回リクエスト - sleepなし
        scraper.fetch("https://example.com/page1")
        assert mock_sleep.call_count == 0
