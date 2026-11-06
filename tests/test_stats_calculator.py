"""
Unit tests for stats_calculator.py module.

Tests the StatsCalculator class including:
- Event type mapping (made/missed shots, free throws, rebounds, turnovers, fouls)
- Statistical accumulation per lineup
- Plus/minus calculation
- Possession estimation
- Shooting percentage calculations
- Edge cases and error handling
"""

import pytest
from unittest.mock import Mock
from processors.stats_calculator import StatsCalculator
from models.game_segment import GameSegment
from models.lineup import Player, Lineup
from models.boxscore import BoxScore


class TestStatsCalculatorInitialization:
    """Test cases for StatsCalculator initialization."""

    def test_stats_calculator_creation(self):
        """Test creating a StatsCalculator with valid data."""
        segments = []
        plays = []

        calculator = StatsCalculator(segments, plays)
        assert calculator.segments == segments
        assert calculator.plays == plays
        assert calculator.play_index == 0

    def test_stats_calculator_with_segments_and_plays(self):
        """Test creating a StatsCalculator with segments and plays."""
        # Create mock segments
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {"EVENTNUM": 1, "EVENTMSGTYPE": 1, "PCTIMESTRING": "11:45", "PERIOD": 1},
        ]

        calculator = StatsCalculator([segment], plays)
        assert len(calculator.segments) == 1
        assert len(calculator.plays) == 1


class TestGetPlaysForSegment:
    """Test cases for retrieving plays within a segment timeframe."""

    def test_get_plays_for_segment_basic(self):
        """Test getting plays for a basic segment."""
        # Create segment from 12:00 to 10:30 in Q1
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,  # 12:00
            end_time=630.0,  # 10:30
        )

        # Create plays
        plays = [
            {"EVENTNUM": 1, "EVENTMSGTYPE": 1, "PCTIMESTRING": "11:45", "PERIOD": 1},  # In segment
            {"EVENTNUM": 2, "EVENTMSGTYPE": 2, "PCTIMESTRING": "11:30", "PERIOD": 1},  # In segment
            {"EVENTNUM": 3, "EVENTMSGTYPE": 1, "PCTIMESTRING": "10:15", "PERIOD": 1},  # After segment
        ]

        calculator = StatsCalculator([segment], plays)
        segment_plays = calculator._get_plays_for_segment(segment, 0)

        # Should get plays 1 and 2
        assert len(segment_plays) == 2
        assert segment_plays[0]["EVENTNUM"] == 1
        assert segment_plays[1]["EVENTNUM"] == 2

    def test_get_plays_for_segment_multiple_quarters(self):
        """Test getting plays for a segment spanning multiple quarters."""
        # Create segment from Q1 to Q2
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=2,
            start_time=720.0,  # 12:00 Q1
            end_time=600.0,  # 10:00 Q2
        )

        plays = [
            {"EVENTNUM": 1, "EVENTMSGTYPE": 1, "PCTIMESTRING": "11:45", "PERIOD": 1},
            {"EVENTNUM": 2, "EVENTMSGTYPE": 13, "PCTIMESTRING": "0:00", "PERIOD": 1},  # End Q1
            {"EVENTNUM": 3, "EVENTMSGTYPE": 12, "PCTIMESTRING": "12:00", "PERIOD": 2},  # Start Q2
            {"EVENTNUM": 4, "EVENTMSGTYPE": 1, "PCTIMESTRING": "11:30", "PERIOD": 2},
            {"EVENTNUM": 5, "EVENTMSGTYPE": 1, "PCTIMESTRING": "9:45", "PERIOD": 2},  # After segment
        ]

        calculator = StatsCalculator([segment], plays)
        segment_plays = calculator._get_plays_for_segment(segment, 0)

        # Should get plays 1, 2, 3, 4
        assert len(segment_plays) == 4
        assert segment_plays[-1]["EVENTNUM"] == 4

    def test_get_plays_for_segment_with_next_segment(self):
        """Test getting plays when there's a next segment."""
        # Create two segments
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])

        segment1 = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,  # 12:00
            end_time=630.0,  # 10:30
        )

        segment2 = GameSegment(
            game_id="0022100001",
            segment_id=2,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=630.0,  # 10:30 (start of segment 2)
            end_time=540.0,  # 9:00
        )

        plays = [
            {"EVENTNUM": 1, "EVENTMSGTYPE": 1, "PCTIMESTRING": "11:45", "PERIOD": 1},  # In segment 1
            {"EVENTNUM": 2, "EVENTMSGTYPE": 2, "PCTIMESTRING": "11:30", "PERIOD": 1},  # In segment 1
            {"EVENTNUM": 3, "EVENTMSGTYPE": 1, "PCTIMESTRING": "10:30", "PERIOD": 1},  # Start of segment 2
            {"EVENTNUM": 4, "EVENTMSGTYPE": 1, "PCTIMESTRING": "10:15", "PERIOD": 1},  # In segment 2
        ]

        calculator = StatsCalculator([segment1, segment2], plays)
        segment1_plays = calculator._get_plays_for_segment(segment1, 0)

        # Should only get plays 1 and 2 (before segment 2 starts)
        assert len(segment1_plays) == 2
        assert segment1_plays[0]["EVENTNUM"] == 1
        assert segment1_plays[1]["EVENTNUM"] == 2


