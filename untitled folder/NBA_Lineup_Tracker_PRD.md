# Product Requirements Document: NBA Lineup-Level Boxscore Tracker

## Executive Summary

This application will analyze NBA games at a granular level by tracking performance metrics for specific lineup matchups. By breaking down play-by-play data into "mini-games" based on lineup changes, the tool will provide insights into which lineup combinations perform best against specific opponents.

**Target Users:** NBA analysts, coaches, fantasy basketball enthusiasts, sports data scientists

**Core Value Proposition:** Transform game-level statistics into actionable lineup matchup intelligence

---

## 1. Product Overview

### 1.1 Problem Statement
Current NBA statistics aggregate performance at the game or season level, making it difficult to understand:
- Which specific lineup combinations are most effective
- How lineups perform against specific opponent matchups
- The impact of substitutions on game momentum
- Granular performance trends within games

### 1.2 Proposed Solution
A Python application that:
1. Fetches play-by-play data from the NBA API
2. Identifies lineup changes for both teams
3. Segments the game into discrete "lineup periods"
4. Calculates comprehensive boxscore statistics for each period
5. Exports structured data for analysis

---

## 2. Key Features & Requirements

### 2.1 Core Functionality

#### Feature 1: Play-by-Play Data Ingestion
**Description:** Retrieve complete play-by-play data for any NBA game

**Requirements:**
- Support for regular season and playoff games
- Handle live game data and historical games
- Robust error handling for API rate limits
- Data validation to ensure completeness

**Acceptance Criteria:**
- Successfully fetch play-by-play data for any valid game ID
- Handle API errors gracefully with appropriate logging
- Validate data integrity before processing

#### Feature 2: Lineup Change Detection
**Description:** Identify when lineups change for either team

**Requirements:**
- Detect substitutions from play-by-play events
- Track 5-player lineups for both home and away teams
- Handle edge cases (injured players, technical issues)
- Maintain lineup continuity across quarters

**Acceptance Criteria:**
- Accurately identify all substitution events
- Create new game segments when any lineup changes
- Handle game start and end appropriately

#### Feature 3: Mini-Game Segmentation
**Description:** Break the game into discrete periods based on lineup matchups

**Requirements:**
- Create a "Game" object for each unique lineup matchup
- Assign start and end timestamps to each segment
- Track game context (score, quarter, time remaining)
- Link segments sequentially

**Acceptance Criteria:**
- Each game segment has exactly 5 players per team
- No overlapping time periods
- All game time is accounted for (except timeouts/breaks)

#### Feature 4: Boxscore Calculation
**Description:** Calculate comprehensive statistics for each lineup period

**Requirements:**
- Track traditional boxscore stats (points, rebounds, assists, etc.)
- Calculate plus/minus for each lineup matchup
- Compute possession-based metrics
- Track shooting efficiency (FG%, 3P%, FT%)

**Metrics to Track:**
- **Scoring:** Points, Field Goals (Made/Attempted), 3-Pointers (Made/Attempted), Free Throws (Made/Attempted)
- **Rebounds:** Offensive, Defensive, Total
- **Playmaking:** Assists, Turnovers, Assist/Turnover Ratio
- **Defense:** Steals, Blocks, Personal Fouls
- **Efficiency:** Plus/Minus, Offensive Rating, Defensive Rating
- **Possession:** Number of possessions, Points per possession
- **Time:** Duration of lineup period, Game clock start/end

**Acceptance Criteria:**
- All statistics accurately reflect play-by-play events
- Boxscores sum correctly to game totals
- Handle missing or null values appropriately

#### Feature 5: Data Export
**Description:** Output processed data in multiple formats

**Requirements:**
- Export to JSON for programmatic access
- Export to CSV for spreadsheet analysis
- Include metadata (game ID, date, teams, etc.)
- Option to export individual segments or aggregated data

**Acceptance Criteria:**
- Clean, well-structured output files
- Consistent naming conventions
- Include documentation/schema

---

## 3. Technical Architecture

