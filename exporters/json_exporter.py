import json
from typing import List, Dict
from models.game_segment import GameSegment

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
    """
    return {
        "segment_id": segment.segment_id,
        "start_quarter": segment.start_quarter,
        "end_quarter": segment.end_quarter,
        "start_time": segment.start_time,
        "end_time": segment.end_time,
        "duration_seconds": segment.duration_seconds,
        "home_lineup": {
            "team": segment.home_lineup.team_abbreviation,
            "lineup_key": segment.home_lineup.get_lineup_key(),
            "players": [p.player_id for p in segment.home_lineup.players]
        },
        "away_lineup": {
            "team": segment.away_lineup.team_abbreviation,
            "lineup_key": segment.away_lineup.get_lineup_key(),
            "players": [p.player_id for p in segment.away_lineup.players]
        },
        "home_boxscore": segment.home_boxscore.__dict__,
        "away_boxscore": segment.away_boxscore.__dict__
    }
