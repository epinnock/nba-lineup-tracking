"""
Unit tests for lineup_detector.py module.

Tests the LineupDetector class including:
- Starting lineup detection
- Substitution event processing
- Segment creation on lineup changes
- Period transition handling
- Edge cases: multiple quick subs, end of game
"""

import pytest
from unittest.mock import Mock
from processors.lineup_detector import LineupDetector
from models.lineup import Player, Lineup
from models.game_segment import GameSegment


class TestLineupDetectorInitialization:
    """Test cases for LineupDetector initialization."""

    def test_lineup_detector_creation(self):
        """Test creating a LineupDetector with valid data."""
        game_id = "0022100001"
        plays = [
            {"EVENTNUM": 1, "EVENTMSGTYPE": 12, "PCTIMESTRING": "12:00", "PERIOD": 1},
        ]

        detector = LineupDetector(game_id, plays)
        assert detector.game_id == game_id
        assert detector.plays == plays
        assert detector.segments == []
        assert detector.current_home_lineup is None
        assert detector.current_away_lineup is None
        assert detector.segment_counter == 0

    def test_lineup_detector_with_empty_plays(self):
        """Test creating a LineupDetector with empty plays list."""
        game_id = "0022100001"
        plays = []

        detector = LineupDetector(game_id, plays)
        assert detector.game_id == game_id
        assert detector.plays == []
        assert detector.segments == []


class TestInitializeStarters:
    """Test cases for starting lineup detection."""

    def test_initialize_starters_basic(self):
        """Test basic starting lineup detection."""
        game_id = "0022100001"
        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 12,
                "PCTIMESTRING": "12:00",
                "PERIOD": 1,
                "PLAYER1_ID": "203507",
                "PLAYER1_NAME": "Giannis Antetokounmpo",
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "PLAYER2_ID": "201950",
                "PLAYER2_NAME": "Jrue Holiday",
                "PLAYER2_TEAM_ABBREVIATION": "MIL",
                "PLAYER3_ID": "203114",
                "PLAYER3_NAME": "Khris Middleton",
                "PLAYER3_TEAM_ABBREVIATION": "MIL",
                "PLAYER4_ID": "1628389",
                "PLAYER4_NAME": "Brook Lopez",
                "PLAYER4_TEAM_ABBREVIATION": "MIL",
                "PLAYER5_ID": "1626179",
                "PLAYER5_NAME": "Grayson Allen",
                "PLAYER5_TEAM_ABBREVIATION": "MIL",
            },
            {
                "EVENTNUM": 2,
                "EVENTMSGTYPE": 10,
                "PCTIMESTRING": "11:45",
                "PERIOD": 1,
                "PLAYER1_ID": "201935",
                "PLAYER1_NAME": "Kevin Durant",
                "PLAYER1_TEAM_ABBREVIATION": "BRK",
                "PLAYER2_ID": "201142",
                "PLAYER2_NAME": "Kyrie Irving",
                "PLAYER2_TEAM_ABBREVIATION": "BRK",
                "PLAYER3_ID": "1627742",
                "PLAYER3_NAME": "James Harden",
                "PLAYER3_TEAM_ABBREVIATION": "BRK",
                "PLAYER4_ID": "202681",
                "PLAYER4_NAME": "Blake Griffin",
                "PLAYER4_TEAM_ABBREVIATION": "BRK",
                "PLAYER5_ID": "1629011",
                "PLAYER5_NAME": "Nic Claxton",
                "PLAYER5_TEAM_ABBREVIATION": "BRK",
            },
        ]

        detector = LineupDetector(game_id, plays)
        detector._initialize_starters()

        # Verify home lineup
        assert detector.current_home_lineup is not None
        assert len(detector.current_home_lineup.players) == 5
        assert detector.current_home_lineup.team_abbreviation == "MIL"
        home_player_ids = {p.player_id for p in detector.current_home_lineup.players}
        assert "203507" in home_player_ids  # Giannis
        assert "201950" in home_player_ids  # Jrue

        # Verify away lineup
        assert detector.current_away_lineup is not None
        assert len(detector.current_away_lineup.players) == 5
        assert detector.current_away_lineup.team_abbreviation == "BRK"
        away_player_ids = {p.player_id for p in detector.current_away_lineup.players}
        assert "201935" in away_player_ids  # Durant
        assert "201142" in away_player_ids  # Kyrie

    def test_initialize_starters_with_duplicate_players(self):
        """Test that duplicate players are not added to lineups."""
        game_id = "0022100001"
        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 12,
                "PCTIMESTRING": "12:00",
                "PERIOD": 1,
                "PLAYER1_ID": "203507",
                "PLAYER1_NAME": "Giannis Antetokounmpo",
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
            },
            {
                "EVENTNUM": 2,
                "EVENTMSGTYPE": 10,
                "PCTIMESTRING": "11:45",
                "PERIOD": 1,
                "PLAYER1_ID": "203507",  # Same player appears again
                "PLAYER1_NAME": "Giannis Antetokounmpo",
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
            },
        ]

        detector = LineupDetector(game_id, plays)
        detector._initialize_starters()

        # Should only have one Giannis in the lineup
        home_player_ids = [p.player_id for p in detector.current_home_lineup.players]
        assert home_player_ids.count("203507") == 1

    def test_initialize_starters_incomplete_lineup(self):
        """Test starting lineup detection with incomplete data."""
        game_id = "0022100001"
        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 12,
                "PCTIMESTRING": "12:00",
                "PERIOD": 1,
                "PLAYER1_ID": "203507",
                "PLAYER1_NAME": "Giannis Antetokounmpo",
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
            },
            # Only 1 player found - should still create lineup
        ]

        detector = LineupDetector(game_id, plays)
        detector._initialize_starters()

        # Should create lineup even with incomplete data
        assert detector.current_home_lineup is not None
        assert len(detector.current_home_lineup.players) == 1

    def test_initialize_starters_no_player_data(self):
        """Test starting lineup detection with no player data."""
        game_id = "0022100001"
        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 12,
                "PCTIMESTRING": "12:00",
                "PERIOD": 1,
                # No player data
            },
        ]

        detector = LineupDetector(game_id, plays)
        detector._initialize_starters()

        # Should handle missing player data gracefully
        assert detector.current_home_lineup is not None
        assert len(detector.current_home_lineup.players) == 0