### 3.1 Technology Stack
- **Language:** Python 3.9+
- **NBA API Library:** `nba_api` (unofficial NBA API wrapper)
- **Data Processing:** `pandas` for data manipulation
- **Date/Time:** `datetime` for timestamp handling
- **Export:** `json`, `csv` standard libraries

### 3.2 Core Components

```
├── main.py                 # Entry point and orchestration
├── api/
│   ├── nba_client.py      # NBA API wrapper and data fetching
│   └── data_validator.py  # Input validation and cleaning
├── models/
│   ├── game_segment.py    # GameSegment class definition
│   ├── lineup.py          # Lineup class definition
│   └── boxscore.py        # Boxscore calculation logic
├── processors/
│   ├── lineup_detector.py # Lineup change detection
│   └── stats_calculator.py # Statistical calculations
├── exporters/
│   ├── json_exporter.py   # JSON export functionality
│   └── csv_exporter.py    # CSV export functionality
├── utils/
│   ├── logger.py          # Logging configuration
│   └── constants.py       # Constants and configuration
└── tests/
    └── test_*.py          # Unit tests
```

### 3.3 Data Models

#### GameSegment Class
```python
class GameSegment:
    segment_id: str
    game_id: str
    home_lineup: List[Player]  # 5 players
    away_lineup: List[Player]  # 5 players
    start_time: float  # Game clock (seconds)
    end_time: float
    start_quarter: int
    end_quarter: int
    home_boxscore: BoxScore
    away_boxscore: BoxScore
    context: GameContext  # Score, game situation
```

#### BoxScore Class
```python
class BoxScore:
    points: int
    fgm: int  # Field goals made
    fga: int  # Field goals attempted
    fg_pct: float
    fg3m: int
    fg3a: int
    fg3_pct: float
    ftm: int
    fta: int
    ft_pct: float
    oreb: int  # Offensive rebounds
    dreb: int
    treb: int  # Total rebounds
    ast: int
    stl: int
    blk: int
    tov: int  # Turnovers
    pf: int  # Personal fouls
    plus_minus: int
    possessions: int
    offensive_rating: float
    defensive_rating: float
    duration_seconds: float
```

#### Lineup Class
```python
class Lineup:
    players: List[Player]  # Exactly 5 players
    team: str

    def get_lineup_key(self) -> str:
        # Returns sorted player IDs for comparison
```

---

## 4. Implementation Details

### 4.1 NBA API Integration

**Endpoints to Use:**
- `playbyplayv2.PlayByPlayV2` - Get play-by-play data
- `boxscoretraditionalv2.BoxScoreTraditionalV2` - Validate totals

**Key Considerations:**
- Rate limiting: Implement delays between requests (recommended 600ms)
- Caching: Store fetched data locally to avoid redundant API calls
- Error handling: Retry logic for transient failures

### 4.2 Lineup Detection Algorithm

**Logic Flow:**
1. Start with opening lineups from initial play-by-play events
2. Monitor all substitution events (EVENTMSGTYPE = 8)
3. When substitution occurs:
   - End current game segment
   - Update relevant team's lineup
   - Start new game segment with new lineups
4. Continue until game end

**Edge Cases:**
- Players fouling out (not substitution, but lineup change)
- Technical issues requiring lineup adjustments
- Starting lineups not explicitly stated

### 4.3 Boxscore Calculation Logic

**Approach:**
- Parse each play-by-play event within a segment
- Map event types to statistical categories
- Accumulate stats for the active lineup
- Calculate derived metrics (percentages, ratings) at segment end

**Event Type Mapping:**
- EVENTMSGTYPE = 1: Made field goal
- EVENTMSGTYPE = 2: Missed field goal
- EVENTMSGTYPE = 3: Free throw
- EVENTMSGTYPE = 4: Rebound
- EVENTMSGTYPE = 5: Turnover
- etc.

### 4.4 Plus/Minus Calculation

For each segment:
- Track score at segment start and end
- Calculate: (Team Points - Opponent Points) during segment
- Assign to all players in lineup during that period

---

## 5. User Stories

### As an NBA Analyst
- I want to identify which lineup combinations have the best plus/minus against specific opponents
- I want to see how lineup performance changes throughout a game
- I want to export data for visualization in external tools

