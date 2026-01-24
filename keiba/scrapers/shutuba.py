"""Shutuba (race entry) scraper module for netkeiba.

This module provides functionality to scrape shutuba (race entry table)
from netkeiba's race entry page.
"""

import re

from bs4 import BeautifulSoup

from keiba.models.entry import RaceEntry, ShutubaData
from keiba.scrapers.base import BaseScraper


class ShutubaScraper(BaseScraper):
    """Scraper for netkeiba shutuba (race entry) pages.

    Extracts race entry information from race.netkeiba.com.

    Attributes:
        BASE_URL: Base URL for netkeiba race pages.

    Example:
        >>> scraper = ShutubaScraper()
        >>> data = scraper.fetch_shutuba(race_id="202606010802")
        >>> print(data.race_name)
        第65回京成杯(G3)
        >>> print(data.entries[0].horse_name)
        テストホース1
    """

    BASE_URL = "https://race.netkeiba.com"

    def fetch_shutuba(self, race_id: str) -> ShutubaData:
        """Fetch shutuba data for a specific race ID.

        Args:
            race_id: The race ID string (e.g., "202606010802").

        Returns:
            ShutubaData containing race info and entries.
        """
        url = self._build_url(race_id)
        html = self.fetch(url)
        soup = self.get_soup(html)

        race_info = self._parse_race_info(soup, race_id)
        entries = self._parse_entries(soup)

        return ShutubaData(
            race_id=race_id,
            race_name=race_info.get("race_name", ""),
            race_number=race_info.get("race_number", 0),
            course=race_info.get("course", ""),
            distance=race_info.get("distance", 0),
            surface=race_info.get("surface", ""),
            date=race_info.get("date", ""),
            entries=tuple(entries),
        )

    def _build_url(self, race_id: str) -> str:
        """Build the shutuba URL for a specific race ID.

        Args:
            race_id: The race ID string (e.g., "202606010802").

        Returns:
            Full URL for the shutuba page.
        """
        return f"{self.BASE_URL}/race/shutuba.html?race_id={race_id}"

    def _parse_race_info(
        self, soup: BeautifulSoup, race_id: str | None = None
    ) -> dict:
        """Parse race information from the page.

        Args:
            soup: BeautifulSoup object of the shutuba page.
            race_id: Optional race ID string for extracting year (e.g., "202606010802").

        Returns:
            Dictionary containing race information.
        """
        race_info: dict = {}

        # Race name from RaceName_main
        race_name_elem = soup.find("h1", class_="RaceName_main")
        if race_name_elem:
            race_info["race_name"] = race_name_elem.get_text(strip=True)

        # Race number from RaceNum
        race_num_elem = soup.find("div", class_="RaceNum")
        if race_num_elem:
            race_num_text = race_num_elem.get_text(strip=True)
            match = re.search(r"(\d+)R", race_num_text, re.IGNORECASE)
            if match:
                race_info["race_number"] = int(match.group(1))

        # Race data from RaceData01
        race_data_elem = soup.find("div", class_="RaceData01")
        if race_data_elem:
            span = race_data_elem.find("span")
            if span:
                text = span.get_text(strip=True)
                self._parse_race_data(text, race_info)

        # Race data from RaceData02 (course name for new HTML format)
        race_data02_elem = soup.find("div", class_="RaceData02")
        if race_data02_elem:
            text02 = race_data02_elem.get_text(strip=True)
            self._parse_race_data02(text02, race_info)

        # Fallback: Extract date from RaceList_Date if not already set
        if "date" not in race_info:
            self._parse_date_from_race_list(soup, race_info, race_id)

        return race_info

    def _parse_race_data(self, text: str, race_info: dict) -> None:
        """Parse race data from RaceData01 span text.

        Supports two formats:
        - Old format: "2026年1月8日 中山 芝2000m"
        - New format: "09:55発走 /ダ1200m(右) / 天候:晴/ 馬場:良"

        Args:
            text: Text containing race data.
            race_info: Dictionary to update with parsed values.
        """
        # Extract date (old format only)
        date_match = re.search(r"(\d{4}年\d+月\d+日)", text)
        if date_match:
            race_info["date"] = date_match.group(1)

        # Extract course (racecourse name) - old format: after date, before surface
        # Pattern: after date, a Japanese word before 芝/ダ
        course_match = re.search(r"\d+日\s+(\S+)\s+[芝ダ]", text)
        if course_match:
            race_info["course"] = course_match.group(1)

        # Extract surface and distance
        # Supports: "芝2000m", "ダ1200m", "ダート1800m", "/ダ1200m(右)"
        surface_dist_match = re.search(r"(芝|ダ|ダート)(\d+)m", text)
        if surface_dist_match:
            surface = surface_dist_match.group(1)
            if surface == "ダ":
                surface = "ダート"
            race_info["surface"] = surface
            race_info["distance"] = int(surface_dist_match.group(2))

    def _parse_race_data02(self, text: str, race_info: dict) -> None:
        """Parse race data from RaceData02 text.

        Expected format: "1回中山8日目サラ系３歳未勝利牝[指]馬齢16頭本賞金:590,240,150,89,59万円"

        Extracts course name (e.g., 中山, 東京, 阪神) if not already set.

        Args:
            text: Text containing race data from RaceData02.
            race_info: Dictionary to update with parsed values.
        """
        # Skip if course is already set (from old format RaceData01)
        if "course" in race_info:
            return

        # Extract course name from new format
        # Pattern: "X回{競馬場名}Y日" where 競馬場名 is 2-3 chars
        course_match = re.search(r"\d+回([^\d]{2,4})\d+日", text)
        if course_match:
            race_info["course"] = course_match.group(1)

    def _parse_date_from_race_list(
        self, soup: BeautifulSoup, race_info: dict, race_id: str | None
    ) -> None:
        """Parse date from RaceList_Date element (new HTML format).

        HTML structure:
        <div class="RaceList_Date clearfix">
          <dl id="RaceList_DateList">
            <dd class="Active">
              <a title="1月24日(土)" href="...">1月24日<span>(土)</span></a>
            </dd>
          </dl>
        </div>

        Args:
            soup: BeautifulSoup object of the shutuba page.
            race_info: Dictionary to update with parsed date.
            race_id: Optional race ID string for extracting year.
        """
        race_list_date = soup.find("div", class_="RaceList_Date")
        if not race_list_date:
            return

        active_dd = race_list_date.find("dd", class_="Active")
        if not active_dd:
            return

        link = active_dd.find("a")
        if not link:
            return

        title = link.get("title", "")
        if not title:
            return

        # Extract month and day from title (e.g., "1月24日(土)" -> "1月24日")
        date_match = re.search(r"(\d+)月(\d+)日", title)
        if not date_match:
            return

        month = date_match.group(1)
        day = date_match.group(2)

        # Determine year from race_id (first 4 characters) or use current year
        if race_id and len(race_id) >= 4:
            year = race_id[:4]
        else:
            from datetime import datetime

            year = str(datetime.now().year)

        race_info["date"] = f"{year}年{month}月{day}日"

    def _parse_entries(self, soup: BeautifulSoup) -> list[RaceEntry]:
        """Parse race entries from the page.

        Args:
            soup: BeautifulSoup object of the shutuba page.

        Returns:
            List of RaceEntry objects.
        """
        entries: list[RaceEntry] = []

        # Find shutuba table
        table = soup.find("table", class_="Shutuba_Table")
        if not table:
            return entries

        # Find tbody or use table directly
        tbody = table.find("tbody", id="Shutuba_HorseList")
        if not tbody:
            tbody = table.find("tbody")

        # If no tbody, search directly from table
        if tbody:
            rows = tbody.find_all("tr", class_="HorseList")
        else:
            rows = table.find_all("tr", class_="HorseList")

        # Parse each row
        for row in rows:
            entry = self._parse_entry_row(row)
            if entry:
                entries.append(entry)

        return entries

    def _parse_entry_row(self, row) -> RaceEntry | None:
        """Parse a single entry row.

        Args:
            row: BeautifulSoup element for the table row.

        Returns:
            RaceEntry object or None if parsing fails.
        """
        try:
            # Bracket number
            waku_cell = row.find("td", class_=lambda x: x and "Waku" in x)
            bracket_number = 0
            if waku_cell:
                span = waku_cell.find("span")
                if span:
                    bracket_text = span.get_text(strip=True)
                    if bracket_text.isdigit():
                        bracket_number = int(bracket_text)

            # Horse number
            umaban_cell = row.find("td", class_=lambda x: x and "Umaban" in x)
            horse_number = 0
            if umaban_cell:
                umaban_text = umaban_cell.get_text(strip=True)
                if umaban_text.isdigit():
                    horse_number = int(umaban_text)

            # Horse info
            horse_info_cell = row.find("td", class_="HorseInfo")
            horse_id = ""
            horse_name = ""
            if horse_info_cell:
                horse_link = horse_info_cell.find("a")
                if horse_link:
                    horse_name = horse_link.get_text(strip=True)
                    href = horse_link.get("href", "")
                    horse_id_match = re.search(r"/horse/(\d+)", href)
                    if horse_id_match:
                        horse_id = horse_id_match.group(1)

            # Sex and age
            barei_cell = row.find("td", class_="Barei")
            sex = ""
            age = 0
            if barei_cell:
                barei_text = barei_cell.get_text(strip=True)
                if barei_text:
                    sex = barei_text[0]
                    age_match = re.search(r"(\d+)", barei_text)
                    if age_match:
                        age = int(age_match.group(1))

            # Impost (weight carried)
            impost = 0.0
            cells = row.find_all("td")
            for cell in cells:
                cell_class = cell.get("class", [])
                if "Txt_C" in cell_class:
                    impost_text = cell.get_text(strip=True)
                    try:
                        impost = float(impost_text)
                    except ValueError:
                        pass
                    break

            # Jockey info
            jockey_cell = row.find("td", class_="Jockey")
            jockey_id = ""
            jockey_name = ""
            if jockey_cell:
                jockey_link = jockey_cell.find("a")
                if jockey_link:
                    jockey_name = jockey_link.get_text(strip=True)
                    href = jockey_link.get("href", "")
                    # ID can be alphanumeric (e.g., "01167", "a0257")
                    jockey_id_match = re.search(r"/jockey/([a-zA-Z0-9]+)", href)
                    if jockey_id_match:
                        jockey_id = jockey_id_match.group(1)

            # Validate required fields
            if not horse_id or not horse_name:
                return None

            return RaceEntry(
                horse_id=horse_id,
                horse_name=horse_name,
                horse_number=horse_number,
                bracket_number=bracket_number,
                jockey_id=jockey_id,
                jockey_name=jockey_name,
                impost=impost,
                sex=sex,
                age=age,
            )
        except (AttributeError, ValueError):
            return None
