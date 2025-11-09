"""
Team scraper scaffolding for fetching raw HTML pages.
"""
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction

from ..models import Team, Season, TeamSeasonStats
from .base import BaseScraper


class TeamScraper(BaseScraper):
    """Scraper that fetches team statistics and prepares them for persistence."""

    COLUMN_MAPPING = {
        'name': ('team_name', None),
        'season': ('season', None),
        'region': ('region', None),
        'games': ('games', '_parse_int'),
        'win rate': ('winrate', '_parse_percent'),
        'winrate': ('winrate', '_parse_percent'),
        'k:d': ('kill_death_ratio', '_parse_float'),
        'gpm': ('gpm', '_parse_int'),
        'gdm': ('gdm', '_parse_int'),
        'game duration': ('game_duration', '_parse_duration'),
        'kills / game': ('kills_per_game', '_parse_float'),
        'deaths / game': ('deaths_per_game', '_parse_float'),
        'towers killed': ('towers_killed', '_parse_float'),
        'towers lost': ('towers_lost', '_parse_float'),
        'fb%': ('first_blood_percent', '_parse_percent'),
        'ft%': ('first_tower_percent', '_parse_percent'),
        'fos%': ('first_objective_percent', '_parse_percent'),
        'drapg': ('dragons_per_game', '_parse_float'),
        'dra%': ('dragon_control_percent', '_parse_percent'),
        'vgpg': ('void_grub_per_game', '_parse_float'),
        'her%': ('herald_percent', '_parse_percent'),
        'atakhan%': ('atakhan_percent', '_parse_percent'),
        'dra@15': ('dragons_at_15', '_parse_float'),
        'td@15': ('tower_difference_15', '_parse_float'),
        'gd@15': ('gold_difference_15', '_parse_int'),
        'ppg': ('points_per_game', '_parse_float'),
        'nashpg': ('nashors_per_game', '_parse_float'),
        'nash%': ('nashor_percent', '_parse_percent'),
        'csm': ('csm', '_parse_float'),
        'dpm': ('dpm', '_parse_int'),
        'wpm': ('wards_per_minute', '_parse_float'),
        'vwpm': ('vision_wards_per_minute', '_parse_float'),
        'wcpm': ('wards_cleared_per_minute', '_parse_float'),
    }

    def _parse_int(self, value: str, default: int = 0) -> int:
        cleaned = (value or '').strip().replace(',', '')
        if not cleaned or cleaned == '-':
            return default
        try:
            return int(float(cleaned))
        except (ValueError, TypeError):
            return default

    def _parse_float(self, value: str, default: float = 0.0) -> float:
        cleaned = (value or '').strip().replace(',', '')
        if not cleaned or cleaned == '-':
            return default
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return default

    def _parse_percent(self, value: str) -> Decimal:
        cleaned = (value or '').strip().replace('%', '').replace(',', '')
        if not cleaned or cleaned == '-':
            return Decimal('0.00')
        try:
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            return Decimal('0.00')

    def _parse_duration(self, value: str) -> Optional[timedelta]:
        cleaned = (value or '').strip()
        if not cleaned or cleaned == '-':
            return None
        try:
            parts = cleaned.split(':')
            if len(parts) == 2:
                minutes, seconds = int(parts[0]), int(parts[1])
                return timedelta(minutes=minutes, seconds=seconds)
            if len(parts) == 3:
                hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
                return timedelta(hours=hours, minutes=minutes, seconds=seconds)
        except (ValueError, TypeError):
            return None
        return None

    def _normalize_header(self, header: str) -> str:
        return (header or '').strip().lower()

    def _convert_row_to_stats(
        self,
        row: Dict[str, str],
        season_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        stats: Dict[str, Any] = {}
        for header, value in row.items():
            normalized = self._normalize_header(header)
            mapping = self.COLUMN_MAPPING.get(normalized)
            if not mapping:
                continue
            field_name, parser_name = mapping
            if parser_name:
                parser = getattr(self, parser_name)
                stats[field_name] = parser(value)
            else:
                stats[field_name] = (value or '').strip()

        if season_name and not stats.get('season'):
            stats['season'] = season_name

        return stats

    def _extract_table_data(self, html: str, season_name: Optional[str] = None) -> Dict[str, Any]:
        """Parse the playerslist table from the provided HTML."""
        soup = self.parse_html(html)
        if soup is None:
            return {
                'error': 'Failed to parse HTML content',
                'table': None,
                'team_stats': [],
            }

        table = soup.find('table', class_='playerslist')
        if table is None:
            return {
                'error': 'No table with class "playerslist" found on the page',
                'table': None,
                'team_stats': [],
            }

        headers: List[str] = []
        header_row = None

        thead = table.find('thead')
        if thead:
            header_row = thead.find('tr')
        if header_row is None:
            header_row = table.find('tr')

        if header_row:
            headers = [
                cell.get_text(strip=True)
                for cell in header_row.find_all(['th', 'td'])
            ]

        body_rows = []
        tbody = table.find('tbody')
        if tbody:
            body_rows = tbody.find_all('tr')
        else:
            all_rows = table.find_all('tr')
            if header_row in all_rows:
                header_index = all_rows.index(header_row)
                body_rows = all_rows[header_index + 1:]
            else:
                body_rows = all_rows

        rows: List[Dict[str, str]] = []
        team_stats: List[Dict[str, Any]] = []

        for row in body_rows:
            cells = row.find_all('td')
            if not cells:
                continue

            cell_values = [cell.get_text(strip=True) for cell in cells]
            row_data: Dict[str, str] = {}
            for index, value in enumerate(cell_values):
                if index < len(headers) and headers[index]:
                    key = headers[index]
                else:
                    key = f'column_{index + 1}'
                row_data[key] = value

            rows.append(row_data)

            stats = self._convert_row_to_stats(row_data, season_name=season_name)
            if stats:
                team_stats.append(stats)

        return {
            'error': None,
            'table': {
                'headers': headers,
                'rows': rows,
            },
            'team_stats': team_stats,
        }

    def scrape(self, source_url: Optional[str] = None, season_name: Optional[str] = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch the HTML content for the provided source URL and parse team statistics.

        Args:
            source_url: URL to fetch
            season_name: Optional season context to enforce on parsed rows

        Returns:
            List containing a single dictionary with response metadata and parsed content,
            or an error payload when the fetch fails.
        """
        if not source_url:
            return [{
                'error': 'source_url is required',
                'data': None,
            }]

        response = self.fetch_page(source_url)

        if response is None:
            return [{
                'error': f'Failed to fetch {source_url}',
                'data': None,
            }]

        table_data = self._extract_table_data(response.text, season_name=season_name)

        if table_data.get('error'):
            return [{
                'error': table_data['error'],
                'data': None,
                'source_url': source_url,
                'status_code': response.status_code,
                'encoding': response.encoding,
                'headers': dict(response.headers),
                'html': response.text,
            }]

        return [{
            'source_url': source_url,
            'status_code': response.status_code,
            'encoding': response.encoding,
            'headers': dict(response.headers),
            'table': table_data['table'],
            'team_stats': table_data['team_stats'],
            # 'html': response.text,
        }]

    def save_stats_to_database(
        self,
        team_stats: List[Dict[str, Any]],
        season_name: Optional[str] = None,
    ) -> Tuple[int, int, List[str], List[Dict[str, Any]]]:
        """
        Persist parsed team statistics to the database.

        Returns:
            Tuple containing:
                - count of created TeamSeasonStats records
                - count of updated TeamSeasonStats records
                - list of team names that were newly created
                - list of rows skipped due to missing information
        """
        if not team_stats:
            return 0, 0, [], []

        created_stats = 0
        updated_stats = 0
        created_teams: List[str] = []
        skipped_rows: List[Dict[str, Any]] = []

        with transaction.atomic():
            for entry in team_stats:
                team_name = entry.get('team_name')
                row_season = entry.get('season') or season_name

                if not team_name or not row_season:
                    skipped_rows.append(entry)
                    continue

                season_obj, _ = Season.objects.get_or_create(name=row_season)

                region_snapshot = (entry.get('region') or '').strip()
                team_region = region_snapshot[:50] if region_snapshot else 'Unknown'

                team_obj, team_created = Team.objects.get_or_create(
                    name=team_name,
                    defaults={'region': team_region}
                )

                if team_created:
                    created_teams.append(team_name)
                elif region_snapshot and team_obj.region != region_snapshot:
                    team_obj.region = region_snapshot[:50]
                    team_obj.save(update_fields=['region'])

                defaults = {
                    'region': region_snapshot[:10] if region_snapshot else team_obj.region[:10],
                    'games': entry.get('games', 0),
                    'winrate': entry.get('winrate', Decimal('0.00')),
                    'kill_death_ratio': entry.get('kill_death_ratio', 0.0),
                    'gpm': entry.get('gpm', 0),
                    'gdm': entry.get('gdm', 0),
                    'game_duration': entry.get('game_duration'),
                    'kills_per_game': entry.get('kills_per_game', 0.0),
                    'deaths_per_game': entry.get('deaths_per_game', 0.0),
                    'towers_killed': entry.get('towers_killed', 0.0),
                    'towers_lost': entry.get('towers_lost', 0.0),
                    'first_blood_percent': entry.get('first_blood_percent', Decimal('0.00')),
                    'first_tower_percent': entry.get('first_tower_percent', Decimal('0.00')),
                    'first_objective_percent': entry.get('first_objective_percent', Decimal('0.00')),
                    'dragons_per_game': entry.get('dragons_per_game', 0.0),
                    'dragon_control_percent': entry.get('dragon_control_percent', Decimal('0.00')),
                    'void_grub_per_game': entry.get('void_grub_per_game', 0.0),
                    'herald_percent': entry.get('herald_percent', Decimal('0.00')),
                    'atakhan_percent': entry.get('atakhan_percent', Decimal('0.00')),
                    'dragons_at_15': entry.get('dragons_at_15', 0.0),
                    'tower_difference_15': entry.get('tower_difference_15', 0.0),
                    'gold_difference_15': entry.get('gold_difference_15', 0),
                    'points_per_game': entry.get('points_per_game', 0.0),
                    'nashors_per_game': entry.get('nashors_per_game', 0.0),
                    'nashor_percent': entry.get('nashor_percent', Decimal('0.00')),
                    'csm': entry.get('csm', 0.0),
                    'dpm': entry.get('dpm', 0),
                    'wards_per_minute': entry.get('wards_per_minute', 0.0),
                    'vision_wards_per_minute': entry.get('vision_wards_per_minute', 0.0),
                    'wards_cleared_per_minute': entry.get('wards_cleared_per_minute', 0.0),
                }

                stats_obj, created = TeamSeasonStats.objects.update_or_create(
                    team=team_obj,
                    season=season_obj,
                    defaults=defaults,
                )

                if created:
                    created_stats += 1
                else:
                    updated_stats += 1

        return created_stats, updated_stats, created_teams, skipped_rows

