# Backend Codemap

> Freshness: 2026-01-19 (Verified against codebase)

## CLI Module (keiba/cli.py)

### Commands

| Command | Options | Description |
|---------|---------|-------------|
| `scrape` | --year, --month, --db, --jra-only | Collect race data for specified month |
| `scrape-horses` | --db, --limit | Collect horse details |
| `analyze` | --db, --date, --venue, --race | Analyze races and display scores |

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
| `_update_horse(session, horse, data)` | Update horse record with scraped data |
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
| `_parse_pedigree(soup)` | dict - bloodline |
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

ScoreCalculator
```

### BaseFactor (keiba/analyzers/factors/base.py)

| Attribute/Method | Type | Purpose |
|------------------|------|---------|
| `name` | str | Factor identifier |
| `calculate(horse_id, race_results, **kwargs)` | float or None | Abstract: compute score (0-100) |

### Factor Implementations

| Factor | Purpose | Score Logic |
|--------|---------|-------------|
| PastResultsFactor | Recent race performance | Weighted avg of relative positions (last 5 races) |
| CourseFitFactor | Course/distance suitability | Top-3 rate on matching conditions |
| TimeIndexFactor | Time performance | Comparison to average time (same conditions) |
| Last3FFactor | Final stretch speed | Linear scale: 33s=100, 38s=0 |
| PopularityFactor | Market evaluation | Based on odds or popularity rank |

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
| `FACTOR_WEIGHTS` | dict | Weight distribution for factors |

Default weights:
- past_results: 0.25 (25%)
- course_fit: 0.20 (20%)
- time_index: 0.20 (20%)
- last_3f: 0.20 (20%)
- popularity: 0.15 (15%)

## Error Handling

- HTTP errors: `requests.HTTPError` propagates
- Parse errors: Returns partial data / None values
- DB errors: SQLAlchemy exceptions propagate
- Factor calculation: Returns None on insufficient data
