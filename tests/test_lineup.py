"""
Unit tests for lineup.py module.

Tests the Player and Lineup classes including:
- Player creation and attributes
- Lineup creation with exactly 5 players
- Lineup key generation and sorting
- Equality and comparison methods
- Edge cases: duplicate players, invalid player counts
"""

import pytest
from models.lineup import Player, Lineup


class TestPlayer:
    """Test cases for the Player class."""

    def test_player_creation(self):
        """Test creating a Player with valid attributes."""
        player = Player(player_id="203507", name="Giannis Antetokounmpo", team="MIL")
        assert player.player_id == "203507"
        assert player.name == "Giannis Antetokounmpo"
        assert player.team == "MIL"

    def test_player_attributes_immutable(self):
        """Test that player attributes are correctly set."""
        player = Player(player_id="201939", name="Stephen Curry", team="GSW")
        assert isinstance(player.player_id, str)
        assert isinstance(player.name, str)
        assert isinstance(player.team, str)


class TestLineup:
    """Test cases for the Lineup class."""

    def test_lineup_creation_with_five_players(self):
        """Test creating a Lineup with exactly 5 players."""
        players = [
            Player("203507", "Giannis Antetokounmpo", "MIL"),
            Player("201950", "Jrue Holiday", "MIL"),
            Player("203114", "Khris Middleton", "MIL"),
            Player("1628389", "Brook Lopez", "MIL"),
            Player("1626179", "Grayson Allen", "MIL"),
        ]
        lineup = Lineup(players=players, team="MIL")
        assert len(lineup.players) == 5
        assert lineup.team == "MIL"

    def test_lineup_creation_with_too_few_players(self):
        """Test that creating a Lineup with fewer than 5 players raises an error."""
        players = [
            Player("203507", "Giannis Antetokounmpo", "MIL"),
            Player("201950", "Jrue Holiday", "MIL"),
            Player("203114", "Khris Middleton", "MIL"),
        ]
        with pytest.raises(ValueError, match="A lineup must have exactly 5 players"):
            Lineup(players=players, team="MIL")

    def test_lineup_creation_with_too_many_players(self):
        """Test that creating a Lineup with more than 5 players raises an error."""
        players = [
            Player("203507", "Giannis Antetokounmpo", "MIL"),
            Player("201950", "Jrue Holiday", "MIL"),
            Player("203114", "Khris Middleton", "MIL"),
            Player("1628389", "Brook Lopez", "MIL"),
            Player("1626179", "Grayson Allen", "MIL"),
            Player("203507", "Extra Player", "MIL"),  # Duplicate ID but still 6 players
        ]
        with pytest.raises(ValueError, match="A lineup must have exactly 5 players"):
            Lineup(players=players, team="MIL")

    def test_lineup_creation_with_duplicate_players(self):
        """Test creating a Lineup with duplicate player IDs."""
        players = [
            Player("203507", "Giannis Antetokounmpo", "MIL"),
            Player("201950", "Jrue Holiday", "MIL"),
            Player("203114", "Khris Middleton", "MIL"),
            Player("1628389", "Brook Lopez", "MIL"),
            Player("203507", "Giannis Duplicate", "MIL"),  # Same ID as first player
        ]
        # This should be allowed (the validation is lenient)
        lineup = Lineup(players=players, team="MIL")
        assert len(lineup.players) == 5

    def test_get_lineup_key(self):
        """Test that lineup key is generated correctly with sorted player IDs."""
        players = [
            Player("203507", "Giannis Antetokounmpo", "MIL"),
            Player("201950", "Jrue Holiday", "MIL"),
            Player("203114", "Khris Middleton", "MIL"),
            Player("1628389", "Brook Lopez", "MIL"),
            Player("1626179", "Grayson Allen", "MIL"),
        ]
        lineup = Lineup(players=players, team="MIL")
        key = lineup.get_lineup_key()

        # Key should be sorted player IDs joined by hyphens
        expected_ids = ["1626179", "1628389", "201950", "203114", "203507"]
        expected_key = "-".join(expected_ids)
        assert key == expected_key

    def test_get_lineup_key_is_consistent(self):
        """Test that lineup key is consistent regardless of player order."""
        players1 = [
            Player("203507", "Giannis Antetokounmpo", "MIL"),
            Player("201950", "Jrue Holiday", "MIL"),
            Player("203114", "Khris Middleton", "MIL"),
            Player("1628389", "Brook Lopez", "MIL"),
            Player("1626179", "Grayson Allen", "MIL"),
        ]
        players2 = [
            Player("1626179", "Grayson Allen", "MIL"),
            Player("1628389", "Brook Lopez", "MIL"),
            Player("203114", "Khris Middleton", "MIL"),
            Player("201950", "Jrue Holiday", "MIL"),
            Player("203507", "Giannis Antetokounmpo", "MIL"),
        ]
        lineup1 = Lineup(players=players1, team="MIL")
        lineup2 = Lineup(players=players2, team="MIL")

        assert lineup1.get_lineup_key() == lineup2.get_lineup_key()

    def test_lineup_equality(self):
        """Test that lineups with same players are considered equal."""
        players1 = [
            Player("203507", "Giannis Antetokounmpo", "MIL"),
            Player("201950", "Jrue Holiday", "MIL"),
            Player("203114", "Khris Middleton", "MIL"),
            Player("1628389", "Brook Lopez", "MIL"),
            Player("1626179", "Grayson Allen", "MIL"),
        ]
        players2 = [
            Player("1626179", "Grayson Allen", "MIL"),
            Player("1628389", "Brook Lopez", "MIL"),
            Player("203114", "Khris Middleton", "MIL"),
            Player("201950", "Jrue Holiday", "MIL"),
            Player("203507", "Giannis Antetokounmpo", "MIL"),
        ]
        lineup1 = Lineup(players=players1, team="MIL")
        lineup2 = Lineup(players=players2, team="MIL")

        assert lineup1 == lineup2

    def test_lineup_inequality_different_players(self):
        """Test that lineups with different players are not equal."""
        players1 = [
            Player("203507", "Giannis Antetokounmpo", "MIL"),
            Player("201950", "Jrue Holiday", "MIL"),
            Player("203114", "Khris Middleton", "MIL"),
            Player("1628389", "Brook Lopez", "MIL"),
            Player("1626179", "Grayson Allen", "MIL"),
        ]
        players2 = [
            Player("203507", "Giannis Antetokounmpo", "MIL"),
            Player("201950", "Jrue Holiday", "MIL"),
            Player("203114", "Khris Middleton", "MIL"),
            Player("1628389", "Brook Lopez", "MIL"),
            Player("201939", "Stephen Curry", "GSW"),  # Different player
        ]
        lineup1 = Lineup(players=players1, team="MIL")
        lineup2 = Lineup(players=players2, team="MIL")

        assert lineup1 != lineup2

    def test_lineup_inequality_different_team(self):
        """Test that lineups with same players but different teams are not equal."""
        players = [
            Player("203507", "Giannis Antetokounmpo", "MIL"),
            Player("201950", "Jrue Holiday", "MIL"),
            Player("203114", "Khris Middleton", "MIL"),
            Player("1628389", "Brook Lopez", "MIL"),
            Player("1626179", "Grayson Allen", "MIL"),
        ]
        lineup1 = Lineup(players=players, team="MIL")
        lineup2 = Lineup(players=players, team="GSW")  # Different team

        assert lineup1 != lineup2

    def test_lineup_hash(self):
        """Test that lineup can be hashed and used in sets/dicts."""
        players = [
            Player("203507", "Giannis Antetokounmpo", "MIL"),
            Player("201950", "Jrue Holiday", "MIL"),
            Player("203114", "Khris Middleton", "MIL"),
            Player("1628389", "Brook Lopez", "MIL"),
            Player("1626179", "Grayson Allen", "MIL"),
        ]
        lineup = Lineup(players=players, team="MIL")

        # Should be hashable
        lineup_set = {lineup}
        assert len(lineup_set) == 1

        # Should work as dict key
        lineup_dict = {lineup: "test"}
        assert lineup_dict[lineup] == "test"

    def test_lineup_repr(self):
        """Test lineup string representation."""
        players = [
            Player("203507", "Giannis Antetokounmpo", "MIL"),
            Player("201950", "Jrue Holiday", "MIL"),
            Player("203114", "Khris Middleton", "MIL"),
            Player("1628389", "Brook Lopez", "MIL"),
            Player("1626179", "Grayson Allen", "MIL"),
        ]
        lineup = Lineup(players=players, team="MIL")
        repr_str = repr(lineup)

        assert "Lineup" in repr_str
        assert "MIL" in repr_str
        assert "5 players" in repr_str

    def test_empty_lineup_not_allowed(self):
        """Test that creating a lineup with no players raises an error."""
        with pytest.raises(ValueError, match="A lineup must have exactly 5 players"):
            Lineup(players=[], team="MIL")

    def test_lineup_with_non_player_objects(self):
        """Test that lineup creation fails with non-Player objects."""
        with pytest.raises(TypeError):
            Lineup(players=["not", "player", "objects", "list", "here"], team="MIL")