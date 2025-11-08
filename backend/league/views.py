from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import (
    Role, Champion, Patch, ChampionPatch, Tournament,
    Team, TeamTournament, Season, ChampionSeasonStats, Game
)
from .serializers import (
    RoleSerializer, ChampionSerializer,
    PatchSerializer, ChampionPatchSerializer,
    TournamentSerializer, TeamSerializer,
    TeamTournamentSerializer, SeasonSerializer,
    ChampionSeasonStatsSerializer, GameSerializer
)


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    search_fields = ['name']


class ChampionViewSet(viewsets.ModelViewSet):
    queryset = Champion.objects.prefetch_related('roles').all()
    serializer_class = ChampionSerializer
    filterset_fields = ['roles', 'primary_damage_type']
    search_fields = ['name']


class PatchViewSet(viewsets.ModelViewSet):
    queryset = Patch.objects.all()
    serializer_class = PatchSerializer
    search_fields = ['version_num']


class ChampionPatchViewSet(viewsets.ModelViewSet):
    queryset = ChampionPatch.objects.select_related('champion', 'patch').all()
    serializer_class = ChampionPatchSerializer
    filterset_fields = ['champion', 'patch', 'change_type']


class TournamentViewSet(viewsets.ModelViewSet):
    queryset = Tournament.objects.select_related('patch').all()
    serializer_class = TournamentSerializer
    filterset_fields = ['tier', 'patch']
    search_fields = ['name']


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    filterset_fields = ['region']
    search_fields = ['name', 'region']


class SeasonViewSet(viewsets.ModelViewSet):
    queryset = Season.objects.all()
    serializer_class = SeasonSerializer
    search_fields = ['name']


class ChampionSeasonStatsViewSet(viewsets.ModelViewSet):
    queryset = ChampionSeasonStats.objects.select_related('champion', 'season').all()
    serializer_class = ChampionSeasonStatsSerializer
    filterset_fields = ['champion', 'season']


class TeamTournamentViewSet(viewsets.ModelViewSet):
    queryset = TeamTournament.objects.select_related('team', 'tournament').all()
    serializer_class = TeamTournamentSerializer
    filterset_fields = ['team', 'tournament', 'placement']


class GameViewSet(viewsets.ModelViewSet):
    queryset = Game.objects.select_related(
        'patch', 'tournament', 'season', 'blue_team', 'red_team', 'winning_team',
        'top_lane_winning_team', 'mid_lane_winning_team', 'bot_lane_winning_team',
        'red_team_champion_pick_1', 'red_team_champion_pick_2', 'red_team_champion_pick_3',
        'red_team_champion_pick_4', 'red_team_champion_pick_5',
        'blue_team_champion_pick_1', 'blue_team_champion_pick_2', 'blue_team_champion_pick_3',
        'blue_team_champion_pick_4', 'blue_team_champion_pick_5'
    ).all()
    serializer_class = GameSerializer
    filterset_fields = ['patch', 'tournament', 'season', 'blue_team', 'red_team', 'winning_team', 'date']
    search_fields = ['blue_team__name', 'red_team__name', 'tournament__name']

    @action(detail=True, methods=['get'])
    def picks(self, request, pk=None):
        """Get champion picks for a specific game"""
        game = self.get_object()
        return Response({
            'red_team_picks': game.get_red_team_picks(),
            'blue_team_picks': game.get_blue_team_picks()
        })
