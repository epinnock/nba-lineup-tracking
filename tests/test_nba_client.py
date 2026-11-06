"""
Unit tests for nba_client.py module.

Tests the NBA API client including:
- Successful data fetch
- Caching mechanism (mock file system)
- Rate limiting verification
- Error handling for invalid game IDs
- Mock NBA API responses to avoid external calls
"""

import json
import os
import time
import pytest
from unittest.mock import Mock, patch, MagicMock
from api.nba_client import get_play_by_play, CACHE_DIR


class TestGetPlayByPlay:
    """Test cases for get_play_by_play function."""

    def test_successful_fetch_with_cache(self, tmp_path, monkeypatch):
        """Test successful data fetch with caching enabled."""
        # Mock the CACHE_DIR to use tmp_path
        monkeypatch.setattr("api.nba_client.CACHE_DIR", str(tmp_path))

        # Mock the PlayByPlayV2 API call
        mock_pbp = Mock()
        mock_data = {
            "resultSets": [
                {
                    "name": "PlayByPlay",
                    "headers": ["GAME_ID", "EVENTNUM"],
                    "rowSet": [["0022100001", 1], ["0022100001", 2]],
                }
            ]
        }
        mock_pbp.get_dict.return_value = mock_data

        with patch("api.nba_client.playbyplayv2.PlayByPlayV2", return_value=mock_pbp):
            with patch("api.nba_client.time.sleep"):  # Skip the sleep for testing
                result = get_play_by_play("0022100001", use_cache=True)

        # Verify the result
        assert result == mock_data
        assert "resultSets" in result
        assert len(result["resultSets"][0]["rowSet"]) == 2

        # Verify cache file was created
        cache_file = tmp_path / "0022100001.json"
        assert cache_file.exists()

        # Verify cache content
        with open(cache_file, "r") as f:
            cached_data = json.load(f)
        assert cached_data == mock_data

    def test_fetch_from_cache(self, tmp_path, monkeypatch):
        """Test fetching data from cache without hitting API."""
        # Mock the CACHE_DIR to use tmp_path
        monkeypatch.setattr("api.nba_client.CACHE_DIR", str(tmp_path))

        # Pre-populate cache
        cached_data = {
            "resultSets": [
                {
                    "name": "PlayByPlay",
                    "headers": ["GAME_ID", "EVENTNUM"],
                    "rowSet": [["0022100001", 1], ["0022100001", 2]],
                }
            ]
        }
        cache_file = tmp_path / "0022100001.json"
        with open(cache_file, "w") as f:
            json.dump(cached_data, f)

        # Mock the API to ensure it's NOT called
        with patch("api.nba_client.playbyplayv2.PlayByPlayV2") as mock_api:
            result = get_play_by_play("0022100001", use_cache=True)

            # Verify API was not called
            mock_api.assert_not_called()

        # Verify result came from cache
        assert result == cached_data

    def test_fetch_without_cache(self, tmp_path, monkeypatch):
        """Test fetching data without using cache."""
        # Mock the CACHE_DIR to use tmp_path
        monkeypatch.setattr("api.nba_client.CACHE_DIR", str(tmp_path))

        # Pre-populate cache (should be ignored)
        cached_data = {"old": "data"}
        cache_file = tmp_path / "0022100001.json"
        with open(cache_file, "w") as f:
            json.dump(cached_data, f)

        # Mock the API call
        mock_pbp = Mock()
        new_data = {
            "resultSets": [
                {
                    "name": "PlayByPlay",
                    "headers": ["GAME_ID", "EVENTNUM"],
                    "rowSet": [["0022100001", 1]],
                }
            ]
        }
        mock_pbp.get_dict.return_value = new_data

        with patch("api.nba_client.playbyplayv2.PlayByPlayV2", return_value=mock_pbp):
            with patch("api.nba_client.time.sleep"):  # Skip the sleep for testing
                result = get_play_by_play("0022100001", use_cache=False)

        # Verify the new data was fetched
        assert result == new_data
        assert result != cached_data

        # Verify cache was updated with new data
        with open(cache_file, "r") as f:
            updated_cache = json.load(f)
        assert updated_cache == new_data

    def test_rate_limiting(self, tmp_path, monkeypatch):
        """Test that rate limiting (sleep) is applied."""
        # Mock the CACHE_DIR to use tmp_path
        monkeypatch.setattr("api.nba_client.CACHE_DIR", str(tmp_path))

        mock_pbp = Mock()
        mock_data = {"resultSets": []}
        mock_pbp.get_dict.return_value = mock_data

        with patch("api.nba_client.playbyplayv2.PlayByPlayV2", return_value=mock_pbp):
            with patch("api.nba_client.time.sleep") as mock_sleep:
                get_play_by_play("0022100001", use_cache=False)

                # Verify sleep was called with 0.6 seconds
                mock_sleep.assert_called_once_with(0.6)

    def test_error_handling_invalid_game_id(self, tmp_path, monkeypatch):
        """Test error handling for invalid game ID."""
        # Mock the CACHE_DIR to use tmp_path
        monkeypatch.setattr("api.nba_client.CACHE_DIR", str(tmp_path))

        # Mock API to raise an exception
        with patch("api.nba_client.playbyplayv2.PlayByPlayV2") as mock_api:
            mock_api.side_effect = Exception("Invalid game ID")

            result = get_play_by_play("INVALID_ID", use_cache=False)

        # Verify empty dict is returned on error
        assert result == {}

    def test_error_handling_api_timeout(self, tmp_path, monkeypatch):
        """Test error handling for API timeout."""
        # Mock the CACHE_DIR to use tmp_path
        monkeypatch.setattr("api.nba_client.CACHE_DIR", str(tmp_path))

        # Mock API to raise a timeout exception
        with patch("api.nba_client.playbyplayv2.PlayByPlayV2") as mock_api:
            mock_api.side_effect = TimeoutError("API timeout")

            result = get_play_by_play("0022100001", use_cache=False)

        # Verify empty dict is returned on error
        assert result == {}

    def test_error_handling_network_error(self, tmp_path, monkeypatch):
        """Test error handling for network errors."""
        # Mock the CACHE_DIR to use tmp_path
        monkeypatch.setattr("api.nba_client.CACHE_DIR", str(tmp_path))

        # Mock API to raise a connection error
        with patch("api.nba_client.playbyplayv2.PlayByPlayV2") as mock_api:
            mock_api.side_effect = ConnectionError("Network error")

            result = get_play_by_play("0022100001", use_cache=False)

        # Verify empty dict is returned on error
        assert result == {}

    def test_cache_directory_creation(self, tmp_path, monkeypatch):
        """Test that cache directory is created if it doesn't exist."""
        # Use a subdirectory that doesn't exist yet
        cache_dir = tmp_path / "new_cache"
        monkeypatch.setattr("api.nba_client.CACHE_DIR", str(cache_dir))

        mock_pbp = Mock()
        mock_data = {"resultSets": []}
        mock_pbp.get_dict.return_value = mock_data

        with patch("api.nba_client.playbyplayv2.PlayByPlayV2", return_value=mock_pbp):
            with patch("api.nba_client.time.sleep"):
                get_play_by_play("0022100001", use_cache=True)

        # Verify cache directory was created
        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_malformed_cache_file(self, tmp_path, monkeypatch):
        """Test handling of malformed cache file."""
        # Mock the CACHE_DIR to use tmp_path
        monkeypatch.setattr("api.nba_client.CACHE_DIR", str(tmp_path))

        # Create malformed cache file
        cache_file = tmp_path / "0022100001.json"
        with open(cache_file, "w") as f:
            f.write("invalid json content")

        # Mock API call
        mock_pbp = Mock()
        mock_data = {"resultSets": []}
        mock_pbp.get_dict.return_value = mock_data

        with patch("api.nba_client.playbyplayv2.PlayByPlayV2", return_value=mock_pbp):
            with patch("api.nba_client.time.sleep"):
                result = get_play_by_play("0022100001", use_cache=True)

        # Should fetch from API when cache is malformed
        assert result == mock_data

        # Verify cache was overwritten with valid data
        with open(cache_file, "r") as f:
            cached_data = json.load(f)
        assert cached_data == mock_data

    def test_empty_api_response(self, tmp_path, monkeypatch):
        """Test handling of empty API response."""
        # Mock the CACHE_DIR to use tmp_path
        monkeypatch.setattr("api.nba_client.CACHE_DIR", str(tmp_path))

        mock_pbp = Mock()
        mock_pbp.get_dict.return_value = {}  # Empty response

        with patch("api.nba_client.playbyplayv2.PlayByPlayV2", return_value=mock_pbp):
            with patch("api.nba_client.time.sleep"):
                result = get_play_by_play("0022100001", use_cache=False)

        # Verify empty dict is returned
        assert result == {}

    def test_complex_playbyplay_structure(self, tmp_path, monkeypatch):
        """Test handling of complex play-by-play data structure."""
        # Mock the CACHE_DIR to use tmp_path
        monkeypatch.setattr("api.nba_client.CACHE_DIR", str(tmp_path))

        # Create complex mock data
        complex_data = {
            "resultSets": [
                {
                    "name": "PlayByPlay",
                    "headers": [
                        "GAME_ID",
                        "EVENTNUM",
                        "EVENTMSGTYPE",
                        "EVENTMSGACTIONTYPE",
                        "PERIOD",
                        "PCTIMESTRING",
                        "HOMEDESCRIPTION",
                        "NEUTRALDESCRIPTION",
                        "VISITORDESCRIPTION",
                        "SCORE",
                        "SCOREMARGIN",
                        "PERSON1TYPE",
                        "PLAYER1_ID",
                        "PLAYER1_NAME",
                        "PLAYER1_TEAM_ID",
                        "PLAYER1_TEAM_CITY",
                        "PLAYER1_TEAM_NICKNAME",
                        "PLAYER1_TEAM_ABBREVIATION",
                    ],
                    "rowSet": [
                        [
                            "0022100001",
                            1,
                            12,
                            0,
                            1,
                            "12:00",
                            None,
                            "Start Period",
                            None,
                            None,
                            None,
                            0,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                        ],
                        [
                            "0022100001",
                            2,
                            10,
                            0,
                            1,
                            "11:45",
                            "G. Antetokounmpo S.FOUL",
                            None,
                            None,
                            None,
                            None,
                            5,
                            "203507",
                            "Giannis Antetokounmpo",
                            "1610612749",
                            "Milwaukee",
                            "Bucks",
                            "MIL",
                        ],
                    ],
                }
            ]
        }

        mock_pbp = Mock()
        mock_pbp.get_dict.return_value = complex_data

        with patch("api.nba_client.playbyplayv2.PlayByPlayV2", return_value=mock_pbp):
            with patch("api.nba_client.time.sleep"):
                result = get_play_by_play("0022100001", use_cache=True)

        # Verify complex data is handled correctly
        assert result == complex_data
        assert len(result["resultSets"][0]["rowSet"]) == 2
        assert result["resultSets"][0]["rowSet"][1][12] == "203507"  # Player ID

    def test_concurrent_requests(self, tmp_path, monkeypatch):
        """Test handling of multiple concurrent requests."""
        # Mock the CACHE_DIR to use tmp_path
        monkeypatch.setattr("api.nba_client.CACHE_DIR", str(tmp_path))

        mock_pbp = Mock()
        mock_data = {"resultSets": []}
        mock_pbp.get_dict.return_value = mock_data

        with patch("api.nba_client.playbyplayv2.PlayByPlayV2", return_value=mock_pbp):
            with patch("api.nba_client.time.sleep"):
                # Make multiple requests
                result1 = get_play_by_play("0022100001", use_cache=True)
                result2 = get_play_by_play("0022100002", use_cache=True)
                result3 = get_play_by_play("0022100001", use_cache=True)  # Same as first

        # Verify all requests succeeded
        assert result1 == mock_data
        assert result2 == mock_data
        assert result3 == mock_data  # Should come from cache

        # Verify separate cache files were created
        assert (tmp_path / "0022100001.json").exists()
        assert (tmp_path / "0022100002.json").exists()


