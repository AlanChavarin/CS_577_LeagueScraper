from django.contrib import admin
from .models import (
    Champion, Patch, ChampionPatch, Tournament, 
    Team, TeamTournament, Season, WinLossRecord, Game
)


@admin.register(Champion)
class ChampionAdmin(admin.ModelAdmin):
    list_display = ['name', 'primary_role', 'primary_damage_type', 'damage_type', 'release_date']
    list_filter = ['primary_role', 'primary_damage_type', 'damage_type']
    search_fields = ['name']
    date_hierarchy = 'release_date'


@admin.register(Patch)
class PatchAdmin(admin.ModelAdmin):
    list_display = ['version_num', 'date']
    list_filter = ['date']
    search_fields = ['version_num']
    date_hierarchy = 'date'


@admin.register(ChampionPatch)
class ChampionPatchAdmin(admin.ModelAdmin):
    list_display = ['champion', 'patch', 'change_type']
    list_filter = ['change_type', 'patch']
    search_fields = ['champion__name', 'patch__version_num']


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ['name', 'tier', 'date', 'patch']
    list_filter = ['tier', 'date', 'patch']
    search_fields = ['name']
    date_hierarchy = 'date'


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'region']
    list_filter = ['region']
    search_fields = ['name', 'region']
    filter_horizontal = ['tournaments']


@admin.register(TeamTournament)
class TeamTournamentAdmin(admin.ModelAdmin):
    list_display = ['team', 'tournament', 'placement']
    list_filter = ['tournament', 'placement']
    search_fields = ['team__name', 'tournament__name']


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ['name', 'date']
    search_fields = ['name']
    date_hierarchy = 'date'


@admin.register(WinLossRecord)
class WinLossRecordAdmin(admin.ModelAdmin):
    list_display = ['champion', 'season', 'wins', 'losses', 'win_rate']
    list_filter = ['season', 'champion']
    search_fields = ['champion__name', 'season__name']
    readonly_fields = ['win_rate']


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['blue_team', 'red_team', 'winning_team', 'date', 'tournament', 'season', 'patch']
    list_filter = ['date', 'patch', 'tournament', 'season', 'blue_team', 'red_team', 'winning_team']
    search_fields = ['blue_team__name', 'red_team__name', 'tournament__name']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']
