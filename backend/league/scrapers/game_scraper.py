"""
Game scraper for League of Legends matches/games.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from django.db.models import QuerySet
from django.utils import timezone

from ..models import Champion, Game, Match, Season, Team
from .base import BaseScraper


@dataclass
class TeamBlock:
    """Structured representation of the per-team block on a game page."""

    side: str  # "blue" or "red"
    name: str
    outcome: Optional[str]
    pick_names: List[str]


class GameScraper(BaseScraper):
    """Scraper for game/match data."""

    BASE_URL = "https://gol.gg"

    def __init__(self, base_url: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(base_url=base_url or self.BASE_URL, **kwargs)
        self._team_cache: Dict[str, Optional[Team]] = {}
        self._champion_cache: Dict[str, Optional[Champion]] = {}
        self._team_index_built = False
        self._team_index_by_normalized: Dict[str, Team] = {}
        self._team_index_by_collapsed: Dict[str, Team] = {}
        self._champion_index_built = False
        self._champion_index_by_normalized: Dict[str, Champion] = {}
        self._champion_index_by_collapsed: Dict[str, Champion] = {}

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def scrape(
        self,
        source_url: Optional[str] = None,
        tournament_id: Optional[int] = None,
        season_id: Optional[int] = None,
        match_ids: Optional[Sequence[int]] = None,
        limit: Optional[int] = None,
        save_to_db: bool = False,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        Scrape game data for matches stored in the database.

        Args:
            source_url: Optional match summary URL to restrict scraping.
            tournament_id: Optional tournament ID filter.
            season_id: Optional season ID filter (matched against Tournament.season_name).
            match_ids: Optional iterable of match IDs to restrict scraping.
            limit: Optional maximum number of matches to process.

        Returns:
            List of dictionaries containing lookup/default payloads for Game records.
            When save_to_db is True, games are persisted automatically and the list
            represents the payloads that were saved.
        """
        matches = self._select_matches(
            source_url=source_url,
            tournament_id=tournament_id,
            season_id=season_id,
            match_ids=match_ids,
            limit=limit,
        )

        print(
            f"GameScraper starting scrape. matches={len(matches)} "
            f"tournament_id={tournament_id} season_id={season_id} "
            f"limit={limit} save_to_db={save_to_db}"
        )

        payloads: List[Dict[str, Any]] = []
        total_created = 0
        total_updated = 0

        for idx, match in enumerate(matches, start=1):
            print(
                f"Processing match {idx}/{len(matches)} "
                f"id={match.id} url={match.match_url}"
            )
            match_payloads = self._scrape_games_for_match(match)
            print(
                f"Match scrape complete. match_id={match.id} "
                f"games_found={len(match_payloads)} "
                f"save_to_db={save_to_db}"
            )
            if not match_payloads:
                if save_to_db:
                    print(f"No games scraped for match id={match.id}; nothing to save.")
                continue

            payloads.extend(match_payloads)

            if save_to_db:
                created, updated = self.save_to_database(match_payloads, Game)
                total_created += created
                total_updated += updated
                print(
                    f"Saved games for match id={match.id}. "
                    f"created={created} updated={updated}"
                )

        if save_to_db and payloads:
            print(
                f"GameScraper saved games to database. "
                f"total_created={total_created} total_updated={total_updated}"
            )

        print(
            f"GameScraper completed. matches_processed={len(matches)} "
            f"games_found={len(payloads)}"
        )
        return payloads

    # ------------------------------------------------------------------ #
    # Match selection helpers
    # ------------------------------------------------------------------ #
    def _select_matches(
        self,
        source_url: Optional[str],
        tournament_id: Optional[int],
        season_id: Optional[int],
        match_ids: Optional[Sequence[int]],
        limit: Optional[int],
    ) -> List[Match]:
        """Construct a queryset for matches that should be scraped."""
        # Build queryset - use only() to avoid select_related issues with NULL foreign keys
        # Override Meta ordering to avoid issues with team_one__name and team_two__name
        qs = Match.objects.all().order_by('id')
        
        if source_url:
            qs = qs.filter(match_url=source_url)
            print(f"Filtering matches by source_url={source_url}")
        
        if match_ids:
            qs = qs.filter(id__in=list(match_ids))
            print(f"Filtering matches by match_ids={list(match_ids)}")
        
        if tournament_id:
            qs = qs.filter(tournament_id=tournament_id)
            print(f"Filtering matches by tournament_id={tournament_id}")
        
        if season_id:
            season = Season.objects.filter(id=season_id).only("name").first()
            if season is None:
                print(f"Season with id={season_id} not found. season filter skipped.")
            else:
                qs = qs.filter(tournament__season_name__iexact=season.name)
                print(
                    f"Filtering matches by season_name='{season.name}' "
                    f"(season_id={season_id})"
                )
        
        if limit is not None and limit > 0:
            qs = qs[:limit]
            print(f"Limiting matches queryset to {limit} record(s)")
        
        # Use only() to fetch essential fields - this avoids select_related issues
        # We'll load related objects on-demand when needed
        qs = qs.only('id', 'match_url', 'tournament_id', 'team_one_id', 'team_two_id', 'date')
        
        queryset_count = qs.count()
        print(f"Match queryset count: {queryset_count}")
        
        # Fetch matches - use iterator for large querysets
        if queryset_count > 10000:
            print("Large queryset detected, using iterator()...")
            matches = list(qs.iterator(chunk_size=1000))
        else:
            matches = list(qs)
        
        print(f"Successfully fetched {len(matches)} matches")
        
        if not matches and source_url:
            print(
                f"No matches found for source_url={source_url}. "
                "The scraper will perform no work."
            )
        elif not matches:
            print("No matches available to scrape.")
        return matches

    # ------------------------------------------------------------------ #
    # Match-level scraping
    # ------------------------------------------------------------------ #
    def _scrape_games_for_match(self, match: Match) -> List[Dict[str, Any]]:
        """Fetch the match summary page and scrape individual game links."""
        if not match.match_url:
            print(f"Match id={match.id} missing match_url. Skipping.")
            return []

        response = self.fetch_page(match.match_url)
        if response is None:
            print(
                f"Failed to fetch match summary for match id={match.id} "
                f"url={match.match_url}"
            )
            return []

        soup = self.parse_html(response.text)
        if soup is None:
            print(f"Unable to parse match summary HTML for match id={match.id}")
            return []

        game_links = self._extract_game_links(soup, match.match_url)
        if not game_links:
            print(
                f"No individual game links found for match id={match.id} "
                f"url={match.match_url}"
            )
            return []

        payloads: List[Dict[str, Any]] = []

        for order, (game_number, game_url) in enumerate(game_links, start=1):
            game_payload = self._scrape_single_game(
                match,
                game_url,
                order,
                game_number=game_number or order,
            )
            if game_payload:
                payloads.append(game_payload)

        print(
            f"Scraped {len(payloads)} game(s) for match id={match.id} "
            f"url={match.match_url}"
        )
        return payloads

    def _extract_game_links(self, soup: BeautifulSoup, base_url: str) -> List[Tuple[Optional[int], str]]:
        """Extract the per-game URLs from the match navigation menu."""
        nav_container = soup.select_one("#gameMenuToggler ul")
        if nav_container is None:
            print(f"Game menu toggler not present on page: {base_url}")
            return []

        links: List[Tuple[Optional[int], str]] = []
        seen: Set[str] = set()

        for anchor in nav_container.find_all("a", href=True):
            href = (anchor.get("href") or "").strip()
            if not href:
                continue
            if "page-game" not in href:
                # Skip preview/summary links.
                continue

            absolute_url = urljoin(f"{self.BASE_URL.rstrip('/')}/", href.lstrip("/"))
            if absolute_url in seen:
                continue

            game_number = self._extract_game_number(anchor.get_text(strip=True))
            links.append((game_number, absolute_url))
            seen.add(absolute_url)

        # Sort by detected game number, falling back to insertion order.
        links.sort(key=lambda item: (item[0] is None, item[0] or 0))
        return links

    def _extract_game_number(self, text: Optional[str]) -> Optional[int]:
        """Best-effort extraction of the game number from link text."""
        if not text:
            return None
        match = re.search(r"game\s*(\d+)", text, flags=re.IGNORECASE)
        if not match:
            return None
        try:
            return int(match.group(1))
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------------ #
    # Game-level scraping
    # ------------------------------------------------------------------ #
    def _scrape_single_game(
        self, match: Match, game_url: str, order: int, game_number: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch and parse a single game page."""
        response = self.fetch_page(game_url)
        if response is None:
            print(
                f"Failed to fetch game page for match id={match.id} "
                f"order={order} url={game_url}"
            )
            return None

        soup = self.parse_html(response.text)
        if soup is None:
            print(
                f"Unable to parse game HTML for match id={match.id} "
                f"order={order}"
            )
            return None

        team_blocks = self._extract_team_blocks(soup)
        if len(team_blocks) != 2:
            print(
                f"Expected 2 team blocks but found {len(team_blocks)} "
                f"for match id={match.id} order={order} url={game_url}"
            )
            return None

        blue_block = next((tb for tb in team_blocks if tb.side == "blue"), team_blocks[0])
        red_block = next((tb for tb in team_blocks if tb.side == "red"), team_blocks[-1])

        blue_team = self._resolve_team(blue_block.name, match)
        red_team = self._resolve_team(red_block.name, match)

        if blue_team is None or red_team is None:
            print(
                f"Failed to resolve teams for match id={match.id} "
                f"order={order} blue='{blue_block.name}' red='{red_block.name}'"
            )
            return None

        winning_team = self._determine_winner(blue_block, red_block, blue_team, red_team)

        blue_picks = self._resolve_champion_picks(blue_block.pick_names)
        red_picks = self._resolve_champion_picks(red_block.pick_names)

        defaults: Dict[str, Any] = {
            "blue_team": blue_team,
            "red_team": red_team,
            "winning_team": winning_team,
            "game_url": game_url,
            "date": match.date or timezone.now().date(),
        }

        for idx, champion in enumerate(blue_picks, start=1):
            defaults[f"blue_team_champion_pick_{idx}"] = champion
        for idx in range(len(blue_picks) + 1, 6):
            defaults[f"blue_team_champion_pick_{idx}"] = None

        for idx, champion in enumerate(red_picks, start=1):
            defaults[f"red_team_champion_pick_{idx}"] = champion
        for idx in range(len(red_picks) + 1, 6):
            defaults[f"red_team_champion_pick_{idx}"] = None

        resolved_game_number = game_number or order

        payload = {
            "match_id": match.id,
            "match_url": match.match_url,
            "game_order": order,
            "game_number": resolved_game_number,
            "lookup": {
                "match": match,
                "game_url": game_url,
            },
            "defaults": defaults,
        }

        payload["defaults"]["game_number"] = resolved_game_number

        return payload

    def _extract_team_blocks(self, soup: BeautifulSoup) -> List[TeamBlock]:
        """Extract structured team blocks from a game page."""
        wrapper = soup.find("div", class_="col-cadre")
        if wrapper is None:
            print("col-cadre wrapper not found on game page.")
            return []

        candidates: Iterable[Tag] = wrapper.select("div.col-12.col-sm-6")

        blocks: List[TeamBlock] = []
        for element in candidates:
            header = element.find("div", class_="blue-line-header")
            side = "blue"
            if header is None:
                header = element.find("div", class_="red-line-header")
                side = "red"
            if header is None:
                continue

            link = header.find("a")
            team_name = link.get_text(strip=True) if link else header.get_text(strip=True)
            outcome = self._extract_outcome(header.get_text(" ", strip=True))

            picks = self._extract_picks_from_block(element)
            blocks.append(TeamBlock(side=side, name=team_name, outcome=outcome, pick_names=picks))

        # Deduplicate by side (keep first occurrence).
        filtered: Dict[str, TeamBlock] = {}
        for block in blocks:
            if block.side not in filtered:
                filtered[block.side] = block
        return list(filtered.values())

    def _extract_outcome(self, text: Optional[str]) -> Optional[str]:
        """Parse the WIN/LOSS outcome from header text."""
        if not text:
            return None
        upper = text.upper()
        if "WIN" in upper:
            return "WIN"
        if "LOSS" in upper or "LOSE" in upper:
            return "LOSS"
        return None

    def _extract_picks_from_block(self, element: Tag) -> List[str]:
        """Extract ordered champion pick names for a team."""
        for row in element.find_all("div", class_="row"):
            label_cell = row.find(
                "div",
                class_="col-2",
                string=lambda value: isinstance(value, str) and value.strip().lower() == "picks",
            )
            if not label_cell:
                continue

            picks_container = label_cell.find_next_sibling("div", class_="col-10")
            if picks_container is None:
                continue

            picks: List[str] = []
            for img in picks_container.find_all("img", alt=True):
                alt_text = (img.get("alt") or "").strip()
                if alt_text:
                    picks.append(alt_text)
            return picks

        return []

    # ------------------------------------------------------------------ #
    # Resolution helpers
    # ------------------------------------------------------------------ #
    def _determine_winner(
        self,
        blue_block: TeamBlock,
        red_block: TeamBlock,
        blue_team: Team,
        red_team: Team,
    ) -> Optional[Team]:
        """Determine the winning team based on parsed outcomes."""
        if blue_block.outcome == "WIN" and red_block.outcome == "LOSS":
            return blue_team
        if red_block.outcome == "WIN" and blue_block.outcome == "LOSS":
            return red_team
        # In case of missing/ambiguous data, fall back to None.
        return None

    def _resolve_team(self, raw_name: str, match: Match) -> Optional[Team]:
        """Resolve a team name to a Team object."""
        normalized = self._normalize_name(raw_name)
        collapsed = self._normalize_name(raw_name, collapse=True)
        if not normalized:
            return None

        if normalized in self._team_cache:
            return self._team_cache[normalized]
        if collapsed in self._team_cache:
            return self._team_cache[collapsed]

        # Load teams on-demand since we're using only() to avoid select_related issues
        team_one = None
        team_two = None
        if match.team_one_id:
            try:
                team_one = Team.objects.get(id=match.team_one_id)
            except Team.DoesNotExist:
                pass
        if match.team_two_id:
            try:
                team_two = Team.objects.get(id=match.team_two_id)
            except Team.DoesNotExist:
                pass

        for candidate in filter(None, [team_one, team_two]):
            candidate_normalized = self._normalize_name(candidate.name)
            candidate_collapsed = self._normalize_name(candidate.name, collapse=True)
            if candidate_normalized == normalized or candidate_collapsed == collapsed:
                self._team_cache[normalized] = candidate
                self._team_cache.setdefault(collapsed, candidate)
                return candidate

        team = Team.objects.filter(name__iexact=raw_name.strip()).first()
        if team is None:
            team = Team.objects.filter(name__icontains=raw_name.strip()).first()
        if team is None:
            self._ensure_team_index()
            team = self._team_index_by_normalized.get(normalized)
        if team is None:
            collapsed = self._normalize_name(raw_name, collapse=True)
            self._ensure_team_index()
            team = self._team_index_by_collapsed.get(collapsed)

        self._team_cache[normalized] = team
        if collapsed:
            self._team_cache.setdefault(collapsed, team)
        return team

    def _resolve_champion_picks(self, pick_names: Sequence[str]) -> List[Optional[Champion]]:
        """Resolve champion names to Champion model instances."""
        resolved: List[Optional[Champion]] = []
        for name in pick_names[:5]:
            champion = self._resolve_champion(name)
            if champion is None:
                print(f"Champion '{name}' not found in database.")
            resolved.append(champion)

        # Ensure the list has exactly 5 entries (pad with None).
        while len(resolved) < 5:
            resolved.append(None)
        return resolved

    def _resolve_champion(self, raw_name: str) -> Optional[Champion]:
        """Resolve a single champion by name, caching the lookup."""
        normalized = self._normalize_name(raw_name)
        collapsed = self._normalize_name(raw_name, collapse=True)
        if not normalized:
            return None

        if normalized in self._champion_cache:
            return self._champion_cache[normalized]
        if collapsed in self._champion_cache:
            return self._champion_cache[collapsed]

        champion = Champion.objects.filter(name__iexact=raw_name.strip()).first()
        if champion is None:
            champion = Champion.objects.filter(name__icontains=raw_name.strip()).first()
        if champion is None:
            self._ensure_champion_index()
            champion = self._champion_index_by_normalized.get(normalized)
        if champion is None:
            collapsed = self._normalize_name(raw_name, collapse=True)
            self._ensure_champion_index()
            champion = self._champion_index_by_collapsed.get(collapsed)

        self._champion_cache[normalized] = champion
        if collapsed:
            self._champion_cache.setdefault(collapsed, champion)
        return champion

    def _ensure_team_index(self) -> None:
        """Build lookup dictionaries for teams if not already built."""
        if self._team_index_built:
            return
        self._team_index_built = True
        for team in Team.objects.all().only("id", "name"):
            normalized = self._normalize_name(team.name)
            collapsed = self._normalize_name(team.name, collapse=True)
            self._team_index_by_normalized.setdefault(normalized, team)
            self._team_index_by_collapsed.setdefault(collapsed, team)

    def _ensure_champion_index(self) -> None:
        """Build lookup dictionaries for champions if not already built."""
        if self._champion_index_built:
            return
        self._champion_index_built = True
        for champion in Champion.objects.all().only("id", "name"):
            normalized = self._normalize_name(champion.name)
            collapsed = self._normalize_name(champion.name, collapse=True)
            self._champion_index_by_normalized.setdefault(normalized, champion)
            self._champion_index_by_collapsed.setdefault(collapsed, champion)

    def persist_games(self, payloads: Sequence[Dict[str, Any]]) -> Tuple[int, int]:
        """
        Convenience wrapper to save scraped games.

        Args:
            payloads: List of payload dictionaries produced by scrape().

        Returns:
            Tuple of (created_count, updated_count).
        """
        if not payloads:
            return 0, 0
        return self.save_to_database(payloads, Game)

    @staticmethod
    def _normalize_name(value: str, collapse: bool = False) -> str:
        """Normalize names for comparison."""
        cleaned = re.sub(r"\s+", " ", (value or "").strip()).lower()
        if collapse:
            cleaned = re.sub(r"[^a-z0-9]", "", cleaned)
        return cleaned