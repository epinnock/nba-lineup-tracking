"""
Unit tests for boxscore.py module.

Tests the BoxScore class including:
- BoxScore creation with all statistical fields
- Calculated properties (FG%, 3P%, FT%)
- Update methods for each stat type
- Edge cases: division by zero, zero attempts
- Plus/minus calculation
- Possession tracking
"""

import pytest
from models.boxscore import BoxScore


class TestBoxScoreCreation:
    """Test cases for BoxScore creation and initialization."""

    def test_boxscore_default_creation(self):
        """Test creating a BoxScore with default values."""
        boxscore = BoxScore()
        assert boxscore.points == 0
        assert boxscore.fgm == 0
        assert boxscore.fga == 0
        assert boxscore.fg3m == 0
        assert boxscore.fg3a == 0
        assert boxscore.ftm == 0
        assert boxscore.fta == 0
        assert boxscore.oreb == 0
        assert boxscore.dreb == 0
        assert boxscore.treb == 0
        assert boxscore.ast == 0
        assert boxscore.stl == 0
        assert boxscore.blk == 0
        assert boxscore.tov == 0
        assert boxscore.pf == 0
        assert boxscore.plus_minus == 0
        assert boxscore.possessions == 0
        assert boxscore.duration_seconds == 0.0

    def test_boxscore_custom_values(self):
        """Test creating a BoxScore with custom values."""
        boxscore = BoxScore(
            points=25,
            fgm=10,
            fga=20,
            fg3m=3,
            fg3a=8,
            ftm=2,
            fta=2,
            oreb=2,
            dreb=8,
            treb=10,
            ast=5,
            stl=2,
            blk=1,
            tov=3,
            pf=2,
            plus_minus=+8,
            possessions=95,
            duration_seconds=480.0,
        )
        assert boxscore.points == 25
        assert boxscore.fgm == 10
        assert boxscore.fga == 20
        assert boxscore.fg3m == 3
        assert boxscore.fg3a == 8
        assert boxscore.ftm == 2
        assert boxscore.fta == 2
        assert boxscore.oreb == 2
        assert boxscore.dreb == 8
        assert boxscore.treb == 10
        assert boxscore.ast == 5
        assert boxscore.stl == 2
        assert boxscore.blk == 1
        assert boxscore.tov == 3
        assert boxscore.pf == 2
        assert boxscore.plus_minus == 8
        assert boxscore.possessions == 95
        assert boxscore.duration_seconds == 480.0


class TestBoxScoreCalculatedProperties:
    """Test cases for calculated properties."""

    def test_fg_pct_normal_case(self):
        """Test FG% calculation with normal values."""
        boxscore = BoxScore(fgm=8, fga=20)
        assert boxscore.fg_pct == 0.4

    def test_fg_pct_perfect_shooting(self):
        """Test FG% calculation with perfect shooting."""
        boxscore = BoxScore(fgm=10, fga=10)
        assert boxscore.fg_pct == 1.0

    def test_fg_pct_zero_made(self):
        """Test FG% calculation with zero made field goals."""
        boxscore = BoxScore(fgm=0, fga=10)
        assert boxscore.fg_pct == 0.0

    def test_fg_pct_zero_attempts(self):
        """Test FG% calculation with zero attempts (edge case)."""
        boxscore = BoxScore(fgm=0, fga=0)
        assert boxscore.fg_pct == 0.0

    def test_fg3_pct_normal_case(self):
        """Test 3P% calculation with normal values."""
        boxscore = BoxScore(fg3m=3, fg3a=8)
        assert boxscore.fg3_pct == 0.375

    def test_fg3_pct_zero_made(self):
        """Test 3P% calculation with zero made threes."""
        boxscore = BoxScore(fg3m=0, fg3a=5)
        assert boxscore.fg3_pct == 0.0

    def test_fg3_pct_zero_attempts(self):
        """Test 3P% calculation with zero attempts."""
        boxscore = BoxScore(fg3m=0, fg3a=0)
        assert boxscore.fg3_pct == 0.0

    def test_ft_pct_normal_case(self):
        """Test FT% calculation with normal values."""
        boxscore = BoxScore(ftm=8, fta=10)
        assert boxscore.ft_pct == 0.8

    def test_ft_pct_zero_made(self):
        """Test FT% calculation with zero made free throws."""
        boxscore = BoxScore(ftm=0, fta=4)
        assert boxscore.ft_pct == 0.0

    def test_ft_pct_zero_attempts(self):
        """Test FT% calculation with zero attempts."""
        boxscore = BoxScore(ftm=0, fta=0)
        assert boxscore.ft_pct == 0.0

    def test_total_rebounds_calculation(self):
        """Test that total rebounds equals offensive + defensive."""
        boxscore = BoxScore(oreb=3, dreb=7)
        assert boxscore.treb == 10
        assert boxscore.treb == boxscore.oreb + boxscore.dreb


