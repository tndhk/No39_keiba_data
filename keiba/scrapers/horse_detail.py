"""Horse detail scraper module for netkeiba.

This module provides functionality to scrape horse details including
pedigree and career information from netkeiba's horse page.
"""

import logging
import re

from bs4 import BeautifulSoup

from keiba.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class HorseDetailScraper(BaseScraper):
    """Scraper for netkeiba horse detail pages.

    Extracts horse profile, pedigree, and career information.

    Attributes:
        BASE_URL: Base URL for netkeiba database pages.
        PEDIGREE_AJAX_URL: Base URL for AJAX pedigree requests.

    Example:
        >>> scraper = HorseDetailScraper()
        >>> data = scraper.fetch_horse_detail(horse_id="2019104251")
        >>> print(data["name"])
        ドウデュース
        >>> print(data["sire"])
        ハーツクライ
    """

    BASE_URL = "https://db.netkeiba.com"
    PEDIGREE_AJAX_URL = "https://db.netkeiba.com/horse/ajax_horse_pedigree.html"

    def parse(self, soup: BeautifulSoup, horse_id: str) -> dict:
        """Parse the horse detail page and extract all information.

        Args:
            soup: BeautifulSoup object of the horse detail page.
            horse_id: The horse ID string.

        Returns:
            Dictionary containing horse information.
        """
        result = {"id": horse_id, "parse_warnings": []}
        warnings = result["parse_warnings"]

        # 各セクションをパース
        profile = self._parse_profile(soup, warnings)
        result.update(profile)

        pedigree = self._parse_pedigree(soup, warnings)
        result.update(pedigree)

        career = self._parse_career(soup)
        result.update(career)

        return result

    def _parse_profile(self, soup: BeautifulSoup, warnings: list) -> dict:
        """Parse basic profile information from the page.

        Args:
            soup: BeautifulSoup object of the horse detail page.
            warnings: List to collect parsing warnings.

        Returns:
            Dictionary containing profile information.
        """
        profile = {}

        # 馬名を取得（h1タグ: 新旧両構造対応）
        # 新構造: div.horse_title > h1 (classなし)
        # 旧構造: h1.horse_title
        horse_title_div = soup.find("div", class_="horse_title")
        if horse_title_div:
            h1 = horse_title_div.find("h1")
        else:
            h1 = soup.find("h1", class_="horse_title")
        if h1:
            profile["name"] = h1.get_text(strip=True)
        else:
            warnings.append("horse_title not found")
            logger.warning("horse_title h1 element not found")

        # プロフィールテーブルを取得
        # db_prof_table または horse_title の後の table を探す
        prof_table = soup.find("table", class_="db_prof_table")
        if not prof_table:
            warnings.append("db_prof_table not found")
            logger.warning("db_prof_table element not found")
            return profile

        if prof_table:
            rows = prof_table.find_all("tr")
            for row in rows:
                th = row.find("th")
                td = row.find("td")
                if th and td:
                    label = th.get_text(strip=True)
                    value = td.get_text(strip=True)

                    if "生年月日" in label:
                        # 生年を抽出（例: "2019年3月7日" -> 2019）
                        match = re.search(r"(\d{4})年", value)
                        if match:
                            profile["birth_year"] = int(match.group(1))

                    elif "調教師" in label:
                        profile["trainer_name"] = value
                        # 調教師IDを抽出
                        link = td.find("a")
                        if link:
                            href = link.get("href", "")
                            id_match = re.search(
                                r"/trainer/(?:result/recent/)?([a-zA-Z0-9]+)", href
                            )
                            if id_match:
                                profile["trainer_id"] = id_match.group(1)

                    elif "馬主" in label:
                        profile["owner_name"] = value
                        # 馬主IDを抽出
                        link = td.find("a")
                        if link:
                            href = link.get("href", "")
                            id_match = re.search(
                                r"/owner/(?:result/recent/)?([a-zA-Z0-9]+)", href
                            )
                            if id_match:
                                profile["owner_id"] = id_match.group(1)

                    elif "生産者" in label:
                        profile["breeder_name"] = value
                        # 生産者IDを抽出
                        link = td.find("a")
                        if link:
                            href = link.get("href", "")
                            id_match = re.search(
                                r"/breeder/(?:result/recent/)?([a-zA-Z0-9]+)", href
                            )
                            if id_match:
                                profile["breeder_id"] = id_match.group(1)

                    elif "産地" in label:
                        profile["birthplace"] = value

                    elif "毛色" in label:
                        profile["coat_color"] = value

                    elif "性別" in label or "性齢" in label:
                        # 性別を抽出（牡、牝、セ）
                        if value:
                            profile["sex"] = value[0] if value else None

        # 馬名の横に性別・年齢がある場合もある（例: "牡5"）
        # horse_title の中の sex_age を探す
        sex_age = soup.find("p", class_="txt_01")
        if sex_age:
            text = sex_age.get_text(strip=True)
            # "牡5" や "牝4" や "牝 鹿毛" などのパターン（年齢部分は任意）
            match = re.match(r"^([牡牝セ])", text)
            if match:
                profile["sex"] = match.group(1)
        else:
            warnings.append("txt_01 not found")
            logger.warning("txt_01 element not found")

        return profile

    def _parse_pedigree(self, soup: BeautifulSoup, warnings: list) -> dict:
        """Parse pedigree (blood line) information from the page.

        Args:
            soup: BeautifulSoup object of the horse detail page.
            warnings: List to collect parsing warnings.

        Returns:
            Dictionary containing pedigree information.
        """
        pedigree = {}

        # 血統テーブルを取得
        blood_table = soup.find("table", class_="blood_table")
        if not blood_table:
            warnings.append("blood_table not found")
            logger.debug("blood_table element not found")
            return pedigree

        # 血統テーブルの構造:
        # 最初の行の最初のセル = 父
        # 2行目の最初のセル = 母
        # 父の父、父の母、母の父、母の母は rowspan で構成される

        rows = blood_table.find_all("tr")
        if len(rows) >= 2:
            # 父を取得
            first_row_cells = rows[0].find_all("td")
            if first_row_cells:
                sire_link = first_row_cells[0].find("a")
                if sire_link:
                    pedigree["sire"] = sire_link.get_text(strip=True)

            if "sire" not in pedigree:
                warnings.append("sire not found")

            # 母を取得
            second_row_cells = rows[2].find_all("td") if len(rows) > 2 else []
            if second_row_cells:
                dam_link = second_row_cells[0].find("a")
                if dam_link:
                    pedigree["dam"] = dam_link.get_text(strip=True)

            if "dam" not in pedigree:
                warnings.append("dam not found")

            # 母父を取得（母の行の2番目のセル、または3行目）
            if len(rows) > 2:
                # 母父は通常、母の行に続くセルまたは別の行にある
                for row in rows[2:4]:
                    cells = row.find_all("td")
                    for cell in cells:
                        link = cell.find("a")
                        if link:
                            text = link.get_text(strip=True)
                            # 母父は母の次に出現する名前
                            if "dam_sire" not in pedigree and text != pedigree.get(
                                "dam"
                            ):
                                pedigree["dam_sire"] = text
                                break

            if "dam_sire" not in pedigree:
                warnings.append("dam_sire not found")

        return pedigree

    def _parse_career(self, soup: BeautifulSoup) -> dict:
        """Parse career statistics from the page.

        Args:
            soup: BeautifulSoup object of the horse detail page.

        Returns:
            Dictionary containing career statistics.
        """
        career = {}

        # 成績サマリーを取得
        # "通算成績" や "x戦y勝" のようなテキストを探す
        # db_h_race_results 内の情報を探す

        # 戦績テーブルから集計
        race_table = soup.find("table", class_="db_h_race_results")
        if race_table:
            tbody = race_table.find("tbody")
            if tbody:
                rows = tbody.find_all("tr")
                career["total_races"] = len(rows)

                wins = 0
                for row in rows:
                    cells = row.find_all("td")
                    if cells:
                        # 着順は通常最初のセル
                        rank_text = cells[0].get_text(strip=True)
                        if rank_text == "1":
                            wins += 1
                career["total_wins"] = wins

        # 獲得賞金を取得
        # プロフィールテーブルや別のテーブルから探す
        prof_table = soup.find("table", class_="db_prof_table")
        if prof_table:
            for row in prof_table.find_all("tr"):
                th = row.find("th")
                td = row.find("td")
                if th and td:
                    label = th.get_text(strip=True)
                    if "獲得賞金" in label or "総賞金" in label:
                        value = td.get_text(strip=True)
                        # "1,234万円" -> 1234
                        earnings_match = re.search(r"([\d,]+)万", value)
                        if earnings_match:
                            earnings_str = earnings_match.group(1).replace(",", "")
                            career["total_earnings"] = int(earnings_str)

        return career

    def _fetch_pedigree_ajax(self, horse_id: str) -> str | None:
        """Fetch pedigree HTML fragment via AJAX request.

        Args:
            horse_id: The horse ID string.

        Returns:
            HTML fragment string containing pedigree table, or None if failed.
        """
        try:
            data = self.fetch_json(
                self.PEDIGREE_AJAX_URL,
                params={"input": "UTF-8", "output": "json", "id": horse_id},
            )
        except Exception:
            logger.warning("AJAX pedigree request failed for %s", horse_id)
            return None

        if data.get("status") != "OK":
            logger.warning("AJAX pedigree status not OK for %s", horse_id)
            return None

        html_fragment = data.get("data")
        if not html_fragment or not isinstance(html_fragment, str):
            logger.warning("AJAX pedigree data missing for %s", horse_id)
            return None

        return html_fragment

    def _build_url(self, horse_id: str) -> str:
        """Build the horse detail URL for a specific horse ID.

        Args:
            horse_id: The horse ID string (e.g., "2019104251").

        Returns:
            Full URL for the horse detail page.
        """
        return f"{self.BASE_URL}/horse/{horse_id}/"

    def fetch_horse_detail(self, horse_id: str) -> dict:
        """Fetch horse details for a specific horse ID.

        If pedigree data is not available in the initial HTML, attempts
        to fetch it via AJAX request.

        Args:
            horse_id: The horse ID string (e.g., "2019104251").

        Returns:
            Dictionary containing all horse information.
        """
        url = self._build_url(horse_id)
        html = self.fetch(url)
        soup = self.get_soup(html)
        result = self.parse(soup, horse_id=horse_id)

        # 血統データが初期HTMLにない場合、AJAXで取得
        has_pedigree = any(key in result for key in ("sire", "dam", "dam_sire"))
        if not has_pedigree:
            pedigree_html = self._fetch_pedigree_ajax(horse_id)
            if pedigree_html:
                pedigree_soup = self.get_soup(pedigree_html)
                warnings = [
                    w for w in result.get("parse_warnings", []) if "blood_table" not in w
                ]
                pedigree = self._parse_pedigree(pedigree_soup, warnings)
                result = {**result, **pedigree, "parse_warnings": warnings}
            else:
                warnings = result.get("parse_warnings", [])
                if not any("ajax" in w.lower() for w in warnings):
                    result = {
                        **result,
                        "parse_warnings": [*warnings, "pedigree AJAX request failed"],
                    }

        return result
