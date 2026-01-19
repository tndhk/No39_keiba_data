# Architecture Codemap

> Freshness: 2026-01-19T09:15:00+09:00

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
├── cli.py          → models, scrapers, db
├── db.py           → models.base (Base)
├── models/
│   ├── __init__.py → all model modules
│   ├── base.py     → sqlalchemy
│   ├── horse.py    → base
│   ├── race.py     → base
│   ├── race_result.py → base
│   ├── jockey.py   → base
│   ├── trainer.py  → base
│   ├── owner.py    → base
│   └── breeder.py  → base
└── scrapers/
    ├── __init__.py → all scraper modules
    ├── base.py     → requests, bs4
    ├── race_list.py → base
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
