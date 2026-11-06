from typing import Dict

# Fantasy scoring providers
FANTASY_PROVIDER_DK = "draftkings"
FANTASY_PROVIDER_FD = "fanduel"
FANTASY_DEFAULT_PROVIDER = FANTASY_PROVIDER_DK

# Scoring weights for supported providers
# Notes:
# - DD/TD bonuses (double-double/triple-double) intentionally included for completeness,
#   but segment-level fantasy typically excludes them since they're game-level bonuses.
#   We will not apply them in segment computations unless explicitly requested.
SCORING_WEIGHTS: Dict[str, Dict[str, float]] = {
    FANTASY_PROVIDER_DK: {
        # DraftKings
        "PTS": 1.0,   # Points
        "3PM": 0.5,   # 3-pointers made
        "REB": 1.25,  # Rebounds
        "AST": 1.5,   # Assists
        "STL": 2.0,   # Steals
        "BLK": 2.0,   # Blocks
        "TOV": -0.5,  # Turnovers
        "DD": 1.5,    # Double-Double (not applied per segment)
        "TD": 3.0,    # Triple-Double (not applied per segment)
    },
    FANTASY_PROVIDER_FD: {
        # FanDuel
        "PTS": 1.0,
        "3PM": 0.0,   # No 3PM bonus on FanDuel
        "REB": 1.2,
        "AST": 1.5,
        "STL": 3.0,
        "BLK": 3.0,
        "TOV": -1.0,
        # No DD/TD bonuses on FanDuel
    },
}

def get_scoring_weights(provider: str | None = None) -> Dict[str, float]:
    """
    Return the scoring weight mapping for a fantasy provider.

    Args:
        provider: The provider key (e.g., "draftkings" or "fanduel"). Defaults to DraftKings.

    Returns:
        A dict of stat -> weight.
    """
    if not provider:
        return SCORING_WEIGHTS[FANTASY_DEFAULT_PROVIDER]
    key = provider.lower()
    return SCORING_WEIGHTS.get(key, SCORING_WEIGHTS[FANTASY_DEFAULT_PROVIDER])