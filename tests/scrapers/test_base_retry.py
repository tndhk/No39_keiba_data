"""Tests for BaseScraper retry and backoff behavior."""

import time
from unittest.mock import Mock, patch

import pytest
import requests

from keiba.scrapers.base import BaseScraper


class TestBaseScraperRetryBackoff:
    """HTTPエラー時のリトライとバックオフのテスト"""

    def setup_method(self):
        """各テスト前にグローバルタイマーをリセット"""
        BaseScraper._global_last_request_time = None

    @patch("keiba.scrapers.base.requests.Session.get")
    @patch("keiba.scrapers.base.time.sleep")
    def test_retry_on_503_with_exponential_backoff(self, mock_sleep, mock_get):
        """503エラー時に指数バックオフでリトライする"""
        # 最初の2回は503エラー、3回目は成功
        mock_response_503 = Mock()
        mock_response_503.raise_for_status.side_effect = requests.HTTPError("503 Service Unavailable")

        mock_response_success = Mock()
        mock_response_success.text = "<html>success</html>"
        mock_response_success.raise_for_status = Mock()

        mock_get.side_effect = [mock_response_503, mock_response_503, mock_response_success]

        scraper = BaseScraper(delay=1.0)

        # fetch()がリトライして最終的に成功する
        result = scraper.fetch("https://example.com/page1")

        # 3回リクエストが実行されたことを確認
        assert mock_get.call_count == 3
        assert result == "<html>success</html>"

        # バックオフのsleepが2回呼ばれたことを確認（1回目失敗後、2回目失敗後）
        # 注: レート制限のsleepもカウントされるため、最低2回のバックオフsleepを確認
        assert mock_sleep.call_count >= 2

        # バックオフの待機時間を確認（5秒、10秒）
        backoff_calls = [call[0][0] for call in mock_sleep.call_args_list if call[0][0] >= 4]
        assert len(backoff_calls) >= 2
        assert 4 <= backoff_calls[0] <= 6  # 1回目のバックオフ: 約5秒
        assert 9 <= backoff_calls[1] <= 11  # 2回目のバックオフ: 約10秒

    @patch("keiba.scrapers.base.requests.Session.get")
    @patch("keiba.scrapers.base.time.sleep")
    def test_retry_on_429_with_exponential_backoff(self, mock_sleep, mock_get):
        """429エラー時に指数バックオフでリトライする"""
        mock_response_429 = Mock()
        mock_response_429.raise_for_status.side_effect = requests.HTTPError("429 Too Many Requests")

        mock_response_success = Mock()
        mock_response_success.text = "<html>success</html>"
        mock_response_success.raise_for_status = Mock()

        mock_get.side_effect = [mock_response_429, mock_response_success]

        scraper = BaseScraper(delay=1.0)

        result = scraper.fetch("https://example.com/page1")

        assert mock_get.call_count == 2
        assert result == "<html>success</html>"

        # 1回目のバックオフが呼ばれたことを確認
        backoff_calls = [call[0][0] for call in mock_sleep.call_args_list if call[0][0] >= 4]
        assert len(backoff_calls) >= 1
        assert 4 <= backoff_calls[0] <= 6  # 約5秒

    @patch("keiba.scrapers.base.requests.Session.get")
    @patch("keiba.scrapers.base.time.sleep")
    def test_retry_on_403_with_exponential_backoff(self, mock_sleep, mock_get):
        """403エラー時に指数バックオフでリトライする"""
        mock_response_403 = Mock()
        mock_response_403.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")

        mock_response_success = Mock()
        mock_response_success.text = "<html>success</html>"
        mock_response_success.raise_for_status = Mock()

        mock_get.side_effect = [mock_response_403, mock_response_success]

        scraper = BaseScraper(delay=1.0)

        result = scraper.fetch("https://example.com/page1")

        assert mock_get.call_count == 2
        assert result == "<html>success</html>"

    @patch("keiba.scrapers.base.requests.Session.get")
    @patch("keiba.scrapers.base.time.sleep")
    def test_max_3_retries_then_raise(self, mock_sleep, mock_get):
        """最大3回リトライ後は例外を投げる"""
        mock_response_503 = Mock()
        mock_response_503.raise_for_status.side_effect = requests.HTTPError("503 Service Unavailable")

        # 4回すべて失敗するように設定
        mock_get.return_value = mock_response_503

        scraper = BaseScraper(delay=1.0)

        # 最大リトライ後に例外が投げられることを確認
        with pytest.raises(requests.HTTPError):
            scraper.fetch("https://example.com/page1")

        # 初回 + 3回リトライ = 合計4回リクエストが実行される
        assert mock_get.call_count == 4

    @patch("keiba.scrapers.base.requests.Session.get")
    @patch("keiba.scrapers.base.time.sleep")
    def test_no_retry_on_404(self, mock_sleep, mock_get):
        """404エラーはリトライしない"""
        mock_response_404 = Mock()
        mock_response_404.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

        mock_get.return_value = mock_response_404

        scraper = BaseScraper(delay=1.0)

        # 404エラーは即座に例外を投げる
        with pytest.raises(requests.HTTPError):
            scraper.fetch("https://example.com/page1")

        # リトライせず1回だけリクエスト
        assert mock_get.call_count == 1

    @patch("keiba.scrapers.base.requests.Session.get")
    @patch("keiba.scrapers.base.time.sleep")
    def test_no_retry_on_500(self, mock_sleep, mock_get):
        """500エラーはリトライしない"""
        mock_response_500 = Mock()
        mock_response_500.raise_for_status.side_effect = requests.HTTPError("500 Internal Server Error")

        mock_get.return_value = mock_response_500

        scraper = BaseScraper(delay=1.0)

        # 500エラーは即座に例外を投げる
        with pytest.raises(requests.HTTPError):
            scraper.fetch("https://example.com/page1")

        # リトライせず1回だけリクエスト
        assert mock_get.call_count == 1

    @patch("keiba.scrapers.base.requests.Session.get")
    @patch("keiba.scrapers.base.time.sleep")
    def test_retry_counter_resets_after_success(self, mock_sleep, mock_get):
        """成功後はリトライカウンタがリセットされる"""
        # 1回目: 503エラー後に成功
        mock_response_503 = Mock()
        mock_response_503.raise_for_status.side_effect = requests.HTTPError("503 Service Unavailable")

        mock_response_success = Mock()
        mock_response_success.text = "<html>success</html>"
        mock_response_success.raise_for_status = Mock()

        # 2回目: 再び503エラー後に成功（カウンタがリセットされていることを確認）
        mock_response_503_2 = Mock()
        mock_response_503_2.raise_for_status.side_effect = requests.HTTPError("503 Service Unavailable")

        mock_response_success_2 = Mock()
        mock_response_success_2.text = "<html>success2</html>"
        mock_response_success_2.raise_for_status = Mock()

        mock_get.side_effect = [
            mock_response_503,
            mock_response_success,
            mock_response_503_2,
            mock_response_success_2,
        ]

        scraper = BaseScraper(delay=1.0)

        # 1回目のfetch（1回失敗、2回目で成功）
        result1 = scraper.fetch("https://example.com/page1")
        assert result1 == "<html>success</html>"

        # 2回目のfetch（カウンタがリセットされているため、再び1回失敗、2回目で成功）
        result2 = scraper.fetch("https://example.com/page2")
        assert result2 == "<html>success2</html>"

        # 合計4回リクエストが実行される
        assert mock_get.call_count == 4