class TestHandleSubstitution:
    """Test cases for substitution handling."""

    def test_handle_substitution_home_team(self):
        """Test handling a home team substitution."""
        game_id = "0022100001"
        plays = []

        detector = LineupDetector(game_id, plays)

        # Set up initial lineup
        home_players = [
            Player("203507", "Giannis", "MIL"),
            Player("201950", "Jrue", "MIL"),
            Player("203114", "Khris", "MIL"),
            Player("1628389", "Brook", "MIL"),
            Player("1626179", "Grayson", "MIL"),
        ]
        detector.current_home_lineup = Lineup(players=home_players)

        # Create substitution play
        sub_play = {
            "EVENTNUM": 10,
            "EVENTMSGTYPE": 8,
            "PLAYER1_ID": "1626179",  # Grayson out
            "PLAYER1_NAME": "Grayson Allen",
            "PLAYER1_TEAM_ABBREVIATION": "MIL",
            "PLAYER2_ID": "203089",  # Pat in
            "PLAYER2_NAME": "Pat Connaughton",
            "PLAYER2_TEAM_ABBREVIATION": "MIL",
        }

        detector._handle_substitution(sub_play)

        # Verify substitution was applied
        assert len(detector.current_home_lineup.players) == 5
        player_ids = {p.player_id for p in detector.current_home_lineup.players}
        assert "1626179" not in player_ids  # Grayson should be out
        assert "203089" in player_ids  # Pat should be in

    def test_handle_substitution_away_team(self):
        """Test handling an away team substitution."""
        game_id = "0022100001"
        plays = []

        detector = LineupDetector(game_id, plays)

        # Set up initial lineup
        away_players = [
            Player("201935", "Durant", "BRK"),
            Player("201142", "Kyrie", "BRK"),
            Player("1627742", "Harden", "BRK"),
            Player("202681", "Blake", "BRK"),
            Player("1629011", "Claxton", "BRK"),
        ]
        detector.current_away_lineup = Lineup(players=away_players)

        # Create substitution play
        sub_play = {
            "EVENTNUM": 15,
            "EVENTMSGTYPE": 8,
            "PLAYER1_ID": "1629011",  # Claxton out
            "PLAYER1_NAME": "Nic Claxton",
            "PLAYER1_TEAM_ABBREVIATION": "BRK",
            "PLAYER2_ID": "200768",  # Aldridge in
            "PLAYER2_NAME": "LaMarcus Aldridge",
            "PLAYER2_TEAM_ABBREVIATION": "BRK",
        }

        detector._handle_substitution(sub_play)

        # Verify substitution was applied
        assert len(detector.current_away_lineup.players) == 5
        player_ids = {p.player_id for p in detector.current_away_lineup.players}
        assert "1629011" not in player_ids  # Claxton should be out
        assert "200768" in player_ids  # Aldridge should be in

    def test_handle_substitution_missing_player_data(self):
        """Test handling substitution with missing player data."""
        game_id = "0022100001"
        plays = []

        detector = LineupDetector(game_id, plays)

        # Set up initial lineup
        home_players = [
            Player("203507", "Giannis", "MIL"),
            Player("201950", "Jrue", "MIL"),
            Player("203114", "Khris", "MIL"),
            Player("1628389", "Brook", "MIL"),
            Player("1626179", "Grayson", "MIL"),
        ]
        detector.current_home_lineup = Lineup(players=home_players)

        # Create substitution play with missing data
        sub_play = {
            "EVENTNUM": 10,
            "EVENTMSGTYPE": 8,
            # Missing PLAYER1_ID (player out)
            "PLAYER2_ID": "203089",
            "PLAYER2_NAME": "Pat Connaughton",
            "PLAYER2_TEAM_ABBREVIATION": "MIL",
        }

        detector._handle_substitution(sub_play)

        # Lineup should remain unchanged due to missing data
        assert len(detector.current_home_lineup.players) == 5
        player_ids = {p.player_id for p in detector.current_home_lineup.players}
        assert "1626179" in player_ids  # Original lineup unchanged

    def test_handle_substitution_player_not_in_lineup(self):
        """Test handling substitution for player not currently in lineup."""
        game_id = "0022100001"
        plays = []

        detector = LineupDetector(game_id, plays)

        # Set up initial lineup
        home_players = [
            Player("203507", "Giannis", "MIL"),
            Player("201950", "Jrue", "MIL"),
            Player("203114", "Khris", "MIL"),
            Player("1628389", "Brook", "MIL"),
            Player("1626179", "Grayson", "MIL"),
        ]
        detector.current_home_lineup = Lineup(players=home_players)

        # Try to substitute out a player not in lineup
        sub_play = {
            "EVENTNUM": 10,
            "EVENTMSGTYPE": 8,
            "PLAYER1_ID": "999999",  # Non-existent player
            "PLAYER1_NAME": "Unknown Player",
            "PLAYER1_TEAM_ABBREVIATION": "MIL",
            "PLAYER2_ID": "203089",
            "PLAYER2_NAME": "Pat Connaughton",
            "PLAYER2_TEAM_ABBREVIATION": "MIL",
        }

        detector._handle_substitution(sub_play)

        # Should add new player but not remove anyone (lineup will have 6 players)
        # This tests error handling - in real usage this shouldn't happen
        assert len(detector.current_home_lineup.players) == 6