class TestCalculateSegmentStatsMadeShots:
    """Test cases for made shot statistics."""

    def test_made_two_point_shot(self):
        """Test recording a made 2-point field goal."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 1,  # Made shot
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis makes 2-pt dunk",
            },
        ]

        calculator = StatsCalculator([segment], plays)
        calculator._calculate_segment_stats(segment, plays)

        # Verify stats
        assert segment.home_boxscore.fgm == 1
        assert segment.home_boxscore.fga == 1
        assert segment.home_boxscore.fg3m == 0
        assert segment.home_boxscore.fg3a == 0
        assert segment.home_boxscore.points == 2

    def test_made_three_point_shot(self):
        """Test recording a made 3-point field goal."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 1,  # Made shot
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis makes 3-pt jump shot",
            },
        ]

        calculator = StatsCalculator([segment], plays)
        calculator._calculate_segment_stats(segment, plays)

        # Verify stats
        assert segment.home_boxscore.fgm == 1
        assert segment.home_boxscore.fga == 1
        assert segment.home_boxscore.fg3m == 1
        assert segment.home_boxscore.fg3a == 1
        assert segment.home_boxscore.points == 3

    def test_made_shot_with_assist(self):
        """Test recording a made shot with an assist."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 1,  # Made shot
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "PLAYER2_ID": "201950",  # Jrue with assist
                "PLAYER2_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis makes 2-pt layup (Jrue Holiday assists)",
            },
        ]

        calculator = StatsCalculator([segment], plays)
        calculator._calculate_segment_stats(segment, plays)

        # Verify stats
        assert segment.home_boxscore.fgm == 1
        assert segment.home_boxscore.fga == 1
        assert segment.home_boxscore.ast == 1
        assert segment.home_boxscore.points == 2

    def test_made_shot_away_team(self):
        """Test recording a made shot for away team."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 1,  # Made shot
                "PLAYER1_TEAM_ABBREVIATION": "BRK",
                "VISITORDESCRIPTION": "Durant makes 2-pt jump shot",
            },
        ]

        calculator = StatsCalculator([segment], plays)
        calculator._calculate_segment_stats(segment, plays)

        # Verify away team stats
        assert segment.away_boxscore.fgm == 1
        assert segment.away_boxscore.fga == 1
        assert segment.away_boxscore.points == 2
        # Home team should have no stats
        assert segment.home_boxscore.fgm == 0
        assert segment.home_boxscore.points == 0


