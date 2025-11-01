from rest_framework import serializers
from .models import (
    Champion, Patch, ChampionPatch, Tournament,
    Team, TeamTournament, Season, WinLossRecord, Game
)


class ChampionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Champion
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class PatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patch
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class ChampionPatchSerializer(serializers.ModelSerializer):
    champion_name = serializers.CharField(source='champion.name', read_only=True)
    patch_version = serializers.CharField(source='patch.version_num', read_only=True)

    class Meta:
        model = ChampionPatch
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class TournamentSerializer(serializers.ModelSerializer):
    patch_version = serializers.CharField(source='patch.version_num', read_only=True)

    class Meta:
        model = Tournament
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class TeamTournamentSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True)
    tournament_name = serializers.CharField(source='tournament.name', read_only=True)

    class Meta:
        model = TeamTournament
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class SeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Season
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class WinLossRecordSerializer(serializers.ModelSerializer):
    champion_name = serializers.CharField(source='champion.name', read_only=True)
    season_name = serializers.CharField(source='season.name', read_only=True)
    win_rate = serializers.FloatField(read_only=True)

    class Meta:
        model = WinLossRecord
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'win_rate']


class GameSerializer(serializers.ModelSerializer):
    blue_team_name = serializers.CharField(source='blue_team.name', read_only=True)
    red_team_name = serializers.CharField(source='red_team.name', read_only=True)
    winning_team_name = serializers.CharField(source='winning_team.name', read_only=True, allow_null=True)
    patch_version = serializers.CharField(source='patch.version_num', read_only=True, allow_null=True)
    tournament_name = serializers.CharField(source='tournament.name', read_only=True, allow_null=True)
    season_name = serializers.CharField(source='season.name', read_only=True, allow_null=True)
    red_team_picks = serializers.SerializerMethodField()
    blue_team_picks = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

    def get_red_team_picks(self, obj):
        picks = obj.get_red_team_picks()
        return [champion.name for champion in picks]

    def get_blue_team_picks(self, obj):
        picks = obj.get_blue_team_picks()
        return [champion.name for champion in picks]