class TestBoxScoreUpdateMethods:
    """Test cases for update methods."""

    def test_add_points(self):
        """Test adding points to boxscore."""
        boxscore = BoxScore(points=10)
        boxscore.add_points(5)
        assert boxscore.points == 15

    def test_add_field_goal_made(self):
        """Test adding a made field goal."""
        boxscore = BoxScore(fgm=5, fga=12)
        boxscore.add_field_goal(made=True)
        assert boxscore.fgm == 6
        assert boxscore.fga == 13

    def test_add_field_goal_missed(self):
        """Test adding a missed field goal."""
        boxscore = BoxScore(fgm=5, fga=12)
        boxscore.add_field_goal(made=False)
        assert boxscore.fgm == 5
        assert boxscore.fga == 13

    def test_add_three_point_made(self):
        """Test adding a made three-point field goal."""
        boxscore = BoxScore(fg3m=2, fg3a=5, fgm=6, fga=12)
        boxscore.add_three_point(made=True)
        assert boxscore.fg3m == 3
        assert boxscore.fg3a == 6
        assert boxscore.fgm == 7
        assert boxscore.fga == 13

    def test_add_three_point_missed(self):
        """Test adding a missed three-point field goal."""
        boxscore = BoxScore(fg3m=2, fg3a=5, fgm=6, fga=12)
        boxscore.add_three_point(made=False)
        assert boxscore.fg3m == 2
        assert boxscore.fg3a == 6
        assert boxscore.fgm == 6
        assert boxscore.fga == 13

    def test_add_free_throw_made(self):
        """Test adding a made free throw."""
        boxscore = BoxScore(ftm=7, fta=9)
        boxscore.add_free_throw(made=True)
        assert boxscore.ftm == 8
        assert boxscore.fta == 10

    def test_add_free_throw_missed(self):
        """Test adding a missed free throw."""
        boxscore = BoxScore(ftm=7, fta=9)
        boxscore.add_free_throw(made=False)
        assert boxscore.ftm == 7
        assert boxscore.fta == 10

    def test_add_rebound_offensive(self):
        """Test adding an offensive rebound."""
        boxscore = BoxScore(oreb=3, treb=8)
        boxscore.add_rebound(offensive=True)
        assert boxscore.oreb == 4
        assert boxscore.treb == 9

    def test_add_rebound_defensive(self):
        """Test adding a defensive rebound."""
        boxscore = BoxScore(dreb=5, treb=8)
        boxscore.add_rebound(offensive=False)
        assert boxscore.dreb == 6
        assert boxscore.treb == 9

    def test_add_assist(self):
        """Test adding an assist."""
        boxscore = BoxScore(ast=4)
        boxscore.add_assist()
        assert boxscore.ast == 5

    def test_add_steal(self):
        """Test adding a steal."""
        boxscore = BoxScore(stl=2)
        boxscore.add_steal()
        assert boxscore.stl == 3

    def test_add_block(self):
        """Test adding a block."""
        boxscore = BoxScore(blk=1)
        boxscore.add_block()
        assert boxscore.blk == 2

    def test_add_turnover(self):
        """Test adding a turnover."""
        boxscore = BoxScore(tov=3)
        boxscore.add_turnover()
        assert boxscore.tov == 4

    def test_add_foul(self):
        """Test adding a personal foul."""
        boxscore = BoxScore(pf=2)
        boxscore.add_foul()
        assert boxscore.pf == 3


class TestBoxScorePlusMinus:
    """Test cases for plus/minus tracking."""

    def test_plus_minus_initial(self):
        """Test initial plus/minus value."""
        boxscore = BoxScore()
        assert boxscore.plus_minus == 0

    def test_plus_minus_update_positive(self):
        """Test updating plus/minus with positive value."""
        boxscore = BoxScore()
        boxscore.update_plus_minus(5)
        assert boxscore.plus_minus == 5

    def test_plus_minus_update_negative(self):
        """Test updating plus/minus with negative value."""
        boxscore = BoxScore()
        boxscore.update_plus_minus(-3)
        assert boxscore.plus_minus == -3

    def test_plus_minus_cumulative(self):
        """Test cumulative plus/minus updates."""
        boxscore = BoxScore()
        boxscore.update_plus_minus(5)
        boxscore.update_plus_minus(-2)
        boxscore.update_plus_minus(3)
        assert boxscore.plus_minus == 6


