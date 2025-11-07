from dataclasses import dataclass, field

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
    ast: int = 0  # Assists
    stl: int = 0  # Steals
    blk: int = 0  # Blocks
    tov: int = 0  # Turnovers
    pf: int = 0   # Personal fouls
    plus_minus: int = 0

    # Calculated fields
    @property
    def fg_pct(self) -> float:
        return self.fgm / self.fga if self.fga > 0 else 0.0

    @property
    def fg3_pct(self) -> float:
        return self.fg3m / self.fg3a if self.fg3a > 0 else 0.0

    @property
    def ft_pct(self) -> float:
        return self.ftm / self.fta if self.fta > 0 else 0.0

    @property
    def treb(self) -> int:
        return self.oreb + self.dreb

    def __repr__(self):
        return (
            f"BoxScore(PTS: {self.points}, FGM: {self.fgm}, FGA: {self.fga}, "
            f"3PM: {self.fg3m}, 3PA: {self.fg3a}, FTM: {self.ftm}, FTA: {self.fta}, "
            f"OREB: {self.oreb}, DREB: {self.dreb}, AST: {self.ast}, "
            f"STL: {self.stl}, BLK: {self.blk}, TOV: {self.tov}, PF: {self.pf}, "
            f"+/-: {self.plus_minus})"
        )
