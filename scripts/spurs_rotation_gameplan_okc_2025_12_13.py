#!/usr/bin/env python3
"""
Spurs rotation game plan vs Thunder (OKC) — Dec 13, 2025

Goal:
- Infer the Spurs' likely rotation from their most recent *completed* game
  before 2025-12-13 (minutes played).
- For each rotation player, generate a matchup-focused "what to look out for"
  checklist vs OKC using:
  - player season per-game profile (2025-26) via LeagueDashPlayerStats
  - role/archetype heuristics from those stats

Notes:
- This script relies on the local nba_api clone in this repo (nba_api/src).
- If the NBA stats response for a given endpoint is unavailable, this script
  prints a clear error and still outputs what it can.

Run:
  python3 nba-lineup-tracking/scripts/spurs_rotation_gameplan_okc_2025_12_13.py
"""

from __future__ import annotations

import datetime as dt
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

# Use local nba_api clone shipped in this repository
sys.path.insert(0, "nba_api/src")

import pandas as pd  # type: ignore

from nba_api.stats.endpoints import (
    BoxScoreTraditionalV3,
    LeagueDashPlayerStats,
    TeamGameLog,
)


SPURS_TEAM_ID = 1610612759
OKC_TEAM_ID = 1610612760

SEASON = "2025-26"
SEASON_TYPE = "Regular Season"

GAME_DATE = dt.date(2025, 12, 13)
DATE_FROM = dt.date(2025, 10, 1)
DATE_TO = GAME_DATE - dt.timedelta(days=1)


@dataclass(frozen=True)
class RotationPlayer:
    player_id: int
    player_name: str
    minutes: float


@dataclass(frozen=True)
class PlayerSeasonProfile:
    player_id: int
    player_name: str
    pts: float
    reb: float
    ast: float
    tov: float
    stl: float
    blk: float
    fg3a: float
    fg3_pct: Optional[float]
    fta: float
    ft_pct: Optional[float]


def _mmss_to_minutes(mmss: str) -> float:
    """
    Convert 'MM:SS' or 'M:SS' into float minutes.

    Returns 0.0 if parsing fails.
    """
    if not isinstance(mmss, str) or ":" not in mmss:
        return 0.0
    try:
        m_str, s_str = mmss.split(":")
        m = int(m_str)
        s = int(s_str)
        return m + (s / 60.0)
    except Exception:
        return 0.0


def _parse_minutes_v3(value) -> float:
    """
    Parse BoxScoreTraditionalV3 `minutes` field.

    Observed formats from stats feeds include:
      - 'MM:SS' (most common)
      - numeric minutes (rare)
      - ISO-ish strings like 'PT34M12.00S' (defensive fallback)

    Returns 0.0 if parsing fails.
    """
    if value is None:
        return 0.0

    # Numeric minutes
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip()
    if not s:
        return 0.0

    # 'MM:SS'
    if ":" in s:
        return _mmss_to_minutes(s)

    # 'PT34M12.00S' -> 34 + 12/60
    if s.startswith("PT") and "M" in s:
        try:
            # PT{m}M{s}S (seconds may be decimal)
            s2 = s[2:]
            m_part, rest = s2.split("M", 1)
            secs = 0.0
            if "S" in rest:
                sec_part = rest.split("S", 1)[0]
                secs = float(sec_part) if sec_part else 0.0
            mins = float(m_part) if m_part else 0.0
            return mins + (secs / 60.0)
        except Exception:
            return 0.0

    # Fallback: best-effort float
    return _safe_float(s, default=0.0)


