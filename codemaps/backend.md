# Backend Codemap

> Freshness: 2026-01-20 (Verified against codebase)

## CLI Module (keiba/cli.py)

### Commands

| Command | Options | Description |
|---------|---------|-------------|
| `scrape` | --year, --month, --db, --jra-only | Collect race data for specified month |
| `scrape-horses` | --db, --limit | Collect horse details (incl. pedigree) |
| `analyze` | --db, --date, --venue, --race | Analyze races and display scores |
| `migrate-grades` | --db | Add grade info to existing races |

### --jra-only Flag

Filters races to JRA (central) only, excluding NAR (regional) races.

```
keiba scrape --year 2024 --month 1 --db data/keiba.db --jra-only
```

### --analyze Command Usage

```
keiba analyze --db data/keiba.db --date 2024-01-01 --venue Nakayama
keiba analyze --db data/keiba.db --date 2024-01-01 --venue Nakayama --race 11
```

### Internal Functions

| Function | Purpose |
|----------|---------|
| `extract_race_id_from_url(url)` | Extract race ID from netkeiba URL |
| `parse_race_date(date_str)` | Parse Japanese date string |
| `_save_race_data(session, data)` | Save race + results to DB (includes sex, age, impost, passing_order) |
| `_update_horse(session, horse, data)` | Update horse record with scraped data (incl. pedigree) |
| `_analyze_race(session, race)` | Analyze single race and display scores |
| `_get_horse_past_results(session, horse_id)` | Fetch horse past results for analysis |
| `_print_score_table(scores)` | Display formatted score table |

## Database Module (keiba/db.py)

### Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `get_engine` | (db_path: str) -> Engine | Create SQLAlchemy engine |
| `get_session` | (engine) -> Session | Context manager for sessions |
| `init_db` | (engine) -> None | Create all tables |

## Scrapers Module (keiba/scrapers/)

### Class Hierarchy

```
BaseScraper
+-- RaceListScraper
+-- RaceDetailScraper
+-- HorseDetailScraper
```

### BaseScraper

| Method | Purpose |
|--------|---------|
| `fetch(url)` | HTTP GET with delay and User-Agent |
| `get_soup(html)` | Parse HTML -> BeautifulSoup |
| `parse(soup)` | Abstract: extract data |

### RaceListScraper

| Method | Returns |
|--------|---------|
| `fetch_race_urls(year, month, day, jra_only)` | List[str] - race URLs |
| `is_jra_race(race_url)` | bool - True if JRA race |
| `_build_url(year, month, day)` | URL string |

URL Pattern: `https://db.netkeiba.com/race/list/YYYYMMDD/`

JRA filtering uses course codes from `keiba/constants.py`:
- Course codes 01-10 are JRA (central)
- Other codes are NAR (regional)

### RaceDetailScraper

| Method | Returns |
|--------|---------|
| `fetch_race_detail(race_id)` | dict{race, results} |
| `_parse_race_info(soup, race_id)` | dict - race metadata |
| `_parse_results(soup)` | List[dict] - horse results |
| `_parse_horse_row(row)` | dict - single horse result |
| `_parse_race_conditions(text, race_info)` | Updates race_info dict |

URL Pattern: `https://db.netkeiba.com/race/{race_id}/`

Column Parsing (db.netkeiba.com format):
| Column | Field | Description |
|--------|-------|-------------|
| 0 | finish_position | Finish position (0=DNF) |
| 1 | bracket_number | Bracket number (1-8) |
| 2 | horse_number | Horse number |
| 3 | horse_id, horse_name | Horse info from link |
| 4 | sex, age | Sex and age (e.g., "bo3" for male 3yo) |
| 5 | impost | Impost weight (e.g., 57.0) |
| 6 | jockey_id, jockey_name | Jockey info from link |
| 7 | time | Finish time |
| 8 | margin | Margin from winner |
| 10 | passing_order | Passing positions (e.g., "2-1-1-1") |
| 11 | last_3f | Last 3 furlongs time |
| 12 | odds | Win odds |
| 13 | popularity | Popularity rank |
| 14 | weight, weight_diff | Horse weight and change |
| 18 | trainer_id, trainer_name | Trainer info from link |

### HorseDetailScraper

| Method | Returns |
|--------|---------|
| `fetch_horse_detail(horse_id)` | dict - all horse info |
| `_parse_profile(soup)` | dict - basic info |
| `_parse_pedigree(soup)` | dict - bloodline (sire, dam, dam_sire) |
| `_parse_career(soup)` | dict - race stats |

URL Pattern: `https://db.netkeiba.com/horse/{horse_id}/`

## Constants Module (keiba/constants.py)

| Constant | Type | Purpose |
|----------|------|---------|
| `JRA_COURSE_CODES` | dict[str, str] | Maps course codes (01-10) to venue names |

