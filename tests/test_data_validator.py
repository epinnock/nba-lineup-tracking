"""
Unit tests for data_validator.py module.

Tests the data validation layer including:
- Valid/invalid game ID formats
- Data completeness checks
- Malformed data handling
- Play-by-play data structure validation
"""

import pytest
from api.data_validator import validate_game_id, validate_playbyplay_data


class TestValidateGameId:
    """Test cases for game ID validation."""

    def test_valid_regular_season_game_id(self):
        """Test validation of valid regular season game ID."""
        assert validate_game_id("0022100001") is True
        assert validate_game_id("0022201234") is True

    def test_valid_playoff_game_id(self):
        """Test validation of valid playoff game ID."""
        assert validate_game_id("0042100001") is True
        assert validate_game_id("0042200456") is True

    def test_valid_preseason_game_id(self):
        """Test validation of valid preseason game ID."""
        assert validate_game_id("0012100001") is True
        assert validate_game_id("0012200789") is True

    def test_invalid_game_id_too_short(self):
        """Test validation of game ID that is too short."""
        assert validate_game_id("002210001") is False  # 9 digits
        assert validate_game_id("12345") is False

    def test_invalid_game_id_too_long(self):
        """Test validation of game ID that is too long."""
        assert validate_game_id("00221000011") is False  # 11 digits
        assert validate_game_id("002210000111111") is False

    def test_invalid_game_id_wrong_prefix(self):
        """Test validation of game ID with wrong prefix."""
        assert validate_game_id("0032100001") is False  # Invalid prefix '003'
        assert validate_game_id("0052100001") is False  # Invalid prefix '005'
        assert validate_game_id("1022100001") is False  # Invalid prefix '102'

    def test_invalid_game_id_non_numeric(self):
        """Test validation of game ID with non-numeric characters."""
        assert validate_game_id("00221A0001") is False  # Contains letter
        assert validate_game_id("00221000X1") is False  # Contains letter
        assert validate_game_id("002210000!") is False  # Contains special char
        assert validate_game_id("00221000-1") is False  # Contains dash

    def test_empty_game_id(self):
        """Test validation of empty game ID."""
        assert validate_game_id("") is False

    def test_none_game_id(self):
        """Test validation of None game ID."""
        assert validate_game_id(None) is False

    def test_game_id_with_spaces(self):
        """Test validation of game ID with spaces."""
        assert validate_game_id("002210 001") is False
        assert validate_game_id(" 0022100001") is False
        assert validate_game_id("0022100001 ") is False

    def test_all_valid_prefixes(self):
        """Test all valid game ID prefixes."""
        valid_prefixes = ["001", "002", "004"]  # Preseason, Regular, Playoffs
        for prefix in valid_prefixes:
            game_id = f"{prefix}2100001"
            assert validate_game_id(game_id) is True


class TestValidatePlayByPlayData:
    """Test cases for play-by-play data validation."""

    def test_valid_playbyplay_structure(self):
        """Test validation of properly structured play-by-play data."""
        valid_data = {
            "resultSets": [
                {
                    "name": "PlayByPlay",
                    "headers": ["GAME_ID", "EVENTNUM", "EVENTMSGTYPE", "EVENTMSGACTIONTYPE"],
                    "rowSet": [
                        ["0022100001", 1, 12, 0],
                        ["0022100001", 2, 10, 0],
                    ],
                }
            ]
        }
        assert validate_playbyplay_data(valid_data) is True

    def test_valid_playbyplay_with_multiple_resultsets(self):
        """Test validation of play-by-play data with multiple result sets."""
        valid_data = {
            "resultSets": [
                {"name": "PlayByPlay", "headers": [], "rowSet": []},
                {"name": "OtherData", "headers": [], "rowSet": []},
            ]
        }
        assert validate_playbyplay_data(valid_data) is True

    def test_empty_playbyplay_data(self):
        """Test validation of empty play-by-play data."""
        assert validate_playbyplay_data({}) is False
        assert validate_playbyplay_data(None) is False

    def test_playbyplay_missing_resultsets(self):
        """Test validation of play-by-play data missing resultSets."""
        invalid_data = {"someOtherKey": "value"}
        assert validate_playbyplay_data(invalid_data) is False

    def test_playbyplay_empty_resultsets(self):
        """Test validation of play-by-play data with empty resultSets."""
        invalid_data = {"resultSets": []}
        assert validate_playbyplay_data(invalid_data) is False

    def test_playbyplay_resultsets_not_list(self):
        """Test validation of play-by-play data where resultSets is not a list."""
        invalid_data = {"resultSets": "not a list"}
        assert validate_playbyplay_data(invalid_data) is False

    def test_playbyplay_missing_playbyplay_resultset(self):
        """Test validation when PlayByPlay result set is missing."""
        invalid_data = {
            "resultSets": [
                {"name": "OtherData", "headers": [], "rowSet": []},
            ]
        }
        # This should still be valid - validation is flexible
        assert validate_playbyplay_data(invalid_data) is True

    def test_playbyplay_with_headers_but_no_rowset(self):
        """Test validation of play-by-play data with headers but no rowSet."""
        invalid_data = {
            "resultSets": [
                {
                    "name": "PlayByPlay",
                    "headers": ["GAME_ID", "EVENTNUM"],
                    # Missing rowSet
                }
            ]
        }
        # Should still be valid - rowSet might be empty or missing
        assert validate_playbyplay_data(invalid_data) is True

    def test_playbyplay_malformed_rowset(self):
        """Test validation of play-by-play data with malformed rowSet."""
        invalid_data = {
            "resultSets": [
                {
                    "name": "PlayByPlay",
                    "headers": ["GAME_ID", "EVENTNUM"],
                    "rowSet": "not a list",  # Should be a list
                }
            ]
        }
        # Should still be valid - validation is lenient
        assert validate_playbyplay_data(invalid_data) is True

    def test_playbyplay_with_null_values(self):
        """Test validation of play-by-play data with null values."""
        valid_data = {
            "resultSets": [
                {
                    "name": "PlayByPlay",
                    "headers": ["GAME_ID", "EVENTNUM", "PLAYER1_ID"],
                    "rowSet": [
                        ["0022100001", 1, "203507"],
                        ["0022100001", 2, None],  # Null player ID
                    ],
                }
            ]
        }
        assert validate_playbyplay_data(valid_data) is True

    def test_playbyplay_minimal_valid_structure(self):
        """Test validation of minimal valid play-by-play structure."""
        minimal_data = {
            "resultSets": [
                {
                    "name": "PlayByPlay",
                    "headers": [],
                    "rowSet": [],
                }
            ]
        }
        assert validate_playbyplay_data(minimal_data) is True


