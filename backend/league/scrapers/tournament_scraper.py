"""
Scraper for tournament listings backed by saved HTML snapshots.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from ..models import Tournament
from .base import BaseScraper

logger = logging.getLogger(__name__)


class TournamentScraper(BaseScraper):
    """
    Parse tournament list tables that have been saved locally per season.
    """

    RAW_HTML_DIRECTORY = (
        Path(__file__).resolve().parent / "rawhtml" / "tournamentListsBySeason"
    )

    def __init__(
        self,
        directory: Optional[Path] = None,
        **kwargs: Any,
    ) -> None:
        """
        Args:
            directory: Optional override for the directory of tournament list HTML files.
        """
        super().__init__(**kwargs)
        self.directory = Path(directory) if directory else self.RAW_HTML_DIRECTORY

    def _iter_tournament_files(self) -> List[Path]:
        if not self.directory.exists():
            return []
        return sorted(self.directory.glob("tournament_list_*.html"))

    def _derive_season_from_filename(self, file_path: Path) -> str:
        match = re.search(r"tournament_list_(.+)\.html$", file_path.name)
        if match:
            return match.group(1)
        return file_path.stem

    def _parse_tournament_table(
        self,
        html: str,
        season: Optional[str] = None,
        file_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        soup = self.parse_html(html)
        if soup is None:
            error_message = "Failed to parse HTML content"
            logger.error("%s for file %s", error_message, file_name or season)
            return {
                "season": season,
                "file_name": file_name,
                "tournaments": [],
                "count": 0,
                "error": error_message,
            }

        table = soup.find("table")
        if table is None:
            error_message = "No <table> element found in HTML content"
            logger.warning("%s for file %s", error_message, file_name or season)
            return {
                "season": season,
                "file_name": file_name,
                "tournaments": [],
                "count": 0,
                "error": error_message,
            }

        body = table.find("tbody") or table
        tournaments: List[Dict[str, Any]] = []

        for row in body.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 7:
                continue

            name_cell = cells[1]
            link_tag = name_cell.find("a")
            name = (link_tag.get_text(strip=True) if link_tag else name_cell.get_text(strip=True)).strip()
            href = link_tag.get("href", "").strip() if link_tag else ""
            region = cells[2].get_text(strip=True)
            last_game = cells[6].get_text(strip=True)

            if not name:
                continue

            tournaments.append(
                {
                    "season": season,
                    "name": name,
                    "href": href,
                    "region": region,
                    "last_game": last_game,
                }
            )

        result: Dict[str, Any] = {
            "season": season,
            "file_name": file_name,
            "tournaments": tournaments,
            "count": len(tournaments),
            "error": None,
        }
        if tournaments:
            result["last_game_dates"] = [t["last_game"] for t in tournaments if t.get("last_game")]
        return result

    def scrape(
        self,
        seasons: Optional[Sequence[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scrape tournament listings from locally saved HTML snapshots.

        Args:
            seasons: Optional iterable of season identifiers (e.g. ["s15", "s14"]).
                     When provided, only matching files will be processed.

        Returns:
            List containing a single dictionary with aggregated results.
        """
        payload: Dict[str, Any] = {
            "directory": str(self.directory),
            "seasons_requested": list(seasons) if seasons is not None else None,
            "tournament_sets": [],
            "total_tournaments": 0,
            "errors": [],
            "timestamp": timezone.now().isoformat(),
        }

        if not self.directory.exists():
            error_message = f"HTML directory not found: {self.directory}"
            logger.error(error_message)
            payload["fatal_error"] = error_message
            payload["errors"].append(error_message)
            return [payload]

        seasons_filter = set(seasons or [])
        for file_path in self._iter_tournament_files():
            season = self._derive_season_from_filename(file_path)
            if seasons and season not in seasons_filter:
                continue

            try:
                html = file_path.read_text(encoding="utf-8")
            except OSError as exc:
                error_message = f"Failed to read {file_path.name}: {exc}"
                logger.error(error_message)
                payload["errors"].append(error_message)
                payload["tournament_sets"].append(
                    {
                        "season": season,
                        "file_name": file_path.name,
                        "tournaments": [],
                        "count": 0,
                        "error": error_message,
                    }
                )
                continue

            result = self._parse_tournament_table(
                html=html,
                season=season,
                file_name=file_path.name,
            )

            if result.get("error"):
                payload["errors"].append(
                    f"{file_path.name}: {result['error']}"
                )

            payload["tournament_sets"].append(result)
            payload["total_tournaments"] += result.get("count", 0)

        if seasons and not payload["tournament_sets"]:
            message = "No tournament files matched the requested seasons"
            logger.warning(message)
            payload["errors"].append(message)

        return [payload]

    def save_to_database(
        self,
        tournament_sets: Sequence[Dict[str, Any]],
    ) -> Tuple[int, int]:
        """
        Persist tournaments into the database.

        Args:
            tournament_sets: Sequence of dictionaries returned inside the payload from scrape()

        Returns:
            Tuple with counts of (created, updated) records.
        """
        created_total = 0
        updated_total = 0

        with transaction.atomic():
            for group in tournament_sets:
                season_name = group.get("season") or group.get("file_name")
                for entry in group.get("tournaments", []):
                    tournament_name = entry.get("name")
                    if not tournament_name:
                        continue

                    season_snapshot = entry.get("season") or season_name or ""
                    last_game_raw = entry.get("last_game")
                    last_game_date = parse_date(last_game_raw) if last_game_raw else None

                    defaults = {
                        "tier": "",
                        "season_name": season_snapshot,
                        "region": entry.get("region", "")[:10],
                        "last_game_date": last_game_date,
                        "details_url": entry.get("href", ""),
                    }

                    obj, created = Tournament.objects.update_or_create(
                        name=tournament_name,
                        season_name=season_snapshot,
                        defaults=defaults,
                    )
                    if created:
                        created_total += 1
                    else:
                        updated_total += 1

        return created_total, updated_total