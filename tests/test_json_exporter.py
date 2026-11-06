"""
Unit tests for json_exporter.py module.

Tests the JSON export functionality including:
- JSON file creation and structure
- Segment dictionary conversion
- Data serialization
- Error handling for file operations
- Data integrity and completeness
- JSON schema compliance
"""

import json
import pytest
from unittest.mock import mock_open, patch
from exporters.json_exporter import export_to_json, _segment_to_dict
from models.game_segment import GameSegment
from models.lineup import Player, Lineup
from models.boxscore import BoxScore


class TestSegmentToDict:
    """Test cases for converting GameSegment to dictionary."""

    def test_segment_to_dict_basic(self):
        """Test converting a basic GameSegment to dictionary."""
        home_lineup = Lineup(players=[
            Player("203507", "Giannis Antetokounmpo", "MIL"),
            Player("201950", "Jrue Holiday", "MIL"),
            Player("203114", "Khris Middleton", "MIL"),
            Player("1628389", "Brook Lopez", "MIL"),
            Player("1626179", "Grayson Allen", "MIL"),
        ])
        away_lineup = Lineup(players=[
            Player("201935", "Kevin Durant", "BRK"),
            Player("201142", "Kyrie Irving", "BRK"),
            Player("1627742", "James Harden", "BRK"),
            Player("202681", "Blake Griffin", "BRK"),
            Player("1629011", "Nic Claxton", "BRK"),
        ])

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

        result = _segment_to_dict(segment)

        # Verify basic structure
        assert result["segment_id"] == 1
        assert result["start_quarter"] == 1
        assert result["end_quarter"] == 1
        assert result["start_time"] == 720.0
        assert result["end_time"] == 630.0
        assert result["duration_seconds"] == 90.0

    def test_segment_to_dict_lineup_info(self):
        """Test lineup information in dictionary."""
        home_lineup = Lineup(players=[
            Player("203507", "Giannis Antetokounmpo", "MIL"),
            Player("201950", "Jrue Holiday", "MIL"),
            Player("203114", "Khris Middleton", "MIL"),
            Player("1628389", "Brook Lopez", "MIL"),
            Player("1626179", "Grayson Allen", "MIL"),
        ])
        away_lineup = Lineup(players=[
            Player("201935", "Kevin Durant", "BRK"),
            Player("201142", "Kyrie Irving", "BRK"),
            Player("1627742", "James Harden", "BRK"),
            Player("202681", "Blake Griffin", "BRK"),
            Player("1629011", "Nic Claxton", "BRK"),
        ])

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

        result = _segment_to_dict(segment)

        # Verify home lineup structure
        assert result["home_lineup"]["team"] == "MIL"
        assert result["home_lineup"]["lineup_key"] == home_lineup.get_lineup_key()
        assert len(result["home_lineup"]["players"]) == 5
        assert "203507" in result["home_lineup"]["players"]

        # Verify away lineup structure
        assert result["away_lineup"]["team"] == "BRK"
        assert result["away_lineup"]["lineup_key"] == away_lineup.get_lineup_key()
        assert len(result["away_lineup"]["players"]) == 5
        assert "201935" in result["away_lineup"]["players"]

    def test_segment_to_dict_boxscore_data(self):
        """Test boxscore data in dictionary."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])

        # Set some boxscore stats
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
        segment.home_boxscore.points = 8
        segment.home_boxscore.fgm = 3
        segment.home_boxscore.fga = 5
        segment.home_boxscore.fg3m = 2
        segment.home_boxscore.fg3a = 3
        segment.home_boxscore.plus_minus = 3
        segment.away_boxscore.points = 5
        segment.away_boxscore.fgm = 2
        segment.away_boxscore.fga = 4
        segment.away_boxscore.plus_minus = -3

        result = _segment_to_dict(segment)

        # Verify home boxscore data
        assert result["home_boxscore"]["points"] == 8
        assert result["home_boxscore"]["fgm"] == 3
        assert result["home_boxscore"]["fga"] == 5
        assert result["home_boxscore"]["fg_pct"] == 60.0  # 3/5 = 60%
        assert result["home_boxscore"]["fg3m"] == 2
        assert result["home_boxscore"]["fg3a"] == 3
        assert result["home_boxscore"]["fg3_pct"] > 66.0  # 2/3 = 66.67%
        assert result["home_boxscore"]["plus_minus"] == 3

        # Verify away boxscore data
        assert result["away_boxscore"]["points"] == 5
        assert result["away_boxscore"]["fgm"] == 2
        assert result["away_boxscore"]["fga"] == 4
        assert result["away_boxscore"]["fg_pct"] == 50.0  # 2/4 = 50%
        assert result["away_boxscore"]["plus_minus"] == -3

    def test_segment_to_dict_all_boxscore_fields(self):
        """Test that all boxscore fields are present in dictionary."""
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

        result = _segment_to_dict(segment)

        # Verify all expected fields are present in home boxscore
        home_box = result["home_boxscore"]
        expected_fields = [
            "points", "fgm", "fga", "fg_pct", "fg3m", "fg3a", "fg3_pct",
            "ftm", "fta", "ft_pct", "oreb", "dreb", "treb", "ast",
            "stl", "blk", "tov", "pf", "plus_minus", "possessions",
            "offensive_rating", "defensive_rating", "duration_seconds"
        ]

        for field in expected_fields:
            assert field in home_box, f"Missing field in home_boxscore: {field}"

        # Verify away boxscore has same fields
        away_box = result["away_boxscore"]
        for field in expected_fields:
            assert field in away_box, f"Missing field in away_boxscore: {field}"

    def test_segment_to_dict_json_serializable(self):
        """Test that the dictionary is JSON serializable."""
        home_lineup = Lineup(players=[
            Player("203507", "Giannis", "MIL"),
            Player("201950", "Jrue", "MIL"),
            Player("203114", "Khris", "MIL"),
            Player("1628389", "Brook", "MIL"),
            Player("1626179", "Grayson", "MIL"),
        ])
        away_lineup = Lineup(players=[
            Player("201935", "Durant", "BRK"),
            Player("201142", "Kyrie", "BRK"),
            Player("1627742", "Harden", "BRK"),
            Player("202681", "Griffin", "BRK"),
            Player("1629011", "Claxton", "BRK"),
        ])

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
        segment.home_boxscore.points = 8
        segment.away_boxscore.points = 5

        result = _segment_to_dict(segment)

        # Should not raise an exception
        json_str = json.dumps(result)
        assert json_str is not None
        assert len(json_str) > 0

        # Verify it can be parsed back
        parsed = json.loads(json_str)
        assert parsed["segment_id"] == 1
        assert parsed["home_boxscore"]["points"] == 8


class TestExportToJson:
    """Test cases for JSON export functionality."""

    def test_export_to_json_success(self):
        """Test successful JSON export."""
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

        game_id = "0022100001"
        segments = [segment]

        # Mock file operations
        with patch("builtins.open", mock_open()) as mock_file:
            with patch("json.dump") as mock_dump:
                export_to_json(game_id, segments, output_dir="/tmp")

                # Verify file was opened
                mock_file.assert_called_once_with("/tmp/0022100001_lineups.json", "w")
                # Verify json.dump was called
                mock_dump.assert_called_once()

    def test_export_to_json_structure(self):
        """Test JSON export structure."""
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

        game_id = "0022100001"
        segments = [segment]

        captured_data = None

        def capture_dump(data, file, **kwargs):
            nonlocal captured_data
            captured_data = data

        with patch("builtins.open", mock_open()):
            with patch("json.dump", side_effect=capture_dump):
                export_to_json(game_id, segments, output_dir="/tmp")

        # Verify structure
        assert captured_data is not None
        assert captured_data["game_id"] == "0022100001"
        assert captured_data["segment_count"] == 1
        assert "segments" in captured_data
        assert len(captured_data["segments"]) == 1
        assert captured_data["segments"][0]["segment_id"] == 1

    def test_export_to_json_multiple_segments(self):
        """Test exporting multiple segments to JSON."""
        home_lineup = Lineup(players=[Player("203507", "Giannis", "MIL") for _ in range(5)])
        away_lineup = Lineup(players=[Player("201935", "Durant", "BRK") for _ in range(5)])

        segment1 = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )
        segment1.home_boxscore.points = 8

        segment2 = GameSegment(
            game_id="0022100001",
            segment_id=2,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=630.0,
            end_time=540.0,
        )
        segment2.home_boxscore.points = 5

        game_id = "0022100001"
        segments = [segment1, segment2]

        captured_data = None

        def capture_dump(data, file, **kwargs):
            nonlocal captured_data
            captured_data = data

        with patch("builtins.open", mock_open()):
            with patch("json.dump", side_effect=capture_dump):
                export_to_json(game_id, segments, output_dir="/tmp")

        # Verify multiple segments
        assert captured_data is not None
        assert captured_data["segment_count"] == 2
        assert len(captured_data["segments"]) == 2
        assert captured_data["segments"][0]["segment_id"] == 1
        assert captured_data["segments"][0]["home_boxscore"]["points"] == 8
        assert captured_data["segments"][1]["segment_id"] == 2
        assert captured_data["segments"][1]["home_boxscore"]["points"] == 5

    def test_export_to_json_empty_segments(self):
        """Test exporting with empty segments list."""
        game_id = "0022100001"
        segments = []

        captured_data = None

        def capture_dump(data, file, **kwargs):
            nonlocal captured_data
            captured_data = data

        with patch("builtins.open", mock_open()):
            with patch("json.dump", side_effect=capture_dump):
                export_to_json(game_id, segments, output_dir="/tmp")

        # Should have empty segments array
        assert captured_data is not None
        assert captured_data["segment_count"] == 0
        assert captured_data["segments"] == []

    def test_export_to_json_with_stats(self):
        """Test exporting segments with statistical data."""
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
        segment.home_boxscore.points = 8
        segment.home_boxscore.fgm = 3
        segment.home_boxscore.fga = 5
        segment.home_boxscore.fg3m = 2
        segment.home_boxscore.fg3a = 3
        segment.home_boxscore.plus_minus = 3
        segment.away_boxscore.points = 5
        segment.away_boxscore.fgm = 2
        segment.away_boxscore.fga = 4
        segment.away_boxscore.plus_minus = -3

        game_id = "0022100001"
        segments = [segment]

        captured_data = None

        def capture_dump(data, file, **kwargs):
            nonlocal captured_data
            captured_data = data

        with patch("builtins.open", mock_open()):
            with patch("json.dump", side_effect=capture_dump):
                export_to_json(game_id, segments, output_dir="/tmp")

        # Verify stats in exported data
        assert captured_data is not None
        home_box = captured_data["segments"][0]["home_boxscore"]
        assert home_box["points"] == 8
        assert home_box["fgm"] == 3
        assert home_box["fga"] == 5
        assert home_box["fg_pct"] == 60.0
        assert home_box["fg3m"] == 2
        assert home_box["fg3a"] == 3
        assert home_box["plus_minus"] == 3

        away_box = captured_data["segments"][0]["away_boxscore"]
        assert away_box["points"] == 5
        assert away_box["fgm"] == 2
        assert away_box["fga"] == 4
        assert away_box["plus_minus"] == -3

    def test_export_to_json_file_error(self):
        """Test handling file write errors."""
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

        game_id = "0022100001"
        segments = [segment]

        # Mock file error
        with patch("builtins.open", side_effect=IOError("Permission denied")):
            with patch("builtins.print") as mock_print:
                export_to_json(game_id, segments, output_dir="/tmp")

                # Verify error message printed
                mock_print.assert_called_with("Error exporting to JSON: Permission denied")

    def test_export_to_json_custom_output_dir(self):
        """Test exporting to custom output directory."""
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

        game_id = "0022100001"
        segments = [segment]

        with patch("builtins.open", mock_open()) as mock_file:
            with patch("json.dump"):
                export_to_json(game_id, segments, output_dir="/custom/path")

                # Verify correct path used
                mock_file.assert_called_once_with("/custom/path/0022100001_lineups.json", "w")

    def test_export_to_json_indent_formatting(self):
        """Test that JSON is formatted with indentation."""
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

        game_id = "0022100001"
        segments = [segment]

        with patch("builtins.open", mock_open()):
            with patch("json.dump") as mock_dump:
                export_to_json(game_id, segments, output_dir="/tmp")

                # Verify indent parameter was used
                args, kwargs = mock_dump.call_args
                assert "indent" in kwargs
                assert kwargs["indent"] == 4


class TestJsonDataIntegrity:
    """Test cases for data integrity in JSON export."""

    def test_json_data_types(self):
        """Test that JSON data has correct types."""
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
        segment.home_boxscore.points = 8
        segment.home_boxscore.fgm = 3
        segment.home_boxscore.fga = 5

        result = _segment_to_dict(segment)

        # Verify data types
        assert isinstance(result["segment_id"], int)
        assert isinstance(result["start_quarter"], int)
        assert isinstance(result["start_time"], float)
        assert isinstance(result["home_boxscore"]["points"], int)
        assert isinstance(result["home_boxscore"]["fgm"], int)
        assert isinstance(result["home_boxscore"]["fga"], int)
        assert isinstance(result["home_boxscore"]["fg_pct"], float)

    def test_lineup_key_in_json(self):
        """Test that lineup key is included in JSON export."""
        home_lineup = Lineup(players=[
            Player("203507", "Giannis", "MIL"),
            Player("201950", "Jrue", "MIL"),
            Player("203114", "Khris", "MIL"),
            Player("1628389", "Brook", "MIL"),
            Player("1626179", "Grayson", "MIL"),
        ])

        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=home_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        result = _segment_to_dict(segment)

        # Lineup keys should be present and identical
        assert "lineup_key" in result["home_lineup"]
        assert "lineup_key" in result["away_lineup"]
        assert result["home_lineup"]["lineup_key"] == result["away_lineup"]["lineup_key"]
        assert len(result["home_lineup"]["lineup_key"]) > 0

    def test_player_ids_in_json(self):
        """Test that player IDs are included in JSON export."""
        home_lineup = Lineup(players=[
            Player("203507", "Giannis", "MIL"),
            Player("201950", "Jrue", "MIL"),
            Player("203114", "Khris", "MIL"),
            Player("1628389", "Brook", "MIL"),
            Player("1626179", "Grayson", "MIL"),
        ])

        segment = GameSegment(
            game_id="0022100001",
            segment_id=1,
            home_lineup=home_lineup,
            away_lineup=home_lineup,
            start_quarter=1,
            end_quarter=1,
            start_time=720.0,
            end_time=630.0,
        )

        result = _segment_to_dict(segment)

        # Player IDs should be in the players array
        assert "players" in result["home_lineup"]
        assert len(result["home_lineup"]["players"]) == 5
        assert "203507" in result["home_lineup"]["players"]
        assert "201950" in result["home_lineup"]["players"]
        assert "203114" in result["home_lineup"]["players"]
        assert "1628389" in result["home_lineup"]["players"]
        assert "1626179" in result["home_lineup"]["players"]

    def test_json_export_with_zero_values(self):
        """Test JSON export with zero values."""
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
        # All stats should be zero by default

        result = _segment_to_dict(segment)

        # Verify zero values are present (not None)
        assert result["home_boxscore"]["points"] == 0
        assert result["home_boxscore"]["fgm"] == 0
        assert result["home_boxscore"]["fga"] == 0
        assert result["home_boxscore"]["fg_pct"] == 0.0
        assert result["away_boxscore"]["points"] == 0
        assert result["away_boxscore"]["fgm"] == 0
        assert result["away_boxscore"]["fga"] == 0
        assert result["away_boxscore"]["fg_pct"] == 0.0

    def test_json_schema_compliance(self):
        """Test that JSON output matches expected schema."""
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

        result = _segment_to_dict(segment)

        # Verify top-level structure
        assert "segment_id" in result
        assert "start_quarter" in result
        assert "end_quarter" in result
        assert "start_time" in result
        assert "end_time" in result
        assert "duration_seconds" in result
        assert "home_lineup" in result
        assert "away_lineup" in result
        assert "home_boxscore" in result
        assert "away_boxscore" in result

        # Verify lineup structure
        assert "team" in result["home_lineup"]
        assert "lineup_key" in result["home_lineup"]
        assert "players" in result["home_lineup"]

        # Verify boxscore structure
        assert "points" in result["home_boxscore"]
        assert "fgm" in result["home_boxscore"]
        assert "fga" in result["home_boxscore"]
        assert "fg_pct" in result["home_boxscore"]