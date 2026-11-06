#!/usr/bin/env python3
"""
OKC Q1 lineup analysis (V3-only endpoints)

Goal:
- Find OKC's N worst 1st quarters (Q1) in a date window.
- For each of those games, reconstruct Q1 lineup stints using PlayByPlayV3 substitution descriptions + inferred starters.
- Summarize which OKC starting/early-Q1 lineups correlate with slow starts, and suggest how opponents can start strong.

V3 endpoints used (local nba_api clone):
- nba_api.stats.endpoints.ScoreboardV3 (discover gameIds by date)
- nba_api.stats.endpoints.BoxScoreSummaryV3 (period1Score, homeTeamId/awayTeamId)
- nba_api.stats.endpoints.BoxScoreTraditionalV3 (player list for name<->personId mapping)
- nba_api.stats.endpoints.PlayByPlayV3 (substitution descriptions + score tracking)

Run examples:
  python3 nba-lineup-tracking/scripts/okc_q1_lineup_analysis_v3.py

  # Limit window (faster)
  python3 nba-lineup-tracking/scripts/okc_q1_lineup_analysis_v3.py --start 2025-10-01 --end 2025-12-13

  # Print debug dataset headers for one gameId
  python3 nba-lineup-tracking/scripts/okc_q1_lineup_analysis_v3.py --probe-game-id 0022500055
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Ensure we import the cloned nba_api package in this repo
sys.path.insert(0, "nba_api/src")

from nba_api.stats.endpoints import (  # noqa: E402
    BoxScoreSummaryV3,
    BoxScoreTraditionalV3,
    PlayByPlayV3,
    ScoreboardV3,
)

OKC_TEAM_ID = 1610612760


def rows_to_dicts(headers: Iterable[str], rows: List[List[Any]]) -> List[Dict[str, Any]]:
    return [dict(zip(headers, r)) for r in rows]


def daterange(d0: date, d1: date) -> Iterable[date]:
    d = d0
    while d <= d1:
        yield d
        d += timedelta(days=1)


def parse_iso_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


_CLOCK_RE = re.compile(r"PT(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", re.IGNORECASE)


def clock_to_seconds(clock: Any) -> Optional[float]:
    """
    Convert various V3 clock strings into seconds remaining in the period.

    Observed / expected formats:
      - "PT11M32.00S"
      - "11:32"
      - "" / None

    Returns None if parsing fails.
    """
    if clock is None:
        return None
    s = str(clock).strip()
    if not s:
        return None

    # ISO-8601-ish duration: PT11M32.00S
    m = _CLOCK_RE.fullmatch(s)
    if m:
        mins = float(m.group(1) or 0)
        secs = float(m.group(2) or 0)
        return mins * 60.0 + secs

    # mm:ss
    if ":" in s:
        try:
            mm, ss = s.split(":")
            return float(mm) * 60.0 + float(ss)
        except Exception:
            return None

    return None


def parse_score_from_pbp_row(row: Dict[str, Any]) -> Optional[Tuple[int, int]]:
    """
    Parse V3 PlayByPlay score fields into (away, home) ints.

    PlayByPlayV3 provides `scoreHome` and `scoreAway` columns (not a single "25-30" string).
    Returns None when score is unavailable for the row.
    """
    home = row.get("scoreHome")
    away = row.get("scoreAway")
    if home is None or away is None:
        return None
    hs = str(home).strip()
    as_ = str(away).strip()
    if not hs or not as_:
        return None
    try:
        return int(as_), int(hs)
    except Exception:
        return None


def first_dataset(data_sets: Dict[str, Any]) -> Dict[str, Any]:
    if not data_sets:
        raise RuntimeError("No datasets returned from endpoint.")
    return data_sets[next(iter(data_sets.keys()))]


@dataclass(frozen=True)
class GameContext:
    game_id: str
    game_date: str
    matchup: str
    away_team_id: int
    home_team_id: int
    okc_is_home: bool
    okc_q1: int
    opp_q1: int
    q1_diff: int


def scoreboard_okc_game_ids(game_date: str) -> List[str]:
    """
    Use ScoreboardV3 LineScore rows to discover which gameIds include OKC.
    """
    ep = ScoreboardV3(game_date=game_date)
    ds = ep.nba_response.get_data_sets(ep.endpoint)

    if "LineScore" not in ds:
        return []

    ls = ds["LineScore"]
    rows = rows_to_dicts(ls["headers"], ls["data"])
    game_ids = sorted({r["gameId"] for r in rows if int(r.get("teamId", -1)) == OKC_TEAM_ID})
    return game_ids


def game_q1_context(game_id: str, game_date: str) -> Optional[GameContext]:
    """
    Use BoxScoreSummaryV3 to get home/away, and Q1 points (period1Score).
    """
    ep = BoxScoreSummaryV3(game_id=game_id)
    ds = ep.nba_response.get_data_sets(ep.endpoint)

    gsum = ds["GameSummary"]
    gsum_row = dict(zip(gsum["headers"], gsum["data"][0]))
    away_id = int(gsum_row["awayTeamId"])
    home_id = int(gsum_row["homeTeamId"])

    ls = ds["LineScore"]
    rows = rows_to_dicts(ls["headers"], ls["data"])
    by_id = {int(r["teamId"]): r for r in rows}

    okc_row = by_id.get(OKC_TEAM_ID)
    if not okc_row:
        return None

    opp_id = away_id if home_id == OKC_TEAM_ID else home_id
    opp_row = by_id.get(opp_id)
    if not opp_row:
        return None

    okc_q1 = int(okc_row.get("period1Score") or 0)
    opp_q1 = int(opp_row.get("period1Score") or 0)
    q1_diff = okc_q1 - opp_q1

    okc_is_home = home_id == OKC_TEAM_ID
    okc_tri = okc_row.get("teamTricode", "OKC")
    opp_tri = opp_row.get("teamTricode", "OPP")
    matchup = f"{opp_tri} @ {okc_tri}" if okc_is_home else f"{okc_tri} @ {opp_tri}"

    return GameContext(
        game_id=game_id,
        game_date=game_date,
        matchup=matchup,
        away_team_id=away_id,
        home_team_id=home_id,
        okc_is_home=okc_is_home,
        okc_q1=okc_q1,
        opp_q1=opp_q1,
        q1_diff=q1_diff,
    )


def probe_game_datasets(game_id: str) -> None:
    print(f"\n=== PROBE gameId={game_id} ===")

    b = BoxScoreTraditionalV3(game_id=game_id)
    bds = b.nba_response.get_data_sets(b.endpoint)
    print("\nBoxScoreTraditionalV3 dataset keys:", list(bds.keys()))
    for name, d in bds.items():
        headers = list(d.get("headers", []))
        rows = d.get("data", [])
        print(f"  - {name}: headers={len(headers)} rows={len(rows)}; first headers={headers[:20]}")

    # Show first 10 OKC players from boxscore (nameI + personId) for name-matching sanity
    if "PlayerStats" in bds:
        ps = bds["PlayerStats"]
        ps_rows = rows_to_dicts(ps["headers"], ps["data"])
        okc_ps = [r for r in ps_rows if int(r.get("teamId", -1)) == OKC_TEAM_ID]
        print("\nBoxScoreTraditionalV3.PlayerStats — OKC players (first 10):")
        for r in okc_ps[:10]:
            print(f"  personId={r.get('personId')} nameI={r.get('nameI')} first={r.get('firstName')} last={r.get('familyName')}")

    p = PlayByPlayV3(game_id=game_id)
    pds = p.nba_response.get_data_sets(p.endpoint)
    print("\nPlayByPlayV3 dataset keys:", list(pds.keys()))
    for name, d in pds.items():
        headers = list(d.get("headers", []))
        rows = d.get("data", [])
        print(f"  - {name}: headers={len(headers)} rows={len(rows)}; first headers={headers[:25]}")

    if "PlayByPlay" in pds:
        pbp = pds["PlayByPlay"]
        pbp_rows = rows_to_dicts(pbp["headers"], pbp["data"])

        q1 = [r for r in pbp_rows if int(r.get("period", 0) or 0) == 1]
        q1.sort(key=lambda r: int(r.get("actionNumber", r.get("actionId", 0)) or 0))

        sub_rows = [r for r in q1 if "SUB" in str(r.get("description") or "").upper()]

        print(f"\nPlayByPlayV3.PlayByPlay — Q1 rows={len(q1)}; Q1 rows containing 'SUB'={len(sub_rows)}")
        print("First 12 'SUB' rows (compact):")
        for r in sub_rows[:12]:
            compact = {
                "actionNumber": r.get("actionNumber"),
                "clock": r.get("clock"),
                "teamTricode": r.get("teamTricode"),
                "teamId": r.get("teamId"),
                "personId": r.get("personId"),
                "actionType": r.get("actionType"),
                "subType": r.get("subType"),
                "description": r.get("description"),
            }
            print(compact)

        # Also print what our parser extracts
        name_to_id, last_to_ids, _ = player_name_maps_from_traditional_v3(game_id)
        print("\nParsed substitutions (first 12 where parser succeeds):")
        hits = 0
        for r in q1:
            if not is_sub_event(r):
                continue
            desc = str(r.get("description") or "")
            parsed = parse_sub_from_description(desc)
            if not parsed:
                continue
            inn, outt = parsed
            in_id = name_to_id.get(_norm_name(inn)) or (
                (last_to_ids.get(_norm_name(inn)) or [None])[0]
            )
            out_id = name_to_id.get(_norm_name(outt)) or (
                (last_to_ids.get(_norm_name(outt)) or [None])[0]
            )
            print(
                {
                    "clock": r.get("clock"),
                    "teamTricode": r.get("teamTricode"),
                    "in": inn,
                    "out": outt,
                    "in_id": in_id,
                    "out_id": out_id,
                    "raw": desc,
                }
            )
            hits += 1
            if hits >= 12:
                break


def _norm_name(s: str) -> str:
    s = s.upper()
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def player_name_maps_from_traditional_v3(
    game_id: str,
) -> Tuple[Dict[str, int], Dict[str, List[int]], Dict[int, str]]:
    """
    Build mappings from various player name representations to personId, using
    BoxScoreTraditionalV3.PlayerStats.

    We also build a last-name-only index because PlayByPlayV3 substitution descriptions
    often use only the family name (e.g. "Joe", "Wallace", "Williams").

    Returns:
      (name_to_id, last_to_ids, id_to_nameI)
    """
    ep = BoxScoreTraditionalV3(game_id=game_id)
    ds = ep.nba_response.get_data_sets(ep.endpoint)

    if "PlayerStats" not in ds:
        raise RuntimeError("Expected PlayerStats dataset in BoxScoreTraditionalV3 response.")

    ps = ds["PlayerStats"]
    rows = rows_to_dicts(ps["headers"], ps["data"])

    name_to_id: Dict[str, int] = {}
    last_to_ids: Dict[str, List[int]] = {}
    id_to_namei: Dict[int, str] = {}

    for r in rows:
        pid = r.get("personId")
        if pid is None:
            continue
        pid_i = int(pid)

        first = str(r.get("firstName") or "").strip()
        last = str(r.get("familyName") or "").strip()
        name_i = str(r.get("nameI") or "").strip()

        if name_i:
            id_to_namei[pid_i] = name_i

        if last:
            last_key = _norm_name(last)
            last_to_ids.setdefault(last_key, [])
            if pid_i not in last_to_ids[last_key]:
                last_to_ids[last_key].append(pid_i)

        candidates = set()
        if first and last:
            candidates.add(f"{first} {last}")
        if name_i:
            candidates.add(name_i)
        if first and last:
            candidates.add(f"{first[:1]}. {last}")

        for c in candidates:
            key = _norm_name(c)
            if key and key not in name_to_id:
                name_to_id[key] = pid_i

    return name_to_id, last_to_ids, id_to_namei


_SUB_RE = re.compile(
    r"SUB:\s*(?P<player_in>.+?)\s+(?:ENTERS THE GAME FOR|FOR)\s+(?P<player_out>.+)$",
    re.IGNORECASE,
)

# Some feeds omit the "SUB:" prefix
_SUB_RE_2 = re.compile(
    r"(?P<player_in>.+?)\s+ENTERS THE GAME FOR\s+(?P<player_out>.+)$",
    re.IGNORECASE,
)


def parse_sub_from_description(desc: str) -> Optional[Tuple[str, str]]:
    """
    Parse substitution description into (player_in_name, player_out_name).
    """
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


def infer_okc_starting_lineup(game: GameContext, name_to_id: Dict[str, int]) -> List[int]:
    """
    Infer OKC's starting 5 from early Q1 play-by-play (before first OKC substitution).

    Rationale:
    - BoxScoreTraditionalV3.PlayerStats does not expose starter flags in this schema.
    - The first OKC substitution tells us one definite on-court player (the "out" player).
    - Before any substitution, only starters can generate events.

    Strategy:
    - Walk Q1 plays in order.
    - Record first-seen OKC personIds until the first OKC substitution.
    - If the first substitution is parsable, force-include the "out" player.
    - If still < 5, continue scanning for additional OKC players until we reach 5,
      but do NOT include "in" players from the first substitution unless needed.
    """
    _, rows = pbp_rows_v3(game.game_id)
    q1 = [r for r in rows if int(r.get("period", 0) or 0) == 1]
    q1.sort(key=lambda r: int(r.get("actionNumber", r.get("actionId", 0)) or 0))

    starters: List[int] = []
    seen = set()

    first_okc_sub_idx: Optional[int] = None
    first_okc_sub_out: Optional[int] = None

    for idx, r in enumerate(q1):
        tid = r.get("teamId")
        if tid is None:
            continue

        if int(tid) == OKC_TEAM_ID:
            pid = r.get("personId")
            if pid is not None:
                pid_i = int(pid)
                if pid_i not in seen:
                    seen.add(pid_i)
                    starters.append(pid_i)
                    if len(starters) >= 5:
                        break

            if is_sub_event(r) and first_okc_sub_idx is None:
                first_okc_sub_idx = idx
                # In observed PBP schema, personId corresponds to the player subbed OUT.
                if r.get("personId") is not None:
                    first_okc_sub_out = int(r["personId"])
                break

    # If we found an "out" player from the first substitution, ensure it's included.
    if first_okc_sub_out is not None and first_okc_sub_out not in starters:
        starters.append(first_okc_sub_out)

    # If we don't have 5 yet, keep scanning subsequent rows (still OKC events) to fill gaps.
    if len(starters) < 5:
        for r in q1[(first_okc_sub_idx or 0) :]:
            tid = r.get("teamId")
            if tid is None or int(tid) != OKC_TEAM_ID:
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

    starters = starters[:5]
    if len(starters) != 5:
        raise RuntimeError(
            f"Could not infer 5 OKC starters from PBP; got {len(starters)}. "
            "Run with --probe-game-id to inspect schema."
        )

    return starters


def pbp_rows_v3(game_id: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Returns (dataset_name, rows) for PlayByPlayV3.

    Note: PlayByPlayV3 returns both "PlayByPlay" and "AvailableVideo" datasets;
    we must explicitly select "PlayByPlay".
    """
    ep = PlayByPlayV3(game_id=game_id)
    ds = ep.nba_response.get_data_sets(ep.endpoint)

    if "PlayByPlay" in ds:
        picked = ds["PlayByPlay"]
        name = "PlayByPlay"
    else:
        picked = first_dataset(ds)
        name = next(iter(ds.keys()))

    rows = rows_to_dicts(picked["headers"], picked["data"])
    return name, rows