class TestEndCurrentSegment:
    """Test cases for segment creation."""

    def test_end_current_segment_basic(self):
        """Test ending a current segment and creating a GameSegment."""
        game_id = "0022100001"
        plays = []

        detector = LineupDetector(game_id, plays)

        # Set up lineups
        home_players = [Player("203507", "Giannis", "MIL") for _ in range(5)]
        away_players = [Player("201935", "Durant", "BRK") for _ in range(5)]
        detector.current_home_lineup = Lineup(players=home_players)
        detector.current_away_lineup = Lineup(players=away_players)

        # Create start and end plays
        start_play = {
            "EVENTNUM": 1,
            "PERIOD": 1,
            "PCTIMESTRING": "12:00",
        }
        end_play = {
            "EVENTNUM": 10,
            "PERIOD": 1,
            "PCTIMESTRING": "10:30",
        }

        detector._end_current_segment(start_play, end_play)

        # Verify segment was created
        assert len(detector.segments) == 1
        segment = detector.segments[0]
        assert isinstance(segment, GameSegment)
        assert segment.game_id == game_id
        assert segment.start_quarter == 1
        assert segment.end_quarter == 1
        assert segment.start_time == 720.0  # 12:00 = 720 seconds
        assert segment.end_time == 630.0  # 10:30 = 630 seconds
        assert segment.duration == 90.0  # 1.5 minutes

    def test_end_current_segment_without_lineups(self):
        """Test ending segment when lineups are not set."""
        game_id = "0022100001"
        plays = []

        detector = LineupDetector(game_id, plays)
        # Don't set lineups

        start_play = {"EVENTNUM": 1, "PERIOD": 1, "PCTIMESTRING": "12:00"}
        end_play = {"EVENTNUM": 10, "PERIOD": 1, "PCTIMESTRING": "10:30"}

        detector._end_current_segment(start_play, end_play)

        # Should not create segment without lineups
        assert len(detector.segments) == 0

    def test_end_current_segment_multiple_segments(self):
        """Test creating multiple segments."""
        game_id = "0022100001"
        plays = []

        detector = LineupDetector(game_id, plays)

        # Set up lineups
        home_players = [Player("203507", "Giannis", "MIL") for _ in range(5)]
        away_players = [Player("201935", "Durant", "BRK") for _ in range(5)]
        detector.current_home_lineup = Lineup(players=home_players)
        detector.current_away_lineup = Lineup(players=away_players)

        # Create multiple segments
        start_play1 = {"EVENTNUM": 1, "PERIOD": 1, "PCTIMESTRING": "12:00"}
        end_play1 = {"EVENTNUM": 10, "PERIOD": 1, "PCTIMESTRING": "10:30"}
        detector._end_current_segment(start_play1, end_play1)

        start_play2 = {"EVENTNUM": 11, "PERIOD": 1, "PCTIMESTRING": "10:30"}
        end_play2 = {"EVENTNUM": 20, "PERIOD": 1, "PCTIMESTRING": "8:00"}
        detector._end_current_segment(start_play2, end_play2)

        # Verify multiple segments were created
        assert len(detector.segments) == 2
        assert detector.segments[0].segment_id == 1
        assert detector.segments[1].segment_id == 2


