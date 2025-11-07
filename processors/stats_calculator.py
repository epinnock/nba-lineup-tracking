from typing import List, Dict
from models.game_segment import GameSegment

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
        # Find the start and end play indices for the segment to optimize search
        start_play_index = self.play_index
        end_play_index = len(self.plays)

        # Find the starting play of the segment
        for i in range(start_play_index, len(self.plays)):
            play = self.plays[i]
            if play['PERIOD'] == segment.start_quarter and self._parse_time_to_seconds(play['PCTIMESTRING']) <= segment.start_time:
                start_play_index = i
                break

        # Find the ending play of the segment
        if segment_index + 1 < len(self.segments):
            next_segment = self.segments[segment_index+1]
            for i in range(start_play_index, len(self.plays)):
                play = self.plays[i]
                if play['PERIOD'] == next_segment.start_quarter and self._parse_time_to_seconds(play['PCTIMESTRING']) == next_segment.start_time:
                    end_play_index = i
                    break

        self.play_index = end_play_index
        return self.plays[start_play_index:end_play_index]

    def _calculate_segment_stats(self, segment: GameSegment, segment_plays: List[Dict]):
        """
        Calculates the boxscore for a single segment based on its plays.
        """
        last_shot_was_miss = False
        shooting_team = None

        for play in segment_plays:
            event_type = play.get('EVENTMSGTYPE')
            team_abbr = play.get('PLAYER1_TEAM_ABBREVIATION')

            is_home_event = team_abbr == segment.home_lineup.team_abbreviation
            boxscore = segment.home_boxscore if is_home_event else segment.away_boxscore

            if event_type == MADE_SHOT:
                boxscore.fga += 1
                boxscore.fgm += 1
                description = play.get('HOMEDESCRIPTION', '') or play.get('VISITORDESCRIPTION', '')
                if "3PT" in description:
                    boxscore.fg3a += 1
                    boxscore.fg3m += 1
                    boxscore.points += 3
                else:
                    boxscore.points += 2

                if play.get(ASSIST_ATTRIBUTE) and play.get('PLAYER2_TEAM_ABBREVIATION') == team_abbr:
                    boxscore.ast += 1
                last_shot_was_miss = False

            elif event_type == MISSED_SHOT:
                boxscore.fga += 1
                description = play.get('HOMEDESCRIPTION', '') or play.get('VISITORDESCRIPTION', '')
                if "3PT" in description:
                    boxscore.fg3a += 1
                if play.get('PLAYER3_ID'): # Player 3 is often the blocker
                    blocking_team_abbr = play.get('PLAYER3_TEAM_ABBREVIATION')
                    if blocking_team_abbr == segment.home_lineup.team_abbreviation:
                        segment.home_boxscore.blk += 1
                    else:
                        segment.away_boxscore.blk += 1
                last_shot_was_miss = True
                shooting_team = team_abbr

            elif event_type == FREE_THROW:
                boxscore.fta += 1
                description = play.get('HOMEDESCRIPTION', '') or play.get('VISITORDESCRIPTION', '')
                if "MISS" not in description:
                    boxscore.ftm += 1
                    boxscore.points += 1
                last_shot_was_miss = "MISS" in description

            elif event_type == REBOUND:
                rebounder_team = play.get('PLAYER1_TEAM_ABBREVIATION')
                if rebounder_team == segment.home_lineup.team_abbreviation:
                    if last_shot_was_miss and shooting_team == rebounder_team:
                        segment.home_boxscore.oreb += 1
                    else:
                        segment.home_boxscore.dreb += 1
                else:
                    if last_shot_was_miss and shooting_team == rebounder_team:
                        segment.away_boxscore.oreb += 1
                    else:
                        segment.away_boxscore.dreb += 1
                last_shot_was_miss = False

            elif event_type == TURNOVER:
                boxscore.tov += 1
                if play.get('PLAYER2_ID'): # Player 2 is often the stealer
                    stealer_team = play.get('PLAYER2_TEAM_ABBREVIATION')
                    if stealer_team != team_abbr:
                         if stealer_team == segment.home_lineup.team_abbreviation:
                            segment.home_boxscore.stl += 1
                         else:
                            segment.away_boxscore.stl += 1

            elif event_type == FOUL:
                boxscore.pf += 1

        # Calculate Plus/Minus at the end of the segment
        home_points = segment.home_boxscore.points
        away_points = segment.away_boxscore.points
        segment.home_boxscore.plus_minus = home_points - away_points
        segment.away_boxscore.plus_minus = away_points - home_points

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
