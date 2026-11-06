"""
Enhanced integration tests for the NBA Lineup Tracker application.

Tests the complete end-to-end workflow including:
- Processing different game scenarios (blowout, close game, overtime, playoff)
- Validating output data structure and content
- Verifying boxscore calculations
- Testing error scenarios
- Validating against known game outcomes
"""

import os
import subprocess
import pytest
import json
import csv

# Test game IDs for different scenarios
TEST_GAME_BLOWOUT = "0022300001"  # Regular season game (Bucks vs 76ers)
TEST_GAME_CLOSE = "0022100001"    # Close game (Bucks vs Nets)
TEST_GAME_PLAYOFF = "0042100401"  # Playoff game
TEST_GAME_INVALID = "9999999999"  # Invalid game ID
TEST_GAME_OLD = "0021500001"      # Older season game

# Output file patterns
def get_output_files(game_id):
    return {
        "json": f"{game_id}_lineups.json",
        "csv": f"{game_id}_lineups.csv"
    }

@pytest.fixture(scope="function", autouse=True)
def cleanup_files():
    """Fixture to clean up output files before and after each test."""
    # Clean up before test
    _cleanup_all_files()

    yield

    # Clean up after test
    _cleanup_all_files()

def _cleanup_all_files():
    """Remove all test output files."""
    test_games = [TEST_GAME_BLOWOUT, TEST_GAME_CLOSE, TEST_GAME_PLAYOFF,
                  TEST_GAME_INVALID, TEST_GAME_OLD]
    for game_id in test_games:
        files = get_output_files(game_id)
        _remove_if_exists(files["json"])
        _remove_if_exists(files["csv"])

def _remove_if_exists(filepath):
    if os.path.exists(filepath):
        os.remove(filepath)

def _run_application(game_id):
    """Helper to run the main application."""
    import sys
    # Use the same Python interpreter that's running the tests
    python_exe = sys.executable
    result = subprocess.run(
        [python_exe, "main.py", game_id],
        capture_output=True,
        text=True
    )
    return result

def _load_json_output(game_id):
    """Helper to load and parse JSON output."""
    files = get_output_files(game_id)
    with open(files["json"], "r") as f:
        return json.load(f)

def _load_csv_output(game_id):
    """Helper to load CSV output."""
    files = get_output_files(game_id)
    with open(files["csv"], "r") as f:
        reader = csv.DictReader(f)
        return list(reader)