class TestCalculateSegmentStatsMissedShots:
    """Test cases for missed shot statistics."""

    def test_missed_two_point_shot(self):
        """Test recording a missed 2-point field goal."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 2,  # Missed shot
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis misses 2-pt jump shot",
            },
        ]

        calculator = StatsCalculator([segment], plays)
        calculator._calculate_segment_stats(segment, plays)

        # Verify stats
        assert segment.home_boxscore.fgm == 0
        assert segment.home_boxscore.fga == 1
        assert segment.home_boxscore.fg3m == 0
        assert segment.home_boxscore.fg3a == 0
        assert segment.home_boxscore.points == 0

    def test_missed_three_point_shot(self):
        """Test recording a missed 3-point field goal."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 2,  # Missed shot
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis misses 3-pt jump shot",
            },
        ]

        calculator = StatsCalculator([segment], plays)
        calculator._calculate_segment_stats(segment, plays)

        # Verify stats
        assert segment.home_boxscore.fgm == 0
        assert segment.home_boxscore.fga == 1
        assert segment.home_boxscore.fg3m == 0
        assert segment.home_boxscore.fg3a == 1
        assert segment.home_boxscore.points == 0

    def test_missed_shot_with_block(self):
        """Test recording a missed shot with a block."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 2,  # Missed shot
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "PLAYER3_ID": "1629011",  # Blocker
                "PLAYER3_TEAM_ABBREVIATION": "BRK",
                "HOMEDESCRIPTION": "Giannis misses 2-pt layup (BLOCK by Claxton)",
            },
        ]

        calculator = StatsCalculator([segment], plays)
        calculator._calculate_segment_stats(segment, plays)

        # Verify stats
        assert segment.home_boxscore.fga == 1
        assert segment.away_boxscore.blk == 1  # Block credited to away team


class TestCalculateSegmentStatsFreeThrows:
    """Test cases for free throw statistics."""

    def test_made_free_throw(self):
        """Test recording a made free throw."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 3,  # Free throw
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis makes free throw 1 of 2",
            },
        ]

        calculator = StatsCalculator([segment], plays)
        calculator._calculate_segment_stats(segment, plays)

        # Verify stats
        assert segment.home_boxscore.ftm == 1
        assert segment.home_boxscore.fta == 1
        assert segment.home_boxscore.points == 1

    def test_missed_free_throw(self):
        """Test recording a missed free throw."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 3,  # Free throw
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis misses free throw 1 of 2",
            },
        ]

        calculator = StatsCalculator([segment], plays)
        calculator._calculate_segment_stats(segment, plays)

        # Verify stats
        assert segment.home_boxscore.ftm == 0
        assert segment.home_boxscore.fta == 1
        assert segment.home_boxscore.points == 0

    def test_multiple_free_throws(self):
        """Test recording multiple free throws."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 3,
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis makes free throw 1 of 2",
            },
            {
                "EVENTNUM": 2,
                "EVENTMSGTYPE": 3,
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis makes free throw 2 of 2",
            },
        ]

        calculator = StatsCalculator([segment], plays)
        calculator._calculate_segment_stats(segment, plays)

        # Verify stats
        assert segment.home_boxscore.ftm == 2
        assert segment.home_boxscore.fta == 2
        assert segment.home_boxscore.points == 2


class TestCalculateSegmentStatsRebounds:
    """Test cases for rebound statistics."""

    def test_defensive_rebound(self):
        """Test recording a defensive rebound."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 2,  # Missed shot first
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis misses 2-pt jump shot",
            },
            {
                "EVENTNUM": 2,
                "EVENTMSGTYPE": 4,  # Rebound
                "PLAYER1_TEAM_ABBREVIATION": "BRK",
                "VISITORDESCRIPTION": "Durant rebound",
            },
        ]

        calculator = StatsCalculator([segment], plays)
        calculator._calculate_segment_stats(segment, plays)

        # Verify stats - away team gets defensive rebound
        assert segment.away_boxscore.dreb == 1
        assert segment.away_boxscore.oreb == 0

    def test_offensive_rebound(self):
        """Test recording an offensive rebound."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 2,  # Missed shot first
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis misses 2-pt jump shot",
            },
            {
                "EVENTNUM": 2,
                "EVENTMSGTYPE": 4,  # Rebound
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis offensive rebound",
            },
        ]

        calculator = StatsCalculator([segment], plays)
        calculator._calculate_segment_stats(segment, plays)

        # Verify stats - home team gets offensive rebound
        assert segment.home_boxscore.oreb == 1
        assert segment.home_boxscore.dreb == 0

    def test_rebound_without_prior_miss(self):
        """Test recording a rebound without a prior missed shot."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 4,  # Rebound without prior miss
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis rebound",
            },
        ]

        calculator = StatsCalculator([segment], plays)
        calculator._calculate_segment_stats(segment, plays)

        # Should be treated as defensive rebound (no prior miss)
        assert segment.home_boxscore.dreb == 1


class TestCalculateSegmentStatsTurnovers:
    """Test cases for turnover statistics."""

    def test_turnover(self):
        """Test recording a turnover."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 5,  # Turnover
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis bad pass turnover",
            },
        ]

        calculator = StatsCalculator([segment], plays)
        calculator._calculate_segment_stats(segment, plays)

        # Verify stats
        assert segment.home_boxscore.tov == 1

    def test_turnover_with_steal(self):
        """Test recording a turnover with a steal."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 5,  # Turnover
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "PLAYER2_ID": "201935",  # Stealer
                "PLAYER2_TEAM_ABBREVIATION": "BRK",
                "HOMEDESCRIPTION": "Giannis bad pass (Durant steals)",
            },
        ]

        calculator = StatsCalculator([segment], plays)
        calculator._calculate_segment_stats(segment, plays)

        # Verify stats
        assert segment.home_boxscore.tov == 1
        assert segment.away_boxscore.stl == 1


class TestCalculateSegmentStatsFouls:
    """Test cases for foul statistics."""

    def test_personal_foul(self):
        """Test recording a personal foul."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 6,  # Foul
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis shooting foul",
            },
        ]

        calculator = StatsCalculator([segment], plays)
        calculator._calculate_segment_stats(segment, plays)

        # Verify stats
        assert segment.home_boxscore.pf == 1


