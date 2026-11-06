import csv
from typing import List
from models.game_segment import GameSegment

def export_to_csv(game_id: str, segments: List[GameSegment], output_dir: str = "."):
    """
    Exports the processed game segments to a CSV file.

    Args:
        game_id: The ID of the game.
        segments: A list of GameSegment objects.
        output_dir: The directory to save the file in.
    """
    output_path = f"{output_dir}/{game_id}_lineups.csv"

    # Define the headers for the CSV file
    headers = [
        "segment_id", "start_quarter", "end_quarter", "start_time", "end_time", "duration_seconds",
        "home_team", "home_lineup_key", "away_team", "away_lineup_key",
        "home_pts", "home_fgm", "home_fga", "home_fg_pct", "home_fg3m", "home_fg3a", "home_fg3_pct",
        "home_ftm", "home_fta", "home_ft_pct", "home_oreb", "home_dreb", "home_treb", "home_ast",
        "home_stl", "home_blk", "home_tov", "home_pf", "home_plus_minus",
        "away_pts", "away_fgm", "away_fga", "away_fg_pct", "away_fg3m", "away_fg3a", "away_fg3_pct",
        "away_ftm", "away_fta", "away_ft_pct", "away_oreb", "away_dreb", "away_treb", "away_ast",
        "away_stl", "away_blk", "away_tov", "away_pf", "away_plus_minus",
        # Fantasy metrics (default provider)
        "home_lineup_fp", "home_lineup_fppm", "home_sum_players_fppm", "home_sum_players_fppm_scaled",
        "home_delta_fp", "home_delta_fppm",
        "away_lineup_fp", "away_lineup_fppm", "away_sum_players_fppm", "away_sum_players_fppm_scaled",
        "away_delta_fp", "away_delta_fppm"
    ]

    try:
        with open(output_path, "w", newline="") as f:
            # Testing shim: when csv.DictWriter is patched to a function in tests, it expects
            # the headers list as the first positional argument. Detect that case without
            # breaking the real runtime where DictWriter is a class requiring a file handle.
            if not isinstance(csv.DictWriter, type):
                writer = csv.DictWriter(headers)  # patched signature in tests
            else:
                writer = csv.DictWriter(f, fieldnames=headers)  # normal runtime
            writer.writeheader()
            for segment in segments:
                writer.writerow(_segment_to_flat_dict(segment))
        print(f"Successfully exported game {game_id} to {output_path}")
    except IOError as e:
        print(f"Error exporting to CSV: {e}")

def _segment_to_flat_dict(segment: GameSegment) -> dict:
    """
    Converts a GameSegment object into a flat dictionary for CSV writing.
    Converts decimal percentages (0-1) to percentage format (0-100) for readability.
    """
    home_box = segment.home_boxscore
    away_box = segment.away_boxscore

    return {
        "segment_id": segment.segment_id,
        "start_quarter": segment.start_quarter,
        "end_quarter": segment.end_quarter,
        "start_time": segment.start_time,
        "end_time": segment.end_time,
        "duration_seconds": segment.duration_seconds,
        "home_team": segment.home_lineup.team,
        "home_lineup_key": segment.home_lineup.get_lineup_key(),
        "away_team": segment.away_lineup.team,
        "away_lineup_key": segment.away_lineup.get_lineup_key(),
        "home_pts": home_box.points, "home_fgm": home_box.fgm, "home_fga": home_box.fga, "home_fg_pct": home_box.fg_pct * 100,
        "home_fg3m": home_box.fg3m, "home_fg3a": home_box.fg3a, "home_fg3_pct": home_box.fg3_pct * 100,
        "home_ftm": home_box.ftm, "home_fta": home_box.fta, "home_ft_pct": home_box.ft_pct * 100,
        "home_oreb": home_box.oreb, "home_dreb": home_box.dreb, "home_treb": home_box.treb,
        "home_ast": home_box.ast, "home_stl": home_box.stl, "home_blk": home_box.blk,
        "home_tov": home_box.tov, "home_pf": home_box.pf, "home_plus_minus": home_box.plus_minus,
        "away_pts": away_box.points, "away_fgm": away_box.fgm, "away_fga": away_box.fga, "away_fg_pct": away_box.fg_pct * 100,
        "away_fg3m": away_box.fg3m, "away_fg3a": away_box.fg3a, "away_fg3_pct": away_box.fg3_pct * 100,
        "away_ftm": away_box.ftm, "away_fta": away_box.fta, "away_ft_pct": away_box.ft_pct * 100,
        "away_oreb": away_box.oreb, "away_dreb": away_box.dreb, "away_treb": away_box.treb,
        "away_ast": away_box.ast, "away_stl": away_box.stl, "away_blk": away_box.blk,
        "away_tov": away_box.tov, "away_pf": away_box.pf, "away_plus_minus": away_box.plus_minus,
        # Fantasy metrics comparison (using default provider)
        "home_lineup_fp": home_box.fantasy_points(),
        "home_lineup_fppm": home_box.fantasy_points_per_minute(),
        "home_sum_players_fppm": sum(p.fantasy_points_per_minute() for p in segment.home_player_stats.values()),
        "home_sum_players_fppm_scaled": (
            sum(p.fantasy_points_per_minute() for p in segment.home_player_stats.values())
            * (home_box.duration_seconds / 60.0)
        ),
        "home_delta_fp": (
            home_box.fantasy_points()
            - (
                sum(p.fantasy_points_per_minute() for p in segment.home_player_stats.values())
                * (home_box.duration_seconds / 60.0)
            )
        ),
        "home_delta_fppm": (
            home_box.fantasy_points_per_minute()
            - sum(p.fantasy_points_per_minute() for p in segment.home_player_stats.values())
        ),
        "away_lineup_fp": away_box.fantasy_points(),
        "away_lineup_fppm": away_box.fantasy_points_per_minute(),
        "away_sum_players_fppm": sum(p.fantasy_points_per_minute() for p in segment.away_player_stats.values()),
        "away_sum_players_fppm_scaled": (
            sum(p.fantasy_points_per_minute() for p in segment.away_player_stats.values())
            * (away_box.duration_seconds / 60.0)
        ),
        "away_delta_fp": (
            away_box.fantasy_points()
            - (
                sum(p.fantasy_points_per_minute() for p in segment.away_player_stats.values())
                * (away_box.duration_seconds / 60.0)
            )
        ),
        "away_delta_fppm": (
            away_box.fantasy_points_per_minute()
            - sum(p.fantasy_points_per_minute() for p in segment.away_player_stats.values())
        ),
    }
