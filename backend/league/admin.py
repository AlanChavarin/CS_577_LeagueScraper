from django.contrib import admin
from .models import (
    Role, Champion, ChampionRole, Patch, ChampionPatch, Tournament,
    Team, TeamTournament, Season, ChampionSeasonStats, TeamSeasonStats, Game, Match,
)

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'updated_at']
    search_fields = ['name']

class ChampionRoleInline(admin.TabularInline):
    """Inline admin for managing Champion-Role relationships"""
    model = ChampionRole
    extra = 1
    autocomplete_fields = ['role']


@admin.register(Champion)
class ChampionAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'release_date', 'get_roles', 'primary_damage_type',
        'created_at', 'updated_at'
    ]
    list_filter = ['roles', 'primary_damage_type']
    search_fields = ['name']
    date_hierarchy = 'release_date'
    inlines = [ChampionRoleInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('roles')

    @admin.display(description='Roles')
    def get_roles(self, obj):
        """Display roles as a comma-separated string"""
        role_names = [role.name for role in obj.roles.all()]
        return ", ".join(role_names) if role_names else "-"


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
    list_display = ['name', 'season_name', 'region', 'last_game_date', 'tier', 'patch']
    list_filter = ['season_name', 'region', 'tier', 'last_game_date', 'patch']
    search_fields = ['name', 'season_name', 'region']
    date_hierarchy = 'last_game_date'


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
    list_display = ['name']
    search_fields = ['name']


@admin.register(ChampionSeasonStats)
class ChampionSeasonStatsAdmin(admin.ModelAdmin):
    list_display = [
        'champion', 'season', 'picks', 'bans', 'wins', 'losses',
        'winrate', 'KDA', 'csm', 'dpm', 'gpm', 'win_rate'
    ]
    list_filter = ['season', 'champion']
    search_fields = ['champion__name', 'season__name']
    readonly_fields = ['win_rate']


@admin.register(TeamSeasonStats)
class TeamSeasonStatsAdmin(admin.ModelAdmin):
    list_display = [
        'team', 'season', 'region', 'games', 'winrate', 'kill_death_ratio',
        'gpm', 'gdm', 'csm', 'dpm'
    ]
    list_filter = ['season', 'team__region']
    search_fields = ['team__name', 'season__name', 'region']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['blue_team', 'red_team', 'winning_team', 'date', 'tournament', 'season', 'patch']
    list_filter = ['date', 'patch', 'tournament', 'season', 'blue_team', 'red_team', 'winning_team']
    search_fields = ['blue_team__name', 'red_team__name', 'tournament__name']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = [
        'tournament', 'team_one', 'team_two', 'date', 'week', 'patch'
    ]
    list_filter = ['tournament', 'week', 'patch', 'date']
    search_fields = [
        'tournament__name', 'team_one__name', 'team_two__name', 'match_url'
    ]
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']