class TestParseTimeToSeconds:
    """Test cases for time parsing."""

    def test_parse_time_to_seconds_full_minutes(self):
        """Test parsing time with full minutes."""
        game_id = "0022100001"
        plays = []

        detector = LineupDetector(game_id, plays)

        assert detector._parse_time_to_seconds("12:00") == 720.0
        assert detector._parse_time_to_seconds("10:00") == 600.0
        assert detector._parse_time_to_seconds("5:00") == 300.0

    def test_parse_time_to_seconds_with_seconds(self):
        """Test parsing time with seconds."""
        game_id = "0022100001"
        plays = []

        detector = LineupDetector(game_id, plays)

        assert detector._parse_time_to_seconds("11:45") == 705.0
        assert detector._parse_time_to_seconds("10:30") == 630.0
        assert detector._parse_time_to_seconds("5:15") == 315.0

    def test_parse_time_to_seconds_end_of_quarter(self):
        """Test parsing time at end of quarter."""
        game_id = "0022100001"
        plays = []

        detector = LineupDetector(game_id, plays)

        assert detector._parse_time_to_seconds("0:00") == 0.0
        assert detector._parse_time_to_seconds("0:01") == 1.0

    def test_parse_time_to_seconds_invalid_format(self):
        """Test parsing time with invalid format."""
        game_id = "0022100001"
        plays = []

        detector = LineupDetector(game_id, plays)

        assert detector._parse_time_to_seconds("") == 0.0
        assert detector._parse_time_to_seconds("invalid") == 0.0
        assert detector._parse_time_to_seconds("12") == 0.0
        assert detector._parse_time_to_seconds(None) == 0.0