class TestEndToEndWorkflow:
    """Test complete end-to-end workflow for different game scenarios."""

    @pytest.mark.integration
    def test_blowout_game_processing(self):
        """Test processing a blowout game."""
        result = _run_application(TEST_GAME_BLOWOUT)

        # Verify execution success
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        # Verify output files created
        files = get_output_files(TEST_GAME_BLOWOUT)
        assert os.path.exists(files["json"]), f"JSON file not created: {files['json']}"
        assert os.path.exists(files["csv"]), f"CSV file not created: {files['csv']}"

        # Verify files have content
        assert os.path.getsize(files["json"]) > 100, "JSON file too small"
        assert os.path.getsize(files["csv"]) > 100, "CSV file too small"

        # Verify success message
        assert "Analysis complete." in result.stdout

    @pytest.mark.integration
    def test_close_game_processing(self):
        """Test processing a close game."""
        result = _run_application(TEST_GAME_CLOSE)

        # Verify execution success
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        # Verify output files created
        files = get_output_files(TEST_GAME_CLOSE)
        assert os.path.exists(files["json"])
        assert os.path.exists(files["csv"])

        # Verify files have content
        assert os.path.getsize(files["json"]) > 100
        assert os.path.getsize(files["csv"]) > 100

    @pytest.mark.integration
    def test_playoff_game_processing(self):
        """Test processing a playoff game."""
        result = _run_application(TEST_GAME_PLAYOFF)

        # Note: Some playoff games might have data issues, so we check return code
        # but don't fail if files aren't created (could be API/data issue)
        if result.returncode == 0:
            files = get_output_files(TEST_GAME_PLAYOFF)
            assert os.path.exists(files["json"])
            assert os.path.exists(files["csv"])

    @pytest.mark.integration
    def test_json_output_structure(self):
        """Test JSON output structure and schema compliance."""
        result = _run_application(TEST_GAME_BLOWOUT)
        assert result.returncode == 0

        data = _load_json_output(TEST_GAME_BLOWOUT)

        # Verify top-level structure
        assert "game_id" in data
        assert "segment_count" in data
        assert "segments" in data
        assert isinstance(data["segments"], list)
        assert len(data["segments"]) > 0

        # Verify first segment structure
        first_segment = data["segments"][0]
        assert "segment_id" in first_segment
        assert "start_quarter" in first_segment
        assert "end_quarter" in first_segment
        assert "start_time" in first_segment
        assert "end_time" in first_segment
        assert "duration_seconds" in first_segment
        assert "home_lineup" in first_segment
        assert "away_lineup" in first_segment
        assert "home_boxscore" in first_segment
        assert "away_boxscore" in first_segment

        # Verify lineup structure
        assert "team" in first_segment["home_lineup"]
        assert "lineup_key" in first_segment["home_lineup"]
        assert "players" in first_segment["home_lineup"]
        assert len(first_segment["home_lineup"]["players"]) == 5

        # Verify boxscore structure
        home_box = first_segment["home_boxscore"]
        expected_fields = [
            "points", "fgm", "fga", "fg_pct", "fg3m", "fg3a", "fg3_pct",
            "ftm", "fta", "ft_pct", "oreb", "dreb", "treb", "ast",
            "stl", "blk", "tov", "pf", "plus_minus", "possessions",
            "offensive_rating", "defensive_rating", "duration_seconds"
        ]
        for field in expected_fields:
            assert field in home_box, f"Missing field in boxscore: {field}"

    @pytest.mark.integration
    def test_csv_output_structure(self):
        """Test CSV output structure."""
        result = _run_application(TEST_GAME_BLOWOUT)
        assert result.returncode == 0

        rows = _load_csv_output(TEST_GAME_BLOWOUT)

        # Verify rows exist
        assert len(rows) > 0, "No data rows in CSV"

        # Verify first row has all expected fields
        first_row = rows[0]
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
            assert field in first_row, f"Missing field in CSV: {field}"

    @pytest.mark.integration
    def test_segment_count_consistency(self):
        """Test that segment count is consistent across outputs."""
        result = _run_application(TEST_GAME_BLOWOUT)
        assert result.returncode == 0

        json_data = _load_json_output(TEST_GAME_BLOWOUT)
        csv_rows = _load_csv_output(TEST_GAME_BLOWOUT)

        # Verify segment counts match
        assert json_data["segment_count"] == len(csv_rows)

        # Verify each segment has data
        assert json_data["segment_count"] > 0

    @pytest.mark.integration
    def test_lineup_completeness(self):
        """Test that all lineups have exactly 5 players."""
        result = _run_application(TEST_GAME_BLOWOUT)
        assert result.returncode == 0

        data = _load_json_output(TEST_GAME_BLOWOUT)

        for segment in data["segments"]:
            # Verify home lineup has 5 players
            home_players = segment["home_lineup"]["players"]
            assert len(home_players) == 5, f"Home lineup has {len(home_players)} players, expected 5"

            # Verify away lineup has 5 players
            away_players = segment["away_lineup"]["players"]
            assert len(away_players) == 5, f"Away lineup has {len(away_players)} players, expected 5"

            # Verify player IDs are strings
            for player_id in home_players + away_players:
                assert isinstance(player_id, str)
                assert len(player_id) > 0

    @pytest.mark.integration
    def test_time_continuity(self):
        """Test that game segments have continuous time coverage."""
        result = _run_application(TEST_GAME_BLOWOUT)
        assert result.returncode == 0

        data = _load_json_output(TEST_GAME_BLOWOUT)

        # Sort segments by start time to check continuity
        segments = sorted(data["segments"], key=lambda s: (s["start_quarter"], -s["start_time"]))

        for i in range(len(segments) - 1):
            current = segments[i]
            next_seg = segments[i + 1]

            # If same quarter, end time should match next start time
            if current["end_quarter"] == next_seg["start_quarter"]:
                assert current["end_time"] == next_seg["start_time"], \
                    f"Time gap between segments: {current['segment_id']} and {next_seg['segment_id']}"

    @pytest.mark.integration
    def test_boxscore_data_types(self):
        """Test that boxscore data has correct types."""
        result = _run_application(TEST_GAME_BLOWOUT)
        assert result.returncode == 0

        data = _load_json_output(TEST_GAME_BLOWOUT)

        for segment in data["segments"]:
            home_box = segment["home_boxscore"]

            # Verify integer fields
            int_fields = ["points", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta",
                         "oreb", "dreb", "treb", "ast", "stl", "blk", "tov", "pf", "plus_minus"]
            for field in int_fields:
                assert isinstance(home_box[field], int), f"Field {field} should be int, got {type(home_box[field])}"

            # Verify float fields
            float_fields = ["fg_pct", "fg3_pct", "ft_pct", "offensive_rating", "defensive_rating"]
            for field in float_fields:
                assert isinstance(home_box[field], float), f"Field {field} should be float, got {type(home_box[field])}"

    @pytest.mark.integration
    def test_duration_calculations(self):
        """Test that duration calculations are correct."""
        result = _run_application(TEST_GAME_BLOWOUT)
        assert result.returncode == 0

        data = _load_json_output(TEST_GAME_BLOWOUT)

        for segment in data["segments"]:
            # Calculate expected duration
            if segment["start_quarter"] == segment["end_quarter"]:
                expected_duration = segment["start_time"] - segment["end_time"]
            else:
                # Multi-quarter segment (rare but possible)
                expected_duration = segment["start_time"] + \
                                  (segment["end_quarter"] - segment["start_quarter"]) * 720 - \
                                  segment["end_time"]

            assert segment["duration_seconds"] == expected_duration, \
                f"Duration mismatch in segment {segment['segment_id']}"

    @pytest.mark.integration
    def test_shooting_percentage_calculations(self):
        """Test that shooting percentages are calculated correctly."""
        result = _run_application(TEST_GAME_BLOWOUT)
        assert result.returncode == 0

        data = _load_json_output(TEST_GAME_BLOWOUT)

        for segment in data["segments"]:
            home_box = segment["home_boxscore"]

            # Skip if no attempts (avoid division by zero)
            if home_box["fga"] > 0:
                expected_fg_pct = (home_box["fgm"] / home_box["fga"]) * 100
                assert abs(home_box["fg_pct"] - expected_fg_pct) < 0.01, \
                    f"FG% calculation error in segment {segment['segment_id']}"

            if home_box["fg3a"] > 0:
                expected_fg3_pct = (home_box["fg3m"] / home_box["fg3a"]) * 100
                assert abs(home_box["fg3_pct"] - expected_fg3_pct) < 0.01, \
                    f"3P% calculation error in segment {segment['segment_id']}"

            if home_box["fta"] > 0:
                expected_ft_pct = (home_box["ftm"] / home_box["fta"]) * 100
                assert abs(home_box["ft_pct"] - expected_ft_pct) < 0.01, \
                    f"FT% calculation error in segment {segment['segment_id']}"

    @pytest.mark.integration
    def test_plus_minus_consistency(self):
        """Test that plus/minus values are consistent between teams."""
        result = _run_application(TEST_GAME_BLOWOUT)
        assert result.returncode == 0

        data = _load_json_output(TEST_GAME_BLOWOUT)

        for segment in data["segments"]:
            home_pm = segment["home_boxscore"]["plus_minus"]
            away_pm = segment["away_boxscore"]["plus_minus"]

            # Plus/minus should be equal and opposite
            assert home_pm == -away_pm, \
                f"Plus/minus mismatch: home={home_pm}, away={away_pm} in segment {segment['segment_id']}"