def is_sub_event(row: Dict[str, Any]) -> bool:
    """
    Heuristic for PlayByPlayV3 substitutions.

    In observed schemas, many non-sub events still have a `subType`, so we should NOT
    treat `subType != None` as "substitution".

    We primarily rely on description text containing "SUB:" / "SUBSTITUTION" /
    "ENTERS THE GAME FOR".
    """
    desc = str(row.get("description") or row.get("actionDescription") or "").upper()

    if "SUB:" in desc:
        return True
    if "SUBSTITUTION" in desc:
        return True
    if "ENTERS THE GAME FOR" in desc:
        return True

    return False


def _select_in_id(candidates: List[int], current_lineup: set[int]) -> Optional[int]:
    """
    If multiple players share the same last name (e.g., "Williams"), choose the one
    not currently on the floor.
    """
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    for cid in candidates:
        if cid not in current_lineup:
            return cid
    return candidates[0]


def sub_players(
    row: Dict[str, Any],
    name_to_id: Dict[str, int],
    last_to_ids: Dict[str, List[int]],
    current_lineup: set[int],
) -> Optional[Tuple[int, int, int]]:
    """
    Extract (teamId, player_in_personId, player_out_personId) from a substitution row.

    Observed schema (PlayByPlayV3):
      - substitution details appear in `description` (e.g. "SUB: Joe FOR Wallace")
      - `personId` on the row corresponds to the player being subbed OUT

    We therefore:
      - parse `in_name` from description
      - read `out_id` from `row["personId"]`
      - resolve `in_id` using full-name map first, then last-name-only index
    """
    team_id = row.get("teamId")
    if team_id is None:
        return None

    out_pid = row.get("personId")
    if out_pid is None:
        return None
    out_id = int(out_pid)

    desc = str(row.get("description") or row.get("actionDescription") or "").strip()
    parsed = parse_sub_from_description(desc)
    if not parsed:
        return None

    in_name, _out_name_unused = parsed
    in_key = _norm_name(in_name)

    in_id = name_to_id.get(in_key)
    if in_id is None:
        in_id = _select_in_id(last_to_ids.get(in_key, []), current_lineup)

    if in_id is None:
        return None

    return int(team_id), int(in_id), int(out_id)