def _safe_float(v, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def _safe_int(v, default: int = 0) -> int:
    try:
        if v is None:
            return default
        return int(v)
    except Exception:
        return default


def _fmt_pct(x: Optional[float]) -> str:
    if x is None:
        return "n/a"
    try:
        return f"{float(x) * 100:.1f}%"
    except Exception:
        return "n/a"


def _fmt_num(x: float, decimals: int = 1) -> str:
    return f"{x:.{decimals}f}"


def find_last_spurs_game_id_before(target_date: dt.date) -> Optional[str]:
    """
    Use TeamGameLog to find the most recent Spurs game before target_date.
    """
    tgl = TeamGameLog(
        team_id=SPURS_TEAM_ID,
        season=SEASON,
        season_type_all_star=SEASON_TYPE,
        date_from_nullable=DATE_FROM.strftime("%m/%d/%Y"),
        date_to_nullable=(target_date - dt.timedelta(days=1)).strftime("%m/%d/%Y"),
    )
    df = tgl.get_data_frames()[0] if tgl.get_data_frames() else pd.DataFrame()
    if df.empty:
        return None

    # GAME_DATE appears as 'YYYY-MM-DD' or similar; sort descending just in case.
    if "GAME_DATE" in df.columns:
        df = df.sort_values("GAME_DATE", ascending=False)
    first = df.iloc[0]
    return str(first.get("Game_ID") or first.get("GAME_ID") or "")


def get_rotation_from_boxscore(game_id: str) -> List[RotationPlayer]:
    """
    Infer Spurs rotation from BoxScoreTraditionalV3 minutes.
    Returns players sorted by minutes descending.

    Heuristic:
      - Use all Spurs players with minutes > 0, then take the top 10 by minutes.
      - If fewer than 10 played, return whoever played.
    """
    bs = BoxScoreTraditionalV3(game_id=game_id)
    frames = bs.get_data_frames()
    if not frames or len(frames) < 1:
        return []

    # In BoxScoreTraditionalV3, frames[0] is PlayerStats (both teams).
    player_df = frames[0]
    if player_df is None or player_df.empty:
        return []

    # V3 columns are camelCase per the endpoint expected_data/parser.
    # We filter to Spurs via teamId.
    if "teamId" not in player_df.columns or "personId" not in player_df.columns:
        return []

    spurs_df = player_df[player_df["teamId"] == SPURS_TEAM_ID].copy()
    if spurs_df.empty:
        return []

    # Build display name; fallback to nameI if present, then personId
    def _name_row(r) -> str:
        first = str(r.get("firstName") or "").strip()
        last = str(r.get("familyName") or "").strip()
        if first or last:
            return (first + " " + last).strip()
        return str(r.get("nameI") or r.get("personId") or "").strip()

    rows: List[RotationPlayer] = []
    for _, r in spurs_df.iterrows():
        pid = _safe_int(r.get("personId"))
        name = _name_row(r)
        mins = _parse_minutes_v3(r.get("minutes"))

        if pid <= 0 or not name:
            continue
        if mins <= 0:
            continue

        rows.append(RotationPlayer(player_id=pid, player_name=name, minutes=mins))

    rows.sort(key=lambda x: x.minutes, reverse=True)
    return rows[:10]


def get_player_season_profiles(player_ids: Iterable[int]) -> Dict[int, PlayerSeasonProfile]:
    """
    Fetch per-game player stats for the season and map by player_id.
    """
    ids = set(int(x) for x in player_ids if int(x) > 0)
    if not ids:
        return {}

    ldps = LeagueDashPlayerStats(
        season=SEASON,
        season_type_all_star=SEASON_TYPE,
        per_mode_detailed="PerGame",
    )
    df = ldps.get_data_frames()[0] if ldps.get_data_frames() else pd.DataFrame()
    if df.empty:
        return {}

    # Normalize columns (nba_api is mostly stable here)
    need_cols = [
        "PLAYER_ID",
        "PLAYER_NAME",
        "PTS",
        "REB",
        "AST",
        "TOV",
        "STL",
        "BLK",
        "FG3A",
        "FG3_PCT",
        "FTA",
        "FT_PCT",
    ]
    missing = [c for c in need_cols if c not in df.columns]
    if missing:
        # Fall back to best-effort if schema changes
        return {}

    out: Dict[int, PlayerSeasonProfile] = {}
    for _, r in df.iterrows():
        pid = _safe_int(r.get("PLAYER_ID"))
        if pid not in ids:
            continue

        out[pid] = PlayerSeasonProfile(
            player_id=pid,
            player_name=str(r.get("PLAYER_NAME") or "").strip(),
            pts=_safe_float(r.get("PTS")),
            reb=_safe_float(r.get("REB")),
            ast=_safe_float(r.get("AST")),
            tov=_safe_float(r.get("TOV")),
            stl=_safe_float(r.get("STL")),
            blk=_safe_float(r.get("BLK")),
            fg3a=_safe_float(r.get("FG3A")),
            fg3_pct=(None if r.get("FG3_PCT") is None else _safe_float(r.get("FG3_PCT"), default=None)),  # type: ignore[arg-type]
            fta=_safe_float(r.get("FTA")),
            ft_pct=(None if r.get("FT_PCT") is None else _safe_float(r.get("FT_PCT"), default=None)),  # type: ignore[arg-type]
        )

    return out


def classify_role(p: PlayerSeasonProfile) -> str:
    """
    Very lightweight archetype classification based on per-game counting stats.
    """
    # Big indicators
    is_rim_big = (p.blk >= 1.2) or (p.reb >= 8.5 and p.fg3a < 1.5)
    is_big = (p.reb >= 7.0) or (p.blk >= 1.0)

    # Guard/creator indicators
    is_primary_creator = (p.ast >= 6.0) or (p.pts >= 18.0 and p.ast >= 4.5)
    is_secondary_creator = (p.ast >= 4.0 and p.pts >= 12.0)

    # Spacing indicators
    is_volume_shooter = p.fg3a >= 5.5
    is_spacer = p.fg3a >= 3.5

    # Pressure indicators
    is_rim_pressure = (p.fta >= 5.5) or (p.pts >= 17.0 and p.fta >= 4.5)

    if is_rim_big and is_spacer:
        return "Stretch rim-protecting big"
    if is_rim_big:
        return "Rim-protecting big"
    if is_primary_creator:
        return "Primary creator"
    if is_secondary_creator and is_rim_pressure:
        return "Secondary creator / rim pressure"
    if is_volume_shooter:
        return "Movement/volume shooter"
    if is_spacer and is_big:
        return "Spacing big / connector"
    if is_spacer:
        return "3-and-D wing/guard"
    if is_big:
        return "Interior big / rebounder"
    return "Connector / role player"


def player_game_plan(p: PlayerSeasonProfile, role: str) -> List[str]:
    """
    Produce matchup-focused bullets: what to watch for vs OKC.
    This is role-driven (since we aren't pulling detailed matchup data here).
    """
    bullets: List[str] = []

    # General OKC notes:
    # - OKC is typically elite at forcing turnovers and shrinking gaps.
    # - They pressure the ball and load the nail, then rotate to shooters.
    # - They run after misses and punish live-ball turnovers.

    # Offensive bullets
    if "Primary creator" in role:
        bullets.append("Offense: value the ball vs OKC pressure (avoid live-ball turnovers that fuel transition).")
        bullets.append("Offense: use change-of-pace to get two feet in the paint; expect nail help—hit the first kickout.")
        bullets.append("Offense: if OKC switches, hunt a matchup you can turn the corner on (don’t settle for early-clock pull-ups).")
    elif "Secondary creator" in role:
        bullets.append("Offense: attack closeouts decisively (1–2 dribbles) and keep the ball moving—OKC recovers fast.")
        bullets.append("Offense: screen/ghost-screen actions to force a defensive decision; slip when OKC top-locks/denies.")
    elif "Movement/volume shooter" in role:
        bullets.append("Offense: keep relocating—OKC’s help is aggressive but can lose shooters on consecutive actions.")
        bullets.append("Offense: be ready for top-lock/deny; counter with back-cuts and quick re-screens into catch-and-shoot.")
    elif "3-and-D" in role or "wing" in role:
        bullets.append("Offense: punish help with catch-and-shoot readiness; no hesitation (OKC contests late but hard).")
        bullets.append("Offense: cut behind ball-watching defenders when OKC loads the paint for drives.")
    elif "Stretch" in role or "Spacing big" in role:
        bullets.append("Offense: pull OKC’s big away from the rim—spacing discipline matters (don’t drift into help lanes).")
        bullets.append("Offense: short-roll reads: catch at the nail, pivot, and hit the dunker/corner before OKC scrambles back.")
    elif "Rim-protecting big" in role or "Interior big" in role:
        bullets.append("Offense: win the offensive glass selectively; prioritize floor balance if you aren’t the designated crash.")
        bullets.append("Offense: set physical screens to free creators; re-screen when OKC fights over with pressure.")
    else:
        bullets.append("Offense: keep possessions clean—quick decisions, strong pivots, and avoid soft passes vs OKC hands.")
        bullets.append("Offense: spacing + cutting: be a constant outlet when OKC sends extra bodies to the ball.")

    # Defensive bullets (OKC-centric)
    if "Rim-protecting big" in role or "Stretch rim-protecting big" in role or "Interior big" in role:
        bullets.append("Defense: be early at the rim without over-fouling; OKC will test verticality and second jumps.")
        bullets.append("Defense: communicate in PnR—OKC’s guards will snake into mid-paint; show a body and recover.")
        bullets.append("Defense: finish the possession (box out) to avoid OKC’s late-clock second-chance points.")
    else:
        bullets.append("Defense: contain dribble penetration without reaching—OKC punishes hand-checks with fouls/FTs.")
        bullets.append("Defense: stay attached to shooters after the first pass; OKC generates corner 3s off paint touches.")
        bullets.append("Defense: transition defense priority #1 (sprint back, pick up the ball early).")

    # Personal stat cues (simple “watch this”)
    cues = []
    if p.tov >= 2.8 and ("creator" in role.lower() or "guard" in role.lower()):
        cues.append("turnovers")
    if p.fg3a >= 4.0:
        cues.append("3PA volume")
    if p.fta >= 5.0:
        cues.append("foul pressure (FTAs)")
    if p.blk >= 1.2:
        cues.append("rim protection")
    if p.reb >= 8.0:
        cues.append("rebounding")

    if cues:
        bullets.append(f"Key watch metric(s): {', '.join(cues)}.")

    return bullets


def print_report(
    game_id: str,
    rotation: List[RotationPlayer],
    profiles: Dict[int, PlayerSeasonProfile],
) -> None:
    print("# Spurs rotation game plan vs Thunder (OKC)")
    print(f"- Target game date: {GAME_DATE.isoformat()}")
    print(f"- Rotation inferred from last Spurs game before date: `{game_id}`")
    print(f"- Season profiles: {SEASON} {SEASON_TYPE}")
    print("")

    if not rotation:
        print("No rotation minutes found (box score empty or unavailable).")
        return

    print("## Likely Spurs rotation (minutes from last game)")
    for rp in rotation:
        print(f"- {rp.player_name} (id={rp.player_id}): {_fmt_num(rp.minutes)} min")
    print("")

    print("## Per-player game plan: what to look out for vs OKC")
    for rp in rotation:
        prof = profiles.get(rp.player_id)
        if prof is None:
            # Still print something actionable even if season stats aren't available
            print(f"### {rp.player_name}")
            print(f"- Likely minutes: {_fmt_num(rp.minutes)}")
            print("- Season profile: unavailable (could not fetch LeagueDashPlayerStats row).")
            print("- Watch list: protect the ball vs OKC pressure; sprint back in transition; be decisive on catches.")
            print("")
            continue

        role = classify_role(prof)
        print(f"### {prof.player_name}")
        print(f"- Likely minutes: {_fmt_num(rp.minutes)}")
        print(
            "- Season snapshot: "
            f"PTS {_fmt_num(prof.pts)}, REB {_fmt_num(prof.reb)}, AST {_fmt_num(prof.ast)}, "
            f"TOV {_fmt_num(prof.tov)}, STL {_fmt_num(prof.stl)}, BLK {_fmt_num(prof.blk)}, "
            f"3PA {_fmt_num(prof.fg3a)}, 3P% {_fmt_pct(prof.fg3_pct)}, "
            f"FTA {_fmt_num(prof.fta)}, FT% {_fmt_pct(prof.ft_pct)}"
        )
        print(f"- Role read: **{role}**")
        for b in player_game_plan(prof, role):
            print(f"- {b}")
        print("")


def main() -> int:
    game_id = find_last_spurs_game_id_before(GAME_DATE)
    if not game_id:
        print("Could not find a Spurs game before target date via TeamGameLog.")
        return 2

    rotation = get_rotation_from_boxscore(game_id)
    profiles = get_player_season_profiles([p.player_id for p in rotation])

    print_report(game_id, rotation, profiles)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())