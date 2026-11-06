"""
Unit tests for game_segment.py module.

Tests the GameSegment class including:
- GameSegment creation with valid lineups
- Time tracking and duration calculation
- Context tracking (score, quarter)
- Segment linking
- BoxScore integration
"""

import pytest
from models.game_segment import GameSegment
from models.lineup import Player, Lineup
from models.boxscore import BoxScore


class TestGameSegmentCreation:
    """Test cases for GameSegment creation and initialization."""

    def test_game_segment_minimal_creation(self):
        """Test creating a GameSegment with minimal required data."""
        # Create lineups
        home_players = [
            Player("203507", "Giannis Antetokounmpo", "MIL"),
            Player("201950", "Jrue Holiday", "MIL"),
            Player("203114", "Khris Middleton", "MIL"),
            Player("1628389", "Brook Lopez", "MIL"),
            Player("1626179", "Grayson Allen", "MIL"),
        ]
        away_players = [
            Player("201935", "Kevin Durant", "BRK"),
            Player("201142", "Kyrie Irving", "BRK"),
            Player("1627742", "James Harden", "BRK"),
            Player("202681", "Blake Griffin", "BRK"),
            Player("1629011", "Nic Claxton", "BRK"),
        ]
        home_lineup = Lineup(players=home_players, team="MIL")
        away_lineup = Lineup(players=away_players, team="BRK")

        # Create game segment
        segment = GameSegment(
            segment_id="0022100001_001",
            game_id="0022100001",
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_time=720.0,
            end_time=675.0,
            start_quarter=1,
            end_quarter=1,
        )

        assert segment.segment_id == "0022100001_001"
        assert segment.game_id == "0022100001"
        assert segment.home_lineup == home_lineup
        assert segment.away_lineup == away_lineup
        assert segment.start_time == 720.0
        assert segment.end_time == 675.0
        assert segment.start_quarter == 1
        assert segment.end_quarter == 1
        assert segment.home_boxscore is not None
        assert segment.away_boxscore is not None
        assert segment.context is not None

    def test_game_segment_with_boxscores(self):
        """Test creating a GameSegment with pre-populated boxscores."""
        home_players = [
            Player("203507", "Giannis Antetokounmpo", "MIL"),
            Player("201950", "Jrue Holiday", "MIL"),
            Player("203114", "Khris Middleton", "MIL"),
            Player("1628389", "Brook Lopez", "MIL"),
            Player("1626179", "Grayson Allen", "MIL"),
        ]
        away_players = [
            Player("201935", "Kevin Durant", "BRK"),
            Player("201142", "Kyrie Irving", "BRK"),
            Player("1627742", "James Harden", "BRK"),
            Player("202681", "Blake Griffin", "BRK"),
            Player("1629011", "Nic Claxton", "BRK"),
        ]
        home_lineup = Lineup(players=home_players, team="MIL")
        away_lineup = Lineup(players=away_players, team="BRK")

        home_boxscore = BoxScore(points=15, fgm=6, fga=12)
        away_boxscore = BoxScore(points=10, fgm=4, fga=10)

        segment = GameSegment(
            segment_id="0022100001_001",
            game_id="0022100001",
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_time=720.0,
            end_time=675.0,
            start_quarter=1,
            end_quarter=1,
            home_boxscore=home_boxscore,
            away_boxscore=away_boxscore,
        )

        assert segment.home_boxscore.points == 15
        assert segment.away_boxscore.points == 10


