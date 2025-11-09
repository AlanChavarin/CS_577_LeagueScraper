"""
Scraper for tournament match listings hosted on gol.gg.
"""
from __future__ import annotations

import logging
import json
from dataclasses import dataclass, asdict
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import quote, urljoin

from importlib import import_module

from django.db import transaction

from ..models import Match, Team, Tournament
from .base import BaseScraper

# Attempt to import Django utilities dynamically so static analysis doesn't fail
try:  # pragma: no cover - runtime import
    timezone = import_module("django.utils.timezone")
    parse_date = import_module("django.utils.dateparse").parse_date
except ModuleNotFoundError:  # pragma: no cover
    class _FallbackTimezone:
        """Minimal fallback implementation mimicking django.utils.timezone."""

        @staticmethod
        def now() -> datetime:
            return datetime.now()

    def _fallback_parse_date(value: Optional[str]) -> Optional[date]:
        if not value:
            return None
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    timezone = _FallbackTimezone()  # type: ignore
    parse_date = _fallback_parse_date  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class MatchRow:
    """Represents a parsed match row from the gol.gg tournament listings."""

    match_href: str
    match_url: str
    team_one_name: str
    team_two_name: str
    team_one_score: Optional[int]
    team_two_score: Optional[int]
    week: str
    patch: str
    date_text: str
    date_iso: Optional[str]
    team_one_resolved_name: Optional[str] = None
    team_two_resolved_name: Optional[str] = None
    team_one_id: Optional[int] = None
    team_two_id: Optional[int] = None


