from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ChampionViewSet, PatchViewSet, ChampionPatchViewSet,
    TournamentViewSet, TeamViewSet, TeamTournamentViewSet,
    SeasonViewSet, WinLossRecordViewSet, GameViewSet
)
from .scraper_views import ScraperViewSet, scraper_health

router = DefaultRouter()
router.register(r'champions', ChampionViewSet)
router.register(r'patches', PatchViewSet)
router.register(r'champion-patches', ChampionPatchViewSet)
router.register(r'tournaments', TournamentViewSet)
router.register(r'teams', TeamViewSet)
router.register(r'team-tournaments', TeamTournamentViewSet)
router.register(r'seasons', SeasonViewSet)
router.register(r'win-loss-records', WinLossRecordViewSet)
router.register(r'games', GameViewSet)
router.register(r'scrapers', ScraperViewSet, basename='scrapers')

app_name = 'league'

urlpatterns = [
    path('', include(router.urls)),
    path('scrapers/health/', scraper_health, name='scraper-health'),
]