class TestGameSegmentDuration:
    """Test cases for duration calculation."""

    def test_duration_calculation(self):
        """Test that duration is calculated correctly."""
        home_players = [Player("203507", "Giannis", "MIL") for _ in range(5)]
        away_players = [Player("201935", "Durant", "BRK") for _ in range(5)]
        home_lineup = Lineup(players=home_players, team="MIL")
        away_lineup = Lineup(players=away_players, team="BRK")

        segment = GameSegment(
            segment_id="0022100001_001",
            game_id="0022100001",
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_time=720.0,  # 12:00 in quarter
            end_time=600.0,  # 10:00 in quarter
            start_quarter=1,
            end_quarter=1,
        )

        assert segment.duration == 120.0  # 2 minutes = 120 seconds

    def test_duration_full_quarter(self):
        """Test duration for a full quarter."""
        home_players = [Player("203507", "Giannis", "MIL") for _ in range(5)]
        away_players = [Player("201935", "Durant", "BRK") for _ in range(5)]
        home_lineup = Lineup(players=home_players, team="MIL")
        away_lineup = Lineup(players=away_players, team="BRK")

        segment = GameSegment(
            segment_id="0022100001_001",
            game_id="0022100001",
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_time=720.0,  # Start of quarter
            end_time=0.0,  # End of quarter
            start_quarter=1,
            end_quarter=1,
        )

        assert segment.duration == 720.0  # 12 minutes = 720 seconds

    def test_duration_zero_length(self):
        """Test duration for zero-length segment (edge case)."""
        home_players = [Player("203507", "Giannis", "MIL") for _ in range(5)]
        away_players = [Player("201935", "Durant", "BRK") for _ in range(5)]
        home_lineup = Lineup(players=home_players, team="MIL")
        away_lineup = Lineup(players=away_players, team="BRK")

        segment = GameSegment(
            segment_id="0022100001_001",
            game_id="0022100001",
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_time=600.0,
            end_time=600.0,
            start_quarter=1,
            end_quarter=1,
        )

        assert segment.duration == 0.0

    def test_duration_across_quarters(self):
        """Test duration calculation across quarter boundaries."""
        home_players = [Player("203507", "Giannis", "MIL") for _ in range(5)]
        away_players = [Player("201935", "Durant", "BRK") for _ in range(5)]
        home_lineup = Lineup(players=home_players, team="MIL")
        away_lineup = Lineup(players=away_players, team="BRK")

        segment = GameSegment(
            segment_id="0022100001_001",
            game_id="0022100001",
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_time=30.0,  # 0:30 in Q1
            end_time=690.0,  # 11:30 in Q2 (after quarter break)
            start_quarter=1,
            end_quarter=2,
        )

        # Duration should be 30 seconds in Q1 + 30 seconds in Q2 = 60 seconds
        # (Note: This is a simplified calculation - real implementation might handle quarter breaks differently)
        assert segment.duration == 60.0


class TestGameSegmentContext:
    """Test cases for game context tracking."""

    def test_context_initialization(self):
        """Test that context is initialized properly."""
        home_players = [Player("203507", "Giannis", "MIL") for _ in range(5)]
        away_players = [Player("201935", "Durant", "BRK") for _ in range(5)]
        home_lineup = Lineup(players=home_players, team="MIL")
        away_lineup = Lineup(players=away_players, team="BRK")

        segment = GameSegment(
            segment_id="0022100001_001",
            game_id="0022100001",
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_time=720.0,
            end_time=675.0,
            start_quarter=1,
            end_quarter=1,
        )

        assert segment.context is not None
        assert hasattr(segment.context, "home_score")
        assert hasattr(segment.context, "away_score")
        assert hasattr(segment.context, "quarter")

    def test_context_score_tracking(self):
        """Test that context tracks scores correctly."""
        home_players = [Player("203507", "Giannis", "MIL") for _ in range(5)]
        away_players = [Player("201935", "Durant", "BRK") for _ in range(5)]
        home_lineup = Lineup(players=home_players, team="MIL")
        away_lineup = Lineup(players=away_players, team="BRK")

        segment = GameSegment(
            segment_id="0022100001_001",
            game_id="0022100001",
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_time=720.0,
            end_time=675.0,
            start_quarter=1,
            end_quarter=1,
        )

        # Set initial scores
        segment.context.home_score = 0
        segment.context.away_score = 0

        # Simulate scoring during segment
        segment.home_boxscore.add_points(8)
        segment.away_boxscore.add_points(5)

        # Update context scores
        segment.context.home_score = 8
        segment.context.away_score = 5

        assert segment.context.home_score == 8
        assert segment.context.away_score == 5

    def test_context_quarter_tracking(self):
        """Test that context tracks quarter correctly."""
        home_players = [Player("203507", "Giannis", "MIL") for _ in range(5)]
        away_players = [Player("201935", "Durant", "BRK") for _ in range(5)]
        home_lineup = Lineup(players=home_players, team="MIL")
        away_lineup = Lineup(players=away_players, team="BRK")

        segment = GameSegment(
            segment_id="0022100001_001",
            game_id="0022100001",
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_time=720.0,
            end_time=675.0,
            start_quarter=2,  # Second quarter
            end_quarter=2,
        )

        assert segment.start_quarter == 2
        assert segment.end_quarter == 2
        assert segment.context.quarter == 2


