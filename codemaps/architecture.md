# Architecture Codemap

> Freshness: 2026-01-24 (Verified against codebase)

## System Overview

```
+-----------------------------------------------------------------+
|                          CLI Layer                               |
|                        (keiba/cli.py)                            |
+---------------------------------+-------------------------------+
                                  |
          +-------------+---------+--------+-------------+---------+
          v             v                  v             v         v
+---------------+ +-----------+ +----------------+ +-----------+ +----------+
|   Scrapers    | |    DB     | |    Analyzers   | |   Models  | | Services |
|keiba/scrapers/| | keiba/db  | |keiba/analyzers/| |keiba/models| | keiba/   |
|               | |           | |                | |           | | services/|
+-------+-------+ +-----+-----+ +--------+-------+ +-----+-----+ +----+-----+
        |               |                |               |            |
        v               v                v               v            v
+-----------------------------------------------------------------+---------+
|                     External Services                            |        |
|               netkeiba.com    SQLite DB                          |   ML   |
|               (db + race)                                        |keiba/ml|
+------------------------------------------------------------------+--------+
```

## Module Dependencies

```
keiba/
+-- __init__.py     -> (empty)
+-- __main__.py     -> cli
+-- cli.py          -> models, scrapers, db, analyzers, utils, services, ml, backtest
+-- constants.py    -> (standalone) JRA_COURSE_CODES
+-- db.py           -> models.base (Base)
+-- models/
|   +-- __init__.py -> all model modules
|   +-- base.py     -> sqlalchemy
|   +-- horse.py    -> base, datetime
|   +-- race.py     -> base
|   +-- race_result.py -> base
|   +-- jockey.py   -> base
|   +-- trainer.py  -> base
|   +-- owner.py    -> base
|   +-- breeder.py  -> base
|   +-- entry.py    -> dataclasses (NEW: RaceEntry, ShutubaData DTOs)
+-- scrapers/
|   +-- __init__.py -> all scraper modules
|   +-- base.py     -> requests, bs4, time
|   +-- race_list.py -> base, constants
|   +-- race_detail.py -> base
|   +-- horse_detail.py -> base
|   +-- shutuba.py  -> base, models.entry (NEW: ShutubaScraper)
+-- services/       (NEW)
|   +-- __init__.py -> prediction_service
|   +-- prediction_service.py -> analyzers.factors, analyzers.score_calculator, models.entry
+-- analyzers/
|   +-- __init__.py -> score_calculator
|   +-- score_calculator.py -> config.weights
|   +-- factors/
|       +-- __init__.py -> all factor modules (7 factors)
|       +-- base.py -> abc
|       +-- past_results.py -> base
|       +-- course_fit.py -> base
|       +-- time_index.py -> base, re
|       +-- last_3f.py -> base
|       +-- popularity.py -> base
|       +-- pedigree.py -> base, config.pedigree_master
|       +-- running_style.py -> base, collections
+-- ml/
|   +-- __init__.py -> feature_builder (lazy: Predictor, Trainer)
|   +-- feature_builder.py -> (standalone)
|   +-- predictor.py -> lightgbm, numpy
|   +-- trainer.py -> lightgbm, sklearn
+-- backtest/
|   +-- __init__.py -> backtester, metrics, reporter
|   +-- backtester.py -> db, models, analyzers, ml
|   +-- metrics.py -> dataclasses
|   +-- reporter.py -> (standalone)
|   +-- factor_calculator.py -> analyzers
|   +-- cache.py -> (standalone)
+-- config/
|   +-- __init__.py -> (empty)
|   +-- weights.py -> (standalone) FACTOR_WEIGHTS (7 factors)
|   +-- pedigree_master.py -> (standalone) SIRE_LINE_MAPPING, LINE_APTITUDE
+-- utils/
    +-- __init__.py -> (empty)
    +-- grade_extractor.py -> re
```

## Data Flow