class TestCacheBehavior:
    """Test cases for cache behavior."""

    def test_cache_isolation_between_games(self, tmp_path, monkeypatch):
        """Test that cache is properly isolated between different games."""
        # Mock the CACHE_DIR to use tmp_path
        monkeypatch.setattr("api.nba_client.CACHE_DIR", str(tmp_path))

        mock_pbp = Mock()
        game1_data = {"resultSets": [{"name": "Game1", "rowSet": []}]}
        game2_data = {"resultSets": [{"name": "Game2", "rowSet": []}]}

        def mock_get_dict():
            if mock_pbp.call_count == 1:
                return game1_data
            return game2_data

        mock_pbp.get_dict.side_effect = mock_get_dict

        with patch("api.nba_client.playbyplayv2.PlayByPlayV2", return_value=mock_pbp):
            with patch("api.nba_client.time.sleep"):
                result1 = get_play_by_play("0022100001", use_cache=True)
                result2 = get_play_by_play("0022100002", use_cache=True)

        # Verify different data was returned
        assert result1 != result2
        assert result1 == game1_data
        assert result2 == game2_data

        # Verify separate cache files
        with open(tmp_path / "0022100001.json", "r") as f:
            assert json.load(f) == game1_data
        with open(tmp_path / "0022100002.json", "r") as f:
            assert json.load(f) == game2_data

    def test_cache_with_use_cache_false_does_not_read_cache(self, tmp_path, monkeypatch):
        """Test that use_cache=False doesn't read from cache but still writes."""
        # Mock the CACHE_DIR to use tmp_path
        monkeypatch.setattr("api.nba_client.CACHE_DIR", str(tmp_path))

        # Create cache file
        old_data = {"old": "cached_data"}
        cache_file = tmp_path / "0022100001.json"
        with open(cache_file, "w") as f:
            json.dump(old_data, f)

        # Mock API to return new data
        mock_pbp = Mock()
        new_data = {"new": "fresh_data"}
        mock_pbp.get_dict.return_value = new_data

        with patch("api.nba_client.playbyplayv2.PlayByPlayV2", return_value=mock_pbp):
            with patch("api.nba_client.time.sleep"):
                result = get_play_by_play("0022100001", use_cache=False)

        # Should return new data, not cached data
        assert result == new_data
        assert result != old_data

        # Cache should be updated with new data
        with open(cache_file, "r") as f:
            assert json.load(f) == new_data