### As a Coach
- I want to understand which lineups perform best in specific game situations
- I want to compare my lineup performance against different opponent lineups
- I want historical data to inform substitution patterns

### As a Data Scientist
- I want clean, structured data for machine learning models
- I want to aggregate lineup performance across multiple games
- I want to analyze trends over a season or career

---

## 6. Success Metrics

### Functional Metrics
- **Accuracy:** 99%+ accuracy in lineup detection compared to manual verification
- **Completeness:** All game time accounted for in segments (excluding timeouts/halftime)
- **Performance:** Process a complete game in under 60 seconds

### Quality Metrics
- **Data Integrity:** Boxscore totals match official NBA statistics
- **Reliability:** 95%+ success rate in fetching and processing games
- **Usability:** Clear documentation and error messages

---

## 7. Development Phases

### Phase 1: Core Infrastructure (Week 1-2)
- Set up project structure and dependencies
- Implement NBA API client with error handling
- Create data models (GameSegment, BoxScore, Lineup)
- Unit tests for core classes

**Deliverables:**
- Functional API client
- Basic data models
- Test coverage > 80%

### Phase 2: Lineup Detection (Week 2-3)
- Implement lineup change detection algorithm
- Handle edge cases (fouling out, injuries)
- Create game segmentation logic
- Integration tests with real game data

**Deliverables:**
- Working lineup detector
- Game segmentation functionality
- Validated against 10+ real games

### Phase 3: Boxscore Calculation (Week 3-4)
- Map play-by-play events to statistics
- Calculate all boxscore metrics
- Implement possession estimation
- Calculate advanced metrics (ratings)

**Deliverables:**
- Complete boxscore calculation
- Metrics validation against official stats
- Performance optimization

### Phase 4: Export & Polish (Week 4-5)
- Implement JSON and CSV exporters
- Create command-line interface
- Write comprehensive documentation
- Performance optimization and bug fixes

**Deliverables:**
- Multi-format export functionality
- User documentation
- Production-ready code

---

## 8. Technical Constraints & Considerations

### 8.1 NBA API Limitations
- **Rate Limits:** Unofficial API has no published limits, but implement conservative delays
- **Data Availability:** Historical data available back to ~2015-16 season
- **Live Data:** May have delays of 1-2 minutes during live games
- **Endpoints:** May change without notice (unofficial API risk)

### 8.2 Data Challenges
- **Substitution Timing:** Exact timing may not always be precise
- **Player Identification:** Handle player ID changes across seasons
- **Incomplete Data:** Some older games may have missing play-by-play
- **Data Quality:** Occasional errors in official NBA data

### 8.3 Performance Considerations
- **Memory Usage:** Loading full games into memory
- **Processing Time:** Complex calculations for long games
- **API Calls:** Minimize redundant requests
- **Caching Strategy:** Balance storage vs. API load

---

## 9. Testing Strategy

### Unit Tests
- Test data model classes independently
- Test statistical calculations with known inputs
- Test lineup comparison and hashing
- Test edge case handling

### Integration Tests
- Test with complete game data
- Validate against official boxscores
- Test multiple game scenarios (blowouts, close games, overtime)
- Test different seasons and rule changes

### Validation Tests
- Compare generated boxscores with official NBA data
- Manual verification of lineup segments for sample games
- Performance benchmarking with various game types

---

## 10. Future Enhancements (Out of Scope for V1)

### Phase 2 Features
- **Database Integration:** Store processed games in PostgreSQL/MongoDB
- **Web API:** REST API to query lineup data
- **Visualization Dashboard:** Interactive web interface
- **Real-time Processing:** Process games as they happen

### Advanced Analytics
- **Win Probability:** Calculate win probability for each segment
- **Lineup Recommendations:** ML model to suggest optimal lineups
- **Matchup Analysis:** Deep dive into specific player matchups
- **Trend Analysis:** Track lineup performance over time

