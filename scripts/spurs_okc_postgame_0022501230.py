#!/usr/bin/env python3
"""
Postgame deep dive: Spurs @ Thunder (NBA Cup West Semifinal) — 2025-12-13
GameId: 0022501230

What this script does (V3-first + PBP reconstruction):
- Pulls:
  - BoxScoreSummaryV3 (quarter scores, team ids, etc.)
  - BoxScoreTraditionalV3 (player list, box score leaders)
  - PlayByPlayV3 (event timeline, substitutions, score)
- Reconstructs on-court 5-man lineups for BOTH teams from Q1 start to final horn by:
  - inferring starters from early-Q1 events until each team’s first substitution
  - applying substitutions parsed from description text (player IN) + row.personId (player OUT)
- Computes:
  - key runs (consecutive scoring without reply)
  - lead changes / ties (from scoring events)
  - 5-man lineup minutes + points for/against + net per 48
  - most-used lineups and best/worst net lineups (minimum minutes threshold)

Run:
  python3 nba-lineup-tracking/scripts/spurs_okc_postgame_0022501230.py

Output:
  nba-lineup-tracking/reports/spurs_okc_postgame_2025-12-13_game_0022501230.md

Notes / limitations:
- PlayByPlayV3 substitution descriptions sometimes include only last names. We resolve the IN player
  via name maps from BoxScoreTraditionalV3 (full name, nameI, and last-name index).
- Rare ambiguity (same last name) is handled by choosing a candidate not currently on the floor.
- This is not an official lineup-stats endpoint; it is a deterministic reconstruction from PBP.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Ensure we import the cloned nba_api package in this repo
sys.path.insert(0, "nba_api/src")

from nba_api.stats.endpoints import (  # noqa: E402
    BoxScoreSummaryV3,
    BoxScoreTraditionalV3,
    PlayByPlayV3,
)

DEFAULT_GAME_ID = "0022501230"

OUT_DIR = Path("nba-lineup-tracking/.cache")
REPORTS_DIR = Path("nba-lineup-tracking/reports")
OUT_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

_CLOCK_RE = re.compile(r"PT(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", re.IGNORECASE)

_SUB_RE = re.compile(
    r"SUB:\s*(?P<player_in>.+?)\s+(?:ENTERS THE GAME FOR|FOR)\s+(?P<player_out>.+)$",
    re.IGNORECASE,
)
_SUB_RE_2 = re.compile(
    r"(?P<player_in>.+?)\s+ENTERS THE GAME FOR\s+(?P<player_out>.+)$",
    re.IGNORECASE,
)


def rows_to_dicts(headers: Iterable[str], rows: List[List[Any]]) -> List[Dict[str, Any]]:
    return [dict(zip(headers, r)) for r in rows]


def safe_int(x: Any, default: int = 0) -> int:
    try:
        if x is None:
            return default
        s = str(x).strip()
        if s == "":
            return default
        return int(float(s))
    except Exception:
        return default


def safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        s = str(x).strip()
        if s == "":
            return default
        return float(s)
    except Exception:
        return default


def clock_to_seconds(clock: Any) -> Optional[float]:
    """
    Convert various V3 clock strings into seconds remaining in the period.

    Observed formats:
      - "PT11M32.00S"
      - "11:32"
      - "" / None
    """
    if clock is None:
        return None
    s = str(clock).strip()
    if not s:
        return None

    m = _CLOCK_RE.fullmatch(s)
    if m:
        mins = float(m.group(1) or 0)
        secs = float(m.group(2) or 0)
        return mins * 60.0 + secs

    if ":" in s:
        try:
            mm, ss = s.split(":")
            return float(mm) * 60.0 + float(ss)
        except Exception:
            return None

    return None


def absolute_elapsed_seconds(period: int, clock_s_remaining: float) -> float:
    """
    Convert (period, seconds remaining) to absolute seconds elapsed since game start.
    Assumes regulation (4x12). (No OT in this game.)
    """
    period_len = 12.0 * 60.0
    elapsed_in_period = max(0.0, period_len - clock_s_remaining)
    return (max(0, period - 1) * period_len) + elapsed_in_period


def parse_score_from_pbp_row(row: Dict[str, Any]) -> Optional[Tuple[int, int]]:
    """
    Returns (away, home)
    """
    away = row.get("scoreAway")
    home = row.get("scoreHome")
    if away is None or home is None:
        return None
    as_ = str(away).strip()
    hs = str(home).strip()
    if not as_ or not hs:
        return None
    try:
        return int(as_), int(hs)
    except Exception:
        return None


def is_sub_event(row: Dict[str, Any]) -> bool:
    desc = str(row.get("description") or row.get("actionDescription") or "").upper()
    return ("SUB:" in desc) or ("SUBSTITUTION" in desc) or ("ENTERS THE GAME FOR" in desc)


def parse_sub_from_description(desc: str) -> Optional[Tuple[str, str]]:
    if not desc:
        return None
    s = desc.strip()
    m = _SUB_RE.match(s)
    if m:
        return m.group("player_in").strip(), m.group("player_out").strip()
    m2 = _SUB_RE_2.match(s)
    if m2:
        return m2.group("player_in").strip(), m2.group("player_out").strip()
    return None


def _norm_name(s: str) -> str:
    s = s.upper()
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def dump_endpoint(ep, out_path: Path) -> Dict[str, Any]:
    ds = ep.nba_response.get_data_sets(ep.endpoint)
    payload = {k: {"headers": v.get("headers", []), "data": v.get("data", [])} for k, v in ds.items()}
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return ds


@dataclass(frozen=True)
class TeamCtx:
    team_id: int
    tricode: str
    name: str


@dataclass(frozen=True)
class GameCtx:
    game_id: str
    away: TeamCtx
    home: TeamCtx
    final_away: int
    final_home: int
    q_scores: Dict[str, List[int]]  # tricode -> [q1,q2,q3,q4]
    attendance: Optional[int]


def load_game_context(game_id: str) -> GameCtx:
    bs = BoxScoreSummaryV3(game_id=game_id)
    bs_ds = dump_endpoint(bs, OUT_DIR / f"{game_id}_boxscore_summary_v3.json")

    gsum = bs_ds["GameSummary"]
    g0 = dict(zip(gsum["headers"], gsum["data"][0]))
    away_id = int(g0["awayTeamId"])
    home_id = int(g0["homeTeamId"])

    attendance = g0.get("attendance")
    attendance_i = int(attendance) if attendance is not None else None

    ls = bs_ds["LineScore"]
    ls_rows = rows_to_dicts(ls["headers"], ls["data"])
    by_id = {int(r["teamId"]): r for r in ls_rows}

    def team_ctx(tid: int) -> TeamCtx:
        r = by_id.get(tid, {})
        tri = str(r.get("teamTricode") or tid)
        name = f"{r.get('teamCity','')} {r.get('teamName','')}".strip() or tri
        return TeamCtx(team_id=tid, tricode=tri, name=name)

    away = team_ctx(away_id)
    home = team_ctx(home_id)

    q_scores: Dict[str, List[int]] = {}
    for t in (away, home):
        r = by_id.get(t.team_id, {})
        q_scores[t.tricode] = [
            safe_int(r.get("period1Score")),
            safe_int(r.get("period2Score")),
            safe_int(r.get("period3Score")),
            safe_int(r.get("period4Score")),
        ]

    final_away = safe_int(by_id.get(away_id, {}).get("score"))
    final_home = safe_int(by_id.get(home_id, {}).get("score"))

    return GameCtx(
        game_id=game_id,
        away=away,
        home=home,
        final_away=final_away,
        final_home=final_home,
        q_scores=q_scores,
        attendance=attendance_i,
    )


def player_name_maps_from_traditional_v3(
    game_id: str,
) -> Tuple[Dict[str, int], Dict[str, List[int]], Dict[int, Dict[str, Any]]]:
    """
    Returns:
      - name_to_id: normalized candidate names -> personId
      - last_to_ids: normalized last-name -> [personId,...]
      - id_to_row: personId -> player row (for rendering names/teams)
    """
    ep = BoxScoreTraditionalV3(game_id=game_id)
    ds = dump_endpoint(ep, OUT_DIR / f"{game_id}_boxscore_traditional_v3.json")

    ps = ds["PlayerStats"]
    rows = rows_to_dicts(ps["headers"], ps["data"])

    name_to_id: Dict[str, int] = {}
    last_to_ids: Dict[str, List[int]] = {}
    id_to_row: Dict[int, Dict[str, Any]] = {}

    for r in rows:
        pid = r.get("personId")
        if pid is None:
            continue
        pid_i = int(pid)
        id_to_row[pid_i] = r

        first = str(r.get("firstName") or "").strip()
        last = str(r.get("familyName") or "").strip()
        name_i = str(r.get("nameI") or "").strip()

        if last:
            last_key = _norm_name(last)
            last_to_ids.setdefault(last_key, [])
            if pid_i not in last_to_ids[last_key]:
                last_to_ids[last_key].append(pid_i)

        candidates = set()
        if first and last:
            candidates.add(f"{first} {last}")
            candidates.add(f"{first[:1]}. {last}")
        if name_i:
            candidates.add(name_i)

        for c in candidates:
            key = _norm_name(c)
            if key and key not in name_to_id:
                name_to_id[key] = pid_i

    return name_to_id, last_to_ids, id_to_row


def pbp_rows_v3(game_id: str) -> List[Dict[str, Any]]:
    ep = PlayByPlayV3(game_id=game_id)
    ds = dump_endpoint(ep, OUT_DIR / f"{game_id}_pbp_v3.json")
    pbp = ds["PlayByPlay"]
    rows = rows_to_dicts(pbp["headers"], pbp["data"])
    rows.sort(key=lambda r: safe_int(r.get("actionNumber", r.get("actionId", 0))))
    return rows


def _select_in_id(candidates: List[int], current_lineup: set[int]) -> Optional[int]:
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    for cid in candidates:
        if cid not in current_lineup:
            return cid
    return candidates[0]


def resolve_in_player_id(
    in_name: str,
    name_to_id: Dict[str, int],
    last_to_ids: Dict[str, List[int]],
    current_lineup: set[int],
) -> Optional[int]:
    key = _norm_name(in_name)
    pid = name_to_id.get(key)
    if pid is not None:
        return int(pid)
    return _select_in_id(last_to_ids.get(key, []), current_lineup)


def infer_starting_five(
    team_id: int,
    rows: List[Dict[str, Any]],
    name_to_id: Dict[str, int],
    last_to_ids: Dict[str, List[int]],
    *,
    period: int = 1,
) -> List[int]:
    """
    Infer the 5-man unit that STARTS a given period from play-by-play until the first
    substitution by this team in that period.

    Strategy:
    - Gather first-seen personIds for team until first sub row in the period.
    - Force-include the OUT player (row.personId) from the first team substitution (still a starter).
    - If still < 5, continue scanning subsequent rows in the period for team personIds.
    """
    p_rows = [r for r in rows if safe_int(r.get("period", 0)) == period]
    starters: List[int] = []
    seen: set[int] = set()

    first_sub_idx: Optional[int] = None
    first_sub_out: Optional[int] = None

    for idx, r in enumerate(p_rows):
        if safe_int(r.get("teamId", -1)) != team_id:
            continue

        pid = r.get("personId")
        if pid is not None:
            pid_i = int(pid)
            if pid_i not in seen:
                seen.add(pid_i)
                starters.append(pid_i)
                if len(starters) >= 5:
                    return starters[:5]

        if is_sub_event(r):
            first_sub_idx = idx
            out_pid = r.get("personId")
            if out_pid is not None:
                first_sub_out = int(out_pid)
            break

    if first_sub_out is not None and first_sub_out not in starters:
        starters.append(first_sub_out)

    # Fill from post-sub events if needed
    if len(starters) < 5:
        for r in p_rows[(first_sub_idx or 0) :]:
            if safe_int(r.get("teamId", -1)) != team_id:
                continue
            pid = r.get("personId")
            if pid is None:
                continue
            pid_i = int(pid)
            if pid_i not in seen:
                seen.add(pid_i)
                starters.append(pid_i)
                if len(starters) >= 5:
                    break

    if len(starters) != 5:
        raise RuntimeError(
            f"Could not infer 5 starters for teamId={team_id} in period={period}; got {len(starters)}: {starters}"
        )

    return starters[:5]


@dataclass
class Stint:
    start_abs_s: float
    end_abs_s: float
    start_period: int
    start_clock: str
    end_period: int
    end_clock: str
    away_lineup: Tuple[int, int, int, int, int]
    home_lineup: Tuple[int, int, int, int, int]
    away_pts: int
    home_pts: int

    @property
    def duration_s(self) -> float:
        return max(0.0, self.end_abs_s - self.start_abs_s)


def reconstruct_stints(game: GameCtx) -> Tuple[List[Stint], Dict[str, Any]]:
    name_to_id, last_to_ids, id_to_row = player_name_maps_from_traditional_v3(game.game_id)
    rows = pbp_rows_v3(game.game_id)

    away_id = game.away.team_id
    home_id = game.home.team_id

    away_start = infer_starting_five(away_id, rows, name_to_id, last_to_ids, period=1)
    home_start = infer_starting_five(home_id, rows, name_to_id, last_to_ids, period=1)

    away_lineup: set[int] = set(away_start)
    home_lineup: set[int] = set(home_start)

    last_score: Optional[Tuple[int, int]] = None
    stint_start_abs = 0.0
    stint_start_period = 1
    stint_start_clock = "PT12M00.00S"
    stint_start_score = (0, 0)

    stints: List[Stint] = []
    prev_period = stint_start_period

    for r in rows:
        period = safe_int(r.get("period", 0))
        clk_s = clock_to_seconds(r.get("clock") or r.get("gameClock"))
        if period <= 0 or clk_s is None:
            continue

        # Force stint boundaries at period breaks (prevents lineups "bleeding" across quarters).
        # Also reset on-court players to the inferred period-starters, since many lineup changes
        # happen during the break without explicit "SUB:" rows.
        if period != prev_period:
            # Close the previous stint at the end of the previous period (clock==0).
            prev_end_abs = absolute_elapsed_seconds(prev_period, 0.0)
            cur_score = last_score or stint_start_score
            away_pts = cur_score[0] - stint_start_score[0]
            home_pts = cur_score[1] - stint_start_score[1]

            stints.append(
                Stint(
                    start_abs_s=stint_start_abs,
                    end_abs_s=prev_end_abs,
                    start_period=stint_start_period,
                    start_clock=stint_start_clock,
                    end_period=prev_period,
                    end_clock="PT00M00.00S",
                    away_lineup=tuple(sorted(away_lineup))[:5],
                    home_lineup=tuple(sorted(home_lineup))[:5],
                    away_pts=away_pts,
                    home_pts=home_pts,
                )
            )

            # Reset lineups to the starters for the new period.
            away_lineup = set(infer_starting_five(away_id, rows, name_to_id, last_to_ids, period=period))
            home_lineup = set(infer_starting_five(home_id, rows, name_to_id, last_to_ids, period=period))

            # Start a new stint at the beginning of the new period (clock==12:00).
            stint_start_abs = absolute_elapsed_seconds(period, 12.0 * 60.0)
            stint_start_period = period
            stint_start_clock = "PT12M00.00S"
            stint_start_score = cur_score
            prev_period = period

        score = parse_score_from_pbp_row(r)
        if score is not None:
            last_score = score

        if not is_sub_event(r):
            continue

        team_id = r.get("teamId")
        out_pid = r.get("personId")
        desc = str(r.get("description") or r.get("actionDescription") or "").strip()
        parsed = parse_sub_from_description(desc)

        if team_id is None or out_pid is None or not parsed:
            continue

        in_name, _out_name_unused = parsed
        out_id = int(out_pid)
        abs_s = absolute_elapsed_seconds(period, float(clk_s))

        # close current stint at this substitution moment
        cur_score = last_score or stint_start_score
        away_pts = cur_score[0] - stint_start_score[0]
        home_pts = cur_score[1] - stint_start_score[1]

        stints.append(
            Stint(
                start_abs_s=stint_start_abs,
                end_abs_s=abs_s,
                start_period=stint_start_period,
                start_clock=stint_start_clock,
                end_period=period,
                end_clock=str(r.get("clock") or r.get("gameClock") or ""),
                away_lineup=tuple(sorted(away_lineup))[:5],
                home_lineup=tuple(sorted(home_lineup))[:5],
                away_pts=away_pts,
                home_pts=home_pts,
            )
        )

        # apply substitution
        team_id_i = int(team_id)
        if team_id_i == away_id:
            in_id = resolve_in_player_id(in_name, name_to_id, last_to_ids, away_lineup)
            if in_id is not None:
                # Prevent shrinking the lineup when IN resolution accidentally points to a player already on-court.
                if out_id in away_lineup and in_id in away_lineup and in_id != out_id:
                    continue
                if out_id in away_lineup:
                    away_lineup.remove(out_id)
                away_lineup.add(in_id)
        elif team_id_i == home_id:
            in_id = resolve_in_player_id(in_name, name_to_id, last_to_ids, home_lineup)
            if in_id is not None:
                if out_id in home_lineup and in_id in home_lineup and in_id != out_id:
                    continue
                if out_id in home_lineup:
                    home_lineup.remove(out_id)
                home_lineup.add(in_id)

        # reset stint start
        stint_start_abs = abs_s
        stint_start_period = period
        stint_start_clock = str(r.get("clock") or r.get("gameClock") or "")
        stint_start_score = cur_score

    # close final stint to game end (48:00)
    end_abs = 48.0 * 60.0
    final_score = last_score or stint_start_score
    stints.append(
        Stint(
            start_abs_s=stint_start_abs,
            end_abs_s=end_abs,
            start_period=stint_start_period,
            start_clock=stint_start_clock,
            end_period=4,
            end_clock="PT00M00.00S",
            away_lineup=tuple(sorted(away_lineup))[:5],
            home_lineup=tuple(sorted(home_lineup))[:5],
            away_pts=final_score[0] - stint_start_score[0],
            home_pts=final_score[1] - stint_start_score[1],
        )
    )

    # Filter tiny stints
    stints = [s for s in stints if s.duration_s >= 1.0]

    meta = {
        "away_starting_five": away_start,
        "home_starting_five": home_start,
        "id_to_row": id_to_row,
    }
    return stints, meta


def name_for(pid: int, id_to_row: Dict[int, Dict[str, Any]]) -> str:
    r = id_to_row.get(pid, {})
    first = str(r.get("firstName") or "").strip()
    last = str(r.get("familyName") or "").strip()
    if first and last:
        return f"{first} {last}"
    return str(r.get("nameI") or pid)


def fmt_min(seconds: float) -> str:
    m = seconds / 60.0
    return f"{m:.1f}"


def compute_lineup_tables(
    stints: List[Stint],
    team: str,
) -> Dict[Tuple[int, int, int, int, int], Dict[str, Any]]:
    """
    team: "away" or "home"
    Returns stats keyed by 5-player tuple.
    """
    out: Dict[Tuple[int, int, int, int, int], Dict[str, Any]] = {}

    for s in stints:
        if team == "away":
            key = s.away_lineup
            pts_for = s.away_pts
            pts_against = s.home_pts
        else:
            key = s.home_lineup
            pts_for = s.home_pts
            pts_against = s.away_pts

        out.setdefault(key, {"secs": 0.0, "for": 0, "against": 0, "stints": 0})
        out[key]["secs"] += s.duration_s
        out[key]["for"] += int(pts_for)
        out[key]["against"] += int(pts_against)
        out[key]["stints"] += 1

    for k, v in out.items():
        secs = float(v["secs"])
        diff = int(v["for"]) - int(v["against"])
        v["mins"] = secs / 60.0
        v["diff"] = diff
        v["net_per_48"] = (diff / max(1.0, secs)) * (48.0 * 60.0)

    return out


@dataclass
class ScoreEvent:
    actionNumber: int
    period: int
    clock: str
    abs_s: float
    team: str
    delta: int
    away: int
    home: int
    description: str


def scoring_events(game: GameCtx) -> List[ScoreEvent]:
    rows = pbp_rows_v3(game.game_id)

    away_tri = game.away.tricode
    home_tri = game.home.tricode

    evs: List[ScoreEvent] = []
    last_score: Optional[Tuple[int, int]] = None

    for r in rows:
        period = safe_int(r.get("period", 0))
        clk_s = clock_to_seconds(r.get("clock") or r.get("gameClock"))
        if period <= 0 or clk_s is None:
            continue

        score = parse_score_from_pbp_row(r)
        if score is None:
            continue

        if last_score is None:
            last_score = score
            continue

        da = score[0] - last_score[0]
        dh = score[1] - last_score[1]
        if da == 0 and dh == 0:
            continue

        if da > 0 and dh == 0:
            team = away_tri
            delta = da
        elif dh > 0 and da == 0:
            team = home_tri
            delta = dh
        else:
            team = str(r.get("teamTricode") or "UNK")
            delta = max(da, dh)

        evs.append(
            ScoreEvent(
                actionNumber=safe_int(r.get("actionNumber", r.get("actionId", 0))),
                period=period,
                clock=str(r.get("clock") or r.get("gameClock") or ""),
                abs_s=absolute_elapsed_seconds(period, float(clk_s)),
                team=team,
                delta=int(delta),
                away=int(score[0]),
                home=int(score[1]),
                description=str(r.get("description") or r.get("actionDescription") or ""),
            )
        )
        last_score = score

    return evs


def compute_runs(game: GameCtx, evs: List[ScoreEvent]) -> List[Dict[str, Any]]:
    """
    Runs = consecutive scoring events by one team until the other team scores.
    """
    if not evs:
        return []

    away_tri = game.away.tricode
    home_tri = game.home.tricode

    runs: List[Dict[str, Any]] = []
    cur_team: Optional[str] = None
    cur_points = 0
    cur_start: Optional[ScoreEvent] = None
    cur_start_score: Optional[Tuple[int, int]] = None
    cur_actions = 0
    prev_end_score: Optional[Tuple[int, int]] = None
    prev_ev: Optional[ScoreEvent] = None

    for ev in evs:
        if cur_team is None:
            cur_team = ev.team
            cur_points = ev.delta
            cur_start = ev
            if ev.team == away_tri:
                cur_start_score = (ev.away - ev.delta, ev.home)
            elif ev.team == home_tri:
                cur_start_score = (ev.away, ev.home - ev.delta)
            else:
                cur_start_score = (ev.away, ev.home)
            cur_actions = 1
            prev_end_score = (ev.away, ev.home)
            prev_ev = ev
            continue

        if ev.team == cur_team:
            cur_points += ev.delta
            cur_actions += 1
            prev_end_score = (ev.away, ev.home)
            prev_ev = ev
            continue

        # close previous run
        runs.append(
            {
                "team": cur_team,
                "points": cur_points,
                "actions": cur_actions,
                "start": {
                    "period": cur_start.period if cur_start else None,
                    "clock": cur_start.clock if cur_start else None,
                    "score": cur_start_score,
                },
                "end": {
                    "period": prev_ev.period if prev_ev else ev.period,
                    "clock": prev_ev.clock if prev_ev else ev.clock,
                    "score": prev_end_score,
                },
            }
        )

        # start new run
        cur_team = ev.team
        cur_points = ev.delta
        cur_start = ev
        if ev.team == away_tri:
            cur_start_score = (ev.away - ev.delta, ev.home)
        elif ev.team == home_tri:
            cur_start_score = (ev.away, ev.home - ev.delta)
        else:
            cur_start_score = (ev.away, ev.home)
        cur_actions = 1
        prev_end_score = (ev.away, ev.home)
        prev_ev = ev

    # close final run
    if cur_team and cur_start and prev_end_score and prev_ev:
        runs.append(
            {
                "team": cur_team,
                "points": cur_points,
                "actions": cur_actions,
                "start": {"period": cur_start.period, "clock": cur_start.clock, "score": cur_start_score},
                "end": {"period": prev_ev.period, "clock": prev_ev.clock, "score": prev_end_score},
            }
        )

    return runs


def compute_lead_changes(game: GameCtx, evs: List[ScoreEvent]) -> Dict[str, Any]:
    """
    Count lead changes and ties by scanning scoring events.
    """
    if not evs:
        return {"ties": 0, "lead_changes": 0, "max_lead": {game.away.tricode: 0, game.home.tricode: 0}}

    away_tri = game.away.tricode
    home_tri = game.home.tricode

    ties = 0
    lead_changes = 0
    prev_sign: Optional[int] = None  # sign(home-away)
    max_home_lead = 0
    max_away_lead = 0

    for ev in evs:
        diff = ev.home - ev.away  # home lead
        if diff == 0:
            ties += 1

        if diff > 0:
            max_home_lead = max(max_home_lead, diff)
            sign = 1
        elif diff < 0:
            max_away_lead = max(max_away_lead, -diff)
            sign = -1
        else:
            sign = 0

        if prev_sign is not None:
            if sign != 0 and prev_sign != 0 and sign != prev_sign:
                lead_changes += 1
        prev_sign = sign

    return {
        "ties": ties,
        "lead_changes": lead_changes,
        "max_lead": {home_tri: max_home_lead, away_tri: max_away_lead},
    }


def md_table(headers: List[str], rows: List[List[str]]) -> str:
    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return "\\n".join(out)


def stint_at_abs_s(stints: List[Stint], abs_s: float) -> Optional[Stint]:
    """
    Return the stint covering abs_s (seconds elapsed since game start), or None.
    Interval is [start, end) except the final stint, where end==2880 can be treated as inclusive.
    """
    if abs_s < 0:
        return None
    for s in stints:
        if s.start_abs_s <= abs_s < s.end_abs_s:
            return s
    # Handle exact game end
    for s in reversed(stints):
        if abs_s == s.end_abs_s and s.end_abs_s >= 48.0 * 60.0:
            return s
    return None


def abs_s_from_period_clock(period: int, clock: str) -> Optional[float]:
    clk = clock_to_seconds(clock)
    if clk is None:
        return None
    return absolute_elapsed_seconds(period, float(clk))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-id", default=DEFAULT_GAME_ID)
    parser.add_argument("--at-abs", type=float, default=None, help="Absolute seconds elapsed since tip (0..2880).")
    parser.add_argument("--at-period", type=int, default=None, help="Period number (1..4).")
    parser.add_argument("--at-clock", default=None, help='Clock remaining in period, e.g. "PT07M56.00S" or "7:56".')
    args = parser.parse_args()

    game_id = str(args.game_id).strip()
    if not game_id:
        raise SystemExit("Missing --game-id")

    game = load_game_context(game_id)

    # Quick box score pull for top performers
    bt = BoxScoreTraditionalV3(game_id=game_id)
    bt_ds = dump_endpoint(bt, OUT_DIR / f"{game_id}_boxscore_traditional_v3.json")

    ps = bt_ds["PlayerStats"]
    ps_rows = rows_to_dicts(ps["headers"], ps["data"])

    def top_n(team_id: int, key: str, n: int = 5) -> List[Dict[str, Any]]:
        rows = [r for r in ps_rows if safe_int(r.get("teamId", -1)) == team_id and str(r.get("minutes") or "").strip()]
        rows.sort(key=lambda r: safe_float(r.get(key, 0)), reverse=True)
        out = []
        for r in rows[:n]:
            out.append(
                {
                    "name": f'{str(r.get("firstName") or "").strip()} {str(r.get("familyName") or "").strip()}'.strip()
                    or r.get("nameI"),
                    "min": r.get("minutes"),
                    "val": r.get(key),
                    "+/-": r.get("plusMinusPoints"),
                    "fg": f'{r.get("fieldGoalsMade")}-{r.get("fieldGoalsAttempted")}',
                    "3p": f'{r.get("threePointersMade")}-{r.get("threePointersAttempted")}',
                    "ft": f'{r.get("freeThrowsMade")}-{r.get("freeThrowsAttempted")}',
                    "reb": r.get("reboundsTotal"),
                    "ast": r.get("assists"),
                    "tov": r.get("turnovers"),
                }
            )
        return out

    # PBP-derived artifacts
    stints, meta = reconstruct_stints(game)
    id_to_row = meta["id_to_row"]

    # Optional query mode: print on-court players at a specific timestamp and exit.
    query_abs: Optional[float] = None
    if args.at_abs is not None:
        query_abs = float(args.at_abs)
    elif args.at_period is not None and args.at_clock is not None:
        query_abs = abs_s_from_period_clock(int(args.at_period), str(args.at_clock))
        if query_abs is None:
            raise SystemExit("Could not parse --at-clock (expected PT..M..S or mm:ss).")

    if query_abs is not None:
        s = stint_at_abs_s(stints, query_abs)
        if s is None:
            raise SystemExit(f"No stint found covering abs_s={query_abs:.1f}")

        away_names = [name_for(pid, id_to_row) for pid in s.away_lineup]
        home_names = [name_for(pid, id_to_row) for pid in s.home_lineup]

        print(f"game_id={game.game_id} abs_s={query_abs:.1f}")
        print(
            f"stint: Q{s.start_period} {s.start_clock} (abs={s.start_abs_s:.1f}) -> "
            f"Q{s.end_period} {s.end_clock} (abs={s.end_abs_s:.1f})"
        )
        print(f"{game.away.tricode} on court:", ", ".join(away_names))
        print(f"{game.home.tricode} on court:", ", ".join(home_names))
        return 0

    away_lineups = compute_lineup_tables(stints, "away")
    home_lineups = compute_lineup_tables(stints, "home")

    evs = scoring_events(game)
    runs = compute_runs(game, evs)
    lead_meta = compute_lead_changes(game, evs)

    # Sort lineups
    MIN_FILTER = 6.0  # minutes
    away_most_used = sorted(away_lineups.items(), key=lambda kv: kv[1]["secs"], reverse=True)
    home_most_used = sorted(home_lineups.items(), key=lambda kv: kv[1]["secs"], reverse=True)

    away_best = sorted(
        [(k, v) for k, v in away_lineups.items() if v["mins"] >= MIN_FILTER],
        key=lambda kv: kv[1]["net_per_48"],
        reverse=True,
    )
    away_worst = sorted(
        [(k, v) for k, v in away_lineups.items() if v["mins"] >= MIN_FILTER],
        key=lambda kv: kv[1]["net_per_48"],
    )

    home_best = sorted(
        [(k, v) for k, v in home_lineups.items() if v["mins"] >= MIN_FILTER],
        key=lambda kv: kv[1]["net_per_48"],
        reverse=True,
    )
    home_worst = sorted(
        [(k, v) for k, v in home_lineups.items() if v["mins"] >= MIN_FILTER],
        key=lambda kv: kv[1]["net_per_48"],
    )

    def render_lineup(pids: Tuple[int, int, int, int, int]) -> str:
        names = [name_for(pid, id_to_row) for pid in pids]
        return ", ".join(names)

    def render_lineup_rows(items: List[Tuple[Tuple[int, int, int, int, int], Dict[str, Any]]], top: int) -> List[List[str]]:
        rows = []
        for k, v in items[:top]:
            rows.append(
                [
                    render_lineup(k),
                    fmt_min(v["secs"]),
                    str(v["for"]),
                    str(v["against"]),
                    f'{v["diff"]:+d}',
                    f'{v["net_per_48"]:.1f}',
                    str(v["stints"]),
                ]
            )
        return rows

    # Runs: top 3 per team
    def best_runs_for(team: str, n: int = 3) -> List[Dict[str, Any]]:
        xs = [r for r in runs if r["team"] == team]
        xs.sort(key=lambda r: (r["points"], r["actions"]), reverse=True)
        return xs[:n]

    # Write report
    report_path = REPORTS_DIR / f"spurs_okc_postgame_2025-12-13_game_{game.game_id}.md"
    dt = datetime.now().astimezone().astimezone().strftime("%Y-%m-%d %H:%M %Z")

    lines: List[str] = []
    lines.append(f"# Spurs @ Thunder — Postgame deep dive (2025-12-13)\\n")
    lines.append(f"- GameId: `{game.game_id}`")
    lines.append(f"- Attendance: {game.attendance if game.attendance is not None else '—'}")
    lines.append(f"- Generated: {dt}\\n")

    lines.append("## Final score")
    lines.append(f"**{game.away.tricode} {game.final_away} — {game.home.tricode} {game.final_home}**\\n")

    qs = [
        [
            game.away.tricode,
            str(game.q_scores[game.away.tricode][0]),
            str(game.q_scores[game.away.tricode][1]),
            str(game.q_scores[game.away.tricode][2]),
            str(game.q_scores[game.away.tricode][3]),
            str(game.final_away),
        ],
        [
            game.home.tricode,
            str(game.q_scores[game.home.tricode][0]),
            str(game.q_scores[game.home.tricode][1]),
            str(game.q_scores[game.home.tricode][2]),
            str(game.q_scores[game.home.tricode][3]),
            str(game.final_home),
        ],
    ]
    lines.append(md_table(["Team", "Q1", "Q2", "Q3", "Q4", "Final"], qs))
    lines.append("")

    lines.append("## Macro game shape (from PBP)")
    lines.append(f"- Ties observed on scoring events: **{lead_meta['ties']}**")
    lines.append(f"- Lead changes (non-tie flips): **{lead_meta['lead_changes']}**")
    lines.append(
        f"- Max lead: {game.home.tricode} **+{lead_meta['max_lead'][game.home.tricode]}**, "
        f"{game.away.tricode} **+{lead_meta['max_lead'][game.away.tricode]}**\\n"
    )

    lines.append("## Key scoring runs (no-reply)")
    for team in (game.away.tricode, game.home.tricode):
        lines.append(f"### {team} biggest runs")
        rr = best_runs_for(team, 3)
        for r in rr:
            s0 = r["start"]["score"]
            s1 = r["end"]["score"]
            lines.append(
                f"- **{team} {r['points']}-0** "
                f"(Q{r['start']['period']} {r['start']['clock']} → Q{r['end']['period']} {r['end']['clock']}) "
                f"| score {game.away.tricode} {s0[0]}–{game.home.tricode} {s0[1]} → "
                f"{game.away.tricode} {s1[0]}–{game.home.tricode} {s1[1]}"
            )
        lines.append("")

    lines.append("## Box score leaders (TraditionalV3)")
    for tid, tri in [(game.away.team_id, game.away.tricode), (game.home.team_id, game.home.tricode)]:
        lines.append(f"### {tri}")
        pts = top_n(tid, "points", 5)
        rows_md = []
        for p in pts:
            rows_md.append([p["name"], str(p["val"]), str(p["min"]), p["fg"], p["3p"], p["ft"], str(p["reb"]), str(p["ast"]), str(p["tov"]), str(p["+/-"])])
        lines.append(md_table(["Player", "PTS", "MIN", "FG", "3P", "FT", "REB", "AST", "TOV", "+/-"], rows_md))
        lines.append("")

    lines.append("## Reconstructed 5-man lineup performance (from PBP subs)")
    lines.append(
        f"Minutes filter for best/worst tables: **{MIN_FILTER:.1f}** minutes (stints aggregated).\\n"
        "Net/48 is computed as (point diff / seconds played) * 48 minutes.\\n"
    )

    lines.append(f"### {game.away.tricode} — most used lineups")
    lines.append(md_table(["Lineup", "MIN", "PF", "PA", "Diff", "Net/48", "Stints"], render_lineup_rows(away_most_used, 8)))
    lines.append("")

    lines.append(f"### {game.home.tricode} — most used lineups")
    lines.append(md_table(["Lineup", "MIN", "PF", "PA", "Diff", "Net/48", "Stints"], render_lineup_rows(home_most_used, 8)))
    lines.append("")

    lines.append(f"### {game.away.tricode} — best lineups (min {MIN_FILTER:.1f} MIN)")
    lines.append(md_table(["Lineup", "MIN", "PF", "PA", "Diff", "Net/48", "Stints"], render_lineup_rows(away_best, 6)))
    lines.append("")

    lines.append(f"### {game.away.tricode} — worst lineups (min {MIN_FILTER:.1f} MIN)")
    lines.append(md_table(["Lineup", "MIN", "PF", "PA", "Diff", "Net/48", "Stints"], render_lineup_rows(away_worst, 6)))
    lines.append("")

    lines.append(f"### {game.home.tricode} — best lineups (min {MIN_FILTER:.1f} MIN)")
    lines.append(md_table(["Lineup", "MIN", "PF", "PA", "Diff", "Net/48", "Stints"], render_lineup_rows(home_best, 6)))
    lines.append("")

    lines.append(f"### {game.home.tricode} — worst lineups (min {MIN_FILTER:.1f} MIN)")
    lines.append(md_table(["Lineup", "MIN", "PF", "PA", "Diff", "Net/48", "Stints"], render_lineup_rows(home_worst, 6)))
    lines.append("")

    report_path.write_text("\\n".join(lines) + "\\n", encoding="utf-8")

    # Persist stint-level data for ad-hoc followups
    stint_path = OUT_DIR / f"{game.game_id}_reconstructed_stints.json"
    stint_path.write_text(json.dumps([s.__dict__ for s in stints], indent=2), encoding="utf-8")

    print("Wrote report:", report_path)
    print("Wrote stints:", stint_path)
    print("Total stints:", len(stints))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())