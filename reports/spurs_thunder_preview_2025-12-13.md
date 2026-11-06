# Spurs @ Thunder — Game Preview (Dec 13, 2025)

Generated from NBA Stats API pulls on 2025-12-12/13 (America/Chicago).

## Game details
- **GameId:** 0022501230
- **Tip:** 9:00 pm ET (8:00 pm CT) — 2025-12-14T02:00:00Z
- **Venue:** T-Mobile Arena, Las Vegas (Neutral site)
- **Matchup:** San Antonio Spurs (SAS) at Oklahoma City Thunder (OKC)

## Team snapshot (2025-26 Regular Season, season-to-date)

| Team | Record | PTS | ORtg | DRtg | Net | Pace | eFG% | TS% | OREB% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SAS | 17-7 (0.708) | 120.1 | 118.6 | 114.4 | +4.2 | 100.65 | 56.4% | 60.3% | 31.2% |
| OKC | 24-1 (0.960) | 123.6 | 120.5 | 103.3 | +17.2 | 101.00 | 58.1% | 62.1% | 25.0% |

### Read
- **OKC’s edge is defense + overall efficiency** (elite DRtg 103.3 and Net +17.2).
- **Pace is similar**, so the game should be high-possession; OKC’s shot quality tends to compound quickly when the game speeds up.
- **SAS’ structural lever is extra possessions** via offensive rebounding (31.2% OREB%).

## Recent form (last 10 games)

| Team | Record | PTS | FG% | 3P% | TOV |
|---|---:|---:|---:|---:|---:|
| SAS | 7-3 | 122.7 | 47.3% | 37.7% | 11.8 |
| OKC | 10-0 | 126.3 | 53.7% | 43.0% | 12.0 |

### Read
- OKC enters on a heater (53.7% FG, 43.0% 3P in last 10). If that holds, SAS needs rebounds/FTs to keep pace.
- SAS’ encouraging sign: turnovers are controlled. Against OKC, avoiding live-ball turnovers is critical.

## Key player production (per-game leaders; min GP=5)

### Spurs
- **Victor Wembanyama:** 26.2 PTS, 12.9 REB, 4.0 AST (50.2% FG, 34.5% 3P)
- **De’Aaron Fox:** 24.0 PTS, 6.3 AST (48.6% FG, 38.8% 3P)
- **Stephon Castle:** 18.2 PTS, 7.3 AST (50.0% FG)

### Thunder
- **Shai Gilgeous-Alexander:** 32.6 PTS, 6.5 AST (56.2% FG, 45.4% 3P)
- **Chet Holmgren:** 18.8 PTS, 8.0 REB (58.1% FG, 39.5% 3P)
- **Jalen Williams:** 17.3 PTS, 6.2 AST

### Read
- OKC’s top-end driver is SGA’s combination of volume and efficiency; SAS must prevent rim/FT dominance and limit clean kickout 3s.
- SAS can hang if Fox + Wemby consistently generate “rim/FT or clean 3” outcomes before OKC’s half-court defense is set.

## 5-man lineup performance (min 30 minutes together)

### SAS — best by Net Rating
- **H. Barnes – D. Vassell – J. Champagnie – V. Wembanyama – S. Castle:** 110 MIN | ORtg 115.6 | DRtg 103.9 | **Net +11.7**

### OKC — best by Net Rating
- **S. Gilgeous-Alexander – L. Dort – C. Holmgren – J. Williams – C. Wallace:** 35 MIN | ORtg 131.3 | DRtg 86.4 | **Net +44.8**

### Read
- When OKC’s best two-way group appears, SAS’ priority becomes **ball security** and **shot quality**; you can’t donate transition.
- SAS’ best unit is stable/defensive; it can win stretches if it also wins the glass.

## OKC’s worst opening quarters (Q1) — what the data shows (2025-10-01 → 2025-12-13)

| Rank | Date | Matchup | OKC Q1 | Opp Q1 | Diff | GameId |
|---:|---|---|---:|---:|---:|---|
| 1 | 2025-11-04 | OKC @ LAC | 23 | 33 | -10 | 0022500170 |
| 2 | 2025-10-06 | OKC @ DAL | 20 | 29 | -9 | 0012500033 |
| 3 | 2025-11-09 | OKC @ MEM | 25 | 33 | -8 | 0022500194 |
| 4 | 2025-10-28 | SAC @ OKC | 24 | 29 | -5 | 0022500126 |
| 5 | 2025-10-23 | OKC @ IND | 22 | 25 | -3 | 0022500005 |

