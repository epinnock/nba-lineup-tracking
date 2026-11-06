from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import pandas as pd

from models.game_segment import GameSegment
from models.lineup import Lineup, Player


@dataclass(frozen=True)
class RotationTeamInfo:
    """Metadata describing how GameRotation labeled a team."""
    team_id: int
    team_city: str
    team_name: str
    team_abbr: str  # e.g. "SAS", "OKC"
    rotation_resultset_name: str  # "AwayTeam" or "HomeTeam"


def fetch_gamerotation_payload(
    game_id: str,
    *,
    timeout: int = 60,
    **_ignored: Any,
) -> Dict[str, Any]:
    """
    Fetch GameRotation payload using nba_api.

    NOTE:
    - This function intentionally does NOT use any on-disk cache. The user explicitly
      requested we avoid stale cached rotation JSON and rely on the endpoint.

    Returns the nba_api `get_dict()` payload (resource/parameters/resultSets).
    """
    # Import here to avoid requiring nba_api at module import time for tests.
    from nba_api.stats.endpoints import gamerotation  # type: ignore

    gr = gamerotation.GameRotation(game_id=game_id, timeout=timeout)
    return gr.get_dict()


def _resultsets_by_name(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    rs = payload.get("resultSets") or []
    out: Dict[str, Dict[str, Any]] = {}
    for r in rs:
        if isinstance(r, dict) and "name" in r:
            out[str(r["name"])] = r
    return out


def _rs_to_df(rs: Dict[str, Any]) -> pd.DataFrame:
    headers = rs.get("headers") or []
    rows = rs.get("rowSet") or []
    return pd.DataFrame(rows, columns=headers)


def _team_abbr_from_team_id(team_id: int) -> str:
    """
    Best-effort mapping from TEAM_ID -> abbreviation using nba_api static teams.

    Falls back to numeric id if mapping isn't available.
    """
    try:
        from nba_api.stats.static import teams  # type: ignore

        found = teams.find_team_name_by_id(team_id)
        if found and found.get("abbreviation"):
            return str(found["abbreviation"])
    except Exception:
        pass
    return str(team_id)


def _fmt_player_name(first: Any, last: Any) -> str:
    f = str(first or "").strip()
    l = str(last or "").strip()
    name = f"{f} {l}".strip()
    return name or "Unknown"


def _time_ds_to_period_and_remaining_seconds(t_ds: float) -> Tuple[int, float]:
    """
    Convert deciseconds-from-game-start into:
      (period_number starting at 1, seconds_remaining_in_period)

    Regulation assumption: 12-minute periods.

    Important boundary rule:
    - If `t_ds` is exactly on a quarter boundary (e.g. 7200, 14400, ...),
      that timestamp represents the *end* of the previous period (00:00 remaining),
      not the start of the next one.
    """
    t_ds_i = int(round(float(t_ds)))

    # Clamp negatives to game start.
    if t_ds_i <= 0:
        return 1, 720.0

    # 12 minutes = 720 seconds = 7200 deciseconds
    quarter_len_ds = 7200

    # Exact boundary (end of a period): 00:00 remaining in that period.
    if t_ds_i % quarter_len_ds == 0:
        period = t_ds_i // quarter_len_ds
        return int(period), 0.0

    period = (t_ds_i // quarter_len_ds) + 1
    in_period_ds = t_ds_i % quarter_len_ds
    remaining_ds = quarter_len_ds - in_period_ds
    return int(period), remaining_ds / 10.0


def _elapsed_ds_from_period_remaining(period: int, remaining_s: float) -> int:
    """
    Convert (period, seconds remaining in that period) into elapsed deciseconds since
    game start.

    Regulation assumption: 12-minute periods (720s).

    Examples:
      - (1, 720) -> 0
      - (1, 0)   -> 7200
      - (2, 720) -> 7200
      - (2, 0)   -> 14400
    """
    p = int(period)
    rem = float(remaining_s)
    rem = max(0.0, min(720.0, rem))
    elapsed_s = (p - 1) * 720.0 + (720.0 - rem)
    return int(round(elapsed_s * 10.0))


def _active_players_at_time(
    team_df: pd.DataFrame,
    *,
    t_probe_ds: float,
) -> pd.DataFrame:
    """
    Return the active 5 players at a probe time using half-open intervals:
      IN_TIME_REAL <= t < OUT_TIME_REAL

    Using a probe time (typically the midpoint of the segment interval) avoids
    boundary ambiguity when a player sub out/in happens at exactly t.
    """
    t = float(t_probe_ds)
    return team_df[(team_df["IN_TIME_REAL"] <= t) & (team_df["OUT_TIME_REAL"] > t)].copy()


@dataclass
class RotationLineupResolver:
    away_team: RotationTeamInfo
    home_team: RotationTeamInfo
    away_df: pd.DataFrame
    home_df: pd.DataFrame
    away_players: Dict[int, Tuple[str, str]]
    home_players: Dict[int, Tuple[str, str]]

    @classmethod
    def from_payload(cls, rotation_payload: Dict[str, Any]) -> "RotationLineupResolver":
        rs_by_name = _resultsets_by_name(rotation_payload)
        if "AwayTeam" not in rs_by_name or "HomeTeam" not in rs_by_name:
            raise ValueError("GameRotation payload missing expected resultSets: AwayTeam/HomeTeam")

        away_df = _rs_to_df(rs_by_name["AwayTeam"])
        home_df = _rs_to_df(rs_by_name["HomeTeam"])

        for df in (away_df, home_df):
            for c in ["TEAM_ID", "PERSON_ID", "IN_TIME_REAL", "OUT_TIME_REAL"]:
                if c not in df.columns:
                    raise ValueError(f"GameRotation dataframe missing column: {c}")

            df["TEAM_ID"] = pd.to_numeric(df["TEAM_ID"], errors="coerce")
            df["PERSON_ID"] = pd.to_numeric(df["PERSON_ID"], errors="coerce")
            df["IN_TIME_REAL"] = pd.to_numeric(df["IN_TIME_REAL"], errors="coerce")
            df["OUT_TIME_REAL"] = pd.to_numeric(df["OUT_TIME_REAL"], errors="coerce")

        away_team_id = int(away_df["TEAM_ID"].dropna().unique()[0])
        home_team_id = int(home_df["TEAM_ID"].dropna().unique()[0])

        away_team_abbr = _team_abbr_from_team_id(away_team_id)
        home_team_abbr = _team_abbr_from_team_id(home_team_id)

        away_team = RotationTeamInfo(
            team_id=away_team_id,
            team_city=str(away_df["TEAM_CITY"].iloc[0]) if "TEAM_CITY" in away_df.columns else "",
            team_name=str(away_df["TEAM_NAME"].iloc[0]) if "TEAM_NAME" in away_df.columns else "",
            team_abbr=away_team_abbr,
            rotation_resultset_name="AwayTeam",
        )
        home_team = RotationTeamInfo(
            team_id=home_team_id,
            team_city=str(home_df["TEAM_CITY"].iloc[0]) if "TEAM_CITY" in home_df.columns else "",
            team_name=str(home_df["TEAM_NAME"].iloc[0]) if "TEAM_NAME" in home_df.columns else "",
            team_abbr=home_team_abbr,
            rotation_resultset_name="HomeTeam",
        )

        def build_player_lookup(df: pd.DataFrame) -> Dict[int, Tuple[str, str]]:
            out: Dict[int, Tuple[str, str]] = {}
            for _, r in df.iterrows():
                pid = r.get("PERSON_ID")
                if pd.isna(pid):
                    continue
                pid_i = int(pid)
                if pid_i in out:
                    continue
                first = r.get("PLAYER_FIRST")
                last = r.get("PLAYER_LAST")
                out[pid_i] = (str(first or "").strip(), str(last or "").strip())
            return out

        away_players = build_player_lookup(away_df)
        home_players = build_player_lookup(home_df)

        return cls(
            away_team=away_team,
            home_team=home_team,
            away_df=away_df,
            home_df=home_df,
            away_players=away_players,
            home_players=home_players,
        )

    def lineups_at_ds(self, t_probe_ds: float) -> Tuple[Lineup, Lineup]:
        """
        Return (home_lineup, away_lineup) at elapsed deciseconds since game start.
        """
        away_active = _active_players_at_time(self.away_df, t_probe_ds=t_probe_ds)
        home_active = _active_players_at_time(self.home_df, t_probe_ds=t_probe_ds)

        if len(away_active) != 5 or len(home_active) != 5:
            raise ValueError(
                f"Expected 5 active players per team at t={t_probe_ds}, "
                f"got away={len(away_active)} home={len(home_active)}"
            )

        away_ids = [int(x) for x in away_active["PERSON_ID"].tolist()]
        home_ids = [int(x) for x in home_active["PERSON_ID"].tolist()]

        away_lineup_players: List[Player] = []
        for pid in sorted(set(away_ids)):
            first, last = self.away_players.get(pid, ("", ""))
            away_lineup_players.append(
                Player(
                    player_id=str(pid),
                    name=_fmt_player_name(first, last),
                    team=self.away_team.team_abbr,
                )
            )

        home_lineup_players: List[Player] = []
        for pid in sorted(set(home_ids)):
            first, last = self.home_players.get(pid, ("", ""))
            home_lineup_players.append(
                Player(
                    player_id=str(pid),
                    name=_fmt_player_name(first, last),
                    team=self.home_team.team_abbr,
                )
            )

        if len(away_lineup_players) != 5 or len(home_lineup_players) != 5:
            raise ValueError("Resolved lineup did not contain exactly 5 unique players")

        return Lineup(players=home_lineup_players), Lineup(players=away_lineup_players)


def apply_gamerotation_lineups_to_segments(
    segments: List[GameSegment],
    rotation_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    For each (same-period) segment, verify/correct its lineups using GameRotation.

    This mutates the provided `segments` in-place by replacing:
      - segment.home_lineup
      - segment.away_lineup

    The goal is to ensure every exported segment is backed by the official rotation
    stints, not only the end-of-quarter edge cases.
    """
    resolver = RotationLineupResolver.from_payload(rotation_payload)

    corrected = 0
    verified = 0
    skipped_cross_period = 0
    skipped_errors = 0

    for seg in segments:
        if seg.start_quarter != seg.end_quarter:
            skipped_cross_period += 1
            continue

        try:
            t0 = _elapsed_ds_from_period_remaining(seg.start_quarter, seg.start_time)
            t1 = _elapsed_ds_from_period_remaining(seg.end_quarter, seg.end_time)

            # Segment clock counts down, so elapsed time increases.
            t_lo = min(t0, t1)
            t_hi = max(t0, t1)

            # Probe midpoint to avoid boundary ambiguity.
            t_probe = (t_lo + t_hi) / 2.0

            expected_home, expected_away = resolver.lineups_at_ds(t_probe)

            verified += 1
            if (
                seg.home_lineup.get_lineup_key() != expected_home.get_lineup_key()
                or seg.away_lineup.get_lineup_key() != expected_away.get_lineup_key()
                or seg.home_lineup.team != expected_home.team
                or seg.away_lineup.team != expected_away.team
            ):
                seg.home_lineup = expected_home
                seg.away_lineup = expected_away
                corrected += 1
        except Exception:
            skipped_errors += 1
            continue

    return {
        "rotation_home_team": resolver.home_team.__dict__,
        "rotation_away_team": resolver.away_team.__dict__,
        "segments_total": len(segments),
        "segments_verified": verified,
        "segments_corrected": corrected,
        "segments_skipped_cross_period": skipped_cross_period,
        "segments_skipped_errors": skipped_errors,
    }


def build_segments_from_gamerotation(
    game_id: str,
    rotation_payload: Dict[str, Any],
    *,
    min_duration_ds: int = 1,
    drop_micro_stints_leq_ds: int = 0,
) -> Tuple[List[GameSegment], Dict[str, Any]]:
    """
    Build `GameSegment`s from the official GameRotation stints.

    Strategy:
    - Collect all unique IN/OUT times (deciseconds) across both teams.
    - Create intervals between consecutive change times.
    - Use the interval midpoint to determine the active 5 players for each team.
    - Convert times into (period, seconds remaining) for `GameSegment`.

    Notes:
    - This produces segments that do NOT cross period boundaries because period
      boundaries (7200, 14400, 21600, 28800) are included in the change times.
    - There can be extremely short/zero-duration stints near the end of games;
      you can optionally drop them via `drop_micro_stints_leq_ds`.
    """
    resolver = RotationLineupResolver.from_payload(rotation_payload)

    # Collect change times; ensure we include start/end + quarter boundaries.
    times: List[int] = []
    for df in (resolver.away_df, resolver.home_df):
        times.extend([int(round(x)) for x in df["IN_TIME_REAL"].dropna().tolist()])
        times.extend([int(round(x)) for x in df["OUT_TIME_REAL"].dropna().tolist()])

    # Add regulation boundaries explicitly.
    for t in (0, 7200, 14400, 21600, 28800):
        times.append(t)

    change_times = sorted(set(t for t in times if 0 <= t <= 28800))

    segments: List[GameSegment] = []
    seg_id = 0

    for t0, t1 in zip(change_times, change_times[1:]):
        dur = t1 - t0
        if dur < min_duration_ds:
            continue
        if drop_micro_stints_leq_ds > 0 and dur <= drop_micro_stints_leq_ds:
            continue

        # Probe at midpoint to avoid edge ambiguities.
        t_probe = (t0 + t1) / 2.0

        try:
            home_lineup, away_lineup = resolver.lineups_at_ds(t_probe)
        except Exception:
            continue

        start_period, start_remaining_s = _time_ds_to_period_and_remaining_seconds(t0)
        end_period, end_remaining_s = _time_ds_to_period_and_remaining_seconds(t1)

        # Because we force boundaries, we expect segments to be within a single period.
        if start_period != end_period:
            # As a safety fallback: skip cross-period segments (should not occur).
            continue

        seg_id += 1
        segment = GameSegment(
            game_id=game_id,
            segment_id=seg_id,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            start_quarter=start_period,
            end_quarter=end_period,
            start_time=start_remaining_s,
            end_time=end_remaining_s,
        )
        segments.append(segment)

    meta = {
        "away_team": resolver.away_team.__dict__,
        "home_team": resolver.home_team.__dict__,
        "change_times_count": len(change_times),
        "segment_count": len(segments),
        "notes": {
            "timebase": "IN_TIME_REAL/OUT_TIME_REAL are deciseconds since game start (0..28800 in regulation)",
            "probe_strategy": "midpoint probe time per interval",
            "dropped_cross_period_segments": True,
        },
    }
    return segments, meta