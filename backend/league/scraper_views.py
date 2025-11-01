"""
API endpoints for triggering scraping processes.
"""
import logging
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ViewSet
from django.utils import timezone
from .models import Champion, Patch, Game, Tournament, Season
from .scrapers.champion_scraper import ChampionScraper
from .scrapers.patch_scraper import PatchScraper
from .scrapers.game_scraper import GameScraper

logger = logging.getLogger(__name__)


class ScraperViewSet(ViewSet):
    """ViewSet for scraper endpoints."""
    
    permission_classes = [AllowAny]  # Adjust permissions as needed
    
    @action(detail=False, methods=['post'], url_path='champions')
    def scrape_champions(self, request):
        """
        Trigger champion scraping.
        
        POST /api/league/scrapers/champions/
        
        Body (optional):
        {
            "source_url": "https://example.com/champions",
            "save_to_db": true
        }
        """
        try:
            source_url = request.data.get('source_url')
            save_to_db = request.data.get('save_to_db', True)
            
            scraper = ChampionScraper()
            data = scraper.scrape(source_url=source_url)
            
            if save_to_db and data:
                created, updated = scraper.save_to_database(data, Champion)
                return Response({
                    'status': 'success',
                    'message': f'Scraped {len(data)} champions',
                    'created': created,
                    'updated': updated,
                    'timestamp': timezone.now().isoformat()
                }, status=status.HTTP_200_OK)
            
            return Response({
                'status': 'success',
                'message': f'Scraped {len(data)} champions',
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
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        Get scraper status/info.
        
        GET /api/league/scrapers/status/
        """
        return Response({
            'status': 'active',
            'available_scrapers': ['champions', 'patches', 'games'],
            'timestamp': timezone.now().isoformat()
        })


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