@dataclass
class LineupStint:
    game_id: str
    game_date: str
    matchup: str
    start_clock_s: float
    end_clock_s: float
    okc_players: Tuple[int, int, int, int, int]
    okc_pts: int
    opp_pts: int

    @property
    def diff(self) -> int:
        return self.okc_pts - self.opp_pts

    @property
    def duration_s(self) -> float:
        return max(0.0, self.start_clock_s - self.end_clock_s)


def q1_stints_for_okc(game: GameContext) -> List[LineupStint]:
    """
    Reconstruct Q1 stints (V3-only):

    - Build a name->personId map from BoxScoreTraditionalV3.PlayerStats.
    - Infer starters from early Q1 PBP (since BoxScoreTraditionalV3 doesn't expose starter flags here).
    - Walk Q1 PBP in order, using `description` to parse substitutions.
    - Track score using scoreHome/scoreAway.
    """
    name_to_id, last_to_ids, _id_to_namei = player_name_maps_from_traditional_v3(game.game_id)

    starters = infer_okc_starting_lineup(game, name_to_id)
    okc_lineup = set(starters)

    _, rows = pbp_rows_v3(game.game_id)

    # Filter to Q1 plays; prefer explicit "period" key
    q1 = [r for r in rows if int(r.get("period", 0) or 0) == 1]

    # Determine ordering: actionNumber usually increases with time
    q1.sort(key=lambda r: int(r.get("actionNumber", r.get("actionId", 0)) or 0))

    # Track score progression (away, home)
    last_score: Optional[Tuple[int, int]] = None
    stint_start_clock = 12 * 60.0  # start of Q1
    stint_start_score: Tuple[int, int] = (0, 0)

    stints: List[LineupStint] = []

    def okc_opp_from_score(score: Tuple[int, int]) -> Tuple[int, int]:
        away, home = score
        okc_pts = home if game.okc_is_home else away
        opp_pts = away if game.okc_is_home else home
        return okc_pts, opp_pts

    for r in q1:
        clk = clock_to_seconds(r.get("clock") or r.get("gameClock"))
        if clk is None:
            continue

        score = parse_score_from_pbp_row(r)
        if score is not None:
            last_score = score

        if is_sub_event(r):
            sub = sub_players(r, name_to_id, last_to_ids, okc_lineup)
            if sub and sub[0] == OKC_TEAM_ID:
                # end current stint at this clock
                current = last_score or stint_start_score

                okc_pts, opp_pts = okc_opp_from_score(current)
                start_okc, start_opp = okc_opp_from_score(stint_start_score)

                stints.append(
                    LineupStint(
                        game_id=game.game_id,
                        game_date=game.game_date,
                        matchup=game.matchup,
                        start_clock_s=stint_start_clock,
                        end_clock_s=clk,
                        okc_players=tuple(sorted(okc_lineup))[:5],  # stable ordering
                        okc_pts=okc_pts - start_okc,
                        opp_pts=opp_pts - start_opp,
                    )
                )

                # apply substitution
                _, player_in, player_out = sub
                if player_out in okc_lineup:
                    okc_lineup.remove(player_out)
                okc_lineup.add(player_in)

                # reset stint start at this moment
                stint_start_clock = clk
                stint_start_score = current

    # close final stint to end of Q1 (clock==0)
    end_clk = 0.0
    final_score = last_score or stint_start_score
    okc_pts, opp_pts = okc_opp_from_score(final_score)
    start_okc, start_opp = okc_opp_from_score(stint_start_score)

    stints.append(
        LineupStint(
            game_id=game.game_id,
            game_date=game.game_date,
            matchup=game.matchup,
            start_clock_s=stint_start_clock,
            end_clock_s=end_clk,
            okc_players=tuple(sorted(okc_lineup))[:5],
            okc_pts=okc_pts - start_okc,
            opp_pts=opp_pts - start_opp,
        )
    )

    # remove ultra-short/zero stints
    stints = [s for s in stints if s.duration_s >= 1.0]
    return stints


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--team-id", type=int, default=OKC_TEAM_ID)
    parser.add_argument("--start", default="2025-10-01", help="YYYY-MM-DD")
    parser.add_argument("--end", default=date.today().strftime("%Y-%m-%d"), help="YYYY-MM-DD")
    parser.add_argument("--worst-n", type=int, default=5, help="How many worst Q1 games to analyze")
    parser.add_argument("--probe-game-id", default=None, help="If set, print dataset headers and exit")
    args = parser.parse_args()

    if args.team_id != OKC_TEAM_ID:
        raise SystemExit("This script currently supports OKC only (team_id 1610612760).")

    if args.probe_game_id:
        probe_game_datasets(args.probe_game_id)
        return 0

    start = parse_iso_date(args.start)
    end = parse_iso_date(args.end)

    # Discover OKC games in window (V3-only)
    games: List[GameContext] = []
    for d in daterange(start, end):
        game_date = d.strftime("%Y-%m-%d")
        try:
            ids = scoreboard_okc_game_ids(game_date)
        except Exception:
            continue
        for gid in ids:
            try:
                ctx = game_q1_context(gid, game_date)
            except Exception:
                ctx = None
            if ctx:
                games.append(ctx)

    if not games:
        print("No OKC games discovered in the requested date window.")
        return 0

    games.sort(key=lambda g: (g.q1_diff, g.okc_q1))
    worst = games[: args.worst_n]

    print("\nOKC — worst opening quarters (Q1) in window")
    print("Rank | Date       | Matchup        | OKC Q1 | Opp Q1 | Diff | GameId")
    print("-----+------------+----------------+--------+--------+------+----------")
    for i, g in enumerate(worst, 1):
        print(f"{i:4} | {g.game_date} | {g.matchup:<14} | {g.okc_q1:6} | {g.opp_q1:6} | {g.q1_diff:+4} | {g.game_id}")

    # Lineup stint analysis in Q1 for the worst games
    all_stints: List[LineupStint] = []
    for g in worst:
        try:
            st = q1_stints_for_okc(g)
        except Exception as e:
            print(f"\n[WARN] Could not reconstruct Q1 stints for {g.game_id} ({g.matchup}): {e}")
            continue
        all_stints.extend(st)

    if not all_stints:
        print("\nNo Q1 lineup stints reconstructed (run with --probe-game-id to inspect headers).")
        return 0

    # Aggregate by lineup (personId tuple)
    agg: Dict[Tuple[int, int, int, int, int], Dict[str, Any]] = {}
    for s in all_stints:
        k = s.okc_players
        if k not in agg:
            agg[k] = {"secs": 0.0, "okc": 0, "opp": 0, "stints": 0}
        agg[k]["secs"] += s.duration_s
        agg[k]["okc"] += s.okc_pts
        agg[k]["opp"] += s.opp_pts
        agg[k]["stints"] += 1

    rows = []
    for k, v in agg.items():
        diff = int(v["okc"]) - int(v["opp"])
        rows.append(
            {
                "lineup": k,
                "secs": v["secs"],
                "mins": v["secs"] / 60.0,
                "okc": v["okc"],
                "opp": v["opp"],
                "diff": diff,
                "stints": v["stints"],
                "net_per_36": (diff / max(1.0, v["secs"])) * (36 * 60.0),
            }
        )

    rows.sort(key=lambda r: (r["diff"], r["secs"]))  # worst diff first
    print("\nOKC Q1 lineups (from worst Q1 games) — WORST by point diff (aggregate stints)")
    print("Rank | Minutes | OKC | OPP | Diff | Net/36 | Stints | Lineup(personIds)")
    print("-----+---------+-----+-----+------+--------+--------+----------------")
    for i, r in enumerate(rows[:10], 1):
        print(
            f"{i:4} | {r['mins']:7.1f} | {r['okc']:3} | {r['opp']:3} | {r['diff']:+4} | {r['net_per_36']:6.1f} | {r['stints']:6} | {r['lineup']}"
        )

    rows.sort(key=lambda r: (-r["diff"], -r["secs"]))  # best diff first
    print("\nOKC Q1 lineups (from worst Q1 games) — BEST by point diff (aggregate stints)")
    print("Rank | Minutes | OKC | OPP | Diff | Net/36 | Stints | Lineup(personIds)")
    print("-----+---------+-----+-----+------+--------+--------+----------------")
    for i, r in enumerate(rows[:10], 1):
        print(
            f"{i:4} | {r['mins']:7.1f} | {r['okc']:3} | {r['opp']:3} | {r['diff']:+4} | {r['net_per_36']:6.1f} | {r['stints']:6} | {r['lineup']}"
        )

    print(
        "\nInterpretation note:\n"
        "- This is lineup reconstruction based on V3 play-by-play substitutions + starter inference.\n"
        "- Some games may fail reconstruction if starter flags/substitution schema differ.\n"
        "- If needed, run --probe-game-id <gameId> to see exact dataset headers for adjustments.\n"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())