Notes:
- Quarter ranking is complete; **lineup stint reconstruction timed out** for DAL and MEM games in this run.
- In reconstructed games, the deficits often came in **short 1–2 minute dead-offense stretches** (e.g., 0–7 or 1–6 bursts).

## Spurs game plan: how to start strong
1. **Win the first possession battle:** crash selectively and prioritize transition defense; don’t trade OREBs for OKC runouts.
2. **Force OKC into half-court early:** make them execute against set defense; avoid early live-ball turnovers.
3. **Attack before the shell is set:** Fox push + early Wemby actions to generate rim pressure/FTs and corner 3s.
4. **Keep spacing on the floor:** avoid dead-spacing lineups—OKC’s best defense is making you play late-clock.
5. **Survive SGA minutes by shrinking mistakes:** switch/ice rules are secondary to eliminating easy points (transition + uncontested 3s).

## Matchup read (summary)
- **OKC is favored** by the efficiency + defense gap (Net +17.2 vs +4.2).
- **SAS’ clearest route** is extra possessions (OREBs), disciplined offense, and maximizing Fox/Wemby advantages in early offense.
- If SAS can keep Q1 within a single possession and avoid the “-7 in 90 seconds” type stretch, the game script becomes much more playable.

---

## Deeper breakdown (more detail)

This report was generated from NBA Stats API pulls using:
- [`spurs_thunder_preview_2025_12_13.py`](nba-lineup-tracking/scripts/spurs_thunder_preview_2025_12_13.py:1)
- [`okc_q1_lineup_analysis_v3.py`](nba-lineup-tracking/scripts/okc_q1_lineup_analysis_v3.py:1)

### Why this matchup is tricky for SAS (even though SAS has been strong)
**The numbers point to two hard problems at once:**
1) **OKC scores like an elite offense** (120.5 ORtg, 58.1 eFG%, 62.1 TS%).  
2) **OKC defends like an elite defense** (103.3 DRtg).  

That combination (plus a similar pace) means SAS isn’t likely to win just by “playing fast” or “making it a track meet”—OKC is built to win those games too.

### Possession math: where the game is likely decided
Both teams are essentially the same **pace** (~101). So the game is less about slowing down and more about **which team wins the possession battle**:

- **If OKC wins possessions** (forces turnovers, ends trips with one shot, gets runouts), their efficiency edge usually turns into separation fast.
- **If SAS can steal possessions** (OREBs + low turnovers), you can keep the game within a 1–2 possession margin deep into the 4th even if OKC is “better per shot.”

### Primary structural lever for SAS: offensive rebounding
SAS’ **31.2% OREB%** vs OKC’s **25.0% OREB%** is the clearest statistical mismatch on the page.

What that suggests in practical terms:
- SAS should treat the offensive glass as a **deliberate game-plan weapon**, but **not at the cost of transition defense**. The best version is “crash with purpose” (big + one wing) while keeping at least 2 back to prevent the instant OKC runout.

### Shot quality + spacing: the hidden tax vs OKC
OKC’s defensive profile (103.3 DRtg) tends to punish:
- **dead-spacing lineups**, and
- **late-clock possessions** where the ball sticks.

That’s why the Spurs’ perimeter mix matters so much:
- Fox is your tempo lever.
- Wemby is your rim/spacing lever.
- The rest of the floor has to be credible enough that OKC can’t collapse without consequences.

### Key player matchup themes (what the stat lines imply)
#### 1) SGA problem: volume + efficiency
**Shai Gilgeous-Alexander: 32.6 PPG on 56.2% FG / 45.4% 3P.**  
That’s not just “he scores”; it’s “he scores efficiently even when defenses know what’s coming.”

Practical implication:
- SAS can’t win by hoping to “hold SGA to 22.”  
- SAS’ better route is **reduce easy points**: avoid live-ball turnovers, limit transition, force more half-court possessions, and make the non-SGA minutes count.