class MatchScraper(BaseScraper):
    """Fetches and parses match listings for tournaments stored in our database."""

    BASE_URL = "https://gol.gg/tournament/tournament-matchlist/"

    def __init__(self, base_url: Optional[str] = None, **kwargs: Any) -> None:
        """
        Args:
            base_url: Optional override for the gol.gg match-list endpoint.
            **kwargs: Additional keyword arguments forwarded to BaseScraper.
        """
        super().__init__(base_url=base_url or self.BASE_URL, **kwargs)
        self._team_cache: Dict[str, Team] = {}

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def scrape(
        self,
        tournament_names: Optional[Sequence[str]] = None,
        tournament_ids: Optional[Sequence[int]] = None,
    ) -> List[Dict[str, Any]]:
        print(
            "MatchScraper.scrape invoked with filters: names=%s ids=%s",
            tournament_names,
            tournament_ids,
        )
        """
        Scrape match listings for tournaments stored in the database.

        Args:
            tournament_names: Optional iterable of tournament names to filter.
            tournament_ids: Optional iterable of tournament IDs to filter.

        Returns:
            List with a single payload dictionary describing the scraping session.
        """
        tournaments = self._load_tournaments(
            tournament_names=tournament_names,
            tournament_ids=tournament_ids,
        )

        print("Loaded %d tournaments to process", len(tournaments))

        payload: Dict[str, Any] = {
            "timestamp": timezone.now().isoformat(),
            "base_url": self.base_url,
            "requested_tournament_names": list(tournament_names) if tournament_names else None,
            "requested_tournament_ids": list(tournament_ids) if tournament_ids else None,
            "tournaments_processed": len(tournaments),
            "match_sets": [],
            "errors": [],
        }

        for tournament in tournaments:
            print("Processing tournament id=%s name='%s'", tournament.id, tournament.name)
            result = self._scrape_matches_for_tournament(tournament)
            if result.get("error"):
                logger.warning(
                    "Encountered error while scraping tournament '%s': %s",
                    tournament.name,
                    result["error"],
                )
                payload["errors"].append(result["error"])
            payload["match_sets"].append(result)

        print(
            "Match scraping complete. tournaments=%d errors=%d total_matches=%d",
            len(payload["match_sets"]),
            len(payload["errors"]),
            sum(group.get("count", 0) for group in payload["match_sets"]),
        )
        return [payload]

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _load_tournaments(
        self,
        tournament_names: Optional[Sequence[str]] = None,
        tournament_ids: Optional[Sequence[int]] = None,
    ) -> List[Tournament]:
        """Fetch the tournaments to process from the database."""
        qs = Tournament.objects.all().only("id", "name", "season_name", "details_url")

        if tournament_names:
            qs = qs.filter(name__in=list(tournament_names))
        if tournament_ids:
            qs = qs.filter(id__in=list(tournament_ids))

        tournaments = list(qs.order_by("name"))
        if tournaments:
            print(
                "Tournament query returned %d row(s). First few names: %s",
                len(tournaments),
                [t.name for t in tournaments[:5]],
            )
        else:
            print("No tournaments matched the provided filters.")
        return tournaments

    def _scrape_matches_for_tournament(self, tournament: Tournament) -> Dict[str, Any]:
        """Fetch and parse the match list table for a single tournament."""
        url = self._build_tournament_url(tournament.name)
        print("Fetching matches for '%s' from %s", tournament.name, url)
        response = self.fetch_page(url)

        if response is None:
            error_message = f"Failed to fetch match list for tournament '{tournament.name}'"
            print(error_message)
            return {
                "tournament_id": tournament.id,
                "tournament_name": tournament.name,
                "tournament_season": tournament.season_name,
                "source_url": url,
                "matches": [],
                "count": 0,
                "error": error_message,
            }

        print(
            "Received response for '%s' with status=%s length=%d",
            tournament.name,
            response.status_code,
            len(response.text),
        )

        matches, table_headers, parse_error = self._parse_match_table(response.text)
        print(
            "Parsed %d match rows for '%s'. headers=%s error=%s",
            len(matches),
            tournament.name,
            table_headers,
            parse_error,
        )
        result: Dict[str, Any] = {
            "tournament_id": tournament.id,
            "tournament_name": tournament.name,
            "tournament_season": tournament.season_name,
            "source_url": url,
            "status_code": response.status_code,
            "encoding": response.encoding,
            "headers": dict(response.headers),
            "table_headers": table_headers,
            "matches": [match.__dict__ for match in matches],
            "count": len(matches),
            "error": parse_error,
        }

        if parse_error:
            print("%s (tournament=%s)", parse_error, tournament.name)

        return result

    def _build_tournament_url(self, tournament_name: str) -> str:
        """Create the gol.gg URL for a tournament's match list."""
        encoded_name = quote((tournament_name or "").strip(), safe="")
        url = urljoin(self.base_url, encoded_name)
        if not url.endswith("/"):
            url = f"{url}/"
        print("Constructed tournament URL: %s", url)
        return url

    def _parse_match_table(self, html: str) -> Tuple[List[MatchRow], List[str], Optional[str]]:
        """Extract match rows from the gol.gg table_list table."""
        soup = self.parse_html(html)
        if soup is None:
            print("BeautifulSoup returned None while parsing match table")
            return [], [], "Failed to parse HTML content for match list."

        table = soup.find("table", class_="table_list")
        if table is None:
            print('No table with class "table_list" found in HTML')
            return [], [], 'No table with class "table_list" found on the page.'

        header_cells = table.find_all("th")
        headers = [cell.get_text(strip=True) for cell in header_cells] if header_cells else []
        print("Found %d table header(s): %s", len(headers), headers)

        body = table.find("tbody") or table
        rows: List[MatchRow] = []

        for row in body.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 7:
                print("Skipping row with insufficient cells: %s", row.get_text(strip=True))
                continue

            link_tag = cells[0].find("a", href=True)
            raw_href = (link_tag["href"] or "").strip() if link_tag else ""
            match_url = urljoin("https://gol.gg", raw_href) if raw_href else ""

            team_one_name = cells[1].get_text(strip=True)
            score_text = cells[2].get_text(strip=True)
            team_two_name = cells[3].get_text(strip=True)
            week = cells[4].get_text(strip=True)
            patch = cells[5].get_text(strip=True)
            date_text = cells[6].get_text(strip=True)
            team_one_score, team_two_score = self._parse_score(score_text)

            if not team_one_name and not team_two_name:
                continue

            match_row = MatchRow(
                match_href=raw_href,
                match_url=match_url,
                team_one_name=team_one_name,
                team_two_name=team_two_name,
                team_one_score=team_one_score,
                team_two_score=team_two_score,
                week=week,
                patch=patch,
                date_text=date_text,
                date_iso=self._normalize_date(date_text),
            )
            self._attach_team_objects(match_row)
            print(
                "Parsed match row: %s",
                json.dumps(asdict(match_row), ensure_ascii=False),
            )
            rows.append(match_row)

        error_message: Optional[str] = None
        if not rows:
            error_message = "No match rows were parsed from the table."
            print("Match table contained no parsable rows.")
        else:
            print("Successfully parsed %d row(s) from match table.", len(rows))

        return rows, headers, error_message

    def _parse_score(self, score_text: str) -> Tuple[Optional[int], Optional[int]]:
        """Split a score string like '1-0' into integer scores per team."""
        cleaned = (score_text or "").strip()
        if not cleaned:
            return None, None

        parts = cleaned.replace(" ", "").split("-")
        if len(parts) != 2:
            return None, None

        try:
            return int(parts[0]), int(parts[1])
        except (TypeError, ValueError):
            return None, None

    def _normalize_date(self, date_text: str) -> Optional[str]:
        """Convert date strings (YYYY-MM-DD) to ISO format when possible."""
        cleaned = (date_text or "").strip()
        if not cleaned:
            return None

        parsed = parse_date(cleaned)
        if parsed is None:
            return None
        return parsed.isoformat()

    def _attach_team_objects(self, match_row: MatchRow) -> None:
        """Ensure teams referenced in a match row exist and attach their IDs."""
        team_one = self._get_or_create_team(match_row.team_one_name)
        team_two = self._get_or_create_team(match_row.team_two_name)

        if team_one is not None:
            match_row.team_one_id = team_one.id
            match_row.team_one_resolved_name = team_one.name
        else:
            print("Failed to resolve team_one for match row: %s", match_row.match_url)

        if team_two is not None:
            match_row.team_two_id = team_two.id
            match_row.team_two_resolved_name = team_two.name
        else:
            print("Failed to resolve team_two for match row: %s", match_row.match_url)

    def _get_or_create_team(self, team_name: str) -> Optional[Team]:
        """Look up a team by name, creating a placeholder when necessary."""
        normalized = (team_name or "").strip()
        if not normalized:
            return None

        cached = self._team_cache.get(normalized)
        if cached:
            return cached

        team, created = Team.objects.get_or_create(
            name=normalized,
            defaults={'region': 'Unknown'},
        )
        if created:
            print("Created placeholder Team record for name='%s'", normalized)
        elif not team.region:
            team.region = 'Unknown'
            team.save(update_fields=['region'])
            print("Updated team '%s' region to 'Unknown' for scraping context", team.name)

        self._team_cache[normalized] = team
        return team

    # ------------------------------------------------------------------ #
    # Persistence helpers
    # ------------------------------------------------------------------ #
    def save_matches_to_database(
        self,
        match_sets: Sequence[Dict[str, Any]],
    ) -> Tuple[int, int, List[Dict[str, Any]]]:
        """
        Persist parsed match sets into the Match model.

        Returns:
            Tuple of (created_count, updated_count, skipped_entries).
        """
        created = 0
        updated = 0
        skipped: List[Dict[str, Any]] = []

        with transaction.atomic():
            for group in match_sets:
                tournament_id = group.get("tournament_id")
                if not tournament_id:
                    skipped.append({"reason": "missing_tournament_id", "group": group})
                    continue

                try:
                    tournament = Tournament.objects.get(id=tournament_id)
                except Tournament.DoesNotExist:
                    skipped.append({"reason": "tournament_not_found", "tournament_id": tournament_id})
                    continue

                for entry in group.get("matches", []):
                    match_url = entry.get("match_url")
                    team_one_id = entry.get("team_one_id")
                    team_two_id = entry.get("team_two_id")

                    if not match_url or not team_one_id or not team_two_id:
                        skipped.append({
                            "reason": "missing_core_fields",
                            "match_url": match_url,
                            "team_one_id": team_one_id,
                            "team_two_id": team_two_id,
                        })
                        continue

                    team_one = Team.objects.filter(id=team_one_id).first()
                    team_two = Team.objects.filter(id=team_two_id).first()
                    if not team_one or not team_two:
                        skipped.append({
                            "reason": "team_lookup_failed",
                            "match_url": match_url,
                            "team_one_id": team_one_id,
                            "team_two_id": team_two_id,
                        })
                        continue

                    date_obj = self._coerce_date(entry.get("date_iso") or entry.get("date_text"))

                    defaults = {
                        "tournament": tournament,
                        "team_one": team_one,
                        "team_two": team_two,
                        "team_one_score": entry.get("team_one_score"),
                        "team_two_score": entry.get("team_two_score"),
                        "week": entry.get("week", ""),
                        "patch": entry.get("patch", ""),
                        "date": date_obj,
                    }

                    _, was_created = Match.objects.update_or_create(
                        match_url=match_url,
                        defaults=defaults,
                    )

                    if was_created:
                        created += 1
                    else:
                        updated += 1

        print(
            "Match persistence complete: created=%s updated=%s skipped=%s",
            created,
            updated,
            len(skipped),
        )
        return created, updated, skipped

    def _coerce_date(self, value: Optional[str]) -> Optional[date]:
        """Convert a string date into a date object if possible."""
        if not value:
            return None

        if isinstance(value, date):
            return value

        parsed = parse_date(str(value))
        if parsed is None:
            print("Failed to parse date value '%s' while saving match.", value)
        return parsed
