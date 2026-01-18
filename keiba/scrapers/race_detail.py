"""Race detail scraper module for netkeiba.

This module provides functionality to scrape race details and results
from netkeiba's race detail page.
"""

import re

from bs4 import BeautifulSoup

from keiba.scrapers.base import BaseScraper


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

        # Race name
        race_name_elem = soup.find("div", class_="RaceName")
        if race_name_elem:
            h1 = race_name_elem.find("h1")
            if h1:
                race_info["name"] = h1.get_text(strip=True)

        # Race date
        race_date_elem = soup.find("div", class_="RaceDate")
        if race_date_elem:
            span = race_date_elem.find("span")
            if span:
                race_info["date"] = span.get_text(strip=True)

        # Race number
        race_num_elem = soup.find("div", class_="RaceNum")
        if race_num_elem:
            span = race_num_elem.find("span")
            if span:
                num_text = span.get_text(strip=True)
                # Extract number from "11R" format
                match = re.match(r"(\d+)R?", num_text)
                if match:
                    race_info["race_number"] = int(match.group(1))

        # Course info from RaceData02
        race_data02 = soup.find("div", class_="RaceData02")
        if race_data02:
            spans = race_data02.find_all("span")
            if len(spans) >= 2:
                race_info["course"] = spans[1].get_text(strip=True)

        # Distance, surface, weather, track_condition from RaceData01
        race_data01 = soup.find("div", class_="RaceData01")
        if race_data01:
            spans = race_data01.find_all("span")
            for span in spans:
                text = span.get_text(strip=True)

                # Parse distance and surface (e.g., "芝右1600m")
                dist_match = re.search(r"(芝|ダート|障).*?(\d+)m", text)
                if dist_match:
                    race_info["surface"] = dist_match.group(1)
                    race_info["distance"] = int(dist_match.group(2))

                # Parse weather (e.g., "天候:晴")
                weather_match = re.match(r"天候[:：](.+)", text)
                if weather_match:
                    race_info["weather"] = weather_match.group(1)

                # Parse track condition (e.g., "馬場:良")
                track_match = re.match(r"馬場[:：](.+)", text)
                if track_match:
                    race_info["track_condition"] = track_match.group(1)

        return race_info

    def _parse_results(self, soup: BeautifulSoup) -> list[dict]:
        """Parse race results from the page.

        Args:
            soup: BeautifulSoup object of the race detail page.

        Returns:
            List of dictionaries containing each horse's result.
        """
        results = []

        # Find result table
        table = soup.find("table", class_="RaceTable01")
        if not table:
            return results

        # Find all horse rows
        rows = table.find_all("tr", class_="HorseList")

        for row in rows:
            horse_result = self._parse_horse_row(row)
            if horse_result:
                results.append(horse_result)

        return results

    def _parse_horse_row(self, row) -> dict | None:
        """Parse a single horse result row.

        Args:
            row: BeautifulSoup element for the table row.

        Returns:
            Dictionary containing the horse's result data.
        """
        result = {}

        # Finish position
        rank_elem = row.find("td", class_="Result_Rank")
        if rank_elem:
            rank_text = rank_elem.get_text(strip=True)
            if rank_text.isdigit():
                result["finish_position"] = int(rank_text)
            else:
                # "中止", "除外" etc.
                result["finish_position"] = None

        # Bracket number
        bracket_elem = row.find("td", class_="Bracket")
        if bracket_elem:
            bracket_num = bracket_elem.find("span", class_="Bracket_Num")
            if bracket_num:
                result["bracket_number"] = int(bracket_num.get_text(strip=True))

        # Horse number
        horse_num_elem = row.find("td", class_="Horse_Num")
        if horse_num_elem:
            result["horse_number"] = int(horse_num_elem.get_text(strip=True))

        # Horse ID and name
        horse_name_elem = row.find("td", class_="Horse_Name")
        if horse_name_elem:
            link = horse_name_elem.find("a")
            if link:
                result["horse_name"] = link.get_text(strip=True)
                # Extract horse ID from URL
                href = link.get("href", "")
                horse_id_match = re.search(r"/horse/(\d+)", href)
                if horse_id_match:
                    result["horse_id"] = horse_id_match.group(1)

        # Jockey ID and name
        jockey_elem = row.find("td", class_="Jockey")
        if jockey_elem:
            link = jockey_elem.find("a")
            if link:
                result["jockey_name"] = link.get_text(strip=True)
                href = link.get("href", "")
                jockey_id_match = re.search(r"/jockey/(\d+)", href)
                if jockey_id_match:
                    result["jockey_id"] = jockey_id_match.group(1)

        # Trainer ID and name
        trainer_elem = row.find("td", class_="Trainer")
        if trainer_elem:
            link = trainer_elem.find("a")
            if link:
                result["trainer_name"] = link.get_text(strip=True)
                href = link.get("href", "")
                trainer_id_match = re.search(r"/trainer/(\d+)", href)
                if trainer_id_match:
                    result["trainer_id"] = trainer_id_match.group(1)

        # Time
        time_elem = row.find("td", class_="Time")
        if time_elem:
            result["time"] = time_elem.get_text(strip=True)

        # Margin
        margin_elem = row.find("td", class_="Margin")
        if margin_elem:
            result["margin"] = margin_elem.get_text(strip=True)

        # Odds
        odds_elem = row.find("td", class_="Odds")
        if odds_elem:
            odds_text = odds_elem.get_text(strip=True)
            if odds_text:
                try:
                    result["odds"] = float(odds_text)
                except ValueError:
                    result["odds"] = None

        # Popularity
        pop_elem = row.find("td", class_="Popularity")
        if pop_elem:
            pop_text = pop_elem.get_text(strip=True)
            if pop_text.isdigit():
                result["popularity"] = int(pop_text)

        # Weight and weight_diff
        weight_elem = row.find("td", class_="Weight")
        if weight_elem:
            weight_text = weight_elem.get_text(strip=True)
            # Parse "512(+4)", "486(-2)", "492(0)" formats
            weight_match = re.match(r"(\d+)\(([+-]?\d+)\)", weight_text)
            if weight_match:
                result["weight"] = int(weight_match.group(1))
                result["weight_diff"] = int(weight_match.group(2))

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