class TestProcessGameBasic:
    """Test cases for full game processing."""

    def test_process_game_no_substitutions(self):
        """Test processing a game with no substitutions."""
        game_id = "0022100001"
        plays = [
            {"EVENTNUM": 1, "EVENTMSGTYPE": 12, "PCTIMESTRING": "12:00", "PERIOD": 1},
            {"EVENTNUM": 2, "EVENTMSGTYPE": 1, "PCTIMESTRING": "11:45", "PERIOD": 1},
            {"EVENTNUM": 3, "EVENTMSGTYPE": 13, "PCTIMESTRING": "0:00", "PERIOD": 1},
        ]

        detector = LineupDetector(game_id, plays)
        segments = detector.process_game()

        # Should have at least one segment (the whole game)
        assert len(segments) >= 1

    def test_process_game_with_substitution(self):
        """Test processing a game with one substitution."""
        game_id = "0022100001"
        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 12,
                "PCTIMESTRING": "12:00",
                "PERIOD": 1,
                "PLAYER1_ID": "203507",
                "PLAYER1_NAME": "Giannis",
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "PLAYER2_ID": "201950",
                "PLAYER2_NAME": "Jrue",
                "PLAYER2_TEAM_ABBREVIATION": "MIL",
                "PLAYER3_ID": "203114",
                "PLAYER3_NAME": "Khris",
                "PLAYER3_TEAM_ABBREVIATION": "MIL",
                "PLAYER4_ID": "1628389",
                "PLAYER4_NAME": "Brook",
                "PLAYER4_TEAM_ABBREVIATION": "MIL",
                "PLAYER5_ID": "1626179",
                "PLAYER5_NAME": "Grayson",
                "PLAYER5_TEAM_ABBREVIATION": "MIL",
            },
            {"EVENTNUM": 2, "EVENTMSGTYPE": 1, "PCTIMESTRING": "11:45", "PERIOD": 1},
            {
                "EVENTNUM": 3,
                "EVENTMSGTYPE": 8,
                "PCTIMESTRING": "10:00",
                "PERIOD": 1,
                "PLAYER1_ID": "1626179",
                "PLAYER1_NAME": "Grayson Allen",
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "PLAYER2_ID": "203089",
                "PLAYER2_NAME": "Pat Connaughton",
                "PLAYER2_TEAM_ABBREVIATION": "MIL",
            },
            {"EVENTNUM": 4, "EVENTMSGTYPE": 13, "PCTIMESTRING": "0:00", "PERIOD": 1},
        ]

        detector = LineupDetector(game_id, plays)
        segments = detector.process_game()

        # Should have at least 2 segments (before and after substitution)
        assert len(segments) >= 2

    def test_process_game_multiple_substitutions(self):
        """Test processing a game with multiple substitutions."""
        game_id = "0022100001"
        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 12,
                "PCTIMESTRING": "12:00",
                "PERIOD": 1,
                "PLAYER1_ID": "203507",
                "PLAYER1_NAME": "Giannis",
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "PLAYER2_ID": "201950",
                "PLAYER2_NAME": "Jrue",
                "PLAYER2_TEAM_ABBREVIATION": "MIL",
                "PLAYER3_ID": "203114",
                "PLAYER3_NAME": "Khris",
                "PLAYER3_TEAM_ABBREVIATION": "MIL",
                "PLAYER4_ID": "1628389",
                "PLAYER4_NAME": "Brook",
                "PLAYER4_TEAM_ABBREVIATION": "MIL",
                "PLAYER5_ID": "1626179",
                "PLAYER5_NAME": "Grayson",
                "PLAYER5_TEAM_ABBREVIATION": "MIL",
            },
            {"EVENTNUM": 2, "EVENTMSGTYPE": 1, "PCTIMESTRING": "11:45", "PERIOD": 1},
            {
                "EVENTNUM": 3,
                "EVENTMSGTYPE": 8,
                "PCTIMESTRING": "10:00",
                "PERIOD": 1,
                "PLAYER1_ID": "1626179",
                "PLAYER1_NAME": "Grayson Allen",
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "PLAYER2_ID": "203089",
                "PLAYER2_NAME": "Pat Connaughton",
                "PLAYER2_TEAM_ABBREVIATION": "MIL",
            },
            {"EVENTNUM": 4, "EVENTMSGTYPE": 1, "PCTIMESTRING": "9:30", "PERIOD": 1},
            {
                "EVENTNUM": 5,
                "EVENTMSGTYPE": 8,
                "PCTIMESTRING": "8:00",
                "PERIOD": 1,
                "PLAYER1_ID": "203089",
                "PLAYER1_NAME": "Pat Connaughton",
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "PLAYER2_ID": "1626179",
                "PLAYER2_NAME": "Grayson Allen",
                "PLAYER2_TEAM_ABBREVIATION": "MIL",
            },
            {"EVENTNUM": 6, "EVENTMSGTYPE": 13, "PCTIMESTRING": "0:00", "PERIOD": 1},
        ]

        detector = LineupDetector(game_id, plays)
        segments = detector.process_game()

        # Should have at least 3 segments (initial, after first sub, after second sub)
        assert len(segments) >= 3