JRA Venues: Sapporo, Hakodate, Fukushima, Niigata, Tokyo, Nakayama, Chukyo, Kyoto, Hanshin, Kokura

## Analyzers Module (keiba/analyzers/)

### Class Hierarchy

```
BaseFactor (ABC)
+-- PastResultsFactor
+-- CourseFitFactor
+-- TimeIndexFactor
+-- Last3FFactor
+-- PopularityFactor
+-- PedigreeFactor      # NEW
+-- RunningStyleFactor  # NEW

ScoreCalculator
```

### BaseFactor (keiba/analyzers/factors/base.py)

| Attribute/Method | Type | Purpose |
|------------------|------|---------|
| `name` | str | Factor identifier |
| `calculate(horse_id, race_results, **kwargs)` | float or None | Abstract: compute score (0-100) |

### Factor Implementations (7 Factors)

| Factor | Purpose | Score Logic |
|--------|---------|-------------|
| PastResultsFactor | Recent race performance | Weighted avg of relative positions (last 5 races) |
| CourseFitFactor | Course/distance suitability | Top-3 rate on matching conditions |
| TimeIndexFactor | Time performance | Comparison to average time (same conditions) |
| Last3FFactor | Final stretch speed | Linear scale: 33s=100, 38s=0 |
| PopularityFactor | Market evaluation | Based on odds or popularity rank |
| PedigreeFactor | Bloodline aptitude | Distance/track aptitude from sire line (NEW) |
| RunningStyleFactor | Running style match | Style tendency vs course win rate (NEW) |

### PedigreeFactor (keiba/analyzers/factors/pedigree.py) - NEW

| Method | Purpose |
|--------|---------|
| `_get_distance_band(distance)` | Classify: sprint/mile/middle/long |
| `_get_track_type(condition)` | Classify: good/heavy |
| `calculate(horse_id, race_results, **kwargs)` | Bloodline aptitude score |

Required kwargs: `sire`, `dam_sire`, `distance`, `track_condition`

Score calculation:
- Sire line aptitude (70%) + Dam-sire line aptitude (30%)
- Distance aptitude + Track aptitude averaged
- Result: 0-100 score

### RunningStyleFactor (keiba/analyzers/factors/running_style.py) - NEW

| Method | Purpose |
|--------|---------|
| `_classify_running_style(passing_order, total_horses)` | Classify: escape/front/stalker/closer |
| `_get_horse_tendency(horse_id, race_results)` | Most common style from last 5 races |
| `calculate(horse_id, race_results, **kwargs)` | Style match score |

Running style classification (1st corner position / total horses):
- escape: <= 15%
- front: 15-40%
- stalker: 40-70%
- closer: > 70%

Optional kwargs: `course_stats` (default win rates used if not provided)

### ScoreCalculator (keiba/analyzers/score_calculator.py)

| Method | Purpose |
|--------|---------|
| `__init__(weights)` | Initialize with custom or default weights |
| `get_weights()` | Return current weight configuration |
| `calculate_total(factor_scores)` | Compute weighted average score (0-100) |

## Config Module (keiba/config/)

### weights.py

| Constant | Value | Purpose |
|----------|-------|---------|
| `FACTOR_WEIGHTS` | dict | Weight distribution for 7 factors |

Current weights (7 factors, equal distribution):
- past_results: 0.143 (14.3%)
- course_fit: 0.143 (14.3%)
- time_index: 0.143 (14.3%)
- last_3f: 0.143 (14.3%)
- popularity: 0.143 (14.3%)
- pedigree: 0.143 (14.3%)
- running_style: 0.142 (14.2%)

### pedigree_master.py - NEW

| Constant/Function | Purpose |
|-------------------|---------|
| `SIRE_LINE_MAPPING` | dict[str, str] - Maps 52 sire names to 8 lines |
| `LINE_APTITUDE` | dict - Distance/track aptitude per line |
| `get_sire_line(sire_name)` | Get line name (returns "other" if unknown) |
| `get_line_aptitude(line)` | Get aptitude dict for line |

8 Sire Lines:
- sunday_silence: Middle distance, good track
- kingmambo: Mile, versatile track
- northern_dancer: Middle-long, heavy track
- mr_prospector: Sprint, heavy track
- roberto: Middle, heavy track
- storm_cat: Sprint, good track
- hail_to_reason: Long distance
- other: Balanced defaults

## Utils Module (keiba/utils/)

### grade_extractor.py

| Function | Purpose |
|----------|---------|
| `extract_grade(race_name)` | Extract grade (G1/G2/G3/L/OP/etc) from race name |

## Error Handling

- HTTP errors: `requests.HTTPError` propagates
- Parse errors: Returns partial data / None values
- DB errors: SQLAlchemy exceptions propagate
- Factor calculation: Returns None on insufficient data
  - PedigreeFactor: None if sire is None or distance is None
  - RunningStyleFactor: None if no passing_order data in history
