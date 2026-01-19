# Architecture Codemap

> Freshness: 2026-01-19 (Verified against codebase)

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI Layer                           │
│                        (keiba/cli.py)                       │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌─────────────────┐ ┌───────────┐ ┌─────────────────┐
│    Scrapers     │ │    DB     │ │     Models      │
│ keiba/scrapers/ │ │ keiba/db  │ │  keiba/models/  │
└────────┬────────┘ └─────┬─────┘ └────────┬────────┘
         │                │                │
         ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│                   External Services                         │
│              netkeiba.com    SQLite DB                      │
└─────────────────────────────────────────────────────────────┘
```

## Module Dependencies

```
keiba/
├── __init__.py     → (empty)
├── __main__.py     → cli
├── cli.py          → models, scrapers, db
├── constants.py    → (standalone) JRA_COURSE_CODES
├── db.py           → models.base (Base)
├── models/
│   ├── __init__.py → all model modules
│   ├── base.py     → sqlalchemy
│   ├── horse.py    → base, datetime
│   ├── race.py     → base
│   ├── race_result.py → base
│   ├── jockey.py   → base
│   ├── trainer.py  → base
│   ├── owner.py    → base
│   └── breeder.py  → base
└── scrapers/
    ├── __init__.py → all scraper modules
    ├── base.py     → requests, bs4, time
    ├── race_list.py → base, constants
    ├── race_detail.py → base
    └── horse_detail.py → base
```

## Data Flow

```
1. CLI Command
   │
   ▼
2. Scraper fetches HTML from netkeiba
   │
   ▼
3. Scraper parses HTML → dict
   │
   ▼
4. CLI creates Model instances
   │
   ▼
5. DB session saves to SQLite
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

### --jra-only Option

Filters races to JRA (Japan Racing Association) only, excluding NAR (regional racing).
Uses course codes defined in `keiba/constants.py`:

```
JRA Course Codes:
01=札幌, 02=函館, 03=福島, 04=新潟, 05=東京
06=中山, 07=中京, 08=京都, 09=阪神, 10=小倉
```

Race ID format: `YYYYPPNNRRXX` where PP is the course code.