class TestPlusMinusCalculation:
    """Test cases for plus/minus calculation."""

    def test_plus_minus_home_team_wins_segment(self):
        """Test plus/minus when home team scores more."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 1,
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis makes 2-pt shot",
            },
            {
                "EVENTNUM": 2,
                "EVENTMSGTYPE": 1,
                "PLAYER1_TEAM_ABBREVIATION": "BRK",
                "VISITORDESCRIPTION": "Durant makes 2-pt shot",
            },
            {
                "EVENTNUM": 3,
                "EVENTMSGTYPE": 1,
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis makes 2-pt shot",
            },
        ]

        calculator = StatsCalculator([segment], plays)
        calculator._calculate_segment_stats(segment, plays)

        # Home: 4 points, Away: 2 points
        # Home plus/minus: +2, Away plus/minus: -2
        assert segment.home_boxscore.plus_minus == 2
        assert segment.away_boxscore.plus_minus == -2

    def test_plus_minus_away_team_wins_segment(self):
        """Test plus/minus when away team scores more."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 1,
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis makes 2-pt shot",
            },
            {
                "EVENTNUM": 2,
                "EVENTMSGTYPE": 1,
                "PLAYER1_TEAM_ABBREVIATION": "BRK",
                "VISITORDESCRIPTION": "Durant makes 3-pt shot",
            },
        ]

        calculator = StatsCalculator([segment], plays)
        calculator._calculate_segment_stats(segment, plays)

        # Home: 2 points, Away: 3 points
        # Home plus/minus: -1, Away plus/minus: +1
        assert segment.home_boxscore.plus_minus == -1
        assert segment.away_boxscore.plus_minus == 1

    def test_plus_minus_tie_segment(self):
        """Test plus/minus when segment ends in a tie."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 1,
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis makes 2-pt shot",
            },
            {
                "EVENTNUM": 2,
                "EVENTMSGTYPE": 1,
                "PLAYER1_TEAM_ABBREVIATION": "BRK",
                "VISITORDESCRIPTION": "Durant makes 2-pt shot",
            },
        ]

        calculator = StatsCalculator([segment], plays)
        calculator._calculate_segment_stats(segment, plays)

        # Both teams: 2 points
        # Both plus/minus: 0
        assert segment.home_boxscore.plus_minus == 0
        assert segment.away_boxscore.plus_minus == 0


class TestCalculateBoxscores:
    """Test cases for full boxscore calculation across segments."""

    def test_calculate_boxscores_multiple_segments(self):
        """Test calculating boxscores for multiple segments."""
        home_lineup1 = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup1 = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment1 = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup1,
            away_lineup=away_lineup1,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        home_lineup2 = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup2 = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment2 = GameSegment(
            game_id="0022100001",
            segment_id=2,
            home_lineup=home_lineup2,
            away_lineup=away_lineup2,
            start_quarter=1,
            end_quarter=1,
            start_time=630.0,
            end_time=540.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 1,
                "PCTIMESTRING": "11:45",
                "PERIOD": 1,
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis makes 2-pt shot",
            },
            {
                "EVENTNUM": 2,
                "EVENTMSGTYPE": 1,
                "PCTIMESTRING": "10:15",
                "PERIOD": 1,
                "PLAYER1_TEAM_ABBREVIATION": "BRK",
                "VISITORDESCRIPTION": "Durant makes 2-pt shot",
            },
        ]

        calculator = StatsCalculator([segment1, segment2], plays)
        result_segments = calculator.calculate_boxscores()

        # Verify both segments were processed
        assert len(result_segments) == 2
        assert result_segments[0].home_boxscore.fgm == 1
        assert result_segments[1].away_boxscore.fgm == 1


class TestParseTimeToSeconds:
    """Test cases for time parsing utility."""

    def test_parse_time_to_seconds_full_minutes(self):
        """Test parsing time with full minutes."""
        calculator = StatsCalculator([], [])

        assert calculator._parse_time_to_seconds("12:00") == 720.0
        assert calculator._parse_time_to_seconds("10:00") == 600.0
        assert calculator._parse_time_to_seconds("5:00") == 300.0

    def test_parse_time_to_seconds_with_seconds(self):
        """Test parsing time with seconds."""
        calculator = StatsCalculator([], [])

        assert calculator._parse_time_to_seconds("11:45") == 705.0
        assert calculator._parse_time_to_seconds("10:30") == 630.0
        assert calculator._parse_time_to_seconds("5:15") == 315.0

    def test_parse_time_to_seconds_end_of_quarter(self):
        """Test parsing time at end of quarter."""
        calculator = StatsCalculator([], [])

        assert calculator._parse_time_to_seconds("0:00") == 0.0
        assert calculator._parse_time_to_seconds("0:01") == 1.0

    def test_parse_time_to_seconds_invalid_format(self):
        """Test parsing time with invalid format."""
        calculator = StatsCalculator([], [])

        assert calculator._parse_time_to_seconds("") == 0.0
        assert calculator._parse_time_to_seconds("invalid") == 0.0
        assert calculator._parse_time_to_seconds("12") == 0.0
        assert calculator._parse_time_to_seconds(None) == 0.0


class TestComplexGameScenarios:
    """Test cases for complex game scenarios."""

    def test_full_possession_sequence(self):
        """Test a full possession sequence: missed shot, offensive rebound, made shot."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 2,  # Missed shot
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis misses 2-pt shot",
            },
            {
                "EVENTNUM": 2,
                "EVENTMSGTYPE": 4,  # Offensive rebound
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis offensive rebound",
            },
            {
                "EVENTNUM": 3,
                "EVENTMSGTYPE": 1,  # Made shot
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis makes 2-pt shot",
            },
        ]

        calculator = StatsCalculator([segment], plays)
        calculator._calculate_segment_stats(segment, plays)

        # Verify stats
        assert segment.home_boxscore.fga == 2  # Two shot attempts
        assert segment.home_boxscore.fgm == 1  # One made
        assert segment.home_boxscore.oreb == 1  # One offensive rebound
        assert segment.home_boxscore.points == 2

    def test_steal_and_fast_break(self):
        """Test a steal leading to a fast break score."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])
        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 5,  # Turnover
                "PLAYER1_TEAM_ABBREVIATION": "BRK",
                "PLAYER2_ID": "203507",  # Stealer
                "PLAYER2_TEAM_ABBREVIATION": "MIL",
                "VISITORDESCRIPTION": "Durant bad pass (Giannis steals)",
            },
            {
                "EVENTNUM": 2,
                "EVENTMSGTYPE": 1,  # Made shot
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "HOMEDESCRIPTION": "Giannis makes 2-pt fast break layup",
            },
        ]

        calculator = StatsCalculator([segment], plays)
        calculator._calculate_segment_stats(segment, plays)

        # Verify stats
        assert segment.away_boxscore.tov == 1  # Away team turnover
        assert segment.home_boxscore.stl == 1  # Home team steal
        assert segment.home_boxscore.fgm == 1  # Home team scored
        assert segment.home_boxscore.points == 2