class TestDataCompleteness:
    """Test cases for data completeness checks."""

    def test_complete_playbyplay_data(self):
        """Test validation of complete play-by-play data."""
        complete_data = {
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
                        ],
                    ],
                }
            ]
        }
        assert validate_playbyplay_data(complete_data) is True

    def test_playbyplay_with_few_plays(self):
        """Test validation of play-by-play data with very few plays."""
        sparse_data = {
            "resultSets": [
                {
                    "name": "PlayByPlay",
                    "headers": ["GAME_ID", "EVENTNUM"],
                    "rowSet": [["0022100001", 1]],  # Only one play
                }
            ]
        }
        # Should still be valid - might be a partial game or error
        assert validate_playbyplay_data(sparse_data) is True

    def test_playbyplay_with_many_plays(self):
        """Test validation of play-by-play data with many plays."""
        many_plays = [["0022100001", i] for i in range(1, 501)]
        large_data = {
            "resultSets": [
                {
                    "name": "PlayByPlay",
                    "headers": ["GAME_ID", "EVENTNUM"],
                    "rowSet": many_plays,
                }
            ]
        }
        assert validate_playbyplay_data(large_data) is True


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_nested_malformed_structures(self):
        """Test validation of deeply nested malformed structures."""
        malformed_data = {
            "resultSets": [
                {
                    "name": "PlayByPlay",
                    "headers": ["GAME_ID"],
                    "rowSet": [
                        ["0022100001"],
                        None,  # None instead of list
                        "not a list",  # String instead of list
                    ],
                }
            ]
        }
        # Should be lenient and return True
        assert validate_playbyplay_data(malformed_data) is True

    def test_unicode_in_data(self):
        """Test validation of play-by-play data with unicode characters."""
        unicode_data = {
            "resultSets": [
                {
                    "name": "PlayByPlay",
                    "headers": ["GAME_ID", "PLAYER_NAME"],
                    "rowSet": [
                        ["0022100001", "Giannis Antetokounmpo"],
                        ["0022100001", "José Juan Barea"],  # Unicode characters
                    ],
                }
            ]
        }
        assert validate_playbyplay_data(unicode_data) is True

    def test_very_large_dataset(self):
        """Test validation of very large play-by-play dataset."""
        # Simulate a full game with ~500 plays
        large_rowset = []
        for i in range(1, 501):
            large_rowset.append(
                [
                    "0022100001",
                    i,
                    1 if i % 5 == 0 else 2,  # Mix of event types
                    0,
                    (i // 100) + 1,  # Period 1-5
                    f"{12 - (i % 12)}:00",
                    f"Event {i}",
                    None,
                    None,
                    None,
                    None,
                ]
            )

        large_data = {
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
                    ],
                    "rowSet": large_rowset,
                }
            ]
        }
        assert validate_playbyplay_data(large_data) is True