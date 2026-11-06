import json
import os
import sys
import time
from pathlib import Path

import requests

# Ensure we can import the vendored nba_api (this repo has nba_api/src/)
_LOCAL_NBA_API_SRC = Path(__file__).resolve().parents[2] / "nba_api" / "src"
if _LOCAL_NBA_API_SRC.exists():
    sys.path.insert(0, str(_LOCAL_NBA_API_SRC))

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

    # Try to load from cache if use_cache is True
    if use_cache and os.path.exists(cache_file):
        print(f"[CACHE] Loading game {game_id} from cache: {cache_file}")
        try:
            with open(cache_file, "r") as f:
                data = json.load(f)
                print(f"[CACHE] Successfully loaded {len(str(data))} bytes from cache")
                print(f"[CACHE] Data keys: {list(data.keys())}")
                if 'resultSets' in data:
                    print(f"[CACHE] Found {len(data['resultSets'])} result sets")
                return data
        except (json.JSONDecodeError, IOError) as e:
            # If cache file is corrupted, fetch from API
            print(f"[CACHE] Cache file corrupted for game {game_id}: {e}")
            print(f"[CACHE] Removing corrupted cache and fetching from API")
            os.remove(cache_file)

    print(f"[API] Fetching game {game_id} from NBA API...")
    try:
        # 1) Prefer nba_api endpoint wrapper (usually has correct headers / retry behavior)
        #    This avoids returning '{}' (2 bytes) which is often bot-mitigation or a blocked response.
        try:
            print("[API] Trying nba_api PlayByPlayV2 endpoint...")
            from nba_api.stats.endpoints import playbyplayv2  # type: ignore

            ep = playbyplayv2.PlayByPlayV2(game_id=game_id, timeout=30)
            data = ep.get_dict()

            if data and ("resultSets" in data or "resultSet" in data):
                print("[API] nba_api PlayByPlayV2 returned a valid payload")
            else:
                print("[API] nba_api PlayByPlayV2 returned an unexpected/empty payload; falling back to direct HTTP")
                data = {}
        except Exception as e:
            print(f"[API] nba_api PlayByPlayV2 failed: {type(e).__name__}: {e}")
            data = {}

        # 2) Fallback: direct HTTP request (legacy path)
        if not data:
            print(f"[API] Making direct HTTP request to NBA API...")

            url = "https://stats.nba.com/stats/playbyplayv2"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.nba.com/",
                "Origin": "https://www.nba.com",
                # Common nba.com stats headers
                "x-nba-stats-origin": "stats",
                "x-nba-stats-token": "true",
                "Connection": "keep-alive",
            }
            params = {
                "GameID": game_id,
                "StartPeriod": 0,
                "EndPeriod": 10,
            }

            print(f"[API] URL: {url}")
            print(f"[API] Parameters: {params}")

            response = requests.get(url, headers=headers, params=params, timeout=30)
            print(f"[API] Response status code: {response.status_code}")
            print(f"[API] Response headers: {dict(response.headers)}")

            if response.status_code != 200:
                print(f"[API] ERROR: Non-200 status code: {response.status_code}")
                print(f"[API] Response text: {response.text[:500]}")
                return {}

            print(f"[API] Received response ({len(response.text)} bytes)")
            print(f"[API] First 200 chars of response: {response.text[:200]}")

            print(f"[API] Parsing JSON...")
            data = response.json()
            print(f"[API] Successfully parsed JSON")
            print(f"[API] Response keys: {list(data.keys())}")
            print(f"[API] Full response structure:")
            print(json.dumps(data, indent=2)[:1000] + "...")

        # Validate that we got valid data
        if not data:
            print(f"[API] ERROR: Empty response from NBA API")
            return {}

        if "resultSets" not in data and "resultSet" not in data:
            print(f"[API] ERROR: Invalid response structure from NBA API for game {game_id}.")
            print(f"[API] Available keys: {list(data.keys())}")
            print("[API] Possible reasons:")
            print("[API]   - Game ID doesn't exist")
            print("[API]   - Game hasn't been played yet")
            print("[API]   - NBA API is temporarily unavailable")
            print("[API]   - Bot mitigation returned an empty/trimmed payload")
            return {}

        # Handle both 'resultSets' (plural) and 'resultSet' (singular)
        result_sets_key = "resultSets" if "resultSets" in data else "resultSet"
        print(f"[API] Found result sets using key: '{result_sets_key}'")
        print(f"[API] Number of result sets: {len(data[result_sets_key])}")

        if data[result_sets_key]:
            play_count = len(data[result_sets_key][0].get("rowSet", []))
            print(f"[API] First result set contains {play_count} plays")
            print(f"[API] First result set keys: {list(data[result_sets_key][0].keys())}")

        # Always write to cache (even if use_cache=False, we still want to update the cache)
        print(f"[API] Writing to cache: {cache_file}")
        with open(cache_file, "w") as f:
            json.dump(data, f, indent=4)
        print(f"[API] Cache written successfully")

        # Respect API rate limits
        print(f"[API] Waiting 0.6s for rate limit...")
        time.sleep(0.6)

        return data

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Network error for game {game_id}: {e}")
        print(f"[ERROR] Error type: {type(e).__name__}")
        import traceback
        print(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return {}
    except (KeyError, json.JSONDecodeError) as e:
        print(f"[ERROR] Data structure/parsing error for game {game_id}: {e}")
        print(f"[ERROR] Error type: {type(e).__name__}")
        print("[ERROR] This usually means the game ID is invalid or the game hasn't been played yet.")
        import traceback
        print(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
        return {}
    except Exception as e:
        print(f"[ERROR] Unexpected error fetching data for game {game_id}: {e}")
        print(f"[ERROR] Error type: {type(e).__name__}")
        import traceback
        print(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
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