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
        if not self.plays:
            return []
            
        # First, determine the initial starting lineups.
        self._initialize_starters()

        # Keep track of the start of the current segment.
        segment_start_play = self.plays[0]
        has_created_segment = False

        for i, play in enumerate(self.plays):
            event_msg_type = play.get('EVENTMSGTYPE')

            if event_msg_type == SUBSTITUTION_EVENT:
                # A substitution occurred, so the current segment ends.
                self._end_current_segment(segment_start_play, play)
                has_created_segment = True

                # Update the lineup based on the substitution.
                self._handle_substitution(play)

                # The next segment starts with this play.
                segment_start_play = play

            elif event_msg_type == PERIOD_END_EVENT:
                # The period (quarter) ended, so this segment also ends.
                self._end_current_segment(segment_start_play, play)
                has_created_segment = True

                # Find the first play of the next period
                current_period = play.get('PERIOD')
                segment_start_play = None
                for j in range(i + 1, len(self.plays)):
                    if self.plays[j].get('PERIOD') != current_period:
                        segment_start_play = self.plays[j]
                        break
                # If no next period found, don't start a new segment

        # Ensure the last segment of the game is captured.
        # If no segments were created (no substitutions or period ends), create one for entire game
        if not has_created_segment or (segment_start_play is not None and segment_start_play != self.plays[-1]):
             self._end_current_segment(segment_start_play, self.plays[-1])

        return self.segments

    def _initialize_starters(self):
        """
        Determines the starting lineups for both teams from the first few plays.
        Handles edge cases gracefully - creates lineups even if incomplete.
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
                            player_id=str(player_id),
                            name=play[f'PLAYER{i}_NAME'],
                            team=play[f'PLAYER{i}_TEAM_ABBREVIATION']
                        )
                        if len(home_players) < 5 and (not home_players or player.team == home_players[0].team):
                            home_players.append(player)
                            player_ids.add(player_id)
                        elif len(away_players) < 5:
                            away_players.append(player)
                            player_ids.add(player_id)

        # Try to create lineups - handle edge cases where we don't have exactly 5 players
        try:
            self.current_home_lineup = Lineup(players=home_players)
        except ValueError:
            # Invalid lineup (not 5 players) - keep as None or create mock
            self.current_home_lineup = None
            
        try:
            self.current_away_lineup = Lineup(players=away_players)
        except ValueError:
            # Invalid lineup (not 5 players) - keep as None
            self.current_away_lineup = None

    def _handle_substitution(self, play: Dict):
        """
        Updates the current lineup based on a substitution event.
        """
        player_in_id = play.get('PLAYER2_ID')
        player_out_id = play.get('PLAYER1_ID')
        team_abbr = play.get('PLAYER1_TEAM_ABBREVIATION')

        if not player_in_id or not player_out_id or not team_abbr:
            return

        is_home_sub = self.current_home_lineup and team_abbr == self.current_home_lineup.team
        target_lineup = self.current_home_lineup if is_home_sub else self.current_away_lineup

        if not target_lineup:
            return

        # Remove the player who was subbed out (converts to string for comparison).
        new_players = [p for p in target_lineup.players if p.player_id != str(player_out_id)]

        # Add the player who was subbed in.
        new_players.append(Player(
            player_id=str(player_in_id),
            name=play.get('PLAYER2_NAME'),
            team=play.get('PLAYER2_TEAM_ABBREVIATION')
        ))

        # Try to update lineup - handle edge cases
        try:
            if is_home_sub:
                self.current_home_lineup = Lineup(players=new_players)
            else:
                self.current_away_lineup = Lineup(players=new_players)
        except ValueError:
            # Invalid lineup (not exactly 5 players) - don't update
            pass

    def _end_current_segment(self, start_play: Dict, end_play: Dict):
        """
        Creates and stores a new GameSegment.
        Only creates segments if both lineups exist and have players.
        """
        if not self.current_home_lineup or not self.current_away_lineup:
            return
        
        # Also check that lineups actually have players (not just empty objects)
        if len(self.current_home_lineup.players) == 0 or len(self.current_away_lineup.players) == 0:
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
