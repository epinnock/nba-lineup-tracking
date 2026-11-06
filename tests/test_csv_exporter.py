"""
Unit tests for csv_exporter.py module.

Tests the CSV export functionality including:
- CSV file creation and structure
- Header row generation
- Data row formatting
- Flat dictionary conversion
- Error handling for file operations
- Data integrity and completeness
"""

import csv
import pytest
from unittest.mock import mock_open, patch, Mock
from exporters.csv_exporter import export_to_csv, _segment_to_flat_dict
from models.game_segment import GameSegment
from models.lineup import Player, Lineup
from models.boxscore import BoxScore


class TestSegmentToFlatDict:
    """Test cases for converting GameSegment to flat dictionary."""

    def test_segment_to_flat_dict_basic(self):
        """Test converting a basic GameSegment to flat dictionary."""
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

        result = _segment_to_flat_dict(segment)

        # Verify basic structure
        assert result["segment_id"] == 1
        assert result["start_quarter"] == 1
        assert result["end_quarter"] == 1
        assert result["start_time"] == 720.0
        assert result["end_time"] == 630.0
        assert result["duration_seconds"] == 90.0

    def test_segment_to_flat_dict_team_info(self):
        """Test team information in flat dictionary."""
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

        result = _segment_to_flat_dict(segment)

        # Verify team info
        assert result["home_team"] == "MIL"
        assert "203507" in result["home_lineup_key"]
        assert result["away_team"] == "BRK"
        assert "201935" in result["away_lineup_key"]

    def test_segment_to_flat_dict_boxscore_data(self):
        """Test boxscore data in flat dictionary."""
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

        result = _segment_to_flat_dict(segment)

        # Verify home boxscore data
        assert result["home_pts"] == 8
        assert result["home_fgm"] == 3
        assert result["home_fga"] == 5
        assert result["home_fg_pct"] == 60.0  # 3/5 = 60%
        assert result["home_fg3m"] == 2
        assert result["home_fg3a"] == 3
        assert result["home_fg3_pct"] > 66.0  # 2/3 = 66.67%
        assert result["home_plus_minus"] == 3

        # Verify away boxscore data
        assert result["away_pts"] == 5
        assert result["away_fgm"] == 2
        assert result["away_fga"] == 4
        assert result["away_fg_pct"] == 50.0  # 2/4 = 50%
        assert result["away_plus_minus"] == -3

    def test_segment_to_flat_dict_all_boxscore_fields(self):
        """Test that all boxscore fields are present in flat dictionary."""
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

        result = _segment_to_flat_dict(segment)

        # Verify all expected fields are present
        expected_fields = [
            "segment_id", "start_quarter", "end_quarter", "start_time", "end_time", "duration_seconds",
            "home_team", "home_lineup_key", "away_team", "away_lineup_key",
            "home_pts", "home_fgm", "home_fga", "home_fg_pct", "home_fg3m", "home_fg3a", "home_fg3_pct",
            "home_ftm", "home_fta", "home_ft_pct", "home_oreb", "home_dreb", "home_treb", "home_ast",
            "home_stl", "home_blk", "home_tov", "home_pf", "home_plus_minus",
            "away_pts", "away_fgm", "away_fga", "away_fg_pct", "away_fg3m", "away_fg3a", "away_fg3_pct",
            "away_ftm", "away_fta", "away_ft_pct", "away_oreb", "away_dreb", "away_treb", "away_ast",
            "away_stl", "away_blk", "away_tov", "away_pf", "away_plus_minus"
        ]

        for field in expected_fields:
            assert field in result, f"Missing field: {field}"