class TestBoxScorePossessions:
    """Test cases for possession tracking."""

    def test_possessions_initial(self):
        """Test initial possessions value."""
        boxscore = BoxScore()
        assert boxscore.possessions == 0

    def test_possessions_update(self):
        """Test updating possessions."""
        boxscore = BoxScore()
        boxscore.possessions = 95
        assert boxscore.possessions == 95

    def test_possessions_add(self):
        """Test adding possessions."""
        boxscore = BoxScore(possessions=50)
        boxscore.possessions += 10
        assert boxscore.possessions == 60


class TestBoxScoreDuration:
    """Test cases for duration tracking."""

    def test_duration_initial(self):
        """Test initial duration value."""
        boxscore = BoxScore()
        assert boxscore.duration_seconds == 0.0

    def test_duration_update(self):
        """Test updating duration."""
        boxscore = BoxScore()
        boxscore.duration_seconds = 480.0
        assert boxscore.duration_seconds == 480.0

    def test_duration_add(self):
        """Test adding to duration."""
        boxscore = BoxScore(duration_seconds=120.0)
        boxscore.duration_seconds += 60.0
        assert boxscore.duration_seconds == 180.0


class TestBoxScoreStringRepresentation:
    """Test cases for string representation."""

    def test_boxscore_str(self):
        """Test string representation of BoxScore."""
        boxscore = BoxScore(points=25, fgm=10, fga=20)
        str_repr = str(boxscore)
        assert "BoxScore" in str_repr
        assert "25" in str_repr
        assert "10/20" in str_repr

    def test_boxscore_repr(self):
        """Test repr of BoxScore."""
        boxscore = BoxScore(points=25, fgm=10, fga=20)
        repr_str = repr(boxscore)
        assert "BoxScore" in repr_str
        assert "points=25" in repr_str


class TestBoxScoreStatAccumulation:
    """Test cases for accumulating stats across multiple events."""

    def test_accumulate_multiple_field_goals(self):
        """Test accumulating multiple field goal events."""
        boxscore = BoxScore()

        # Add 3 made FGs and 2 missed FGs
        boxscore.add_field_goal(made=True)
        boxscore.add_field_goal(made=True)
        boxscore.add_field_goal(made=True)
        boxscore.add_field_goal(made=False)
        boxscore.add_field_goal(made=False)

        assert boxscore.fgm == 3
        assert boxscore.fga == 5
        assert boxscore.fg_pct == 0.6

    def test_accumulate_full_game_stats(self):
        """Test accumulating stats for a full game segment."""
        boxscore = BoxScore()

        # Simulate a game segment
        events = [
            ("fg", True),  # Made FG
            ("fg", False),  # Missed FG
            ("fg", True),  # Made FG
            ("3p", True),  # Made 3P
            ("3p", False),  # Missed 3P
            ("ft", True),  # Made FT
            ("ft", True),  # Made FT
            ("reb", True),  # OREB
            ("reb", False),  # DREB
            ("ast", None),  # AST
            ("stl", None),  # STL
            ("blk", None),  # BLK
            ("tov", None),  # TOV
            ("pf", None),  # PF
        ]

        for event in events:
            if event[0] == "fg":
                boxscore.add_field_goal(made=event[1])
            elif event[0] == "3p":
                boxscore.add_three_point(made=event[1])
            elif event[0] == "ft":
                boxscore.add_free_throw(made=event[1])
            elif event[0] == "reb":
                boxscore.add_rebound(offensive=event[1])
            elif event[0] == "ast":
                boxscore.add_assist()
            elif event[0] == "stl":
                boxscore.add_steal()
            elif event[0] == "blk":
                boxscore.add_block()
            elif event[0] == "tov":
                boxscore.add_turnover()
            elif event[0] == "pf":
                boxscore.add_foul()

        # Verify accumulated stats
        assert boxscore.fgm == 3
        assert boxscore.fga == 5
        assert boxscore.fg3m == 1
        assert boxscore.fg3a == 2
        assert boxscore.ftm == 2
        assert boxscore.fta == 2
        assert boxscore.oreb == 1
        assert boxscore.dreb == 1
        assert boxscore.treb == 2
        assert boxscore.ast == 1
        assert boxscore.stl == 1
        assert boxscore.blk == 1
        assert boxscore.tov == 1
        assert boxscore.pf == 1