#### 2) Wemby’s leverage: rim pressure + gravity
Wembanyama’s 26.2/12.9 with 34.5% from 3 means:
- OKC can’t treat him like a non-shooter, and
- SAS can create advantages both as a roller and as a spacer.

The key is how SAS uses him:
- If Wemby is mostly a static post-up target against set defense, OKC can shrink the floor.
- If Wemby is active as a screener/short-roll decision maker, SAS can generate rim attempts + corner 3s earlier in the clock.

#### 3) Fox/Castle creation vs OKC pressure
Castle’s 7.3 AST and Fox’s 6.3 AST matter because OKC’s best lineups punish “no-creator” minutes.
- If SAS ever has a stretch where **nobody is bending the defense**, OKC’s defense turns those into empty trips.

### Lineups: what the “best groups” say about game-planning
The lineup stats in the preview were constrained to **min 30 minutes together** (to avoid noise). That means we’re looking at groups the teams actually trust.

#### Spurs — key 5-man groups (from the preview pull)
**Best by Net (min 30):**
- Barnes – Vassell – Champagnie – Wembanyama – Castle (**Net +11.7** in 110 min)

**Most used:**
- Barnes – Fox – Kornet – Vassell – Champagnie (112 min, Net +6.4)
- Barnes – Vassell – Champagnie – Wembanyama – Castle (110 min, Net +11.7)
- Barnes – Fox – Vassell – Wembanyama – Castle (47 min, Net +11.5)
- Barnes – Fox – Kornet – Vassell – Castle (30 min, Net +6.0)

**What that implies**
- SAS’ best-performing group is a “two-way stability” group: enough size/defense to survive and enough creation via Castle/Wemby.
- The Kornet lineups showing up as high-minute groups hints SAS has leaned into **traditional-size lineups** at times—useful for rebounding, but it demands enough spacing/creation elsewhere.

#### Thunder — key 5-man groups (from the preview pull)
**Best by Net (min 30):**
- SGA – Dort – Holmgren – J. Williams – Wallace (**Net +44.8** in 35 min)

**Most used:**
- Hartenstein – SGA – Dort – Holmgren – Wallace (112 min, Net +18.3)
- Hartenstein – SGA – Holmgren – Wallace – Ajay Mitchell (48 min, Net +33.8)
- Hartenstein – SGA – Dort – Wiggins – Wallace (36 min, Net -3.9)
- SGA – Dort – Holmgren – J. Williams – Wallace (35 min, Net +44.8)

**What that implies**
- OKC has multiple viable looks, but their best groups combine:
  - SGA creation,
  - strong point-of-attack defense,
  - rim protection/spacers at the big spots,
  - and low mistake rate.

### Opening quarter focus (using OKC’s “worst Q1s”)
From the “worst Q1” sample, the key takeaway is **not** “OKC always starts slow.” It’s:

- When OKC does lose Q1, it’s frequently because the opponent strings together a **short burst** (1–2 minutes) where OKC’s offense stalls and the opponent scores quickly.

For SAS, “start strong” means:
- **no live-ball turnovers** in the first 6 minutes,
- generate at least a few **rim/FT possessions** early (to stabilize scoring),
- and keep OKC from getting comfortable rhythm 3s.

### Concrete “if-then” game scripts to watch
1) **If OKC starts hot from 3 again (like their last-10):**  
   SAS needs extra possessions (OREBs) *and* must keep pace via early offense—not half-court-only.

2) **If SAS dominates the offensive glass early:**  
   The game stays playable even if OKC’s shot-making is superior, because SAS is manufacturing shot volume.

3) **If SAS has a 2–3 turnover stretch in Q1:**  
   That’s where OKC’s efficiency gap turns into a quick +10 swing. The worst OKC Q1s show the inverse: short bursts decide quarters.

4) **If Wemby’s rim pressure consistently draws help:**  
   The quality of SAS’ kick-out threes becomes a swing factor (not the raw number of threes).

### Bottom line (expanded)
OKC is favored because they have the rare “elite offense + elite defense” profile and have been in peak form recently. SAS’ realistic path is to win possessions (OREBs, low turnovers), keep spacing on the floor, and use Fox/Wemby to force OKC into defensive rotations early in the shot clock—so SAS isn’t living in late-clock possessions against a top-tier defense.