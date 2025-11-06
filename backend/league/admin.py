from django.contrib import admin
from .models import (
    Role, Champion, Patch, ChampionPatch, Tournament, 
    Team, TeamTournament, Season, WinLossRecord, Game
)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'updated_at']
    search_fields = ['name']


@admin.register(Champion)
class ChampionAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'release_date', 'get_roles', 'primary_damage_type',
        'picks', 'bans', 'prioscore', 'wins', 'losses', 'winrate',
        'KDA', 'avg_bt', 'avg_rp', 'gt', 'csm', 'dpm', 'gpm',
        'csd_15', 'gd_15', 'xpd_15', 'created_at', 'updated_at'
    ]
    list_filter = ['roles', 'primary_damage_type']
    search_fields = ['name']
    date_hierarchy = 'release_date'
    filter_horizontal = ['roles']
    
    def get_roles(self, obj):
        """Display roles as a comma-separated string"""
        return ", ".join([role.name for role in obj.roles.all()]) or "-"
    get_roles.short_description = "Roles"


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
