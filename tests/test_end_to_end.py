import os
import subprocess
import pytest

# A known game ID with accessible data
TEST_GAME_ID = "0022300001"
OUTPUT_JSON_FILE = f"{TEST_GAME_ID}_lineups.json"
OUTPUT_CSV_FILE = f"{TEST_GAME_ID}_lineups.csv"

@pytest.fixture(scope="module", autouse=True)
def cleanup_files():
    """Fixture to clean up output files before and after tests."""
    # Run before tests
    _remove_if_exists(OUTPUT_JSON_FILE)
    _remove_if_exists(OUTPUT_CSV_FILE)

    yield # This is where the tests will run

    # Run after tests
    _remove_if_exists(OUTPUT_JSON_FILE)
    _remove_if_exists(OUTPUT_CSV_FILE)

def _remove_if_exists(filepath):
    if os.path.exists(filepath):
        os.remove(filepath)

def test_application_runs_end_to_end():
    """
    Tests if the main application runs without critical errors and creates output files.
    """
    # Execute the main script as a subprocess
    result = subprocess.run(
        ["python", "main.py", TEST_GAME_ID],
        capture_output=True,
        text=True
    )

    # 1. Check if the script executed successfully
    assert result.returncode == 0, f"Script failed with error: {result.stderr}"

    # 2. Check if the output files were created
    assert os.path.exists(OUTPUT_JSON_FILE), f"Expected output file {OUTPUT_JSON_FILE} was not created."
    assert os.path.exists(OUTPUT_CSV_FILE), f"Expected output file {OUTPUT_CSV_FILE} was not created."

    # 3. Check if the output files have content
    assert os.path.getsize(OUTPUT_JSON_FILE) > 0, f"{OUTPUT_JSON_FILE} is empty."
    assert os.path.getsize(OUTPUT_CSV_FILE) > 0, f"{OUTPUT_CSV_FILE} is empty."

    # 4. Check for expected output messages
    assert "Analysis complete." in result.stdout, "Expected 'Analysis complete.' message not found in output."