### Data Expansion
- **Multiple Games:** Batch process entire seasons
- **Team Aggregation:** Aggregate lineup stats across games
- **League-wide Analysis:** Compare lineups across all teams
- **Historical Trends:** Track meta-game shifts over years

---

## 11. Dependencies & Requirements

### Required Python Packages
```
nba_api>=1.1.14
pandas>=1.5.0
numpy>=1.23.0
python-dateutil>=2.8.2
requests>=2.28.0
```

### Development Dependencies
```
pytest>=7.2.0
pytest-cov>=4.0.0
black>=22.0.0
flake8>=6.0.0
mypy>=0.990
```

### System Requirements
- Python 3.9 or higher
- 4GB RAM minimum (8GB recommended)
- Internet connection for API access
- 1GB storage for cached data (optional)

---

## 12. Risk Assessment

### High Priority Risks
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| NBA API changes/deprecation | Medium | High | Abstract API layer, monitor for changes, have backup data sources |
| Lineup detection accuracy | Low | High | Extensive testing, manual validation, edge case handling |
| Performance issues | Medium | Medium | Implement caching, optimize algorithms, parallel processing |

### Medium Priority Risks
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Data quality issues | Medium | Medium | Validation layer, data quality checks, fallback logic |
| Rate limiting | Low | Medium | Implement delays, respect rate limits, user warnings |
| Incomplete play-by-play | Low | Low | Graceful degradation, clear error messages |

---

## 13. Documentation Requirements

### User Documentation
- Installation guide
- Quick start tutorial
- API usage examples
- Configuration options
- Troubleshooting guide

### Developer Documentation
- Code architecture overview
- API integration guide
- Data model specifications
- Contributing guidelines
- Testing procedures

### Data Documentation
- Output schema definitions
- Metric calculations explained
- Data quality notes
- Known limitations

---

## 14. Acceptance Criteria

The project will be considered complete when:

1. ✅ Application successfully processes any NBA game from 2015-present
2. ✅ Lineup changes are detected with 99%+ accuracy
3. ✅ Generated boxscores match official NBA totals within 1% margin
4. ✅ All specified metrics are calculated correctly
5. ✅ Data exports in both JSON and CSV formats
6. ✅ Comprehensive documentation is provided
7. ✅ Test coverage exceeds 80%
8. ✅ Processing time is under 60 seconds per game
9. ✅ Graceful error handling for all edge cases
10. ✅ Code follows PEP 8 style guidelines

---

## 15. Glossary

- **Lineup:** The 5 players on the court for a team at any given time
- **Game Segment:** A continuous period where both team lineups remain unchanged
- **Boxscore:** Statistical summary of performance metrics
- **Plus/Minus:** Point differential while a lineup is on the court
- **Possession:** An offensive opportunity ending in a score, turnover, or defensive rebound
- **Offensive Rating:** Points scored per 100 possessions
- **Defensive Rating:** Points allowed per 100 possessions

---

## Appendix A: Sample Output Structure

### JSON Output Example
```json
{
  "game_id": "0022100001",
  "date": "2021-10-19",
  "home_team": "MIL",
  "away_team": "BRK",
  "segments": [
    {
      "segment_id": "0022100001_001",
      "home_lineup": ["203507", "201950", "203114", "1628389", "1626179"],
      "away_lineup": ["201935", "201142", "1627742", "202681", "1629011"],
      "start_time": 720.0,
      "end_time": 675.0,
      "quarter": 1,
      "home_boxscore": {
        "points": 8,
        "fgm": 3,
        "fga": 5,
        "fg3m": 2,
        "fg3a": 3,
        "plus_minus": 3,
        "duration": 45.0
      },
      "away_boxscore": {
        "points": 5,
        "fgm": 2,
        "fga": 4,
        "fg3m": 1,
        "fg3a": 2,
        "plus_minus": -3,
        "duration": 45.0
      }
    }
  ]
}
```

---

## Contact & Support

**Product Owner:** [Your Name]
**Technical Lead:** [TBD]
**Repository:** [GitHub URL]
**Slack Channel:** #nba-lineup-tracker

**Questions or Feedback:** Please create an issue in the GitHub repository or reach out in the Slack channel.