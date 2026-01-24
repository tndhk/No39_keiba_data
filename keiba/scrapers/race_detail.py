"""Race detail scraper module for netkeiba.

This module provides functionality to scrape race details and results
from netkeiba's race detail page.
"""

import re

from bs4 import BeautifulSoup

from keiba.scrapers.base import BaseScraper
from keiba.utils.grade_extractor import extract_grade


class RaceDetailScraper(BaseScraper):
    """Scraper for netkeiba race detail pages.

    Extracts race information and horse results from a race detail page.

    Attributes:
        BASE_URL: Base URL for netkeiba database pages.

    Example:
        >>> scraper = RaceDetailScraper()
        >>> data = scraper.fetch_race_detail(race_id="202401010101")
        >>> print(data["race"]["name"])
        有馬記念(G1)
        >>> print(data["results"][0]["horse_name"])
        ドウデュース
    """

    BASE_URL = "https://db.netkeiba.com"

    def parse(self, soup: BeautifulSoup, race_id: str) -> dict:
        """Parse the race detail page and extract race info and results.

        Args:
            soup: BeautifulSoup object of the race detail page.
            race_id: The race ID string.

        Returns:
            Dictionary containing "race" info and "results" list.
        """
        race_info = self._parse_race_info(soup, race_id)
        results = self._parse_results(soup)

        return {"race": race_info, "results": results}

    def _parse_race_info(self, soup: BeautifulSoup, race_id: str) -> dict:
        """Parse race information from the page.

        Args:
            soup: BeautifulSoup object of the race detail page.
            race_id: The race ID string.

        Returns:
            Dictionary containing race information.
        """
        race_info = {"id": race_id}

        # Find the data_intro div which contains all race info
        data_intro = soup.find("div", class_="data_intro")

        # Race name - db.netkeiba.com: <dd><h1>レース名</h1></dd>
        dd_elem = soup.find("dd")
        if dd_elem:
            h1 = dd_elem.find("h1")
            if h1:
                race_info["name"] = h1.get_text(strip=True)

        # Date and course from p.smalltxt
        # Format: "2024年01月01日 11回川崎1日目"
        smalltxt = soup.find("p", class_="smalltxt")
        if smalltxt:
            text = smalltxt.get_text(strip=True)
            # Extract date
            date_match = re.search(r"(\d{4}年\d{2}月\d{2}日)", text)
            if date_match:
                race_info["date"] = date_match.group(1)
            # Extract course name (e.g., "川崎" from "11回川崎1日目")
            course_match = re.search(r"\d+回(.+?)\d+日目", text)
            if course_match:
                race_info["course"] = course_match.group(1)

        # Race number from dt - Format: "1 R"
        dt_elem = soup.find("dt")
        if dt_elem:
            dt_text = dt_elem.get_text(strip=True)
            # Extract number from "1 R" or "11R" format
            match = re.search(r"(\d+)\s*R", dt_text, re.IGNORECASE)
            if match:
                race_info["race_number"] = int(match.group(1))

        # Distance, surface, weather, track_condition from span inside dd > p
        # Format: "ダ左1500m / 天候 : 晴 / ダート : 良 / 発走 : 11:20"
        # The span is inside dd > p element
        if dd_elem:
            p_elem = dd_elem.find("p")
            if p_elem:
                span = p_elem.find("span")
                if span:
                    text = span.get_text()
                    # Normalize whitespace
                    text = " ".join(text.split())
                    self._parse_race_conditions(text, race_info)

        # Fallback: search all spans if not found in dd > p
        if "distance" not in race_info:
            for span in soup.find_all("span"):
                text = span.get_text()
                text = " ".join(text.split())
                if "m" in text and ("天候" in text or "/" in text):
                    self._parse_race_conditions(text, race_info)
                    break

        # Extract grade from race name
        if "name" in race_info:
            race_info["grade"] = extract_grade(race_info["name"])

        return race_info

    def _parse_race_conditions(self, text: str, race_info: dict) -> None:
        """Parse race conditions from text.

        Supports multiple formats:
        - Standard: "ダ左1500m / 天候 : 晴 / ダート : 良"
        - Alternate: "2880m / 芝 : 左 / 馬 : 牡"
        - Hurdle: "障芝 ダート2880m / 天候 : 晴 / 芝 : 稍重"
        - NAR: "1500m / ダート : 左 / 天候 : 晴 / ダート : 良"

        Args:
            text: Text containing race conditions.
            race_info: Dictionary to update with parsed values.
        """
        parts = [p.strip() for p in text.split("/")]
        for part in parts:
            # Pattern 0: Hurdle race format - "障芝 ダート2880m" or "障芝2880m"
            # These are steeplechase/hurdle races
            hurdle_match = re.search(r"障芝\s*(?:ダート)?\s*(\d+)m", part)
            if hurdle_match:
                race_info["surface"] = "障害"
                race_info["distance"] = int(hurdle_match.group(1))
                continue

            # Pattern 1: Standard format - surface + direction + distance
            # e.g., "ダ左1500m", "芝右1600m", "障芝3000m"
            dist_match = re.search(r"(ダ|芝|障)[左右直]?\s*外?\s*(\d+)m", part)
            if dist_match:
                surface = dist_match.group(1)
                if surface == "ダ":
                    surface = "ダート"
                race_info["surface"] = surface
                race_info["distance"] = int(dist_match.group(2))
                continue

            # Pattern 2: Distance only (e.g., "2880m")
            if "distance" not in race_info:
                dist_only_match = re.search(r"(\d+)m", part)
                if dist_only_match:
                    race_info["distance"] = int(dist_only_match.group(1))
                    continue

            # Pattern 3: Surface with direction (e.g., "芝 : 左", "ダート : 右")
            if "surface" not in race_info:
                surface_match = re.search(r"(芝|ダート|障害)\s*[:：]\s*[左右直]", part)
                if surface_match:
                    race_info["surface"] = surface_match.group(1)
                    continue

            # Parse weather (e.g., "天候 : 晴")
            weather_match = re.search(r"天候\s*[:：]\s*(.+)", part)
            if weather_match:
                race_info["weather"] = weather_match.group(1).strip()
                continue

            # Parse track condition (e.g., "ダート : 良" or "芝 : 良")
            # Only match track conditions, not directions
            track_match = re.search(r"(?:ダート|芝)\s*[:：]\s*(良|稍重|重|不良)", part)
            if track_match:
                race_info["track_condition"] = track_match.group(1)

        # Set default surface if not found
        if "surface" not in race_info:
            race_info["surface"] = "不明"

    def _parse_results(self, soup: BeautifulSoup) -> list[dict]:
        """Parse race results from the page.

        Args:
            soup: BeautifulSoup object of the race detail page.

        Returns:
            List of dictionaries containing each horse's result.
        """
        results = []

        # Find result table - db.netkeiba.com uses "race_table_01"
        table = soup.find("table", class_="race_table_01")
        if not table:
            return results

        # Find all horse rows in tbody (skip header)
        tbody = table.find("tbody")
        if tbody:
            rows = tbody.find_all("tr")
        else:
            # Fallback: get all tr except first (header)
            rows = table.find_all("tr")[1:]

        for row in rows:
            horse_result = self._parse_horse_row(row)
            if horse_result:
                results.append(horse_result)

        return results

    def _parse_horse_row(self, row) -> dict | None:
        """Parse a single horse result row.

        Column order for db.netkeiba.com (21 columns total):
        0: 着順, 1: 枠番, 2: 馬番, 3: 馬名, 4: 性齢, 5: 斤量, 6: 騎手,
        7: タイム, 8: 着差, 9: タイム指数, 10: 通過, 11: 上り,
        12: 単勝(オッズ), 13: 人気, 14: 馬体重, 15-17: プレミアム,
        18: 調教師, 19: 馬主, 20: 賞金

        Args:
            row: BeautifulSoup element for the table row.

        Returns:
            Dictionary containing the horse's result data.
        """
        result = {}
        cells = row.find_all("td")
        if len(cells) < 10:
            return None

        # Column 0: Finish position
        rank_text = cells[0].get_text(strip=True)
        if rank_text.isdigit():
            result["finish_position"] = int(rank_text)
        else:
            # "中止", "除外" etc.
            result["finish_position"] = None

        # Column 1: Bracket number
        bracket_span = cells[1].find("span")
        if bracket_span:
            bracket_text = bracket_span.get_text(strip=True)
            if bracket_text.isdigit():
                result["bracket_number"] = int(bracket_text)
        else:
            bracket_text = cells[1].get_text(strip=True)
            if bracket_text.isdigit():
                result["bracket_number"] = int(bracket_text)

        # Column 2: Horse number
        horse_num_text = cells[2].get_text(strip=True)
        if horse_num_text.isdigit():
            result["horse_number"] = int(horse_num_text)

        # Column 3: Horse ID and name
        horse_link = cells[3].find("a")
        if horse_link:
            result["horse_name"] = horse_link.get_text(strip=True)
            href = horse_link.get("href", "")
            # Pattern: /horse/2019104251/ or /horse/result/recent/2019104251/
            horse_id_match = re.search(r"/horse/(?:result/recent/)?(\d+)", href)
            if horse_id_match:
                result["horse_id"] = horse_id_match.group(1)

        # Column 4: Sex and age (e.g., "牡3", "牝4", "セ5")
        if len(cells) > 4:
            sex_age_text = cells[4].get_text(strip=True)
            if sex_age_text:
                sex = sex_age_text[0]
                age_match = re.search(r"(\d+)", sex_age_text)
                if age_match:
                    result["sex"] = sex
                    result["age"] = int(age_match.group(1))

        # Column 5: Impost (e.g., "57.0")
        if len(cells) > 5:
            impost_text = cells[5].get_text(strip=True)
            if impost_text:
                try:
                    result["impost"] = float(impost_text)
                except ValueError:
                    pass

        # Column 6: Jockey ID and name
        if len(cells) > 6:
            jockey_link = cells[6].find("a")
            if jockey_link:
                result["jockey_name"] = jockey_link.get_text(strip=True)
                href = jockey_link.get("href", "")
                # Pattern: /jockey/01167/ or /jockey/result/recent/01167/
                # ID can be alphanumeric (e.g., "05365", "a0257")
                jockey_id_match = re.search(r"/jockey/(?:result/recent/)?([a-zA-Z0-9]+)", href)
                if jockey_id_match:
                    result["jockey_id"] = jockey_id_match.group(1)

        # Column 7: Time
        if len(cells) > 7:
            result["time"] = cells[7].get_text(strip=True)

        # Column 8: Margin
        if len(cells) > 8:
            result["margin"] = cells[8].get_text(strip=True)

        # Column 10: Passing order (e.g., "2-1-1-1")
        if len(cells) > 10:
            passing_text = cells[10].get_text(strip=True)
            if passing_text:
                result["passing_order"] = passing_text
            else:
                result["passing_order"] = None

        # Column 11: Last 3 furlongs (上がり3F)
        if len(cells) > 11:
            last_3f_text = cells[11].get_text(strip=True)
            if last_3f_text:
                try:
                    result["last_3f"] = float(last_3f_text)
                except ValueError:
                    result["last_3f"] = None
            else:
                result["last_3f"] = None

        # Column 12: Odds (単勝)
        if len(cells) > 12:
            odds_text = cells[12].get_text(strip=True)
            if odds_text:
                try:
                    result["odds"] = float(odds_text)
                except ValueError:
                    result["odds"] = None

        # Column 13: Popularity
        if len(cells) > 13:
            pop_text = cells[13].get_text(strip=True)
            if pop_text.isdigit():
                result["popularity"] = int(pop_text)

        # Column 14: Weight and weight_diff
        if len(cells) > 14:
            weight_text = cells[14].get_text(strip=True)
            # Parse "512(+4)", "486(-2)", "492(0)" formats
            weight_match = re.match(r"(\d+)\(([+-]?\d+)\)", weight_text)
            if weight_match:
                result["weight"] = int(weight_match.group(1))
                result["weight_diff"] = int(weight_match.group(2))

        # Column 18: Trainer ID and name
        if len(cells) > 18:
            trainer_link = cells[18].find("a")
            if trainer_link:
                result["trainer_name"] = trainer_link.get_text(strip=True)
                href = trainer_link.get("href", "")
                # Pattern: /trainer/01088/ or /trainer/result/recent/01088/
                # ID can be alphanumeric
                trainer_id_match = re.search(r"/trainer/(?:result/recent/)?([a-zA-Z0-9]+)", href)
                if trainer_id_match:
                    result["trainer_id"] = trainer_id_match.group(1)

        # Set default values for missing optional fields
        # (e.g., for scratched or disqualified horses)
        result.setdefault("popularity", None)
        result.setdefault("weight", None)
        result.setdefault("weight_diff", None)
        result.setdefault("last_3f", None)
        result.setdefault("sex", None)
        result.setdefault("age", None)
        result.setdefault("impost", None)
        result.setdefault("passing_order", None)

        return result

    def _build_url(self, race_id: str) -> str:
        """Build the race detail URL for a specific race ID.

        Args:
            race_id: The race ID string (e.g., "202401010101").

        Returns:
            Full URL for the race detail page.
        """
        return f"{self.BASE_URL}/race/{race_id}/"

    def fetch_race_detail(self, race_id: str) -> dict:
        """Fetch race details for a specific race ID.

        Args:
            race_id: The race ID string (e.g., "202401010101").

        Returns:
            Dictionary containing "race" info and "results" list.
        """
        url = self._build_url(race_id)
        html = self.fetch(url)
        soup = self.get_soup(html)
        return self.parse(soup, race_id=race_id)

    def fetch_payouts(self, race_id: str) -> list[dict]:
        """Fetch fukusho (place) payouts for a specific race.

        Args:
            race_id: The race ID string (e.g., "202401010101").

        Returns:
            List of dictionaries containing "horse_number" and "payout" keys.
            Returns empty list if no payout data is found.

        Example:
            >>> scraper = RaceDetailScraper()
            >>> payouts = scraper.fetch_payouts("202401010101")
            >>> print(payouts)
            [{"horse_number": 5, "payout": 150}, {"horse_number": 3, "payout": 280}]
        """
        url = self._build_url(race_id)
        html = self.fetch(url)
        soup = self.get_soup(html)
        return self._parse_fukusho_payouts(soup)

    def _parse_fukusho_payouts(self, soup: BeautifulSoup) -> list[dict]:
        """Parse fukusho (place) payouts from the page.

        Args:
            soup: BeautifulSoup object of the race detail page.

        Returns:
            List of dictionaries containing "horse_number" and "payout" keys.
        """
        payouts = []

        # Find the payout table with class "pay_table_01"
        pay_tables = soup.find_all("table", class_="pay_table_01")
        if not pay_tables:
            return payouts

        # Search for fukusho row in all pay tables
        for table in pay_tables:
            fuku_th = table.find("th", class_="fuku")
            if fuku_th:
                row = fuku_th.find_parent("tr")
                if row:
                    tds = row.find_all("td")
                    if len(tds) >= 2:
                        # First td contains horse numbers (can be multiple separated by <br>)
                        # Second td contains payouts (can be multiple separated by <br>)
                        horse_numbers = self._parse_br_separated_values(tds[0])
                        payout_values = self._parse_br_separated_values(tds[1])

                        # Validate that counts match
                        if len(horse_numbers) != len(payout_values):
                            return []

                        for horse_num, payout in zip(horse_numbers, payout_values):
                            try:
                                # Parse horse number
                                horse_number = int(horse_num.strip())
                                # Parse payout (remove commas)
                                payout_int = int(payout.strip().replace(",", ""))
                                payouts.append({
                                    "horse_number": horse_number,
                                    "payout": payout_int
                                })
                            except ValueError:
                                # Skip malformed data
                                continue
                break

        return payouts

    def _parse_br_separated_values(self, td_element) -> list[str]:
        """Parse values separated by <br> tags in a td element.

        Args:
            td_element: BeautifulSoup td element.

        Returns:
            List of string values.
        """
        # Get all text content, splitting by br tags
        values = []
        for content in td_element.children:
            if hasattr(content, 'name') and content.name == 'br':
                continue
            text = content.get_text(strip=True) if hasattr(content, 'get_text') else str(content).strip()
            if text:
                values.append(text)
        return values
