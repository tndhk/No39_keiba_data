# Backend Codemap

> Freshness: 2026-01-19T09:15:00+09:00

## CLI Module (keiba/cli.py)

### Commands

| Command | Options | Description |
|---------|---------|-------------|
| `scrape` | --year, --month, --db | Collect race data for specified month |
| `scrape-horses` | --db, --limit | Collect horse details |

### Internal Functions

| Function | Purpose |
|----------|---------|
| `extract_race_id_from_url(url)` | Extract race ID from netkeiba URL |
| `parse_race_date(date_str)` | Parse Japanese date string |
| `_save_race_data(session, data)` | Save race + results to DB |
| `_update_horse(session, horse, data)` | Update horse record with scraped data |

## Database Module (keiba/db.py)

### Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `get_engine` | (db_path: str) → Engine | Create SQLAlchemy engine |
| `get_session` | (engine) → Session | Context manager for sessions |
| `init_db` | (engine) → None | Create all tables |

## Scrapers Module (keiba/scrapers/)

### Class Hierarchy

```
BaseScraper
├── RaceListScraper
├── RaceDetailScraper
└── HorseDetailScraper
```

### BaseScraper

| Method | Purpose |
|--------|---------|
| `fetch(url)` | HTTP GET with delay & User-Agent |
| `get_soup(html)` | Parse HTML → BeautifulSoup |
| `parse(soup)` | Abstract: extract data |

### RaceListScraper

| Method | Returns |
|--------|---------|
| `fetch_race_urls(year, month, day)` | List[str] - race URLs |
| `_build_url(year, month, day)` | URL string |

URL Pattern: `https://db.netkeiba.com/race/list/YYYYMMDD/`

### RaceDetailScraper

| Method | Returns |
|--------|---------|
| `fetch_race_detail(race_id)` | dict{race, results} |
| `_parse_race_info(soup, race_id)` | dict - race metadata |
| `_parse_results(soup)` | List[dict] - horse results |

URL Pattern: `https://db.netkeiba.com/race/{race_id}/`

### HorseDetailScraper

| Method | Returns |
|--------|---------|
| `fetch_horse_detail(horse_id)` | dict - all horse info |
| `_parse_profile(soup)` | dict - basic info |
| `_parse_pedigree(soup)` | dict - bloodline |
| `_parse_career(soup)` | dict - race stats |

URL Pattern: `https://db.netkeiba.com/horse/{horse_id}/`

## Error Handling

- HTTP errors: `requests.HTTPError` propagates
- Parse errors: Returns partial data / None values
- DB errors: SQLAlchemy exceptions propagate
