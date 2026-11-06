from typing import List, Dict
from models.game_segment import GameSegment
from models.player_boxscore import PlayerBoxScore

# NBA API Event Message Types
MADE_SHOT = 1
MISSED_SHOT = 2
FREE_THROW = 3
REBOUND = 4
TURNOVER = 5
FOUL = 6
ASSIST_ATTRIBUTE = 'PLAYER2_ID'

class StatsCalculator:
    """
    Calculates boxscore statistics for each game segment.
    """
    def __init__(self, segments: List[GameSegment], plays: List[Dict]):
        self.segments = segments
        self.plays = plays
        self.play_index = 0

    def calculate_boxscores(self) -> List[GameSegment]:
        """
        Processes all segments and calculates their boxscores.
        """
        for i, segment in enumerate(self.segments):
            # Get the plays that fall within the current segment's timeframe
            segment_plays = self._get_plays_for_segment(segment, i)
            self._calculate_segment_stats(segment, segment_plays)
        return self.segments

    def _get_plays_for_segment(self, segment: GameSegment, segment_index: int) -> List[Dict]:
        """
        Retrieves the list of plays that occurred during a specific game segment.
        """
        segment_plays = []
        
        for play in self.plays:
            play_quarter = play.get('PERIOD', 0)
            play_time = self._parse_time_to_seconds(play.get('PCTIMESTRING', '0:00'))
            
            # Check if play is within segment time bounds
            # Segment runs from start_time (higher) to end_time (lower) in game clock
            # So we want plays where end_time <= play_time <= start_time
            
            if play_quarter == segment.start_quarter and play_quarter == segment.end_quarter:
                # Same quarter - simple range check
                if segment.end_time <= play_time <= segment.start_time:
                    segment_plays.append(play)
            elif play_quarter == segment.start_quarter:
                # Play is in start quarter, check if before segment end
                if play_time <= segment.start_time:
                    segment_plays.append(play)
            elif play_quarter == segment.end_quarter:
                # Play is in end quarter, check if after segment start
                if play_time >= segment.end_time:
                    segment_plays.append(play)
            elif segment.start_quarter < play_quarter < segment.end_quarter:
                # Play is in a middle quarter (multi-quarter segment)
                segment_plays.append(play)
                
        return segment_plays

    def _calculate_segment_stats(self, segment: GameSegment, segment_plays: List[Dict]):
        """
        Calculates the boxscore for a single segment based on its plays.
        """
        # Initialize player boxscores for all players in the lineup
        self._initialize_player_stats(segment)

        # Store plays in segment for export
        segment.plays = segment_plays.copy()

        last_shot_was_miss = False
        shooting_team = None

        for play in segment_plays:
            event_type = play.get('EVENTMSGTYPE')
            team_abbr = play.get('PLAYER1_TEAM_ABBREVIATION')

            is_home_event = team_abbr == segment.home_lineup.team
            boxscore = segment.home_boxscore if is_home_event else segment.away_boxscore

            if event_type == MADE_SHOT:
                description = play.get('HOMEDESCRIPTION', '') or play.get('VISITORDESCRIPTION', '')
                # Check for three-pointer using multiple patterns
                is_three = '3PT' in description.upper() or '3-PT' in description.upper()

                boxscore.fga += 1
                boxscore.fgm += 1

                if is_three:
                    boxscore.fg3a += 1
                    boxscore.fg3m += 1
                    boxscore.points += 3
                else:
                    boxscore.points += 2

                # Update player stats for the shooter
                player1_id = str(play.get('PLAYER1_ID', ''))
                player_stat = segment.home_player_stats.get(player1_id) or segment.away_player_stats.get(player1_id)
                if player_stat:
                    player_stat.fga += 1
                    player_stat.fgm += 1
                    if is_three:
                        player_stat.fg3a += 1
                        player_stat.fg3m += 1
                        player_stat.points += 3
                    else:
                        player_stat.points += 2

                if play.get(ASSIST_ATTRIBUTE) and play.get('PLAYER2_TEAM_ABBREVIATION') == team_abbr:
                    boxscore.ast += 1
                    # Update player stats for the assister
                    assister_id = str(play.get(ASSIST_ATTRIBUTE))
                    assister_stat = segment.home_player_stats.get(assister_id) or segment.away_player_stats.get(assister_id)
                    if assister_stat:
                        assister_stat.ast += 1

                last_shot_was_miss = False

            elif event_type == MISSED_SHOT:
                description = play.get('HOMEDESCRIPTION', '') or play.get('VISITORDESCRIPTION', '')
                # Check for three-pointer using multiple patterns
                is_three = '3PT' in description.upper() or '3-PT' in description.upper()

                boxscore.fga += 1
                if is_three:
                    boxscore.fg3a += 1

                # Update player stats for the shooter
                player1_id = str(play.get('PLAYER1_ID', ''))
                player_stat = segment.home_player_stats.get(player1_id) or segment.away_player_stats.get(player1_id)
                if player_stat:
                    player_stat.fga += 1
                    if is_three:
                        player_stat.fg3a += 1

                if play.get('PLAYER3_ID'): # Player 3 is often the blocker
                    blocking_team_abbr = play.get('PLAYER3_TEAM_ABBREVIATION')
                    if blocking_team_abbr == segment.home_lineup.team:
                        segment.home_boxscore.blk += 1
                        # Update player stats for the blocker
                        blocker_id = str(play.get('PLAYER3_ID'))
                        blocker_stat = segment.home_player_stats.get(blocker_id)
                        if blocker_stat:
                            blocker_stat.blk += 1
                    else:
                        segment.away_boxscore.blk += 1
                        # Update player stats for the blocker
                        blocker_id = str(play.get('PLAYER3_ID'))
                        blocker_stat = segment.away_player_stats.get(blocker_id)
                        if blocker_stat:
                            blocker_stat.blk += 1

                last_shot_was_miss = True
                shooting_team = team_abbr

            elif event_type == FREE_THROW:
                boxscore.fta += 1
                description = play.get('HOMEDESCRIPTION', '') or play.get('VISITORDESCRIPTION', '')
                # Free throw is made if description does NOT contain "MISS"
                if "MISS" in description.upper():
                    # It's a miss - don't add points or ftm
                    last_shot_was_miss = True
                else:
                    # It's a make
                    boxscore.ftm += 1
                    boxscore.points += 1
                    last_shot_was_miss = False

                # Update player stats for the free throw shooter
                player1_id = str(play.get('PLAYER1_ID', ''))
                player_stat = segment.home_player_stats.get(player1_id) or segment.away_player_stats.get(player1_id)
                if player_stat:
                    player_stat.fta += 1
                    if not "MISS" in description.upper():
                        player_stat.ftm += 1
                        player_stat.points += 1

            elif event_type == REBOUND:
                rebounder_team = play.get('PLAYER1_TEAM_ABBREVIATION')
                rebounder_id = str(play.get('PLAYER1_ID', ''))

                if rebounder_team == segment.home_lineup.team:
                    if last_shot_was_miss and shooting_team == rebounder_team:
                        segment.home_boxscore.oreb += 1
                    else:
                        segment.home_boxscore.dreb += 1
                    segment.home_boxscore.treb = segment.home_boxscore.oreb + segment.home_boxscore.dreb

                    # Update player stats for rebounder
                    rebounder_stat = segment.home_player_stats.get(rebounder_id)
                    if rebounder_stat:
                        if last_shot_was_miss and shooting_team == rebounder_team:
                            rebounder_stat.oreb += 1
                        else:
                            rebounder_stat.dreb += 1
                        rebounder_stat.treb = rebounder_stat.oreb + rebounder_stat.dreb

                else:
                    if last_shot_was_miss and shooting_team == rebounder_team:
                        segment.away_boxscore.oreb += 1
                    else:
                        segment.away_boxscore.dreb += 1
                    segment.away_boxscore.treb = segment.away_boxscore.oreb + segment.away_boxscore.dreb

                    # Update player stats for rebounder
                    rebounder_stat = segment.away_player_stats.get(rebounder_id)
                    if rebounder_stat:
                        if last_shot_was_miss and shooting_team == rebounder_team:
                            rebounder_stat.oreb += 1
                        else:
                            rebounder_stat.dreb += 1
                        rebounder_stat.treb = rebounder_stat.oreb + rebounder_stat.dreb

                last_shot_was_miss = False

            elif event_type == TURNOVER:
                boxscore.tov += 1

                # Update player stats for the turnover player
                player1_id = str(play.get('PLAYER1_ID', ''))
                player_stat = segment.home_player_stats.get(player1_id) or segment.away_player_stats.get(player1_id)
                if player_stat:
                    player_stat.tov += 1

                if play.get('PLAYER2_ID'): # Player 2 is often the stealer
                    stealer_team = play.get('PLAYER2_TEAM_ABBREVIATION')
                    if stealer_team != team_abbr:
                         if stealer_team == segment.home_lineup.team:
                            segment.home_boxscore.stl += 1
                            # Update player stats for the stealer
                            stealer_id = str(play.get('PLAYER2_ID'))
                            stealer_stat = segment.home_player_stats.get(stealer_id)
                            if stealer_stat:
                                stealer_stat.stl += 1
                         else:
                            segment.away_boxscore.stl += 1
                            # Update player stats for the stealer
                            stealer_id = str(play.get('PLAYER2_ID'))
                            stealer_stat = segment.away_player_stats.get(stealer_id)
                            if stealer_stat:
                                stealer_stat.stl += 1

            elif event_type == FOUL:
                boxscore.pf += 1

                # Update player stats for the fouled player
                player1_id = str(play.get('PLAYER1_ID', ''))
                player_stat = segment.home_player_stats.get(player1_id) or segment.away_player_stats.get(player1_id)
                if player_stat:
                    player_stat.pf += 1

        # Calculate Plus/Minus at the end of the segment
        home_points = segment.home_boxscore.points
        away_points = segment.away_boxscore.points
        segment.home_boxscore.plus_minus = home_points - away_points
        segment.away_boxscore.plus_minus = away_points - home_points
        
        # Update duration for both boxscores
        duration = segment.duration_seconds
        segment.home_boxscore.duration_seconds = duration
        segment.away_boxscore.duration_seconds = duration

        # Update duration for all player boxscores
        for player_stat in segment.home_player_stats.values():
            player_stat.duration_seconds = duration
        for player_stat in segment.away_player_stats.values():
            player_stat.duration_seconds = duration

        # Estimate possessions for each team (team-level estimate)
        # Possessions ≈ FGA + 0.44 × FTA + TOV − OREB
        def _est(box):
            return max(0, int(round(box.fga + 0.44 * box.fta + box.tov - box.oreb)))

        home_poss = _est(segment.home_boxscore)
        away_poss = _est(segment.away_boxscore)
        segment.home_boxscore.possessions = home_poss
        segment.away_boxscore.possessions = away_poss

        # Compute offensive/defensive ratings (per 100 possessions)
        # ORtg = (Team Points / Team Possessions) * 100
        # DRtg = (Opponent Points / Opponent Possessions) * 100
        segment.home_boxscore.offensive_rating = (home_points * 100.0 / home_poss) if home_poss > 0 else 0.0
        segment.away_boxscore.offensive_rating = (away_points * 100.0 / away_poss) if away_poss > 0 else 0.0

        segment.home_boxscore.defensive_rating = (away_points * 100.0 / away_poss) if away_poss > 0 else 0.0
        segment.away_boxscore.defensive_rating = (home_points * 100.0 / home_poss) if home_poss > 0 else 0.0
        
    def _initialize_player_stats(self, segment: GameSegment):
        """Create PlayerBoxScore for each player in the lineup."""
        for player in segment.home_lineup.players:
            segment.home_player_stats[player.player_id] = PlayerBoxScore(
                player_id=player.player_id,
                player_name=player.name,
                team=player.team
            )

        for player in segment.away_lineup.players:
            segment.away_player_stats[player.player_id] = PlayerBoxScore(
                player_id=player.player_id,
                player_name=player.name,
                team=player.team
            )

    def _parse_time_to_seconds(self, time_str: str) -> float:
        """
        Converts a 'MM:SS' time string to total seconds remaining in the quarter.
        """
        if not time_str:
            return 0.0
        try:
            minutes, seconds = map(int, time_str.split(':'))
            return float(minutes * 60 + seconds)
        except ValueError:
            return 0.0
