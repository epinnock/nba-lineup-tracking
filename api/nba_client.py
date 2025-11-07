import json
import os
import time
from nba_api.stats.endpoints import playbyplayv2

# Directory to cache API responses
CACHE_DIR = ".cache"

def get_play_by_play(game_id: str, use_cache: bool = True) -> dict:
    """
    Fetches the play-by-play data for a given game ID.

    Args:
        game_id: The Game ID to fetch data for.
        use_cache: Whether to use the local cache.

    Returns:
        A dictionary containing the play-by-play data.
    """
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    cache_file = os.path.join(CACHE_DIR, f"{game_id}.json")

    if use_cache and os.path.exists(cache_file):
        print(f"Loading game {game_id} from cache.")
        with open(cache_file, "r") as f:
            return json.load(f)

    print(f"Fetching game {game_id} from NBA API.")
    try:
        pbp = playbyplayv2.PlayByPlayV2(game_id=game_id)
        data = pbp.get_dict()

        if use_cache:
            with open(cache_file, "w") as f:
                json.dump(data, f, indent=4)

        # Respect API rate limits
        time.sleep(0.6)

        return data
    except Exception as e:
        print(f"Error fetching data for game {game_id}: {e}")
        return {}

if __name__ == '__main__':
    # Example usage:
    # python api/nba_client.py
    sample_game_id = "0022300001"  # A real game ID
    pbp_data = get_play_by_play(sample_game_id)
    if pbp_data:
        print(f"Successfully fetched data for game {sample_game_id}.")
        # Print number of plays
        play_count = len(pbp_data.get('resultSets', [{}])[0].get('rowSet', []))
        print(f"Found {play_count} plays in the data.")