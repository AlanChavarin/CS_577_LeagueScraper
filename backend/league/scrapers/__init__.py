"""
Scrapers module for League of Legends data.

This module contains all web scraping logic for collecting data from external sources.
"""

from .base import BaseScraper
from .champion_scraper import ChampionScraper
from .patch_scraper import PatchScraper
from .game_scraper import GameScraper
from .match_scraper import MatchScraper

__all__ = ['BaseScraper', 'ChampionScraper', 'PatchScraper', 'GameScraper', 'MatchScraper']

