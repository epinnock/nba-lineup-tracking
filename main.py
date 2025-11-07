import argparse
import sys
from api.nba_client import get_play_by_play
from processors.lineup_detector import LineupDetector
from processors.stats_calculator import StatsCalculator
from exporters.json_exporter import export_to_json
from exporters.csv_exporter import export_to_csv

def main():
    """
    Main entry point for the NBA Lineup Tracker application.
    """
    parser = argparse.ArgumentParser(
        description="Analyzes NBA games to provide lineup-level boxscore statistics."
    )
    parser.add_argument(
        "game_id",
        type=str,
        help="The Game ID to analyze (e.g., 0022300001)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=".",
        help="Directory to save the output files."
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching of API responses."
    )
    args = parser.parse_args()

    print(f"Starting analysis for Game ID: {args.game_id}...")

    # 1. Fetch data from the NBA API
    raw_data = get_play_by_play(args.game_id, use_cache=not args.no_cache)
    if not raw_data or 'resultSets' not in raw_data or not raw_data['resultSets']:
        print(f"Failed to fetch or parse data for game {args.game_id}. Exiting.")
        sys.exit(1)

    plays = raw_data['resultSets'][0].get('rowSet', [])
    if not plays:
        print(f"No plays found for game {args.game_id}. Exiting.")
        sys.exit(1)

    # Convert list of lists to list of dicts for easier processing
    headers = raw_data['resultSets'][0].get('headers', [])
    play_dicts = [dict(zip(headers, play)) for play in plays]

    # 2. Detect lineup changes and create game segments
    print("Detecting lineup segments...")
    detector = LineupDetector(args.game_id, play_dicts)
    segments = detector.process_game()
    if not segments:
        print("No game segments could be created. There might be an issue with the data.")
        sys.exit(1)
    print(f"Found {len(segments)} lineup segments.")

    # 3. Calculate boxscore statistics for each segment
    print("Calculating statistics for each segment...")
    calculator = StatsCalculator(segments, play_dicts)
    processed_segments = calculator.calculate_boxscores()

    # 4. Export the results
    print("Exporting results...")
    export_to_json(args.game_id, processed_segments, args.output_dir)
    export_to_csv(args.game_id, processed_segments, args.output_dir)

    print("\nAnalysis complete.")

if __name__ == "__main__":
    main()
