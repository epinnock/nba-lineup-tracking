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
        "--game-id", "--game_id",
        type=str,
        required=True,
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
    parser.add_argument(
        "--use-rotation",
        action="store_true",
        help="Build lineup segments from GameRotation (official rotation stints) instead of inferring from substitutions in play-by-play."
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Starting analysis for Game ID: {args.game_id}")
    print(f"Cache enabled: {not args.no_cache}")
    print(f"Output directory: {args.output_dir}")
    print(f"{'='*60}\n")

    # 1. Fetch data from the NBA API
    print(f"[MAIN] Step 1: Fetching play-by-play data...")
    raw_data = get_play_by_play(args.game_id, use_cache=not args.no_cache)
    
    print(f"[MAIN] Received raw_data: {type(raw_data)}")
    if raw_data:
        print(f"[MAIN] Raw data keys: {list(raw_data.keys())}")
    
    # Try to get resultSets (plural) first, then resultSet (singular) as fallback
    result_sets = raw_data.get('resultSets') or raw_data.get('resultSet')
    
    if not raw_data or not result_sets:
        print(f"[MAIN] ERROR: Failed to fetch or parse data for game {args.game_id}. Exiting.")
        sys.exit(1)

    print(f"[MAIN] Found result_sets: {type(result_sets)}, length: {len(result_sets) if isinstance(result_sets, list) else 'N/A'}")

    # Get the first result set (play-by-play data)
    plays = result_sets[0].get('rowSet', []) if isinstance(result_sets, list) else []
    if not plays:
        print(f"[MAIN] ERROR: No plays found for game {args.game_id}. Exiting.")
        sys.exit(1)

    print(f"[MAIN] Extracted {len(plays)} plays from first result set")

    # Convert list of lists to list of dicts for easier processing
    headers = result_sets[0].get('headers', []) if isinstance(result_sets, list) else []
    print(f"[MAIN] Headers ({len(headers)}): {headers[:5]}..." if len(headers) > 5 else f"[MAIN] Headers: {headers}")
    play_dicts = [dict(zip(headers, play)) for play in plays]
    print(f"[MAIN] Converted to {len(play_dicts)} play dictionaries")

    # 2. Detect lineup changes and create game segments
    print(f"\n[MAIN] Step 2: Detecting lineup segments...")
    try:
        rotation_payload = None

        if args.use_rotation:
            from processors.rotation_segment_builder import (
                fetch_gamerotation_payload,
                build_segments_from_gamerotation,
            )
            print("[MAIN] Using GameRotation to build segments...")
            # NOTE: rotation payload is intentionally NOT cached on disk.
            rotation_payload = fetch_gamerotation_payload(args.game_id)
            segments, meta = build_segments_from_gamerotation(args.game_id, rotation_payload)
            print(
                "[MAIN] GameRotation teams: "
                f"away={meta['away_team']['team_abbr']} home={meta['home_team']['team_abbr']}; "
                f"segments={meta['segment_count']}"
            )
        else:
            detector = LineupDetector(args.game_id, play_dicts)
            print(f"[MAIN] LineupDetector created, processing game...")
            segments = detector.process_game()

        if not segments:
            print("[MAIN] ERROR: No game segments could be created. There might be an issue with the data.")
            sys.exit(1)

        print(f"[MAIN] Successfully found {len(segments)} lineup segments")

        # Always verify/correct lineups using GameRotation for *every* segment (not only end-of-quarter).
        # This keeps the PBP-derived segmentation but ensures the lineups per segment are official.
        try:
            from processors.rotation_segment_builder import (
                fetch_gamerotation_payload,
                apply_gamerotation_lineups_to_segments,
            )

            if rotation_payload is None:
                rotation_payload = fetch_gamerotation_payload(args.game_id)

            verify_meta = apply_gamerotation_lineups_to_segments(segments, rotation_payload)
            print(
                "[MAIN] GameRotation lineup verification: "
                f"verified={verify_meta['segments_verified']} "
                f"corrected={verify_meta['segments_corrected']} "
                f"skipped_cross_period={verify_meta['segments_skipped_cross_period']} "
                f"skipped_errors={verify_meta['segments_skipped_errors']}"
            )
        except Exception as e:
            print(f"[MAIN] WARNING: GameRotation lineup verification failed: {type(e).__name__}: {e}")

    except Exception as e:
        print(f"[MAIN] ERROR during lineup detection: {e}")
        import traceback
        print(f"[MAIN] Traceback:\n{traceback.format_exc()}")
        sys.exit(1)

    # 3. Calculate boxscore statistics for each segment
    print(f"\n[MAIN] Step 3: Calculating statistics for each segment...")
    try:
        calculator = StatsCalculator(segments, play_dicts)
        print(f"[MAIN] StatsCalculator created, calculating boxscores...")
        processed_segments = calculator.calculate_boxscores()
        print(f"[MAIN] Successfully calculated statistics for {len(processed_segments)} segments")
    except Exception as e:
        print(f"[MAIN] ERROR during stats calculation: {e}")
        import traceback
        print(f"[MAIN] Traceback:\n{traceback.format_exc()}")
        sys.exit(1)

    # 4. Export the results
    print(f"\n[MAIN] Step 4: Exporting results to {args.output_dir}...")
    try:
        json_file = export_to_json(args.game_id, processed_segments, args.output_dir)
        print(f"[MAIN] JSON export complete: {json_file}")
        csv_file = export_to_csv(args.game_id, processed_segments, args.output_dir)
        print(f"[MAIN] CSV export complete: {csv_file}")
    except Exception as e:
        print(f"[MAIN] ERROR during export: {e}")
        import traceback
        print(f"[MAIN] Traceback:\n{traceback.format_exc()}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("Analysis complete successfully!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
