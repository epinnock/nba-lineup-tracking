import json
from typing import List, Dict
from models.game_segment import GameSegment
from utils.constants import FANTASY_DEFAULT_PROVIDER

def export_to_json(game_id: str, segments: List[GameSegment], output_dir: str = "."):
    """
    Exports the processed game segments to a JSON file.

    Args:
        game_id: The ID of the game.
        segments: A list of GameSegment objects.
        output_dir: The directory to save the file in.
    """
    output_data = {
        "game_id": game_id,
        "segment_count": len(segments),
        "segments": [_segment_to_dict(s) for s in segments]
    }

    output_path = f"{output_dir}/{game_id}_lineups.json"
    try:
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=4)
        print(f"Successfully exported game {game_id} to {output_path}")
    except IOError as e:
        print(f"Error exporting to JSON: {e}")

def _segment_to_dict(segment: GameSegment) -> Dict:
    """
    Converts a GameSegment object to a JSON-serializable dictionary.
    Converts decimal percentages (0-1) to percentage format (0-100) for readability.
    """
    def boxscore_to_dict(boxscore):
        """Convert BoxScore to dict including @property fields with percentages as 0-100."""
        # Calculate duration in minutes for usage rate calculations
        duration_minutes = boxscore.duration_seconds / 60.0

        return {
            "points": boxscore.points,
            "fgm": boxscore.fgm,
            "fga": boxscore.fga,
            "fg_pct": boxscore.fg_pct * 100,  # Convert to percentage
            "fg3m": boxscore.fg3m,
            "fg3a": boxscore.fg3a,
            "fg3_pct": boxscore.fg3_pct * 100,  # Convert to percentage
            "ftm": boxscore.ftm,
            "fta": boxscore.fta,
            "ft_pct": boxscore.ft_pct * 100,  # Convert to percentage
            "oreb": boxscore.oreb,
            "dreb": boxscore.dreb,
            "treb": boxscore.treb,
            "ast": boxscore.ast,
            "stl": boxscore.stl,
            "blk": boxscore.blk,
            "tov": boxscore.tov,
            "pf": boxscore.pf,
            "plus_minus": boxscore.plus_minus,
            "possessions": boxscore.possessions,
            "offensive_rating": boxscore.offensive_rating,
            "defensive_rating": boxscore.defensive_rating,
            "duration_seconds": boxscore.duration_seconds,
            # Advanced Statistics
            "true_shooting_pct": boxscore.true_shooting_pct * 100,
            "effective_fg_pct": boxscore.effective_fg_pct * 100,
            "points_per_possession": boxscore.points_per_possession,
            "possessions_per_minute": boxscore.possessions_per_minute,
            "time_of_possession": boxscore.time_of_possession,
            "three_point_rate": boxscore.three_point_rate * 100,
            "steals_per_possession": boxscore.steals_per_possession(),
            "rebound_balance": boxscore.rebound_balance() * 100
        }

    def player_boxscore_to_dict(player_boxscore):
        """Convert PlayerBoxScore to dict including @property fields with percentages as 0-100."""
        return {
            "player_id": player_boxscore.player_id,
            "player_name": player_boxscore.player_name,
            "team": player_boxscore.team,
            "points": player_boxscore.points,
            "fgm": player_boxscore.fgm,
            "fga": player_boxscore.fga,
            "fg_pct": player_boxscore.fg_pct * 100,  # Convert to percentage
            "fg3m": player_boxscore.fg3m,
            "fg3a": player_boxscore.fg3a,
            "fg3_pct": player_boxscore.fg3_pct * 100,  # Convert to percentage
            "ftm": player_boxscore.ftm,
            "fta": player_boxscore.fta,
            "ft_pct": player_boxscore.ft_pct * 100,  # Convert to percentage
            "oreb": player_boxscore.oreb,
            "dreb": player_boxscore.dreb,
            "treb": player_boxscore.treb,
            "ast": player_boxscore.ast,
            "stl": player_boxscore.stl,
            "blk": player_boxscore.blk,
            "tov": player_boxscore.tov,
            "pf": player_boxscore.pf,
            "plus_minus": player_boxscore.plus_minus,
            "duration_seconds": player_boxscore.duration_seconds,
            # Advanced Statistics
            "true_shooting_pct": player_boxscore.true_shooting_pct * 100,
            "effective_fg_pct": player_boxscore.effective_fg_pct * 100,
            "three_point_rate": player_boxscore.three_point_rate * 100,
            "rebound_balance": player_boxscore.rebound_balance() * 100
        }

    return {
        "segment_id": segment.segment_id,
        "start_quarter": segment.start_quarter,
        "end_quarter": segment.end_quarter,
        "start_time": segment.start_time,
        "end_time": segment.end_time,
        "duration_seconds": segment.duration_seconds,
        "home_lineup": {
            "team": segment.home_lineup.team,
            "lineup_key": segment.home_lineup.get_lineup_key(),
            "players": [p.player_id for p in segment.home_lineup.players]
        },
        "away_lineup": {
            "team": segment.away_lineup.team,
            "lineup_key": segment.away_lineup.get_lineup_key(),
            "players": [p.player_id for p in segment.away_lineup.players]
        },
        "home_boxscore": boxscore_to_dict(segment.home_boxscore),
        "away_boxscore": boxscore_to_dict(segment.away_boxscore),
        "home_player_boxscores": [player_boxscore_to_dict(pbs) for pbs in segment.home_player_stats.values()],
        "away_player_boxscores": [player_boxscore_to_dict(pbs) for pbs in segment.away_player_stats.values()],
        "home_fantasy": {
            "provider": FANTASY_DEFAULT_PROVIDER,
            "lineup_fp": segment.home_boxscore.fantasy_points(),
            "lineup_fppm": segment.home_boxscore.fantasy_points_per_minute(),
            "sum_players_fppm": sum(p.fantasy_points_per_minute() for p in segment.home_player_stats.values()),
            "sum_players_fppm_scaled": (
                sum(p.fantasy_points_per_minute() for p in segment.home_player_stats.values())
                * (segment.home_boxscore.duration_seconds / 60.0)
            ),
            "delta_fp": (
                segment.home_boxscore.fantasy_points()
                - (
                    sum(p.fantasy_points_per_minute() for p in segment.home_player_stats.values())
                    * (segment.home_boxscore.duration_seconds / 60.0)
                )
            ),
            "delta_fppm": (
                segment.home_boxscore.fantasy_points_per_minute()
                - sum(p.fantasy_points_per_minute() for p in segment.home_player_stats.values())
            ),
        },
        "away_fantasy": {
            "provider": FANTASY_DEFAULT_PROVIDER,
            "lineup_fp": segment.away_boxscore.fantasy_points(),
            "lineup_fppm": segment.away_boxscore.fantasy_points_per_minute(),
            "sum_players_fppm": sum(p.fantasy_points_per_minute() for p in segment.away_player_stats.values()),
            "sum_players_fppm_scaled": (
                sum(p.fantasy_points_per_minute() for p in segment.away_player_stats.values())
                * (segment.away_boxscore.duration_seconds / 60.0)
            ),
            "delta_fp": (
                segment.away_boxscore.fantasy_points()
                - (
                    sum(p.fantasy_points_per_minute() for p in segment.away_player_stats.values())
                    * (segment.away_boxscore.duration_seconds / 60.0)
                )
            ),
            "delta_fppm": (
                segment.away_boxscore.fantasy_points_per_minute()
                - sum(p.fantasy_points_per_minute() for p in segment.away_player_stats.values())
            ),
        },
        "plays": segment.plays
    }