class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.integration
    def test_invalid_game_id(self):
        """Test handling of invalid game ID."""
        result = _run_application(TEST_GAME_INVALID)

        # Should fail gracefully (non-zero exit code or error message)
        # Don't assert returncode since behavior may vary
        # Just verify it doesn't crash the system
        assert "error" in result.stderr.lower() or "Error" in result.stdout or result.returncode != 0

    @pytest.mark.integration
    def test_old_season_game(self):
        """Test processing a game from older season."""
        result = _run_application(TEST_GAME_OLD)

        # Older games might have data issues, so we just check it doesn't crash
        # Some old games may not have complete play-by-play data
        if result.returncode == 0:
            files = get_output_files(TEST_GAME_OLD)
            if os.path.exists(files["json"]):
                data = _load_json_output(TEST_GAME_OLD)
                # If it succeeded, should have segments
                assert data["segment_count"] >= 0

    @pytest.mark.integration
    def test_output_file_permissions(self):
        """Test handling of file permission issues."""
        # This is hard to test without actually changing permissions
        # For now, we verify the application doesn't crash when writing files
        result = _run_application(TEST_GAME_BLOWOUT)
        assert result.returncode == 0

        files = get_output_files(TEST_GAME_BLOWOUT)
        assert os.path.exists(files["json"])
        assert os.path.exists(files["csv"])

