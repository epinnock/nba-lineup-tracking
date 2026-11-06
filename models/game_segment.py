from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from models.lineup import Lineup
from models.boxscore import BoxScore
from models.player_boxscore import PlayerBoxScore

@dataclass
class GameContext:
    """Represents the game context at a specific point in time."""
    home_score: int = 0
    away_score: int = 0
    quarter: int = 1
    time_remaining: float = 720.0

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
    context: Optional[GameContext] = None

    # NEW: Player-level boxscores
    home_player_stats: Dict[str, PlayerBoxScore] = field(default_factory=dict)
    away_player_stats: Dict[str, PlayerBoxScore] = field(default_factory=dict)

    # NEW: Play-by-play events during this segment
    plays: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        # Initialize context with the correct quarter and time if not provided
        if self.context is None:
            self.context = GameContext(
                quarter=self.start_quarter,
                time_remaining=self.start_time
            )

    @property
    def duration(self) -> float:
        """
        Calculates the duration of the game segment in seconds.
        Accounts for segments that span multiple quarters.
        """
        if self.start_quarter == self.end_quarter:
            # Same quarter - simple subtraction
            return self.start_time - self.end_time
        else:
            # Spans quarters - need to calculate across quarter boundaries
            # start_time to end of start quarter + full middle quarters + start of end quarter to end_time
            duration = self.start_time  # Time remaining in start quarter
            
            # Add full quarters in between (12 minutes = 720 seconds each)
            quarters_between = self.end_quarter - self.start_quarter - 1
            if quarters_between > 0:
                duration += quarters_between * 720.0
            
            # Add time from start of end quarter to end_time
            duration += (720.0 - self.end_time)
            
            return duration

    @property
    def duration_seconds(self) -> float:
        """Alias for duration property for backwards compatibility."""
        return self.duration

    def get_plays_for_segment(self, all_plays: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Returns the plays that occurred during this segment.
        
        Args:
            all_plays: List of all plays from the game
            
        Returns:
            List of plays that fall within this segment's time range
        """
        segment_plays = []
        for play in all_plays:
            play_quarter = play.get('PERIOD', 0)
            play_time = self._parse_time_to_seconds(play.get('PCTIMESTRING', '0:00'))
            
            # Check if play is within segment bounds
            if play_quarter == self.start_quarter:
                if self.start_quarter == self.end_quarter:
                    # Same quarter - check time range
                    if self.end_time <= play_time <= self.start_time:
                        segment_plays.append(play)
                else:
                    # Segment spans quarters - include from start to end of quarter
                    if play_time <= self.start_time:
                        segment_plays.append(play)
            elif play_quarter == self.end_quarter and play_quarter != self.start_quarter:
                # End quarter of multi-quarter segment
                if play_time >= self.end_time:
                    segment_plays.append(play)
            elif self.start_quarter < play_quarter < self.end_quarter:
                # Middle quarters
                segment_plays.append(play)
                
        return segment_plays

    def _parse_time_to_seconds(self, time_str: str) -> float:
        """Convert 'MM:SS' to seconds."""
        if not time_str:
            return 0.0
        try:
            minutes, seconds = map(int, time_str.split(':'))
            return float(minutes * 60 + seconds)
        except (ValueError, AttributeError):
            return 0.0

    def get_player_boxscore(self, player_id: str) -> Optional[PlayerBoxScore]:
        """Get boxscore for a specific player."""
        return (self.home_player_stats.get(player_id) or
                self.away_player_stats.get(player_id))

    def __repr__(self):
        return (
            f"GameSegment(segment_id='{self.segment_id}', game_id='{self.game_id}', "
            f"home_team='{self.home_lineup.team}', away_team='{self.away_lineup.team}', "
            f"start_quarter={self.start_quarter}, start_time={self.start_time}, "
            f"end_quarter={self.end_quarter}, end_time={self.end_time}, "
            f"home_players={len(self.home_player_stats)}, away_players={len(self.away_player_stats)}, "
            f"plays={len(self.plays)})"
        )