class TestProcessGameEdgeCases:
    """Test cases for edge cases in game processing."""

    def test_process_game_period_transitions(self):
        """Test processing a game with period transitions."""
        game_id = "0022100001"
        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 12,
                "PCTIMESTRING": "12:00",
                "PERIOD": 1,
                "PLAYER1_ID": "203507",
                "PLAYER1_NAME": "Giannis",
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "PLAYER2_ID": "201950",
                "PLAYER2_NAME": "Jrue",
                "PLAYER2_TEAM_ABBREVIATION": "MIL",
                "PLAYER3_ID": "203114",
                "PLAYER3_NAME": "Khris",
                "PLAYER3_TEAM_ABBREVIATION": "MIL",
                "PLAYER4_ID": "1628389",
                "PLAYER4_NAME": "Brook",
                "PLAYER4_TEAM_ABBREVIATION": "MIL",
                "PLAYER5_ID": "1626179",
                "PLAYER5_NAME": "Grayson",
                "PLAYER5_TEAM_ABBREVIATION": "MIL",
            },
            {"EVENTNUM": 2, "EVENTMSGTYPE": 1, "PCTIMESTRING": "11:45", "PERIOD": 1},
            {"EVENTNUM": 3, "EVENTMSGTYPE": 13, "PCTIMESTRING": "0:00", "PERIOD": 1},  # End Q1
            {"EVENTNUM": 4, "EVENTMSGTYPE": 12, "PCTIMESTRING": "12:00", "PERIOD": 2},  # Start Q2
            {"EVENTNUM": 5, "EVENTMSGTYPE": 1, "PCTIMESTRING": "11:30", "PERIOD": 2},
            {"EVENTNUM": 6, "EVENTMSGTYPE": 13, "PCTIMESTRING": "0:00", "PERIOD": 2},  # End Q2
        ]

        detector = LineupDetector(game_id, plays)
        segments = detector.process_game()

        # Should have segments for each period
        assert len(segments) >= 2

    def test_process_game_back_to_back_substitutions(self):
        """Test processing a game with back-to-back substitutions."""
        game_id = "0022100001"
        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 12,
                "PCTIMESTRING": "12:00",
                "PERIOD": 1,
                "PLAYER1_ID": "203507",
                "PLAYER1_NAME": "Giannis",
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "PLAYER2_ID": "201950",
                "PLAYER2_NAME": "Jrue",
                "PLAYER2_TEAM_ABBREVIATION": "MIL",
                "PLAYER3_ID": "203114",
                "PLAYER3_NAME": "Khris",
                "PLAYER3_TEAM_ABBREVIATION": "MIL",
                "PLAYER4_ID": "1628389",
                "PLAYER4_NAME": "Brook",
                "PLAYER4_TEAM_ABBREVIATION": "MIL",
                "PLAYER5_ID": "1626179",
                "PLAYER5_NAME": "Grayson",
                "PLAYER5_TEAM_ABBREVIATION": "MIL",
            },
            {
                "EVENTNUM": 2,
                "EVENTMSGTYPE": 8,
                "PCTIMESTRING": "10:00",
                "PERIOD": 1,
                "PLAYER1_ID": "1626179",
                "PLAYER1_NAME": "Grayson Allen",
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "PLAYER2_ID": "203089",
                "PLAYER2_NAME": "Pat Connaughton",
                "PLAYER2_TEAM_ABBREVIATION": "MIL",
            },
            {
                "EVENTNUM": 3,
                "EVENTMSGTYPE": 8,
                "PCTIMESTRING": "10:00",
                "PERIOD": 1,
                "PLAYER1_ID": "203114",
                "PLAYER1_NAME": "Khris Middleton",
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "PLAYER2_ID": "203476",
                "PLAYER2_NAME": "Bobby Portis",
                "PLAYER2_TEAM_ABBREVIATION": "MIL",
            },
            {"EVENTNUM": 4, "EVENTMSGTYPE": 13, "PCTIMESTRING": "0:00", "PERIOD": 1},
        ]

        detector = LineupDetector(game_id, plays)
        segments = detector.process_game()

        # Should handle back-to-back substitutions
        assert len(segments) >= 3

    def test_process_game_empty_lineup_after_sub(self):
        """Test processing when substitution data is incomplete."""
        game_id = "0022100001"
        plays = [
            {
                "EVENTNUM": 1,
                "EVENTMSGTYPE": 12,
                "PCTIMESTRING": "12:00",
                "PERIOD": 1,
                "PLAYER1_ID": "203507",
                "PLAYER1_NAME": "Giannis",
                "PLAYER1_TEAM_ABBREVIATION": "MIL",
                "PLAYER2_ID": "201950",
                "PLAYER2_NAME": "Jrue",
                "PLAYER2_TEAM_ABBREVIATION": "MIL",
                "PLAYER3_ID": "203114",
                "PLAYER3_NAME": "Khris",
                "PLAYER3_TEAM_ABBREVIATION": "MIL",
                "PLAYER4_ID": "1628389",
                "PLAYER4_NAME": "Brook",
                "PLAYER4_TEAM_ABBREVIATION": "MIL",
                "PLAYER5_ID": "1626179",
                "PLAYER5_NAME": "Grayson",
                "PLAYER5_TEAM_ABBREVIATION": "MIL",
            },
            {
                "EVENTNUM": 2,
                "EVENTMSGTYPE": 8,
                "PCTIMESTRING": "10:00",
                "PERIOD": 1,
                # Missing player in data
                "PLAYER2_ID": "203089",
                "PLAYER2_NAME": "Pat Connaughton",
                "PLAYER2_TEAM_ABBREVIATION": "MIL",
            },
            {"EVENTNUM": 3, "EVENTMSGTYPE": 13, "PCTIMESTRING": "0:00", "PERIOD": 1},
        ]

        detector = LineupDetector(game_id, plays)
        segments = detector.process_game()

        # Should handle incomplete substitution data gracefully
        assert len(segments) >= 1