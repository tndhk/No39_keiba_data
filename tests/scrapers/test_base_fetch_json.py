"""Tests for BaseScraper.fetch_json() method."""

import json
from unittest.mock import Mock, patch

import pytest
import requests

from keiba.scrapers.base import BaseScraper


class TestBaseScraperFetchJsonReturnsParsedDict:
    """JSONレスポンスがdictで返る"""

    @patch("keiba.scrapers.base.requests.Session.get")
    def test_fetch_json_returns_parsed_dict(self, mock_get):
        """fetch_json()はJSONレスポンスをdictとして返す"""
        # モックレスポンス
        mock_response = Mock()
        mock_response.text = '{"key": "value", "number": 123}'
        mock_response.json.return_value = {"key": "value", "number": 123}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=0)
        result = scraper.fetch_json("https://example.com/api/data")

        assert isinstance(result, dict)
        assert result == {"key": "value", "number": 123}


class TestBaseScraperFetchJsonAppliesDelay:
    """_apply_delayが呼ばれる"""

    @patch("keiba.scrapers.base.requests.Session.get")
    @patch.object(BaseScraper, "_apply_delay")
    def test_fetch_json_applies_delay(self, mock_apply_delay, mock_get):
        """fetch_json()は_apply_delay()を呼び出す"""
        mock_response = Mock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=1.0)
        scraper.fetch_json("https://example.com/api/data")

        # _apply_delay()が呼ばれたことを確認
        mock_apply_delay.assert_called_once()


class TestBaseScraperFetchJsonUpdatesLastRequestTime:
    """完了後に_last_request_timeが更新される"""

    @patch("keiba.scrapers.base.requests.Session.get")
    @patch("keiba.scrapers.base.time.time", return_value=12345.678)
    def test_fetch_json_updates_last_request_time(self, mock_time, mock_get):
        """fetch_json()完了後に_last_request_timeが更新される"""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=0)

        # 初期状態では_last_request_timeはNone
        assert scraper._last_request_time is None

        scraper.fetch_json("https://example.com/api/data")

        # リクエスト完了後に_last_request_timeが更新されている
        assert scraper._last_request_time == 12345.678


class TestBaseScraperFetchJsonUpdatesLastRequestTimeOnError:
    """HTTPエラー時も更新される"""

    @patch("keiba.scrapers.base.requests.Session.get")
    @patch("keiba.scrapers.base.time.time", return_value=99999.123)
    def test_fetch_json_updates_last_request_time_on_error(self, mock_time, mock_get):
        """HTTPエラー発生時も_last_request_timeが更新される"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Internal Server Error")
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=0)

        # 初期状態では_last_request_timeはNone
        assert scraper._last_request_time is None

        # HTTPエラーが発生
        with pytest.raises(requests.HTTPError):
            scraper.fetch_json("https://example.com/api/error")

        # エラー発生後も_last_request_timeが更新されている
        assert scraper._last_request_time == 99999.123


class TestBaseScraperFetchJsonDoesNotSetEucJp:
    """EUC-JPエンコーディングを設定しない"""

    @patch("keiba.scrapers.base.requests.Session.get")
    def test_fetch_json_does_not_set_euc_jp(self, mock_get):
        """fetch_json()はnetkeiba.comでもEUC-JPエンコーディングを設定しない"""
        mock_response = Mock()
        mock_response.json.return_value = {"data": "json"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=0)
        scraper.fetch_json("https://race.netkeiba.com/api/data.json")

        # response.encodingが設定されていないことを確認
        # fetch_json()内でencoding属性への代入が行われないことをMockで検証
        # Mockは属性アクセスで自動的に属性を作るが、代入は追跡できる
        # encoding属性が呼び出し可能なMockのままであることを確認（代入されていない証拠）
        assert callable(mock_response.encoding)


class TestBaseScraperFetchJsonPassesParams:
    """paramsがクエリ文字列として渡される"""

    @patch("keiba.scrapers.base.requests.Session.get")
    def test_fetch_json_passes_params(self, mock_get):
        """fetch_json()はparamsをクエリ文字列として渡す"""
        mock_response = Mock()
        mock_response.json.return_value = {"result": "success"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=0)
        params = {"race_id": "202606010802", "type": "shutuba"}
        scraper.fetch_json("https://example.com/api/race", params=params)

        # session.get()がparamsと共に呼ばれたことを確認
        mock_get.assert_called_once()
        call_args = mock_get.call_args

        # URL確認
        assert call_args[0][0] == "https://example.com/api/race"

        # paramsがキーワード引数として渡されたことを確認
        assert call_args[1]["params"] == params


class TestBaseScraperFetchJsonRaisesOnHttpError:
    """HTTPErrorが伝播する"""

    @patch("keiba.scrapers.base.requests.Session.get")
    def test_fetch_json_raises_on_http_error(self, mock_get):
        """fetch_json()はHTTPErrorを伝播する"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=0)

        # HTTPErrorが伝播することを確認
        with pytest.raises(requests.HTTPError, match="404 Not Found"):
            scraper.fetch_json("https://example.com/api/notfound")
