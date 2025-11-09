"""
API endpoints for triggering scraping processes.
"""
import logging
from typing import Any, Dict, List
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ViewSet
from django.utils import timezone
from .models import Patch, Game

logger = logging.getLogger(__name__)

# Lazy imports to avoid import errors at startup
try:
    from .scrapers.champion_scraper import ChampionScraper
    from .scrapers.patch_scraper import PatchScraper
    from .scrapers.game_scraper import GameScraper
    from .scrapers.match_scraper import MatchScraper
    from .scrapers.team_scraper import TeamScraper
    from .scrapers.tournament_scraper import TournamentScraper
except ImportError as e:
    logger.warning(f"Failed to import scrapers: {e}")
    ChampionScraper = None
    PatchScraper = None
    GameScraper = None
    MatchScraper = None
    TeamScraper = None
    TournamentScraper = None


class ScraperViewSet(ViewSet):
    """ViewSet for scraper endpoints."""
    
    permission_classes = [AllowAny]  # Adjust permissions as needed
    
    @action(detail=False, methods=['post'], url_path='scrape-champions')
    def scrape_champions(self, request):
        """
        Trigger champion scraping.
        
        POST /api/league/scrapers/scrape-champions/
        
        Body (optional):
        {
            "source_url": "https://example.com/champions",  # URL to scrape OR file path
            "file_path": "champion_table.html",  # Optional: explicit path to local HTML file (relative to scraper dir)
            "season_name": "2024 Spring",  # Required when save_to_db is true
            "save_to_db": true  # If true, saves parsed champion stats to database
        }
        
        Note: 
        - If you save the rendered HTML from your browser (with JavaScript executed),
          you can pass the file path to scrape from the local file instead of the URL.
        - The scraper parses all rows after the header row and stores per-season ChampionSeasonStats.
        - Champion records are never created or modified by this endpoint.
        """
        try:
            if ChampionScraper is None:
                return Response({
                    'status': 'error',
                    'message': 'ChampionScraper is not available'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            source_url = request.data.get('source_url')
            file_path = request.data.get('file_path')  # Optional: path to local HTML file
            save_to_db = request.data.get('save_to_db', False)  # Default to False
            season_name = request.data.get('season_name')

            if save_to_db and not season_name:
                return Response({
                    'status': 'error',
                    'message': 'season_name is required when save_to_db is true'
                }, status=status.HTTP_400_BAD_REQUEST)

            scraper = ChampionScraper()
            data = scraper.scrape(source_url=source_url, file_path=file_path, season_name=season_name)
            
            # Extract champions data from the response
            scraped_response = data[0] if data else {}
            champion_stats = scraped_response.get('champion_stats', [])
            
            # Save to database if requested
            created_count = 0
            updated_count = 0
            missing_champions = []
            if save_to_db:
                created_count, updated_count, missing_champions = scraper.save_stats_to_database(
                    season_name=season_name
                )
            
            return Response({
                'status': 'success',
                'source_url': source_url,
                'file_path': file_path,
                'season_name': season_name,
                'champions_parsed': len(champion_stats),
                'stats_created': created_count if save_to_db else None,
                'stats_updated': updated_count if save_to_db else None,
                'missing_champions': missing_champions if save_to_db else [],
                'champion_stats': champion_stats,
                'save_to_db': save_to_db,
                'data': data,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Champion scraping failed: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='patches')
    def scrape_patches(self, request):
        """
        Trigger patch scraping.
        
        POST /api/league/scrapers/patches/
        
        Body (optional):
        {
            "source_url": "https://example.com/patches",
            "save_to_db": true
        }
        """
        try:
            if PatchScraper is None:
                return Response({
                    'status': 'error',
                    'message': 'PatchScraper is not available'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            source_url = request.data.get('source_url')
            save_to_db = request.data.get('save_to_db', True)
            
            scraper = PatchScraper()
            data = scraper.scrape(source_url=source_url)
            
            if save_to_db and data:
                created, updated = scraper.save_to_database(data, Patch)
                return Response({
                    'status': 'success',
                    'message': f'Scraped {len(data)} patches',
                    'created': created,
                    'updated': updated,
                    'timestamp': timezone.now().isoformat()
                }, status=status.HTTP_200_OK)
            
            return Response({
                'status': 'success',
                'message': f'Scraped {len(data)} patches',
                'data': data,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Patch scraping failed: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='games')
    def scrape_games(self, request):
        """
        Trigger game scraping.
        
        POST /api/league/scrapers/games/
        
        Body (optional):
        {
            "source_url": "https://example.com/games",
            "tournament_id": 1,
            "season_id": 1,
            "save_to_db": true
        }
        """
        try:
            if GameScraper is None:
                return Response({
                    'status': 'error',
                    'message': 'GameScraper is not available'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            source_url = request.data.get('source_url')
            tournament_id = request.data.get('tournament_id')
            season_id = request.data.get('season_id')
            save_to_db = request.data.get('save_to_db', True)
            
            scraper = GameScraper()
            data = scraper.scrape(
                source_url=source_url,
                tournament_id=tournament_id,
                season_id=season_id
            )
            
            if save_to_db and data:
                created, updated = scraper.save_to_database(data, Game)
                return Response({
                    'status': 'success',
                    'message': f'Scraped {len(data)} games',
                    'created': created,
                    'updated': updated,
                    'timestamp': timezone.now().isoformat()
                }, status=status.HTTP_200_OK)
            
            return Response({
                'status': 'success',
                'message': f'Scraped {len(data)} games',
                'data': data,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Game scraping failed: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='teams')
    def scrape_teams(self, request):
        """
        Trigger team scraping to extract the playerslist table.

        POST /api/league/scrapers/teams/

        Body:
        {
            "source_url": "https://example.com/team-page"
        }
        """
        try:
            if TeamScraper is None:
                return Response({
                    'status': 'error',
                    'message': 'TeamScraper is not available'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            source_url = request.data.get('source_url')
            season_name = request.data.get('season_name')
            save_to_db = request.data.get('save_to_db', False)

            if not source_url:
                return Response({
                    'status': 'error',
                    'message': 'source_url is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            if save_to_db and not season_name:
                return Response({
                    'status': 'error',
                    'message': 'season_name is required when save_to_db is true'
                }, status=status.HTTP_400_BAD_REQUEST)

            scraper = TeamScraper()
            data = scraper.scrape(source_url=source_url, season_name=season_name)
            scraped_response = data[0] if data else {}

            if scraped_response.get('error'):
                return Response({
                    'status': 'error',
                    'message': scraped_response['error'],
                }, status=status.HTTP_502_BAD_GATEWAY)

            table = scraped_response.get('table', {})
            team_stats = scraped_response.get('team_stats', [])
            stats_created = None
            stats_updated = None
            teams_created = []
            skipped_rows = []

            if save_to_db:
                stats_created, stats_updated, teams_created, skipped_rows = scraper.save_stats_to_database(
                    team_stats=team_stats,
                    season_name=season_name,
                )

            return Response({
                'status': 'success',
                'source_url': scraped_response.get('source_url'),
                'status_code': scraped_response.get('status_code'),
                'encoding': scraped_response.get('encoding'),
                'headers': scraped_response.get('headers'),
                'table': table,
                'team_stats': team_stats,
                'row_count': len(table.get('rows', [])) if table else 0,
                'season_name': season_name,
                'save_to_db': save_to_db,
                'stats_created': stats_created,
                'stats_updated': stats_updated,
                'teams_created': teams_created,
                'skipped_rows': skipped_rows,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Team scraping failed: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        Get scraper status/info.
        
        GET /api/league/scrapers/status/
        """
        return Response({
            'status': 'active',
            'available_scrapers': ['champions', 'patches', 'games', 'teams', 'tournaments', 'matches'],
            'timestamp': timezone.now().isoformat()
        })

    @action(detail=False, methods=['get'], url_path='teams/fetch-page')
    def fetch_team_page(self, request):
        """
        Fetch the raw HTML content for a provided team page URL.

        GET /api/league/scrapers/teams/fetch-page/?source_url=https://example.com
        """
        try:
            if TeamScraper is None:
                return Response({
                    'status': 'error',
                    'message': 'TeamScraper is not available'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            source_url = request.query_params.get('source_url')
            if not source_url:
                return Response({
                    'status': 'error',
                    'message': 'source_url query parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            scraper = TeamScraper()
            data = scraper.scrape(source_url=source_url)
            scraped_response = data[0] if data else {}

            if scraped_response.get('error'):
                return Response({
                    'status': 'error',
                    'message': scraped_response['error'],
                }, status=status.HTTP_502_BAD_GATEWAY)

            html_content = scraped_response.get('html', '')

            return Response({
                'status': 'success',
                'source_url': scraped_response.get('source_url'),
                'status_code': scraped_response.get('status_code'),
                'encoding': scraped_response.get('encoding'),
                'headers': scraped_response.get('headers'),
                'html': html_content,
                'table': scraped_response.get('table'),
                'team_stats': scraped_response.get('team_stats'),
                'row_count': len(scraped_response.get('table', {}).get('rows', [])) if scraped_response.get('table') else 0,
                'content_length': len(html_content),
                'timestamp': scraped_response.get('timestamp') or timezone.now().isoformat()
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Team page fetch failed: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='matches')
    def scrape_matches(self, request):
        """
        Trigger match scraping for tournaments stored in the database.

        POST /api/league/scrapers/matches/

        Body (optional):
        {
            "tournament_names": ["LCS 2024 Spring"],
            "tournament_ids": [1, 2],
            "save_to_db": true
        }
        """
        try:
            print(
                "scrape_matches endpoint called with body=%s",
                request.data,
            )

            if MatchScraper is None:
                print("MatchScraper import unavailable")
                return Response({
                    'status': 'error',
                    'message': 'MatchScraper is not available'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            tournament_names = request.data.get('tournament_names')
            if tournament_names is not None and not isinstance(tournament_names, (list, tuple)):
                print("Invalid tournament_names payload: %s", tournament_names)
                return Response({
                    'status': 'error',
                    'message': 'tournament_names must be a list of strings'
                }, status=status.HTTP_400_BAD_REQUEST)

            tournament_ids = request.data.get('tournament_ids')
            if tournament_ids is not None and not isinstance(tournament_ids, (list, tuple)):
                print("Invalid tournament_ids payload: %s", tournament_ids)
                return Response({
                    'status': 'error',
                    'message': 'tournament_ids must be a list of integers'
                }, status=status.HTTP_400_BAD_REQUEST)

            save_to_db = bool(request.data.get('save_to_db', False))

            scraper = MatchScraper()
            data = scraper.scrape(
                tournament_names=tournament_names,
                tournament_ids=tournament_ids,
            )

            payload = data[0] if data else {}

            matches_created = None
            matches_updated = None
            matches_skipped: List[Dict[str, Any]] = []
            if save_to_db:
                match_sets = payload.get('match_sets', [])
                matches_created, matches_updated, matches_skipped = scraper.save_matches_to_database(match_sets)

            print(
                "Match scraping endpoint returning tournaments_processed=%s total_matches=%s errors=%s",
                payload.get('tournaments_processed'),
                sum(group.get('count', 0) for group in payload.get('match_sets', [])),
                len(payload.get('errors', [])),
            )

            return Response({
                'status': 'success',
                'timestamp': timezone.now().isoformat(),
                'base_url': payload.get('base_url'),
                'tournaments_processed': payload.get('tournaments_processed', 0),
                'match_sets': payload.get('match_sets', []),
                'errors': payload.get('errors', []),
                'requested_tournament_names': payload.get('requested_tournament_names'),
                'requested_tournament_ids': payload.get('requested_tournament_ids'),
                'save_to_db': save_to_db,
                'matches_created': matches_created,
                'matches_updated': matches_updated,
                'matches_skipped': matches_skipped,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Match scraping failed: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='tournaments')
    def scrape_tournaments(self, request):
        """
        Trigger tournament scraping from locally saved HTML snapshots.

        POST /api/league/scrapers/tournaments/

        Body (optional):
        {
            "seasons": ["s15", "s14"],  # Process only the specified tournament list files
            "save_to_db": true          # Persist tournaments into the database
        }
        """
        try:
            if TournamentScraper is None:
                return Response({
                    'status': 'error',
                    'message': 'TournamentScraper is not available'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            seasons = request.data.get('seasons')
            if seasons is not None and not isinstance(seasons, (list, tuple)):
                return Response({
                    'status': 'error',
                    'message': 'seasons must be a list of season identifiers'
                }, status=status.HTTP_400_BAD_REQUEST)

            save_to_db = bool(request.data.get('save_to_db', False))

            scraper = TournamentScraper()
            data = scraper.scrape(seasons=seasons)
            payload = data[0] if data else {}

            fatal_error = payload.get('fatal_error')
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR if fatal_error else status.HTTP_200_OK

            response_body = {
                'status': 'error' if fatal_error else 'success',
                'directory': payload.get('directory'),
                'seasons_requested': payload.get('seasons_requested'),
                'total_tournaments': payload.get('total_tournaments', 0),
                'tournament_sets': payload.get('tournament_sets', []),
                'errors': payload.get('errors', []),
                'timestamp': payload.get('timestamp') or timezone.now().isoformat(),
                'save_to_db': save_to_db,
            }

            if not fatal_error and save_to_db:
                created, updated = scraper.save_to_database(payload.get('tournament_sets', []))
                response_body['created'] = created
                response_body['updated'] = updated

            if fatal_error:
                response_body['message'] = fatal_error

            return Response(response_body, status=status_code)

        except Exception as e:
            logger.error(f"Tournament scraping failed: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def scraper_health(request):
    """
    Health check endpoint for scrapers.
    
    GET /api/league/scrapers/health/
    """
    return Response({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat()
    })

