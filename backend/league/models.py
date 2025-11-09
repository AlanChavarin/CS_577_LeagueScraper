from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Role(models.Model):
    """Represents a champion role (e.g., Fighter, Mage, Support, etc.)"""
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        db_table = 'roles'

    def __str__(self):
        return self.name


class ChampionRole(models.Model):
    """Explicit through model for Champion-Role many-to-many relationship"""
    champion = models.ForeignKey('Champion', on_delete=models.CASCADE, db_column='champion_id')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, db_column='role_id')

    class Meta:
        db_table = 'champions_roles'
        unique_together = [['champion', 'role']]

    def __str__(self):
        return f"{self.champion.name} - {self.role.name}"


class Champion(models.Model):
    """Represents a League of Legends champion"""
    name = models.CharField(max_length=100, unique=True)
    release_date = models.DateField()
    primary_damage_type = models.CharField(max_length=50, help_text="Primary damage type: AD or AP (what the champion builds)")
    roles = models.ManyToManyField(
        Role,
        through='ChampionRole',
        related_name='champions',
        blank=True,
        help_text="Champion roles (can have multiple)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        db_table = 'champions'

    def __str__(self):
        return self.name


class Patch(models.Model):
    """Represents a game patch/version"""
    version_num = models.CharField(max_length=20, unique=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-version_num']
        db_table = 'patches'
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['version_num']),
        ]

    def __str__(self):
        return f"Patch {self.version_num}"


class ChampionPatch(models.Model):
    """Junction table linking Champions to Patches with change information"""
    champion = models.ForeignKey(Champion, on_delete=models.CASCADE, related_name='champion_patches')
    patch = models.ForeignKey(Patch, on_delete=models.CASCADE, related_name='champion_patches')
    change_type = models.CharField(max_length=100)  # e.g., "buff", "nerf", "rework"
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['patch', 'champion']
        unique_together = [['champion', 'patch']]
        db_table = 'champion_patches'
        indexes = [
            models.Index(fields=['champion', 'patch']),
            models.Index(fields=['patch']),
        ]

    def __str__(self):
        return f"{self.champion.name} - {self.patch.version_num} ({self.change_type})"


class Tournament(models.Model):
    """Represents a tournament"""
    name = models.CharField(max_length=200)
    tier = models.CharField(max_length=50)  # e.g., "S-Tier", "A-Tier"
    date = models.DateField()
    patch = models.ForeignKey(Patch, on_delete=models.SET_NULL, null=True, blank=True, related_name='tournaments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', 'name']
        db_table = 'tournaments'
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['tier']),
        ]

    def __str__(self):
        return f"{self.name} ({self.tier})"


class Team(models.Model):
    """Represents a team"""
    name = models.CharField(max_length=100, unique=True)
    region = models.CharField(max_length=50)  # e.g., "NA", "EUW", "KR"
    tournaments = models.ManyToManyField('Tournament', through='TeamTournament', related_name='teams')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['region', 'name']
        db_table = 'teams'
        indexes = [
            models.Index(fields=['region']),
        ]

    def __str__(self):
        return f"{self.name} ({self.region})"


class TeamTournament(models.Model):
    """Junction table linking Teams to Tournaments"""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='team_tournaments')
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='team_tournaments')
    placement = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1)])  # Final placement in tournament
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['tournament', 'placement']
        unique_together = [['team', 'tournament']]
        db_table = 'team_tournaments'
        indexes = [
            models.Index(fields=['team', 'tournament']),
            models.Index(fields=['tournament', 'placement']),
        ]

    def __str__(self):
        return f"{self.team.name} in {self.tournament.name}"


class Season(models.Model):
    """Represents a competitive season"""
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        db_table = 'seasons'

    def __str__(self):
        return self.name