```
1. CLI Command (scrape/scrape-horses/analyze/predict/backtest/migrate-grades)
   |
   v
2. Scraper fetches HTML from netkeiba (scrape/scrape-horses/predict)
   +-- RaceListScraper: db.netkeiba.com/race/list/
   +-- RaceDetailScraper: db.netkeiba.com/race/
   +-- HorseDetailScraper: db.netkeiba.com/horse/
   +-- ShutubaScraper: race.netkeiba.com/race/shutuba.html (NEW)
   |
   v
3. Scraper parses HTML -> dict or DTO
   +-- Scrapers return dict for historical data
   +-- ShutubaScraper returns ShutubaData DTO (NEW)
   |
   v
4. CLI/Service creates Model instances or uses DTOs
   |
   v
5. DB session saves to SQLite (for scrape commands)
   |
   v (for analyze/predict/backtest command)
6. Analyzers read from DB -> calculate scores (7 factors)
   +-- PredictionService orchestrates for predict command (NEW)
   |
   v
7. Scores aggregated by ScoreCalculator -> weighted total
   |
   v (optional: ML prediction)
8. FeatureBuilder constructs features -> Trainer/Predictor (LightGBM)
```

## External Dependencies

| Package | Purpose |
|---------|---------|
| sqlalchemy | ORM, DB operations |
| requests | HTTP client |
| beautifulsoup4 | HTML parsing |
| lxml | HTML parser backend |
| click | CLI framework |
| lightgbm | ML prediction (3着以内予測) |
| scikit-learn | ML utilities (CV, metrics) |
| numpy | Numerical operations |
| joblib | Model serialization |

## Entry Points

| Entry | Module | Function |
|-------|--------|----------|
| `keiba` | keiba.cli | main() |
| `python -m keiba` | keiba.__main__ | main() |

## CLI Commands

| Command | Description | Key Options |
|---------|-------------|-------------|
| `keiba scrape` | Collect race data | --year, --month, --db, --jra-only |
| `keiba scrape-horses` | Collect horse details (with pedigree) | --db, --limit |
| `keiba analyze` | Analyze races and show scores | --db, --date, --venue, --race, --no-predict |
| `keiba predict` | Real-time prediction from shutuba URL | --url, --db, --no-ml (NEW) |
| `keiba backtest` | ML backtest verification | --db, --from, --to, --months, --retrain-interval, -v |
| `keiba migrate-grades` | Add grade info to existing races | --db |

### --jra-only Option

Filters races to JRA (Japan Racing Association) only, excluding NAR (regional racing).
Uses course codes defined in `keiba/constants.py`:

```
JRA Course Codes:
01=Sapporo, 02=Hakodate, 03=Fukushima, 04=Niigata, 05=Tokyo
06=Nakayama, 07=Chukyo, 08=Kyoto, 09=Hanshin, 10=Kokura
```

Race ID format: `YYYYPPNNRRXX` where PP is the course code.

## Analysis Factors (7 Total)

| Factor | Weight | Purpose |
|--------|--------|---------|
| past_results | 14.3% | Recent race performance |
| course_fit | 14.3% | Course/distance suitability |
| time_index | 14.3% | Time performance |
| last_3f | 14.3% | Final stretch speed |
| popularity | 14.3% | Market evaluation |
| pedigree | 14.3% | Bloodline aptitude |
| running_style | 14.2% | Running style match |

## New Features (2026-01-24)

### Real-time Prediction (predict command)

```bash
keiba predict --url "https://race.netkeiba.com/race/shutuba.html?race_id=202606010801" --db data/keiba.db
```

Components:
- `ShutubaScraper`: Scrapes race.netkeiba.com shutuba pages
- `RaceEntry`, `ShutubaData`: Immutable DTOs for entry data
- `PredictionService`: Orchestrates factor calculation and ML prediction
- `SQLAlchemyRaceResultRepository`: Repository for past results lookup

Data Leak Prevention:
- Uses `before_date` parameter to fetch only past results before race date
- Does not use same-day odds/popularity for prediction
