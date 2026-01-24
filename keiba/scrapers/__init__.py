"""Scraper modules for keiba data collection."""

from keiba.scrapers.base import BaseScraper
from keiba.scrapers.horse_detail import HorseDetailScraper
from keiba.scrapers.race_detail import RaceDetailScraper
from keiba.scrapers.race_list import RaceListScraper
from keiba.scrapers.shutuba import RaceEntry, ShutubaScraper, ShutubaData

__all__ = [
    "BaseScraper",
    "HorseDetailScraper",
    "RaceDetailScraper",
    "RaceListScraper",
    "RaceEntry",
    "ShutubaScraper",
    "ShutubaData",
]