class ChampionSeasonStats(models.Model):
    """Tracks seasonal statistics for champions"""
    champion = models.ForeignKey(Champion, on_delete=models.CASCADE, related_name='season_stats')
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='champion_stats')
    picks = models.PositiveIntegerField(default=0)
    bans = models.PositiveIntegerField(default=0)
    prioscore = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00, validators=[
            MinValueValidator(0.0), MaxValueValidator(100.0)
        ], help_text="Priority score as a percent (0-100)"
    )
    wins = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    losses = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    winrate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00, validators=[
            MinValueValidator(0.0), MaxValueValidator(100.0)
        ], help_text="Win rate as a percent (0-100)"
    )
    KDA = models.FloatField(default=0.0, help_text="Kill/Death/Assist ratio (float)")
    avg_bt = models.FloatField(default=0.0, help_text="Average Baron time (float, minutes)")
    avg_rp = models.FloatField(default=0.0, help_text="Average Rift time (float, minutes)")
    gt = models.DurationField(null=True, blank=True, help_text="Average game time (duration)")
    csm = models.FloatField(default=0.0, help_text="Creep score per minute")
    dpm = models.PositiveIntegerField(default=0, help_text="Damage per minute")
    gpm = models.PositiveIntegerField(default=0, help_text="Gold per minute")
    csd_15 = models.IntegerField(default=0, help_text="CS difference at 15 minutes")
    gd_15 = models.IntegerField(default=0, help_text="Gold difference at 15 minutes")
    xpd_15 = models.IntegerField(default=0, help_text="XP difference at 15 minutes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['season', 'champion']
        unique_together = [['champion', 'season']]
        db_table = 'champion_season_stats'
        indexes = [
            models.Index(fields=['champion', 'season']),
            models.Index(fields=['season']),
        ]

    @property
    def win_rate(self):
        total = self.wins + self.losses
        if total == 0:
            return 0.0
        return (self.wins / total) * 100

    def __str__(self):
        return f"{self.champion.name} - {self.season.name}"


class TeamSeasonStats(models.Model):
    """Tracks seasonal statistics for teams"""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='season_stats')
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='team_stats')
    region = models.CharField(max_length=10, blank=True, help_text="Region code snapshot (e.g., NA, EUW)")
    games = models.PositiveIntegerField(default=0)
    winrate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Win rate as a percent (0-100)"
    )
    kill_death_ratio = models.FloatField(default=0.0, help_text="Kill/Death ratio")
    gpm = models.PositiveIntegerField(default=0, help_text="Gold per minute")
    gdm = models.IntegerField(default=0, help_text="Gold difference per minute")
    game_duration = models.DurationField(null=True, blank=True, help_text="Average game duration")
    kills_per_game = models.FloatField(default=0.0)
    deaths_per_game = models.FloatField(default=0.0)
    towers_killed = models.FloatField(default=0.0)
    towers_lost = models.FloatField(default=0.0)
    first_blood_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="First blood percentage (0-100)"
    )
    first_tower_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="First tower percentage (0-100)"
    )
    first_objective_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="First objective secured percentage (FOS%, 0-100)"
    )
    dragons_per_game = models.FloatField(default=0.0, help_text="Average dragons per game (DRAPG)")
    dragon_control_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Dragon control rate (DRA%, 0-100)"
    )
    void_grub_per_game = models.FloatField(default=0.0, help_text="Void grubs per game (VGPG)")
    herald_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Herald control percentage (HER%, 0-100)"
    )
    atakhan_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="ATAKHAN control percentage (0-100)"
    )
    dragons_at_15 = models.FloatField(default=0.0, help_text="Dragons per game by 15 minutes (DRA@15)")
    tower_difference_15 = models.FloatField(default=0.0, help_text="Tower difference at 15 minutes (TD@15)")
    gold_difference_15 = models.IntegerField(default=0, help_text="Gold difference at 15 minutes (GD@15)")
    points_per_game = models.FloatField(default=0.0, help_text="Points per game (PPG)")
    nashors_per_game = models.FloatField(default=0.0, help_text="Barons per game (NASHPG)")
    nashor_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Baron control percentage (NASH%, 0-100)"
    )
    csm = models.FloatField(default=0.0, help_text="Creep score per minute (CSM)")
    dpm = models.PositiveIntegerField(default=0, help_text="Damage per minute (DPM)")
    wards_per_minute = models.FloatField(default=0.0, help_text="Wards per minute (WPM)")
    vision_wards_per_minute = models.FloatField(default=0.0, help_text="Vision wards per minute (VWPM)")
    wards_cleared_per_minute = models.FloatField(default=0.0, help_text="Wards cleared per minute (WCPM)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['season', 'team']
        unique_together = [['team', 'season']]
        db_table = 'team_season_stats'
        indexes = [
            models.Index(fields=['team', 'season']),
            models.Index(fields=['season']),
            models.Index(fields=['region']),
        ]

    def __str__(self):
        return f"{self.team.name} - {self.season.name}"


class Game(models.Model):
    """Represents a single game/match"""
    # Patch, tournament, season and teams
    patch = models.ForeignKey(Patch, on_delete=models.SET_NULL, null=True, blank=True, related_name='games')
    tournament = models.ForeignKey(Tournament, on_delete=models.SET_NULL, null=True, blank=True, related_name='games')
    season = models.ForeignKey(Season, on_delete=models.SET_NULL, null=True, blank=True, related_name='games')
    blue_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='blue_games')
    red_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='red_games')
    winning_team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_games')
    
    # Lane-specific winning teams
    top_lane_winning_team = models.ForeignKey(
        Team, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='top_lane_wins'
    )
    mid_lane_winning_team = models.ForeignKey(
        Team, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='mid_lane_wins'
    )
    bot_lane_winning_team = models.ForeignKey(
        Team, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='bot_lane_wins'
    )
    
    # Champion picks - Red Team
    red_team_champion_pick_1 = models.ForeignKey(
        Champion, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='red_pick_1_games'
    )
    red_team_champion_pick_2 = models.ForeignKey(
        Champion, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='red_pick_2_games'
    )
    red_team_champion_pick_3 = models.ForeignKey(
        Champion, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='red_pick_3_games'
    )
    red_team_champion_pick_4 = models.ForeignKey(
        Champion, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='red_pick_4_games'
    )
    red_team_champion_pick_5 = models.ForeignKey(
        Champion, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='red_pick_5_games'
    )
    
    # Champion picks - Blue Team
    blue_team_champion_pick_1 = models.ForeignKey(
        Champion, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='blue_pick_1_games'
    )
    blue_team_champion_pick_2 = models.ForeignKey(
        Champion, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='blue_pick_2_games'
    )
    blue_team_champion_pick_3 = models.ForeignKey(
        Champion, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='blue_pick_3_games'
    )
    blue_team_champion_pick_4 = models.ForeignKey(
        Champion, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='blue_pick_4_games'
    )
    blue_team_champion_pick_5 = models.ForeignKey(
        Champion, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='blue_pick_5_games'
    )
    
    # Game date
    date = models.DateField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        db_table = 'games'
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['patch', 'date']),
            models.Index(fields=['tournament', 'date']),
            models.Index(fields=['season', 'date']),
            models.Index(fields=['blue_team', 'date']),
            models.Index(fields=['red_team', 'date']),
            models.Index(fields=['winning_team']),
        ]

    def get_red_team_picks(self):
        """Returns a list of red team champion picks"""
        picks = [
            self.red_team_champion_pick_1,
            self.red_team_champion_pick_2,
            self.red_team_champion_pick_3,
            self.red_team_champion_pick_4,
            self.red_team_champion_pick_5,
        ]
        return [pick for pick in picks if pick is not None]

    def get_blue_team_picks(self):
        """Returns a list of blue team champion picks"""
        picks = [
            self.blue_team_champion_pick_1,
            self.blue_team_champion_pick_2,
            self.blue_team_champion_pick_3,
            self.blue_team_champion_pick_4,
            self.blue_team_champion_pick_5,
        ]
        return [pick for pick in picks if pick is not None]

    def __str__(self):
        return f"{self.blue_team.name} vs {self.red_team.name} - {self.date}"