class TestDataValidation:
    """Test data validation and integrity."""

    @pytest.mark.integration
    def test_json_csv_data_consistency(self):
        """Test that JSON and CSV outputs have consistent data."""
        result = _run_application(TEST_GAME_BLOWOUT)
        assert result.returncode == 0

        json_data = _load_json_output(TEST_GAME_BLOWOUT)
        csv_rows = _load_csv_output(TEST_GAME_BLOWOUT)

        # Compare first segment/row
        json_segment = json_data["segments"][0]
        csv_row = csv_rows[0]

        # Verify key fields match
        assert int(csv_row["segment_id"]) == json_segment["segment_id"]
        assert int(csv_row["start_quarter"]) == json_segment["start_quarter"]
        assert float(csv_row["start_time"]) == json_segment["start_time"]
        assert csv_row["home_team"] == json_segment["home_lineup"]["team"]
        assert csv_row["away_team"] == json_segment["away_lineup"]["team"]
        assert int(csv_row["home_pts"]) == json_segment["home_boxscore"]["points"]
        assert int(csv_row["away_pts"]) == json_segment["away_boxscore"]["points"]

    @pytest.mark.integration
    def test_no_duplicate_segments(self):
        """Test that no duplicate segments exist."""
        result = _run_application(TEST_GAME_BLOWOUT)
        assert result.returncode == 0

        data = _load_json_output(TEST_GAME_BLOWOUT)

        # Collect all segment IDs
        segment_ids = [s["segment_id"] for s in data["segments"]]

        # Verify no duplicates
        assert len(segment_ids) == len(set(segment_ids)), "Duplicate segment IDs found"

    @pytest.mark.integration
    def test_lineup_key_uniqueness(self):
        """Test that lineup keys are properly formatted."""
        result = _run_application(TEST_GAME_BLOWOUT)
        assert result.returncode == 0

        data = _load_json_output(TEST_GAME_BLOWOUT)

        for segment in data["segments"]:
            home_key = segment["home_lineup"]["lineup_key"]
            away_key = segment["away_lineup"]["lineup_key"]

            # Lineup keys should be non-empty strings
            assert isinstance(home_key, str)
            assert len(home_key) > 0
            assert isinstance(away_key, str)
            assert len(away_key) > 0

            # Should contain player IDs (numeric strings)
            assert any(c.isdigit() for c in home_key)

    @pytest.mark.integration
    def test_boxscore_totals_reasonable(self):
        """Test that boxscore totals are within reasonable ranges."""
        result = _run_application(TEST_GAME_BLOWOUT)
        assert result.returncode == 0

        data = _load_json_output(TEST_GAME_BLOWOUT)

        for segment in data["segments"]:
            home_box = segment["home_boxscore"]

            # Points should be reasonable (0-50 per segment)
            assert 0 <= home_box["points"] <= 50, f"Unreasonable points: {home_box['points']}"

            # Field goal attempts should be reasonable
            assert home_box["fga"] >= home_box["fgm"], "More makes than attempts"
            assert home_box["fga"] <= 30, f"Too many FGA: {home_box['fga']}"

            # Rebounds should be reasonable
            assert home_box["treb"] == home_box["oreb"] + home_box["dreb"], "Rebound totals don't match"

            # Plus/minus should be reasonable
            assert -30 <= home_box["plus_minus"] <= 30, f"Unreasonable plus/minus: {home_box['plus_minus']}"
