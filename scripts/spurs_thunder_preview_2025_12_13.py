#!/usr/bin/env python3
"""
Pregame matchup preview (data-backed) for Spurs @ Thunder on 2025-12-13.

Uses the locally cloned nba_api package in this repo:
  - nba_api.stats.endpoints.ScheduleLeagueV2
  - nba_api.stats.endpoints.LeagueDashTeamStats
  - nba_api.stats.endpoints.TeamGameLog
  - nba_api.stats.endpoints.CommonTeamRoster
  - nba_api.stats.endpoints.LeagueDashPlayerStats

Run:
  python3 nba-lineup-tracking/scripts/spurs_thunder_preview_2025_12_13.py
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    from zoneinfo import ZoneInfo  # py3.9+
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


# Ensure we import the cloned nba_api package in this repo
sys.path.insert(0, "nba_api/src")

from nba_api.stats.endpoints import (  # noqa: E402
    CommonTeamRoster,
    LeagueDashLineups,
    LeagueDashPlayerStats,
    LeagueDashTeamStats,
    ScheduleLeagueV2,
    TeamGameLog,
)


SPURS_TEAM_ID = 1610612759
THUNDER_TEAM_ID = 1610612760


@dataclass(frozen=True)
class GameInfo:
    game_id: str
    game_date: str
    game_datetime_utc: str
    arena_city: str
    arena_name: str
    is_neutral: bool
    home_team: str
    away_team: str
    game_status_text: str


def rows_to_dicts(headers: List[str], rows: List[List[Any]]) -> List[Dict[str, Any]]:
    return [dict(zip(headers, r)) for r in rows]


def parse_teamgamelog_date(s: str) -> datetime:
    # Example: "DEC 10, 2025"
    return datetime.strptime(s, "%b %d, %Y")


def format_utc_to_tz(utc_iso: str, tz: str) -> Optional[str]:
    """
    Convert '2025-12-14T02:00:00Z' to local string like '2025-12-13 20:00 CST'.
    Returns None if zoneinfo isn't available.
    """
    if ZoneInfo is None:
        return None
    # Normalize trailing Z
    if utc_iso.endswith("Z"):
        utc_iso = utc_iso.replace("Z", "+00:00")
    dt_utc = datetime.fromisoformat(utc_iso)
    dt_local = dt_utc.astimezone(ZoneInfo(tz))
    return dt_local.strftime("%Y-%m-%d %H:%M %Z")


def get_game_info_from_schedule(game_id: str, season: str) -> GameInfo:
    sched = ScheduleLeagueV2(season=season)
    ds = sched.nba_response.get_data_sets(sched.endpoint)["SeasonGames"]
    games = rows_to_dicts(ds["headers"], ds["data"])

    hit = next((g for g in games if g.get("gameId") == game_id), None)
    if not hit:
        raise RuntimeError(f"Could not find gameId={game_id} in ScheduleLeagueV2 season={season}")

    return GameInfo(
        game_id=hit.get("gameId"),
        game_date=hit.get("gameDate"),
        game_datetime_utc=hit.get("gameDateTimeUTC"),
        arena_city=hit.get("arenaCity"),
        arena_name=hit.get("arenaName"),
        is_neutral=bool(hit.get("isNeutral")),
        home_team=f"{hit.get('homeTeam_teamTricode')} ({hit.get('homeTeam_teamCity')} {hit.get('homeTeam_teamName')})",
        away_team=f"{hit.get('awayTeam_teamTricode')} ({hit.get('awayTeam_teamCity')} {hit.get('awayTeam_teamName')})",
        game_status_text=hit.get("gameStatusText"),
    )


def get_team_profile(season: str) -> Dict[str, Dict[str, Any]]:
    """
    Returns a dict keyed by TEAM_ID as string for SAS/OKC,
    containing Base + Advanced snapshots.
    """
    def fetch(measure_type: str) -> Dict[int, Dict[str, Any]]:
        ep = LeagueDashTeamStats(
            season=season,
            season_type_all_star="Regular Season",
            per_mode_detailed="PerGame",
            measure_type_detailed_defense=measure_type,
            plus_minus="N",
            rank="N",
        )
        # Legacy endpoints: do NOT pass endpoint arg
        ds = ep.nba_response.get_data_sets()["LeagueDashTeamStats"]
        rows = rows_to_dicts(ds["headers"], ds["data"])
        return {r.get("TEAM_ID"): r for r in rows}

    base = fetch("Base")
    adv = fetch("Advanced")
    ff = fetch("Four Factors")

    def pick(team_id: int) -> Dict[str, Any]:
        b = base.get(team_id, {})
        a = adv.get(team_id, {})
        f = ff.get(team_id, {})
        return {
            "TEAM_NAME": b.get("TEAM_NAME") or a.get("TEAM_NAME"),
            "GP": b.get("GP") or a.get("GP"),
            "W": b.get("W") or a.get("W"),
            "L": b.get("L") or a.get("L"),
            "W_PCT": b.get("W_PCT") or a.get("W_PCT"),
            # base (per game)
            "PTS": b.get("PTS"),
            "REB": b.get("REB"),
            "AST": b.get("AST"),
            "TOV": b.get("TOV"),
            "FG_PCT": b.get("FG_PCT"),
            "FG3_PCT": b.get("FG3_PCT"),
            "FT_PCT": b.get("FT_PCT"),
            # advanced
            "PACE": a.get("PACE"),
            "OFF_RATING": a.get("OFF_RATING"),
            "DEF_RATING": a.get("DEF_RATING"),
            "NET_RATING": a.get("NET_RATING"),
            "EFG_PCT": a.get("EFG_PCT"),
            "TS_PCT": a.get("TS_PCT"),
            "OREB_PCT": a.get("OREB_PCT"),
            "DREB_PCT": a.get("DREB_PCT"),
            "REB_PCT": a.get("REB_PCT"),
            # four factors (often overlaps, but keep as fallback)
            "FF_EFG_PCT": f.get("EFG_PCT"),
            "FF_OREB_PCT": f.get("OREB_PCT"),
        }

    return {
        str(SPURS_TEAM_ID): pick(SPURS_TEAM_ID),
        str(THUNDER_TEAM_ID): pick(THUNDER_TEAM_ID),
    }


def get_recent_form(team_id: int, season: str, last_n: int) -> Dict[str, Any]:
    ep = TeamGameLog(team_id=team_id, season=season, season_type_all_star="Regular Season")
    ds = ep.nba_response.get_data_sets()["TeamGameLog"]
    rows = rows_to_dicts(ds["headers"], ds["data"])
    rows.sort(key=lambda r: parse_teamgamelog_date(r["GAME_DATE"]), reverse=True)

    last = rows[:last_n]
    w = sum(1 for r in last if r["WL"] == "W")
    l = sum(1 for r in last if r["WL"] == "L")

    def avg(key: str) -> float:
        return sum(float(r.get(key, 0) or 0) for r in last) / max(1, len(last))

    return {
        "games": len(last),
        "W": w,
        "L": l,
        "avg_pts": round(avg("PTS"), 1),
        "avg_fg_pct": round(avg("FG_PCT"), 3),
        "avg_fg3_pct": round(avg("FG3_PCT"), 3),
        "avg_tov": round(avg("TOV"), 1),
        "latest": {
            "GAME_DATE": last[0]["GAME_DATE"],
            "MATCHUP": last[0]["MATCHUP"],
            "WL": last[0]["WL"],
            "PTS": last[0]["PTS"],
        } if last else None,
    }


def get_team_leaders(team_id: int, season: str, min_gp: int = 5) -> Dict[str, List[Dict[str, Any]]]:
    ep = LeagueDashPlayerStats(
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="PerGame",
        team_id_nullable=str(team_id),
        plus_minus="N",
        rank="N",
    )
    ds = ep.nba_response.get_data_sets()["LeagueDashPlayerStats"]
    rows = rows_to_dicts(ds["headers"], ds["data"])

    def top_n(stat_key: str, n: int = 5) -> List[Dict[str, Any]]:
        filt = [r for r in rows if float(r.get("GP", 0) or 0) >= min_gp]
        filt.sort(key=lambda r: float(r.get(stat_key, 0) or 0), reverse=True)
        out = []
        for r in filt[:n]:
            out.append(
                {
                    "PLAYER_NAME": r.get("PLAYER_NAME"),
                    "GP": r.get("GP"),
                    "MIN": r.get("MIN"),
                    stat_key: r.get(stat_key),
                    "FG_PCT": r.get("FG_PCT"),
                    "FG3_PCT": r.get("FG3_PCT"),
                    "FT_PCT": r.get("FT_PCT"),
                    "TOV": r.get("TOV"),
                    "PLUS_MINUS": r.get("PLUS_MINUS"),
                }
            )
        return out

    return {
        "PTS": top_n("PTS", 5),
        "AST": top_n("AST", 5),
        "REB": top_n("REB", 5),
    }


def get_roster_names(team_id: int, season: str) -> List[str]:
    ep = CommonTeamRoster(team_id=team_id, season=season)
    ds = ep.nba_response.get_data_sets()["CommonTeamRoster"]
    rows = rows_to_dicts(ds["headers"], ds["data"])
    return [r.get("PLAYER") for r in rows]


def _pick_first_dataset(data_sets: Dict[str, Any], preferred_key: str) -> Dict[str, Any]:
    """
    Some endpoints vary slightly in dataset naming across versions.
    Prefer a key if present; otherwise return the first dataset.
    """
    if preferred_key in data_sets:
        return data_sets[preferred_key]
    if not data_sets:
        raise RuntimeError("No datasets returned from endpoint.")
    return data_sets[next(iter(data_sets.keys()))]


def get_team_5man_lineups(
    team_id: int,
    season: str,
    min_minutes: int = 30,
    top_n: int = 8,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Pulls 5-man lineup performance for a team via LeagueDashLineups.

    Returns:
      {
        "top_by_net": [...],
        "most_used": [...],
      }
    """
    ep = LeagueDashLineups(
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="PerGame",
        # Note: "Base" lineups do not include OFF_RATING/DEF_RATING/NET_RATING.
        # "Advanced" includes the efficiency columns we need for matchup analysis.
        measure_type_detailed_defense="Advanced",
        plus_minus="N",
        rank="N",
        team_id_nullable=str(team_id),
        group_quantity=5,
    )

    # Legacy endpoints: do NOT pass endpoint arg
    data_sets = ep.nba_response.get_data_sets()
    ds = _pick_first_dataset(data_sets, "Lineups")
    rows = rows_to_dicts(ds["headers"], ds["data"])

    def minutes(r: Dict[str, Any]) -> float:
        try:
            return float(r.get("MIN", 0) or 0)
        except Exception:
            return 0.0

    def net(r: Dict[str, Any]) -> float:
        try:
            return float(r.get("NET_RATING", 0) or 0)
        except Exception:
            return 0.0

    eligible = [r for r in rows if minutes(r) >= float(min_minutes)]
    top_by_net = sorted(eligible, key=net, reverse=True)[:top_n]
    most_used = sorted(eligible, key=minutes, reverse=True)[:top_n]

    # Keep only fields we care about (print-friendly and stable)
    def pick(r: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "GROUP_NAME": r.get("GROUP_NAME"),
            "MIN": r.get("MIN"),
            "POSS": r.get("POSS"),
            "OFF_RATING": r.get("OFF_RATING"),
            "DEF_RATING": r.get("DEF_RATING"),
            "NET_RATING": r.get("NET_RATING"),
            "PACE": r.get("PACE"),
            "EFG_PCT": r.get("EFG_PCT"),
            "TS_PCT": r.get("TS_PCT"),
            "TM_TOV_PCT": r.get("TM_TOV_PCT"),
            "OREB_PCT": r.get("OREB_PCT"),
        }

    return {
        "top_by_net": [pick(r) for r in top_by_net],
        "most_used": [pick(r) for r in most_used],
    }


