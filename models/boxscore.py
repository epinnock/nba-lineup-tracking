from dataclasses import dataclass, field
from typing import Optional
from utils.constants import get_scoring_weights

@dataclass
class BoxScore:
    """
    Represents the boxscore for a single lineup during a game segment.
    """
    points: int = 0
    fgm: int = 0  # Field goals made
    fga: int = 0  # Field goals attempted
    fg3m: int = 0 # 3-pointers made
    fg3a: int = 0 # 3-pointers attempted
    ftm: int = 0  # Free throws made
    fta: int = 0  # Free throws attempted
    oreb: int = 0 # Offensive rebounds
    dreb: int = 0 # Defensive rebounds
    treb: int = 0 # Total rebounds (stored field)
    ast: int = 0  # Assists
    stl: int = 0  # Steals
    blk: int = 0  # Blocks
    tov: int = 0  # Turnovers
    pf: int = 0   # Personal fouls
    plus_minus: int = 0
    possessions: int = 0
    offensive_rating: float = 0.0
    defensive_rating: float = 0.0
    duration_seconds: float = 0.0

    # Calculated fields (returned as decimals 0-1 for internal use)
    @property
    def fg_pct(self) -> float:
        return (self.fgm / self.fga) if self.fga > 0 else 0.0

    @property
    def fg3_pct(self) -> float:
        return (self.fg3m / self.fg3a) if self.fg3a > 0 else 0.0

    @property
    def ft_pct(self) -> float:
        return (self.ftm / self.fta) if self.fta > 0 else 0.0

    # Advanced Statistics Properties

    @property
    def true_shooting_pct(self) -> float:
        """True Shooting Percentage: (Points) / (2 × (FGA + 0.44 × FTA))"""
        denominator = 2 * (self.fga + 0.44 * self.fta)
        return (self.points / denominator) if denominator > 0 else 0.0

    @property
    def effective_fg_pct(self) -> float:
        """Effective Field Goal Percentage: (FGM + 0.5 × 3PM) / FGA"""
        return ((self.fgm + 0.5 * self.fg3m) / self.fga) if self.fga > 0 else 0.0

    @property
    def points_per_possession(self) -> float:
        """Points per Possession: Points / Possessions"""
        return (self.points / self.possessions) if self.possessions > 0 else 0.0

    @property
    def possessions_per_minute(self) -> float:
        """Possessions per Minute: Possessions / (Duration / 60)"""
        duration_minutes = self.duration_seconds / 60.0
        return (self.possessions / duration_minutes) if duration_minutes > 0 else 0.0

    @property
    def time_of_possession(self) -> float:
        """Time of Possession: Average seconds per possession"""
        return (self.duration_seconds / self.possessions) if self.possessions > 0 else 0.0

    @property
    def three_point_rate(self) -> float:
        """3-Point Rate: 3PA / FGA"""
        return (self.fg3a / self.fga) if self.fga > 0 else 0.0

    def usage_rate(self, team_possessions: int, duration_minutes: float) -> float:
        """Usage Rate: (FGA + 0.44 × FTA + TOV) / (Team Possessions × Duration)"""
        if team_possessions <= 0 or duration_minutes <= 0:
            return 0.0
        numerator = self.fga + 0.44 * self.fta + self.tov
        denominator = team_possessions * duration_minutes
        return numerator / denominator

    def compute_defensive_rating(self, opponent_points: int) -> float:
        """Defensive Rating (computed): Opponent Points × 100 / Possessions"""
        return (opponent_points * 100 / self.possessions) if self.possessions > 0 else 0.0

    def steals_per_possession(self) -> float:
        """Steals per Possession: STL / Possessions"""
        return (self.stl / self.possessions) if self.possessions > 0 else 0.0

    def block_rate(self, opponent_fga: int, opponent_fg3a: int) -> float:
        """Block Rate: BLK / (Opponent FGA - Opponent 3PA)"""
        denominator = opponent_fga - opponent_fg3a
        return (self.blk / denominator) if denominator > 0 else 0.0

    def forced_turnover_rate(self, opponent_tov: int, opponent_possessions: int) -> float:
        """Forced Turnover Rate: Opponent TOV / (Possessions + Opponent Possessions)"""
        denominator = self.possessions + opponent_possessions
        return (opponent_tov / denominator) if denominator > 0 else 0.0

    def offensive_rebound_pct(self, opponent_dreb: int) -> float:
        """Offensive Rebound Percentage: OREB / (OREB + Opponent DREB)"""
        denominator = self.oreb + opponent_dreb
        return (self.oreb / denominator) if denominator > 0 else 0.0

    def rebound_balance(self) -> float:
        """Rebound Balance: OREB% vs DREB% - returns OREB/(OREB+DREB)"""
        total_reb = self.oreb + self.dreb
        return (self.oreb / total_reb) if total_reb > 0 else 0.0

    def __post_init__(self):
        # Auto-calculate treb if it wasn't explicitly set (i.e., is still 0)
        # This allows both: BoxScore(oreb=3, dreb=7) -> treb=10
        # And: BoxScore(oreb=3, dreb=0, treb=8) -> treb=8 (preserved)
        if self.treb == 0:
            self.treb = self.oreb + self.dreb

    def add_points(self, points: int):
        """Add points to the boxscore."""
        self.points += points

    def add_field_goal(self, made: bool, is_three: bool = False):
        """Add a field goal attempt (and make if applicable)."""
        self.fga += 1
        if made:
            self.fgm += 1
            self.points += 3 if is_three else 2
            if is_three:
                self.fg3m += 1
                self.fg3a += 1
        else:
            if is_three:
                self.fg3a += 1

    def add_three_point(self, made: bool):
        """Add a three-point field goal attempt."""
        self.add_field_goal(made, is_three=True)

    def add_free_throw(self, made: bool):
        """Add a free throw attempt."""
        self.fta += 1
        if made:
            self.ftm += 1
            self.points += 1

    def add_rebound(self, offensive: bool = False):
        """Add a rebound."""
        if offensive:
            self.oreb += 1
        else:
            self.dreb += 1
        self.treb += 1

    def add_assist(self):
        """Add an assist."""
        self.ast += 1

    def add_steal(self):
        """Add a steal."""
        self.stl += 1

    def add_block(self):
        """Add a block."""
        self.blk += 1

    def add_turnover(self):
        """Add a turnover."""
        self.tov += 1

    def add_foul(self):
        """Add a personal foul."""
        self.pf += 1

    def update_plus_minus(self, value: int):
        """Update the plus/minus value."""
        self.plus_minus += value

    def add_possessions(self, count: int = 1):
        """Add possessions."""
        self.possessions += count

    def add_duration(self, seconds: float):
        """Add duration in seconds."""
        self.duration_seconds += seconds

    def fantasy_points(self, provider: Optional[str] = None) -> float:
        """
        Compute fantasy points for this lineup segment based on provider weights.
        """
        w = get_scoring_weights(provider)
        return (
            self.points * w.get("PTS", 0.0)
            + self.fg3m * w.get("3PM", 0.0)
            + self.treb * w.get("REB", 0.0)
            + self.ast * w.get("AST", 0.0)
            + self.stl * w.get("STL", 0.0)
            + self.blk * w.get("BLK", 0.0)
            + self.tov * w.get("TOV", 0.0)
        )

    def fantasy_points_per_minute(self, provider: Optional[str] = None) -> float:
        """
        Compute fantasy points per minute for this lineup segment.
        """
        minutes = self.duration_seconds / 60.0
        total_fp = self.fantasy_points(provider)
        return (total_fp / minutes) if minutes > 0 else 0.0

    def __str__(self):
        return (
            f"BoxScore(PTS: {self.points}, FG: {self.fgm}/{self.fga}, "
            f"3P: {self.fg3m}/{self.fg3a}, FT: {self.ftm}/{self.fta}, "
            f"REB: {self.oreb}+{self.dreb}={self.treb}, AST: {self.ast}, "
            f"STL: {self.stl}, BLK: {self.blk}, TOV: {self.tov}, PF: {self.pf}, "
            f"+/-: {self.plus_minus})"
        )

    def __repr__(self):
        return (
            f"BoxScore(points={self.points}, fgm={self.fgm}, fga={self.fga}, "
            f"fg3m={self.fg3m}, fg3a={self.fg3a}, ftm={self.ftm}, fta={self.fta}, "
            f"oreb={self.oreb}, dreb={self.dreb}, treb={self.treb}, ast={self.ast}, "
            f"stl={self.stl}, blk={self.blk}, tov={self.tov}, pf={self.pf}, "
            f"plus_minus={self.plus_minus})"
        )
