from typing import List, Dict, Optional
import pandas as pd
from models.lineup import Player, Lineup
from models.game_segment import GameSegment

# NBA API Event Message Types
SUBSTITUTION_EVENT = 8
PERIOD_START_EVENT = 12
PERIOD_END_EVENT = 13

class LineupDetector:
    """
    Processes play-by-play data to detect lineups and create game segments.
    """
    def __init__(self, game_id: str, plays: List[Dict]):
        self.game_id = game_id
        self.plays = plays
        self.segments: List[GameSegment] = []
        self.current_home_lineup: Optional[Lineup] = None
        self.current_away_lineup: Optional[Lineup] = None
        self.segment_counter = 0

    def process_game(self) -> List[GameSegment]:
        """
        Main method to process the entire game and return game segments.
        """
        # First, determine the initial starting lineups.
        self._initialize_starters()

        # Keep track of the start of the current segment.
        segment_start_play = self.plays[0]

        for i, play in enumerate(self.plays):
            event_msg_type = play.get('EVENTMSGTYPE')

            if event_msg_type == SUBSTITUTION_EVENT:
                # A substitution occurred, so the current segment ends.
                self._end_current_segment(segment_start_play, play)

                # Update the lineup based on the substitution.
                self._handle_substitution(play)

                # The next segment starts with this play.
                segment_start_play = play

            elif event_msg_type == PERIOD_END_EVENT:
                # The period (quarter) ended, so this segment also ends.
                self._end_current_segment(segment_start_play, play)

                # The next segment will start with the next play (if any).
                if i + 1 < len(self.plays):
                    segment_start_play = self.plays[i + 1]

        # Ensure the last segment of the game is captured.
        if segment_start_play != self.plays[-1]:
             self._end_current_segment(segment_start_play, self.plays[-1])

        return self.segments

    def _initialize_starters(self):
        """
        Determines the starting lineups for both teams from the first few plays.
        """
        home_players = []
        away_players = []
        player_ids = set()

        for play in self.plays:
            if len(home_players) == 5 and len(away_players) == 5:
                break

            for i in range(1, 6):
                if play.get(f'PLAYER{i}_TEAM_ABBREVIATION') and play.get(f'PLAYER{i}_ID'):
                    player_id = play[f'PLAYER{i}_ID']
                    if player_id not in player_ids:
                        player = Player(
                            player_id=player_id,
                            player_name=play[f'PLAYER{i}_NAME'],
                            team_abbreviation=play[f'PLAYER{i}_TEAM_ABBREVIATION']
                        )
                        if len(home_players) < 5 and (not home_players or player.team_abbreviation == home_players[0].team_abbreviation):
                            home_players.append(player)
                            player_ids.add(player_id)
                        elif len(away_players) < 5:
                            away_players.append(player)
                            player_ids.add(player_id)

        self.current_home_lineup = Lineup(players=home_players)
        self.current_away_lineup = Lineup(players=away_players)

    def _handle_substitution(self, play: Dict):
        """
        Updates the current lineup based on a substitution event.
        """
        player_in_id = play.get('PLAYER2_ID')
        player_out_id = play.get('PLAYER1_ID')
        team_abbr = play.get('PLAYER1_TEAM_ABBREVIATION')

        if not player_in_id or not player_out_id or not team_abbr:
            return

        is_home_sub = self.current_home_lineup and team_abbr == self.current_home_lineup.team_abbreviation
        target_lineup = self.current_home_lineup if is_home_sub else self.current_away_lineup

        if not target_lineup:
            return

        # Remove the player who was subbed out.
        new_players = [p for p in target_lineup.players if p.player_id != player_out_id]

        # Add the player who was subbed in.
        new_players.append(Player(
            player_id=player_in_id,
            player_name=play.get('PLAYER2_NAME'),
            team_abbreviation=play.get('PLAYER2_TEAM_ABBREVIATION')
        ))

        if is_home_sub:
            self.current_home_lineup = Lineup(players=new_players)
        else:
            self.current_away_lineup = Lineup(players=new_players)

    def _end_current_segment(self, start_play: Dict, end_play: Dict):
        """
        Creates and stores a new GameSegment.
        """
        if not self.current_home_lineup or not self.current_away_lineup:
            return

        self.segment_counter += 1

        segment = GameSegment(
            game_id=self.game_id,
            segment_id=self.segment_counter,
            home_lineup=self.current_home_lineup,
            away_lineup=self.current_away_lineup,
            start_quarter=start_play.get('PERIOD'),
            end_quarter=end_play.get('PERIOD'),
            start_time=self._parse_time_to_seconds(start_play.get('PCTIMESTRING')),
            end_time=self._parse_time_to_seconds(end_play.get('PCTIMESTRING')),
        )
        self.segments.append(segment)

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
