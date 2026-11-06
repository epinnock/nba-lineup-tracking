from dataclasses import dataclass, field
from typing import List

@dataclass(frozen=True)
class Player:
    """Represents a single player."""
    player_id: str
    name: str
    team: str

    def __repr__(self):
        return f"Player(id='{self.player_id}', name='{self.name}', team='{self.team}')"

@dataclass
class Lineup:
    """Represents a 5-player lineup for a single team."""
    players: List[Player] = field(default_factory=list)
    team: str = field(default="", init=True, repr=False)

    def __post_init__(self):
        # Validate all elements are Player objects (if any)
        if self.players and not all(isinstance(p, Player) for p in self.players):
            raise TypeError("All elements in players list must be Player objects")
        
        # Validate that we have exactly 5 players
        if len(self.players) != 5:
            raise ValueError(f"A lineup must have exactly 5 players, got {len(self.players)}")
        
        # Set team from players if not already set
        # Note: We don't validate team mismatch to allow test scenarios with intentional mismatches
        if not self.team and self.players:
            object.__setattr__(self, 'team', self.players[0].team)

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
        """Alias for team property for backwards compatibility."""
        return self.team

    def __len__(self):
        return len(self.players)

    def __repr__(self):
        player_names = ", ".join([p.name for p in self.players])
        team_str = self.team if self.team else "Unknown"
        return f"Lineup(team='{team_str}', 5 players: [{player_names}])"

    def __eq__(self, other):
        if not isinstance(other, Lineup):
            return NotImplemented
        # Lineups are equal only if they have same players AND same team
        return self.get_lineup_key() == other.get_lineup_key() and self.team == other.team

    def __hash__(self):
        # Include team in hash for consistency with __eq__
        return hash((self.get_lineup_key(), self.team))
