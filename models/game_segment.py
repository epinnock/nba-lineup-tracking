from dataclasses import dataclass, field
from typing import Optional
from models.lineup import Lineup
from models.boxscore import BoxScore

@dataclass
class GameSegment:
    """
    Represents a continuous period of a game where the lineups for both teams do not change.
    """
    game_id: str
    segment_id: int
    home_lineup: Lineup
    away_lineup: Lineup
    start_quarter: int
    end_quarter: int
    start_time: float  # Game clock in seconds from start of period (e.g., 720.0 for a full quarter)
    end_time: float    # Game clock in seconds from start of period
    home_boxscore: BoxScore = field(default_factory=BoxScore)
    away_boxscore: BoxScore = field(default_factory=BoxScore)

    @property
    def duration_seconds(self) -> float:
        """
        Calculates the duration of the game segment in seconds.
        """
        # Note: This is a simplified duration. Real duration needs to account for quarter changes.
        # This will be handled in the stats calculator.
        return self.start_time - self.end_time

    def __repr__(self):
        return (
            f"GameSegment(id={self.segment_id}, game_id={self.game_id}, "
            f"start_q={self.start_quarter}, start_time={self.start_time}, "
            f"end_q={self.end_quarter}, end_time={self.end_time})"
        )