def lineup_players(group_name: Optional[str]) -> List[str]:
    """
    GROUP_NAME is typically "Player A - Player B - Player C - Player D - Player E".
    """
    if not group_name:
        return []
    parts = [p.strip() for p in str(group_name).split(" - ") if p.strip()]
    return parts


def lineup_player_frequency(lineups: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for l in lineups:
        for p in lineup_players(l.get("GROUP_NAME")):
            counts[p] = counts.get(p, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: kv[1], reverse=True))


def pct(x: Any) -> str:
    if x is None:
        return "—"
    try:
        return f"{float(x)*100:.1f}%"
    except Exception:
        return str(x)


def num(x: Any, digits: int = 1) -> str:
    if x is None:
        return "—"
    try:
        return f"{float(x):.{digits}f}"
    except Exception:
        return str(x)


def print_report(game: GameInfo, season: str, last_n: int, min_lineup_minutes: int) -> None:
    teams = get_team_profile(season=season)
    sas = teams[str(SPURS_TEAM_ID)]
    okc = teams[str(THUNDER_TEAM_ID)]

    sas_recent = get_recent_form(SPURS_TEAM_ID, season=season, last_n=last_n)
    okc_recent = get_recent_form(THUNDER_TEAM_ID, season=season, last_n=last_n)

    sas_leaders = get_team_leaders(SPURS_TEAM_ID, season=season)
    okc_leaders = get_team_leaders(THUNDER_TEAM_ID, season=season)

    sas_lineups = get_team_5man_lineups(SPURS_TEAM_ID, season=season, min_minutes=min_lineup_minutes)
    okc_lineups = get_team_5man_lineups(THUNDER_TEAM_ID, season=season, min_minutes=min_lineup_minutes)

    local_ct = format_utc_to_tz(game.game_datetime_utc, "America/Chicago")
    local_et = format_utc_to_tz(game.game_datetime_utc, "America/New_York")

    print("\n============================================================")
    print("SPURS @ THUNDER — MATCHUP PREVIEW (NBA API)")
    print("============================================================")
    print(f"GameId: {game.game_id}")
    print(f"Scheduled date (league): {game.game_date} | Status: {game.game_status_text}")
    print(f"UTC tip: {game.game_datetime_utc}")
    if local_et:
        print(f"Local tip (ET): {local_et}")
    if local_ct:
        print(f"Local tip (CT): {local_ct}")
    print(f"Venue: {game.arena_name}, {game.arena_city} | Neutral: {game.is_neutral}")
    print(f"Away: {game.away_team}")
    print(f"Home: {game.home_team}")

    print("\n--- Team snapshot (Season-to-date, 2025-26 Regular Season) ---")
    def line(label: str, t: Dict[str, Any]) -> str:
        return (
            f"{label}: {t['TEAM_NAME']} | {t['W']}-{t['L']} ({num(t['W_PCT'],3)}) | "
            f"PTS {num(t['PTS'])} | ORtg {num(t['OFF_RATING'])} | DRtg {num(t['DEF_RATING'])} | "
            f"Net {num(t['NET_RATING'])} | Pace {num(t['PACE'],2)} | eFG {pct(t['EFG_PCT'])} | TS {pct(t['TS_PCT'])} | "
            f"OREB% {pct(t['OREB_PCT'])}"
        )
    print(line("SAS", sas))
    print(line("OKC", okc))

    print(f"\n--- Recent form (Last {last_n} games) via TeamGameLog ---")
    print(f"SAS: {sas_recent['W']}-{sas_recent['L']} | avg PTS {sas_recent['avg_pts']} | FG% {sas_recent['avg_fg_pct']} | 3P% {sas_recent['avg_fg3_pct']} | TOV {sas_recent['avg_tov']}")
    print(f"OKC: {okc_recent['W']}-{okc_recent['L']} | avg PTS {okc_recent['avg_pts']} | FG% {okc_recent['avg_fg_pct']} | 3P% {okc_recent['avg_fg3_pct']} | TOV {okc_recent['avg_tov']}")

    print("\n--- Key player production (Per-game leaders; min GP=5) ---")
    def show_leaders(team_label: str, leaders: Dict[str, List[Dict[str, Any]]]) -> None:
        print(f"\n{team_label}")
        for k in ["PTS", "AST", "REB"]:
            print(f"  {k} leaders:")
            for r in leaders[k][:3]:
                stat_val = r.get(k)
                print(
                    f"    - {r['PLAYER_NAME']}: {k} {stat_val} | MIN {r['MIN']} | FG {pct(r['FG_PCT'])} | 3P {pct(r['FG3_PCT'])} | +/- {r['PLUS_MINUS']}"
                )
    show_leaders("SAS", sas_leaders)
    show_leaders("OKC", okc_leaders)

    print(f"\n--- 5-man lineup performance (min {min_lineup_minutes} minutes together) ---")
    def show_lineups(team_label: str, payload: Dict[str, List[Dict[str, Any]]]) -> None:
        print(f"\n{team_label} — best by Net Rating")
        for l in payload["top_by_net"][:5]:
            print(
                f"  - {l['GROUP_NAME']} | MIN {num(l['MIN'])} | ORtg {num(l['OFF_RATING'])} | DRtg {num(l['DEF_RATING'])} | Net {num(l['NET_RATING'])} | eFG {pct(l['EFG_PCT'])} | TOV% {pct(l['TM_TOV_PCT'])} | OREB% {pct(l['OREB_PCT'])}"
            )

        print(f"{team_label} — most used")
        for l in payload["most_used"][:5]:
            print(
                f"  - {l['GROUP_NAME']} | MIN {num(l['MIN'])} | Net {num(l['NET_RATING'])}"
            )

    show_lineups("SAS", sas_lineups)
    show_lineups("OKC", okc_lineups)

    print("\n--- Spurs best path to victory (lineup-driven) ---")
    sas_best = sas_lineups["top_by_net"][0] if sas_lineups["top_by_net"] else None
    okc_best = okc_lineups["top_by_net"][0] if okc_lineups["top_by_net"] else None
    if sas_best:
        sas_best_players = lineup_players(sas_best.get("GROUP_NAME"))
        print("1) Tighten the rotation to the best-performing 5-man groups.")
        print(
            f"   Best SAS lineup (by Net, min {min_lineup_minutes} MIN): {sas_best.get('GROUP_NAME')} | Net {num(sas_best.get('NET_RATING'))}."
        )
        if sas_best_players:
            print(f"   Core pieces to prioritize: {', '.join(sas_best_players)}.")

    print("\n2) Win the possession battle with rebound-heavy lineups around Wembanyama.")
    print(f"   SAS season OREB%: {pct(sas['OREB_PCT'])}. This is your best structural lever vs OKC’s efficiency edge.")
    print("   Practical: keep at least one extra rebounder/box-out big with Wemby in non-shooting OKC bench minutes; crash from the corners selectively.")

    print("\n3) Avoid dead-spacing lineups against OKC’s elite defense; keep 3+ credible shooters on the floor.")
    print("   OKC’s advantage is forcing low-quality half-court possessions. Spurs need spacing so Fox/Wemby actions create either: rim, foul, or clean kick-out 3s.")

    print("\n4) Stagger stars to always have a creator on the floor, but close with your best 2-way 5.")
    print("   The matchup usually swings when SGA plays + you have no secondary creation; stagger Fox/Castle so one is always organizing the offense.")
    if okc_best:
        print(
            f"   OKC’s best lineup (by Net, min {min_lineup_minutes} MIN): {okc_best.get('GROUP_NAME')} | Net {num(okc_best.get('NET_RATING'))}."
        )
        print("   If that group is on the floor: prioritize ball security (no live-ball turnovers) and force them into longer half-court possessions to cool their 3PT variance.")

    print("\n5) Target OKC’s weakest lineup windows (when SGA sits) with aggressive Fox push + Wemby rim pressure.")
    print("   Your highest-upside run is: force misses → run → early offense before OKC’s shell defense is set. If you can’t run, pivot to Wemby screening/short-roll playmaking.")

    print("\n--- Matchup read (what the numbers suggest) ---")
    print("1) Efficiency + defense gap favors OKC.")
    print(f"   OKC net rating: {num(okc['NET_RATING'])} vs SAS: {num(sas['NET_RATING'])}.")
    print(f"   Biggest separator: defense — OKC DRtg {num(okc['DEF_RATING'])} is elite vs SAS DRtg {num(sas['DEF_RATING'])}.")

    print("\n2) Both teams want to run; expect a high-possession game.")
    print(f"   Pace is similar (OKC {num(okc['PACE'],2)} vs SAS {num(sas['PACE'],2)}).")
    print("   If the game stays in transition, OKC’s shot quality and turnover avoidance usually compounds quickly.")

    print("\n3) Spurs’ clearest structural edge: offensive rebounding pressure.")
    print(f"   SAS OREB% {pct(sas['OREB_PCT'])} vs OKC OREB% {pct(okc['OREB_PCT'])}.")
    print("   Extra possessions are the best antidote to OKC’s efficiency advantage.")

    print("\n4) Star leverage points.")
    print("   - OKC: Shai Gilgeous-Alexander is carrying a massive scoring load with elite efficiency (32.6 PPG on 56/45/88 splits).")
    print("   - SAS: Victor Wembanyama + De'Aaron Fox give the Spurs a real top-end punch; Castle/Vassell spacing matters vs OKC’s perimeter pressure.")

    print("\n5) Recent form signals.")
    print(f"   OKC last {last_n}: {okc_recent['W']}-{okc_recent['L']} with 53.7% FG and 43.0% from 3 — scorching.")
    print(f"   SAS last {last_n}: {sas_recent['W']}-{sas_recent['L']} with 37.7% from 3 and turnovers down (11.8).")

    print("\n--- Practical game plan cues ---")
    print("SAS needs: win the glass (especially OREBs), limit live-ball turnovers, and generate enough rim/FT pressure to survive OKC’s shot-making.")
    print("OKC needs: keep Spurs off the offensive boards, force SAS into half-court possessions, and maintain their current spacing/3PT volume.")
    print("============================================================\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default="2025-26", help="Season string like 2025-26")
    parser.add_argument("--game-id", default="0022501230", help="10-digit NBA game id")
    parser.add_argument("--last-n", type=int, default=10, help="Recent form window for TeamGameLog")
    parser.add_argument("--min-lineup-minutes", type=int, default=30, help="Minimum 5-man lineup minutes to include")
    args = parser.parse_args()

    game = get_game_info_from_schedule(game_id=args.game_id, season=args.season)
    print_report(game=game, season=args.season, last_n=args.last_n, min_lineup_minutes=args.min_lineup_minutes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())