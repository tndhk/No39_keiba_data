"""Tests for HorseDetailScraper._fetch_pedigree_ajax method."""

from unittest.mock import Mock, patch

import pytest
import requests

from keiba.scrapers.horse_detail import HorseDetailScraper


class TestFetchPedigreeAjax:
    """HorseDetailScraper._fetch_pedigree_ajax()のテスト"""

    @pytest.fixture
    def scraper(self):
        """HorseDetailScraperインスタンスを返す"""
        return HorseDetailScraper(delay=0)

    @pytest.fixture
    def valid_ajax_response(self):
        """正常なAJAXレスポンスデータを返す"""
        return {
            "status": "OK",
            "data": "<table><tr><td>血統HTMLフラグメント</td></tr></table>",
        }

    def test_fetch_pedigree_ajax_returns_html_fragment(
        self, scraper, valid_ajax_response
    ):
        """OK時にHTMLフラグメントを返却する"""
        with patch.object(scraper.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = valid_ajax_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = scraper._fetch_pedigree_ajax("2019104251")

            assert result == "<table><tr><td>血統HTMLフラグメント</td></tr></table>"

    def test_fetch_pedigree_ajax_returns_none_on_non_ok_status(self, scraper):
        """status != OK の場合にNoneを返す"""
        with patch.object(scraper.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "status": "ERROR",
                "data": "エラーメッセージ",
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = scraper._fetch_pedigree_ajax("2019104251")

            assert result is None

    def test_fetch_pedigree_ajax_returns_none_on_missing_data(self, scraper):
        """dataキーが欠損している場合にNoneを返す"""
        with patch.object(scraper.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "status": "OK",
                # dataキーが存在しない
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = scraper._fetch_pedigree_ajax("2019104251")

            assert result is None

    def test_fetch_pedigree_ajax_returns_none_on_http_error(self, scraper):
        """HTTPErrorが発生した場合にグレースフルにNoneを返す"""
        with patch.object(scraper.session, "get") as mock_get:
            mock_get.side_effect = requests.HTTPError("404 Not Found")

            result = scraper._fetch_pedigree_ajax("2019104251")

            assert result is None

    def test_fetch_pedigree_ajax_calls_correct_url_and_params(self, scraper):
        """正しいURLとパラメータでリクエストを送信する"""
        with patch.object(scraper.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "status": "OK",
                "data": "<div>test</div>",
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            scraper._fetch_pedigree_ajax("2019104251")

            # 呼び出しが1回行われたことを確認
            mock_get.assert_called_once()

            # 呼び出し引数を取得
            call_args = mock_get.call_args

            # URLが正しいことを確認（新エンドポイント）
            expected_url = "https://db.netkeiba.com/horse/ajax_horse_pedigree.html"
            assert call_args[0][0] == expected_url

            # パラメータが正しいことを確認（新パラメータ形式）
            assert "params" in call_args[1]
            assert call_args[1]["params"] == {
                "input": "UTF-8",
                "output": "json",
                "id": "2019104251",
            }

            # User-Agentヘッダーが設定されていることを確認
            assert "headers" in call_args[1]
            assert "User-Agent" in call_args[1]["headers"]

    def test_fetch_pedigree_ajax_returns_none_on_json_decode_error(self, scraper):
        """JSONデコードエラーが発生した場合にNoneを返す"""
        with patch.object(scraper.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = scraper._fetch_pedigree_ajax("2019104251")

            assert result is None

    def test_fetch_pedigree_ajax_applies_delay(self, scraper):
        """リクエスト時にdelayを適用する"""
        with patch.object(scraper, "_apply_delay") as mock_apply_delay:
            with patch.object(scraper.session, "get") as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "status": "OK",
                    "data": "<div>test</div>",
                }
                mock_response.raise_for_status = Mock()
                mock_get.return_value = mock_response

                scraper._fetch_pedigree_ajax("2019104251")

                # _apply_delayが呼び出されたことを確認
                mock_apply_delay.assert_called_once()

    def test_fetch_pedigree_ajax_updates_last_request_time(self, scraper):
        """リクエスト後に_last_request_timeを更新する"""
        with patch.object(scraper.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "status": "OK",
                "data": "<div>test</div>",
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # 初期状態を確認
            assert scraper._last_request_time is None

            scraper._fetch_pedigree_ajax("2019104251")

            # _last_request_timeが更新されたことを確認
            assert scraper._last_request_time is not None
            assert isinstance(scraper._last_request_time, float)

    def test_fetch_pedigree_ajax_timeout_parameter(self, scraper):
        """リクエストにtimeoutパラメータが設定されている"""
        with patch.object(scraper.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "status": "OK",
                "data": "<div>test</div>",
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            scraper._fetch_pedigree_ajax("2019104251")

            # timeoutが設定されていることを確認
            call_kwargs = mock_get.call_args[1]
            assert "timeout" in call_kwargs
            assert call_kwargs["timeout"] == 10


# =============================================================================
# Task #3: fetch_horse_detail 統合テスト（AJAX対応）
# =============================================================================


@pytest.fixture
def horse_detail_html_without_blood_table():
    """blood_tableがないHTMLフィクスチャ（AJAX血統取得が必要）"""
    return """
    <html><body>
        <div class="horse_title">
            <h1 class="horse_title">ドウデュース</h1>
            <p class="txt_01">牡5</p>
        </div>
        <table class="db_prof_table">
            <tr>
                <th>生年月日</th>
                <td>2019年3月7日</td>
            </tr>
            <tr>
                <th>調教師</th>
                <td><a href="/trainer/01088/">友道康夫</a></td>
            </tr>
        </table>
        <table class="db_h_race_results">
            <tbody>
                <tr><td>1</td></tr>
                <tr><td>2</td></tr>
                <tr><td>1</td></tr>
            </tbody>
        </table>
    </body></html>
    """


@pytest.fixture
def horse_detail_html_with_blood_table():
    """blood_tableがある通常のHTMLフィクスチャ"""
    from pathlib import Path

    fixture_path = Path(__file__).parent.parent / "fixtures" / "horse_detail.html"
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def ajax_pedigree_html_fragment():
    """AJAX血統APIが返すHTMLフラグメント"""
    return """
    <table class="blood_table">
        <tr>
            <td><a>ハーツクライ</a></td>
        </tr>
        <tr><td></td></tr>
        <tr>
            <td><a>ダストアンドダイヤモンズ</a></td>
            <td><a>Vindication</a></td>
        </tr>
    </table>
    """


class TestFetchHorseDetailAjaxIntegration:
    """fetch_horse_detail()のAJAX血統取得統合テスト（Task #3）"""

    @patch.object(HorseDetailScraper, "fetch")
    @patch.object(HorseDetailScraper, "_fetch_pedigree_ajax")
    def test_fetch_horse_detail_uses_ajax_when_blood_table_missing(
        self,
        mock_fetch_pedigree_ajax,
        mock_fetch,
        horse_detail_html_without_blood_table,
        ajax_pedigree_html_fragment,
    ):
        """blood_tableなしHTML → AJAX呼出 → sire/dam/dam_sire取得"""
        # Arrange
        scraper = HorseDetailScraper(delay=0)
        mock_fetch.return_value = horse_detail_html_without_blood_table
        mock_fetch_pedigree_ajax.return_value = ajax_pedigree_html_fragment

        # Act
        result = scraper.fetch_horse_detail(horse_id="2019104251")

        # Assert - AJAXが呼び出された
        mock_fetch_pedigree_ajax.assert_called_once_with("2019104251")

        # Assert - AJAX結果が反映されている
        assert result["sire"] == "ハーツクライ"
        assert result["dam"] == "ダストアンドダイヤモンズ"
        assert result["dam_sire"] == "Vindication"

        # Assert - 基本情報も正常に取得されている
        assert result["name"] == "ドウデュース"
        assert result["sex"] == "牡"

    @patch.object(HorseDetailScraper, "fetch")
    @patch.object(HorseDetailScraper, "_fetch_pedigree_ajax")
    def test_fetch_horse_detail_skips_ajax_when_blood_table_present(
        self, mock_fetch_pedigree_ajax, mock_fetch, horse_detail_html_with_blood_table
    ):
        """静的blood_tableあり → AJAXスキップ"""
        # Arrange
        scraper = HorseDetailScraper(delay=0)
        mock_fetch.return_value = horse_detail_html_with_blood_table

        # Act
        result = scraper.fetch_horse_detail(horse_id="2019104251")

        # Assert - AJAXは呼び出されない
        mock_fetch_pedigree_ajax.assert_not_called()

        # Assert - 静的HTMLから血統情報が取得されている
        assert result["sire"] == "ハーツクライ"
        assert result["dam"] == "ダストアンドダイヤモンズ"
        assert result["dam_sire"] == "Vindication"

    @patch.object(HorseDetailScraper, "fetch")
    @patch.object(HorseDetailScraper, "_fetch_pedigree_ajax")
    def test_fetch_horse_detail_adds_warning_on_ajax_failure(
        self, mock_fetch_pedigree_ajax, mock_fetch, horse_detail_html_without_blood_table
    ):
        """AJAX失敗 → parse_warningsに警告追加"""
        # Arrange
        scraper = HorseDetailScraper(delay=0)
        mock_fetch.return_value = horse_detail_html_without_blood_table
        mock_fetch_pedigree_ajax.return_value = None  # AJAX失敗

        # Act
        result = scraper.fetch_horse_detail(horse_id="2019104251")

        # Assert - AJAXは呼び出された
        mock_fetch_pedigree_ajax.assert_called_once_with("2019104251")

        # Assert - 警告が追加されている
        assert "parse_warnings" in result
        assert any(
            "ajax" in warning.lower() or "pedigree" in warning.lower()
            for warning in result["parse_warnings"]
        )

        # Assert - 血統情報は取得できていない（警告のみ）
        # 既存のwarning（blood_table not found）は含まれている
        assert "blood_table not found" in result["parse_warnings"]

    @patch.object(HorseDetailScraper, "fetch")
    @patch.object(HorseDetailScraper, "_fetch_pedigree_ajax")
    def test_fetch_horse_detail_returns_profile_on_ajax_failure(
        self, mock_fetch_pedigree_ajax, mock_fetch, horse_detail_html_without_blood_table
    ):
        """AJAX失敗でもprofile/careerは正常返却"""
        # Arrange
        scraper = HorseDetailScraper(delay=0)
        mock_fetch.return_value = horse_detail_html_without_blood_table
        mock_fetch_pedigree_ajax.return_value = None  # AJAX失敗

        # Act
        result = scraper.fetch_horse_detail(horse_id="2019104251")

        # Assert - プロフィール情報は取得できている
        assert result["id"] == "2019104251"
        assert result["name"] == "ドウデュース"
        assert result["sex"] == "牡"
        assert result["birth_year"] == 2019
        assert result["trainer_id"] == "01088"

        # Assert - キャリア情報も取得できている
        assert result["total_races"] == 3
        assert result["total_wins"] == 2


# =============================================================================
# Task #3: 新AJAX APIエンドポイントテスト
# =============================================================================


class TestFetchPedigreeAjaxNewEndpoint:
    """新AJAXエンドポイントのURL・パラメータ確認テスト"""

    @pytest.fixture
    def scraper(self):
        """HorseDetailScraperインスタンスを返す"""
        return HorseDetailScraper(delay=0)

    def test_fetch_pedigree_ajax_uses_new_endpoint(self, scraper):
        """新エンドポイントURLを使用する"""
        with patch.object(scraper.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "status": "OK",
                "data": "<div>test</div>",
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            scraper._fetch_pedigree_ajax("2019104251")

            call_args = mock_get.call_args
            expected_url = "https://db.netkeiba.com/horse/ajax_horse_pedigree.html"
            assert call_args[0][0] == expected_url

    def test_fetch_pedigree_ajax_sends_new_params(self, scraper):
        """新パラメータ形式 (input, output, id) を送信する"""
        with patch.object(scraper.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "status": "OK",
                "data": "<div>test</div>",
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            scraper._fetch_pedigree_ajax("2019104251")

            call_args = mock_get.call_args
            assert "params" in call_args[1]
            assert call_args[1]["params"] == {
                "input": "UTF-8",
                "output": "json",
                "id": "2019104251",
            }


# =============================================================================
# Task #3: 新HTML構造 + AJAX 統合テスト
# =============================================================================


@pytest.fixture
def new_html_without_blood_table():
    """新HTML構造のフィクスチャ（classなしh1、年齢なしtxt_01）"""
    from pathlib import Path

    fixture_path = Path(__file__).parent.parent / "fixtures" / "horse_detail_new.html"
    return fixture_path.read_text(encoding="utf-8")


class TestFetchHorseDetailNewHtmlIntegration:
    """新HTML構造 + AJAX血統取得の統合テスト"""

    @patch.object(HorseDetailScraper, "fetch")
    @patch.object(HorseDetailScraper, "_fetch_pedigree_ajax")
    def test_new_html_triggers_ajax_and_returns_full_data(
        self,
        mock_fetch_pedigree_ajax,
        mock_fetch,
        new_html_without_blood_table,
        ajax_pedigree_html_fragment,
    ):
        """新HTML構造 + AJAX成功 = プロフィール + 血統の全データ返却"""
        # Arrange
        scraper = HorseDetailScraper(delay=0)
        mock_fetch.return_value = new_html_without_blood_table
        mock_fetch_pedigree_ajax.return_value = ajax_pedigree_html_fragment

        # Act
        result = scraper.fetch_horse_detail(horse_id="2021999999")

        # Assert - AJAXが呼び出された
        mock_fetch_pedigree_ajax.assert_called_once_with("2021999999")

        # Assert - 新HTML構造からプロフィール取得
        assert result["name"] == "テスト馬名"
        assert result["sex"] == "牝"
        assert result["birth_year"] == 2021

        # Assert - AJAX結果から血統取得
        assert result["sire"] == "ハーツクライ"
        assert result["dam"] == "ダストアンドダイヤモンズ"
        assert result["dam_sire"] == "Vindication"

    @patch.object(HorseDetailScraper, "fetch")
    @patch.object(HorseDetailScraper, "_fetch_pedigree_ajax")
    def test_new_html_with_ajax_failure_returns_profile_only(
        self,
        mock_fetch_pedigree_ajax,
        mock_fetch,
        new_html_without_blood_table,
    ):
        """新HTML構造 + AJAX失敗 = プロフィールのみ返却 + 警告"""
        # Arrange
        scraper = HorseDetailScraper(delay=0)
        mock_fetch.return_value = new_html_without_blood_table
        mock_fetch_pedigree_ajax.return_value = None  # AJAX失敗

        # Act
        result = scraper.fetch_horse_detail(horse_id="2021999999")

        # Assert - プロフィール情報は取得できている
        assert result["name"] == "テスト馬名"
        assert result["sex"] == "牝"
        assert result["birth_year"] == 2021

        # Assert - 血統情報は取得できていない
        assert "sire" not in result
        assert "dam" not in result

        # Assert - 警告が含まれている
        assert any(
            "ajax" in w.lower() or "pedigree" in w.lower()
            for w in result["parse_warnings"]
        )
