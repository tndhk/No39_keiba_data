# Architecture Codemap

> Freshness: 2026-01-19 (Verified against codebase)

## System Overview

```
+-----------------------------------------------------------------+
|                          CLI Layer                               |
|                        (keiba/cli.py)                            |
+---------------------------------+-------------------------------+
                                  |
          +-------------+---------+--------+-------------+
          v             v                  v             v
+---------------+ +-----------+ +----------------+ +-----------+
|   Scrapers    | |    DB     | |    Analyzers   | |   Models  |
|keiba/scrapers/| | keiba/db  | |keiba/analyzers/| |keiba/models|
+-------+-------+ +-----+-----+ +--------+-------+ +-----+-----+
        |               |                |               |
        v               v                v               v
+-----------------------------------------------------------------+
|                     External Services                            |
|               netkeiba.com    SQLite DB                          |
+-----------------------------------------------------------------+
```

## Module Dependencies

```
keiba/
+-- __init__.py     -> (empty)
+-- __main__.py     -> cli
+-- cli.py          -> models, scrapers, db, analyzers
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
+-- scrapers/
|   +-- __init__.py -> all scraper modules
|   +-- base.py     -> requests, bs4, time
|   +-- race_list.py -> base, constants
|   +-- race_detail.py -> base
|   +-- horse_detail.py -> base
+-- analyzers/
|   +-- __init__.py -> score_calculator
|   +-- score_calculator.py -> config.weights
|   +-- factors/
|       +-- __init__.py -> all factor modules
|       +-- base.py -> abc
|       +-- past_results.py -> base
|       +-- course_fit.py -> base
|       +-- time_index.py -> base, re
|       +-- last_3f.py -> base
|       +-- popularity.py -> base
+-- config/
    +-- __init__.py -> (empty)
    +-- weights.py -> (standalone) FACTOR_WEIGHTS
```

## Data Flow

```
1. CLI Command (scrape/scrape-horses/analyze)
   |
   v
2. Scraper fetches HTML from netkeiba (scrape/scrape-horses)
   |
   v
3. Scraper parses HTML -> dict
   |
   v
4. CLI creates Model instances
   |
   v
5. DB session saves to SQLite
   |
   v (for analyze command)
6. Analyzers read from DB -> calculate scores
```

## External Dependencies

| Package | Purpose |
|---------|---------|
| sqlalchemy | ORM, DB operations |
| requests | HTTP client |
| beautifulsoup4 | HTML parsing |
| lxml | HTML parser backend |
| click | CLI framework |

## Entry Points

| Entry | Module | Function |
|-------|--------|----------|
| `keiba` | keiba.cli | main() |
| `python -m keiba` | keiba.__main__ | main() |

## CLI Commands

| Command | Description | Key Options |
|---------|-------------|-------------|
| `keiba scrape` | Collect race data | --year, --month, --db, --jra-only |
| `keiba scrape-horses` | Collect horse details | --db, --limit |
| `keiba analyze` | Analyze races and show scores | --db, --date, --venue, --race |

### --jra-only Option

Filters races to JRA (Japan Racing Association) only, excluding NAR (regional racing).
Uses course codes defined in `keiba/constants.py`:

```
JRA Course Codes:
01=Sapporo, 02=Hakodate, 03=Fukushima, 04=Niigata, 05=Tokyo
06=Nakayama, 07=Chukyo, 08=Kyoto, 09=Hanshin, 10=Kokura
```

Race ID format: `YYYYPPNNRRXX` where PP is the course code.
