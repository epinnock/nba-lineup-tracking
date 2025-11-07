from dataclasses import dataclass, field
from typing import List

@dataclass
class Player:
    """Represents a single player."""
    player_id: int
    player_name: str
    team_abbreviation: str

@dataclass
class Lineup:
    """Represents a 5-player lineup for a single team."""
    players: List[Player] = field(default_factory=list)

    def __post_init__(self):
        # Sort players by ID to ensure consistency for comparisons and key generation.
        self.players.sort(key=lambda p: p.player_id)

    def get_lineup_key(self) -> str:
        """
        Generates a unique and consistent key for the lineup.
        This is crucial for identifying when a specific lineup is on the court.
        Example: '201939-202681-203507-1627749-1628369'
        """
        return "-".join(sorted([str(p.player_id) for p in self.players]))

    @property
    def team_abbreviation(self) -> str:
        """
        Returns the team abbreviation for the lineup.
        Assumes all players are from the same team.
        """
        if not self.players:
            return ""
        return self.players[0].team_abbreviation

    def __len__(self):
        return len(self.players)

    def __repr__(self):
        player_names = ", ".join([p.player_name for p in self.players])
        return f"Lineup(team='{self.team_abbreviation}', players=[{player_names}])"

    def __eq__(self, other):
        if not isinstance(other, Lineup):
            return NotImplemented
        return self.get_lineup_key() == other.get_lineup_key()

    def __hash__(self):
        return hash(self.get_lineup_key())
