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

        race_info = self._parse_race_info(soup)
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

    def _parse_race_info(self, soup: BeautifulSoup) -> dict:
        """Parse race information from the page.

        Args:
            soup: BeautifulSoup object of the shutuba page.

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

        return race_info

    def _parse_race_data(self, text: str, race_info: dict) -> None:
        """Parse race data from RaceData01 span text.

        Expected format: "2026年1月8日 中山 芝2000m"

        Args:
            text: Text containing race data.
            race_info: Dictionary to update with parsed values.
        """
        # Extract date
        date_match = re.search(r"(\d{4}年\d+月\d+日)", text)
        if date_match:
            race_info["date"] = date_match.group(1)

        # Extract course (racecourse name) - appears after date, before surface
        # Pattern: after date, a Japanese word before 芝/ダ
        course_match = re.search(r"\d+日\s+(\S+)\s+[芝ダ]", text)
        if course_match:
            race_info["course"] = course_match.group(1)

        # Extract surface and distance
        surface_dist_match = re.search(r"(芝|ダ|ダート)(\d+)m", text)
        if surface_dist_match:
            surface = surface_dist_match.group(1)
            if surface == "ダ":
                surface = "ダート"
            race_info["surface"] = surface
            race_info["distance"] = int(surface_dist_match.group(2))

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

        # Find tbody
        tbody = table.find("tbody", id="Shutuba_HorseList")
        if not tbody:
            tbody = table.find("tbody")
        if not tbody:
            return entries

        # Parse each row
        rows = tbody.find_all("tr", class_="HorseList")
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