class TestExportToCsv:
    """Test cases for CSV export functionality."""

    def test_export_to_csv_success(self):
        """Test successful CSV export."""
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
            with patch("csv.DictWriter") as mock_writer_class:
                mock_writer = Mock()
                mock_writer_class.return_value = mock_writer

                export_to_csv(game_id, segments, output_dir="/tmp")

                # Verify file was opened
                mock_file.assert_called_once_with("/tmp/0022100001_lineups.csv", "w", newline="")
                # Verify writer was created
                mock_writer_class.assert_called_once()
                # Verify header was written
                mock_writer.writeheader.assert_called_once()
                # Verify row was written
                mock_writer.writerow.assert_called_once()

    def test_export_to_csv_headers(self):
        """Test that correct headers are written."""
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

        captured_headers = None

        def capture_writer(headers, **kwargs):
            nonlocal captured_headers
            captured_headers = headers
            mock_writer = Mock()
            return mock_writer

        with patch("builtins.open", mock_open()):
            with patch("csv.DictWriter", side_effect=capture_writer):
                export_to_csv(game_id, segments, output_dir="/tmp")

        # Verify headers include all expected fields
        assert captured_headers is not None
        assert "segment_id" in captured_headers
        assert "home_team" in captured_headers
        assert "away_team" in captured_headers
        assert "home_pts" in captured_headers
        assert "away_pts" in captured_headers
        assert "home_plus_minus" in captured_headers
        assert "away_plus_minus" in captured_headers
        # Should have many fields (all boxscore stats for both teams)
        assert len(captured_headers) > 40

    def test_export_to_csv_multiple_segments(self):
        """Test exporting multiple segments to CSV."""
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

        captured_rows = []

        def capture_writer(headers, **kwargs):
            mock_writer = Mock()
            mock_writer.writerow = lambda row: captured_rows.append(row)
            return mock_writer

        with patch("builtins.open", mock_open()):
            with patch("csv.DictWriter", side_effect=capture_writer):
                export_to_csv(game_id, segments, output_dir="/tmp")

        # Verify multiple rows written
        assert len(captured_rows) == 2
        assert captured_rows[0]["segment_id"] == 1
        assert captured_rows[0]["home_pts"] == 8
        assert captured_rows[1]["segment_id"] == 2
        assert captured_rows[1]["home_pts"] == 5

    def test_export_to_csv_empty_segments(self):
        """Test exporting with empty segments list."""
        game_id = "0022100001"
        segments = []

        with patch("builtins.open", mock_open()):
            with patch("csv.DictWriter") as mock_writer_class:
                mock_writer = Mock()
                mock_writer_class.return_value = mock_writer

                export_to_csv(game_id, segments, output_dir="/tmp")

                # Header should be written but no rows
                mock_writer.writeheader.assert_called_once()
                mock_writer.writerow.assert_not_called()

    def test_export_to_csv_with_stats(self):
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

        captured_row = None

        def capture_writer(headers, **kwargs):
            mock_writer = Mock()
            def capture_row(row):
                nonlocal captured_row
                captured_row = row
            mock_writer.writerow = capture_row
            return mock_writer

        with patch("builtins.open", mock_open()):
            with patch("csv.DictWriter", side_effect=capture_writer):
                export_to_csv(game_id, segments, output_dir="/tmp")

        # Verify stats in exported row
        assert captured_row is not None
        assert captured_row["home_pts"] == 8
        assert captured_row["home_fgm"] == 3
        assert captured_row["home_fga"] == 5
        assert captured_row["home_fg_pct"] == 60.0
        assert captured_row["home_fg3m"] == 2
        assert captured_row["home_fg3a"] == 3
        assert captured_row["home_plus_minus"] == 3
        assert captured_row["away_pts"] == 5
        assert captured_row["away_fgm"] == 2
        assert captured_row["away_fga"] == 4
        assert captured_row["away_plus_minus"] == -3

    def test_export_to_csv_file_error(self):
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
                export_to_csv(game_id, segments, output_dir="/tmp")

                # Verify error message printed
                mock_print.assert_called_with("Error exporting to CSV: Permission denied")

    def test_export_to_csv_custom_output_dir(self):
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
            with patch("csv.DictWriter"):
                export_to_csv(game_id, segments, output_dir="/custom/path")

                # Verify correct path used
                mock_file.assert_called_once_with("/custom/path/0022100001_lineups.csv", "w", newline="")


class TestCsvDataIntegrity:
    """Test cases for data integrity in CSV export."""

    def test_csv_row_data_types(self):
        """Test that CSV row has correct data types."""
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

        result = _segment_to_flat_dict(segment)

        # Verify data types
        assert isinstance(result["segment_id"], int)
        assert isinstance(result["start_quarter"], int)
        assert isinstance(result["start_time"], float)
        assert isinstance(result["home_pts"], int)
        assert isinstance(result["home_fgm"], int)
        assert isinstance(result["home_fga"], int)
        assert isinstance(result["home_fg_pct"], float)

    def test_lineup_key_in_csv(self):
        """Test that lineup key is included in CSV export."""
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

        result = _segment_to_flat_dict(segment)

        # Lineup keys should be present and identical
        assert "home_lineup_key" in result
        assert "away_lineup_key" in result
        assert result["home_lineup_key"] == result["away_lineup_key"]
        assert len(result["home_lineup_key"]) > 0

    def test_csv_row_count_consistency(self):
        """Test that CSV row has consistent field count."""
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

        result = _segment_to_flat_dict(segment)

        # Count fields (should match header count)
        field_count = len(result)
        assert field_count > 40  # Should have many fields

        # All values should be present (no None values that would cause CSV issues)
        for key, value in result.items():
            assert value is not None, f"Field {key} has None value"

    def test_csv_export_with_zero_values(self):
        """Test CSV export with zero values."""
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

        result = _segment_to_flat_dict(segment)

        # Verify zero values are present (not None)
        assert result["home_pts"] == 0
        assert result["home_fgm"] == 0
        assert result["home_fga"] == 0
        assert result["home_fg_pct"] == 0.0
        assert result["away_pts"] == 0
        assert result["away_fgm"] == 0
        assert result["away_fga"] == 0
        assert result["away_fg_pct"] == 0.0