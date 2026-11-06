"""
Data validation module for NBA Lineup Tracker.

Provides validation functions for game IDs and play-by-play data structures.
"""

import re
from typing import Any, Dict


def validate_game_id(game_id: Any) -> bool:
    """
    Validate a game ID format.

    Game IDs should be 10-digit strings starting with:
    - '001' for preseason
    - '002' for regular season
    - '004' for playoffs

    Args:
        game_id: The game ID to validate

    Returns:
        True if valid, False otherwise
    """
    if game_id is None:
        return False

    if not isinstance(game_id, str):
        return False

    # Must be exactly 10 characters
    if len(game_id) != 10:
        return False

    # Must be all digits
    if not game_id.isdigit():
        return False

    # Must start with valid prefix
    valid_prefixes = ["001", "002", "004"]
    prefix = game_id[:3]

    return prefix in valid_prefixes


def validate_playbyplay_data(data: Any) -> bool:
    """
    Validate play-by-play data structure.

    Checks for basic structure with resultSets containing PlayByPlay data.
    This is a lenient validator that checks for the presence of required
    structure but allows for variations in the actual data.

    Args:
        data: The play-by-play data to validate

    Returns:
        True if structure is valid, False otherwise
    """
    if data is None:
        return False

    if not isinstance(data, dict):
        return False

    # Must have resultSets key
    if "resultSets" not in data:
        return False

    result_sets = data["resultSets"]

    # resultSets must be a list
    if not isinstance(result_sets, list):
        return False

    # resultSets should not be empty (though this is flexible)
    if len(result_sets) == 0:
        return False

    # Basic structure is valid
    return True