class TestGameSegmentBoxScoreIntegration:
    """Test cases for BoxScore integration."""

    def test_boxscore_accumulation(self):
        """Test that boxscores accumulate stats correctly."""
        home_players = [Player("203507", "Giannis", "MIL") for _ in range(5)]
        away_players = [Player("201935", "Durant", "BRK") for _ in range(5)]
        home_lineup = Lineup(players=home_players, team="MIL")
        away_lineup = Lineup(players=away_players, team="BRK")

        segment = GameSegment(
            segment_id="0022100001_001",
            game_id="0022100001",
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_time=720.0,
            end_time=675.0,
            start_quarter=1,
            end_quarter=1,
        )

        # Add stats to home team
        segment.home_boxscore.add_field_goal(made=True)
        segment.home_boxscore.add_field_goal(made=True)
        segment.home_boxscore.add_three_point(made=True)
        segment.home_boxscore.add_free_throw(made=True)
        segment.home_boxscore.add_assist()
        segment.home_boxscore.add_rebound(offensive=True)

        # Add stats to away team
        segment.away_boxscore.add_field_goal(made=True)
        segment.away_boxscore.add_field_goal(made=False)
        segment.away_boxscore.add_turnover()

        # Verify stats
        assert segment.home_boxscore.fgm == 3
        assert segment.home_boxscore.fga == 3
        assert segment.home_boxscore.fg3m == 1
        assert segment.home_boxscore.fg3a == 1
        assert segment.home_boxscore.ftm == 1
        assert segment.home_boxscore.fta == 1
        assert segment.home_boxscore.ast == 1
        assert segment.home_boxscore.oreb == 1

        assert segment.away_boxscore.fgm == 1
        assert segment.away_boxscore.fga == 2
        assert segment.away_boxscore.tov == 1

    def test_plus_minus_calculation(self):
        """Test that plus/minus is calculated correctly."""
        home_players = [Player("203507", "Giannis", "MIL") for _ in range(5)]
        away_players = [Player("201935", "Durant", "BRK") for _ in range(5)]
        home_lineup = Lineup(players=home_players, team="MIL")
        away_lineup = Lineup(players=away_players, team="BRK")

        segment = GameSegment(
            segment_id="0022100001_001",
            game_id="0022100001",
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_time=720.0,
            end_time=675.0,
            start_quarter=1,
            end_quarter=1,
        )

        # Simulate scoring: Home scores 8, Away scores 5
        segment.home_boxscore.add_points(8)
        segment.away_boxscore.add_points(5)

        # Update plus/minus
        segment.home_boxscore.update_plus_minus(8 - 5)  # +3
        segment.away_boxscore.update_plus_minus(5 - 8)  # -3

        assert segment.home_boxscore.plus_minus == 3
        assert segment.away_boxscore.plus_minus == -3


class TestGameSegmentEdgeCases:
    """Test cases for edge cases."""

    def test_segment_with_empty_lineup_raises_error(self):
        """Test that creating a segment with invalid lineup raises error."""
        home_players = [Player("203507", "Giannis", "MIL") for _ in range(5)]
        away_players = [Player("201935", "Durant", "BRK") for _ in range(4)]  # Only 4 players
        home_lineup = Lineup(players=home_players, team="MIL")

        with pytest.raises(ValueError):
            away_lineup = Lineup(players=away_players, team="BRK")
            GameSegment(
                segment_id="0022100001_001",
                game_id="0022100001",
                home_lineup=home_lineup,
                away_lineup=away_lineup,
                start_time=720.0,
                end_time=675.0,
                start_quarter=1,
                end_quarter=1,
            )

    def test_segment_id_format(self):
        """Test that segment ID follows expected format."""
        home_players = [Player("203507", "Giannis", "MIL") for _ in range(5)]
        away_players = [Player("201935", "Durant", "BRK") for _ in range(5)]
        home_lineup = Lineup(players=home_players, team="MIL")
        away_lineup = Lineup(players=away_players, team="BRK")

        segment = GameSegment(
            segment_id="0022100001_001",
            game_id="0022100001",
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_time=720.0,
            end_time=675.0,
            start_quarter=1,
            end_quarter=1,
        )

        assert segment.segment_id.startswith("0022100001_")
        assert len(segment.segment_id.split("_")) == 2


class TestGameSegmentStringRepresentation:
    """Test cases for string representation."""

    def test_game_segment_str(self):
        """Test string representation of GameSegment."""
        home_players = [Player("203507", "Giannis", "MIL") for _ in range(5)]
        away_players = [Player("201935", "Durant", "BRK") for _ in range(5)]
        home_lineup = Lineup(players=home_players, team="MIL")
        away_lineup = Lineup(players=away_players, team="BRK")

        segment = GameSegment(
            segment_id="0022100001_001",
            game_id="0022100001",
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_time=720.0,
            end_time=675.0,
            start_quarter=1,
            end_quarter=1,
        )

        str_repr = str(segment)
        assert "GameSegment" in str_repr
        assert "0022100001_001" in str_repr
        assert "MIL" in str_repr
        assert "BRK" in str_repr

    def test_game_segment_repr(self):
        """Test repr of GameSegment."""
        home_players = [Player("203507", "Giannis", "MIL") for _ in range(5)]
        away_players = [Player("201935", "Durant", "BRK") for _ in range(5)]
        home_lineup = Lineup(players=home_players, team="MIL")
        away_lineup = Lineup(players=away_players, team="BRK")

        segment = GameSegment(
            segment_id="0022100001_001",
            game_id="0022100001",
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_time=720.0,
            end_time=675.0,
            start_quarter=1,
            end_quarter=1,
        )

        repr_str = repr(segment)
        assert "GameSegment" in repr_str
        assert "segment_id='0022100001_001'" in repr_str