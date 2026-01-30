"""Tests for HorseDetailScraper with new HTML structure.

The new netkeiba HTML structure differs from the old in:
- h1 tag has no class attribute (was class="horse_title")
- txt_01 has no age digits (e.g. "牝 鹿毛" instead of "牡5")
- blood_table is absent (pedigree loaded via AJAX)
- db_h_race_results may be absent
"""

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from keiba.scrapers.horse_detail import HorseDetailScraper


@pytest.fixture
def scraper():
    """HorseDetailScraperインスタンスを返す"""
    return HorseDetailScraper(delay=0)


@pytest.fixture
def new_html_soup():
    """新HTML構造のBeautifulSoupオブジェクトを返す"""
    fixture_path = (
        Path(__file__).parent.parent / "fixtures" / "horse_detail_new.html"
    )
    html = fixture_path.read_text(encoding="utf-8")
    return BeautifulSoup(html, "lxml")


@pytest.fixture
def old_html_soup():
    """旧HTML構造のBeautifulSoupオブジェクトを返す（後方互換性テスト用）"""
    fixture_path = (
        Path(__file__).parent.parent / "fixtures" / "horse_detail.html"
    )
    html = fixture_path.read_text(encoding="utf-8")
    return BeautifulSoup(html, "lxml")


class TestParseNewHtmlStructure:
    """新HTML構造でのparse()テスト"""

    def test_parse_extracts_name_from_new_structure(self, scraper, new_html_soup):
        """div.horse_title > h1 (classなし) から馬名を抽出する"""
        result = scraper.parse(new_html_soup, horse_id="2021999999")

        assert result["name"] == "テスト馬名"

    def test_parse_extracts_sex_without_age_digits(self, scraper, new_html_soup):
        """'牝 鹿毛' (年齢なし形式) から性別を抽出する"""
        result = scraper.parse(new_html_soup, horse_id="2021999999")

        assert result["sex"] == "牝"

    @pytest.mark.parametrize(
        "txt_01_content,expected_sex",
        [
            ("牡5", "牡"),
            ("牝 鹿毛", "牝"),
            ("現役 牡4歳 栗毛", "牡"),
            ("引退 セ 青鹿毛", "セ"),
            ("セ5", "セ"),
            ("現役　牝3歳　黒鹿毛", "牝"),
        ],
    )
    def test_parse_extracts_sex_from_various_txt_01_formats(
        self, scraper, txt_01_content, expected_sex
    ):
        """txt_01の様々なフォーマットから性別を抽出する"""
        html = f"""
        <html><body>
            <div class="horse_title">
                <h1>TestHorse</h1>
                <p class="txt_01">{txt_01_content}</p>
            </div>
            <table class="db_prof_table">
                <tr><th>生年月日</th><td>2021年4月1日</td></tr>
            </table>
        </body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        result = scraper.parse(soup, horse_id="9999999999")
        assert result["sex"] == expected_sex

    def test_parse_returns_blood_table_warning(self, scraper, new_html_soup):
        """blood_table不在時にparse_warningsに警告を含む"""
        result = scraper.parse(new_html_soup, horse_id="2021999999")

        assert "blood_table not found" in result["parse_warnings"]

    def test_parse_career_missing_no_exception(self, scraper, new_html_soup):
        """db_h_race_results不在時に例外を投げない"""
        result = scraper.parse(new_html_soup, horse_id="2021999999")

        # 例外なく完了し、career系キーが存在しないことを確認
        assert "total_races" not in result
        assert "total_wins" not in result

    def test_parse_extracts_profile_fields(self, scraper, new_html_soup):
        """新HTML構造でもプロフィールフィールドを正常に抽出する"""
        result = scraper.parse(new_html_soup, horse_id="2021999999")

        assert result["birth_year"] == 2021
        assert result["trainer_name"] == "田中太郎(美浦)"
        assert result["trainer_id"] == "01099"
        assert result["owner_name"] == "テストオーナー"
        assert result["owner_id"] == "002345"
        assert result["breeder_name"] == "テストファーム"
        assert result["breeder_id"] == "006789"
        assert result["birthplace"] == "新冠町"
        assert result["coat_color"] == "鹿毛"
        assert result["total_earnings"] == 5678


class TestBackwardCompatibility:
    """旧HTML構造での後方互換性テスト"""

    def test_old_html_still_extracts_name(self, scraper, old_html_soup):
        """旧HTML構造 (h1 class='horse_title') でも馬名を抽出する"""
        result = scraper.parse(old_html_soup, horse_id="2019104251")

        assert result["name"] == "ドウデュース"

    def test_old_html_still_extracts_sex(self, scraper, old_html_soup):
        """旧HTML構造 ('牡5' 形式) でも性別を抽出する"""
        result = scraper.parse(old_html_soup, horse_id="2019104251")

        assert result["sex"] == "牡"

    def test_old_html_still_extracts_pedigree(self, scraper, old_html_soup):
        """旧HTML構造でも血統情報を抽出する"""
        result = scraper.parse(old_html_soup, horse_id="2019104251")

        assert result["sire"] == "ハーツクライ"
        assert result["dam"] == "ダストアンドダイヤモンズ"
        assert result["dam_sire"] == "Vindication"

    def test_old_html_still_extracts_career(self, scraper, old_html_soup):
        """旧HTML構造でもキャリア情報を抽出する"""
        result = scraper.parse(old_html_soup, horse_id="2019104251")

        assert result["total_races"] == 5
        assert result["total_wins"] == 3
