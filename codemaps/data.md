# Data Models Codemap

> Freshness: 2026-01-20 (Verified against codebase)

## Entity Relationship

```
+---------+     +-------------+     +---------+
|  Race   |----<| RaceResult  |>----|  Horse  |
+---------+     +------+------+     +----+----+
                       |                 |
              +--------+--------+        |
              v        v        v        |
         +--------++--------++--------+  |
         | Jockey ||Trainer || Owner  |  |
         +--------++--------++--------+  |
                                         |
                                   +-----+-----+
                                   |  Breeder  |
                                   +-----------+
```

## Models

### Race

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | String | PK | Race ID (e.g., 202403010101) |
| name | String | No | Race name |
| date | Date | No | Race date |
| course | String | No | Venue (e.g., Nakayama) |
| race_number | Integer | No | Race number (1-12) |
| distance | Integer | No | Distance in meters |
| surface | String | No | Track type (Turf/Dirt/Hurdle) |
| weather | String | Yes | Weather condition |
| track_condition | String | Yes | Track condition (Good/Slightly Heavy/Heavy/Bad) |

### Horse

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | String | PK | Horse ID |
| name | String | No | Horse name |
| sex | String | No | Gender (Male/Female/Gelding) |
| birth_year | Integer | No | Birth year |
| sire | String | Yes | Father |
| dam | String | Yes | Mother |
| dam_sire | String | Yes | Mother's father |
| coat_color | String | Yes | Coat color |
| birthplace | String | Yes | Birthplace |
| trainer_id | String | Yes | Trainer ID (FK) |
| owner_id | String | Yes | Owner ID (FK) |
| breeder_id | String | Yes | Breeder ID (FK) |
| total_races | Integer | Yes | Career race count |
| total_wins | Integer | Yes | Career wins |
| total_earnings | Integer | Yes | Total earnings (10K JPY) |
| created_at | DateTime | No | Record creation time |
| updated_at | DateTime | No | Record update time |

### RaceResult

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | Integer | PK | Auto-increment |
| race_id | String | FK | Race ID |
| horse_id | String | FK | Horse ID |
| jockey_id | String | FK | Jockey ID |
| trainer_id | String | FK | Trainer ID |
| finish_position | Integer | No | Finish position (0=DNF) |
| bracket_number | Integer | No | Bracket number (1-8) |
| horse_number | Integer | No | Horse number |
| odds | Float | Yes | Win odds |
| popularity | Integer | Yes | Popularity rank |
| weight | Integer | Yes | Horse weight (kg) |
| weight_diff | Integer | Yes | Weight change |
| time | String | No | Finish time |
| margin | String | No | Margin from winner |
| last_3f | Float | Yes | Last 3 furlongs time (seconds) |
| sex | String | Yes | Sex (Male/Female/Gelding) - NEW |
| age | Integer | Yes | Age - NEW |
| impost | Float | Yes | Impost weight (kg) - NEW |
| passing_order | String | Yes | Passing order (e.g., "2-1-1-1") - NEW |
| created_at | DateTime | No | Record creation time |
| updated_at | DateTime | No | Record update time |

Indexes:
- ix_race_results_horse_id (horse_id)
- ix_race_results_jockey_id (jockey_id)
- ix_race_results_trainer_id (trainer_id)

### Jockey

| Column | Type | Description |
|--------|------|-------------|
| id | String | PK - Jockey ID |
| name | String | Jockey name |

### Trainer

| Column | Type | Description |
|--------|------|-------------|
| id | String | PK - Trainer ID |
| name | String | Trainer name |

### Owner

| Column | Type | Description |
|--------|------|-------------|
| id | String | PK - Owner ID |
| name | String | Owner name |

### Breeder

| Column | Type | Description |
|--------|------|-------------|
| id | String | PK - Breeder ID |
| name | String | Breeder name |

## Database

- Engine: SQLite
- ORM: SQLAlchemy 2.0+
- Default path: `data/keiba.db`

## Recent Schema Changes

### 2026-01-19: RaceResult Expanded Fields

Added 4 new columns to RaceResult for race-time horse attributes:

| Column | Source | Description |
|--------|--------|-------------|
| sex | Column 4 (first char) | Sex parsed from "bo3" format |
| age | Column 4 (digits) | Age parsed from "bo3" format |
| impost | Column 5 | Weight carried (e.g., 57.0 kg) |
| passing_order | Column 10 | Corner passing positions |

These fields are:
- Parsed by RaceDetailScraper._parse_horse_row()
- Saved by CLI._save_race_data()
- Available for analysis queries

## Migration Notes

When adding columns to existing tables:
```sql
ALTER TABLE race_results ADD COLUMN sex VARCHAR;
ALTER TABLE race_results ADD COLUMN age INTEGER;
ALTER TABLE race_results ADD COLUMN impost REAL;
ALTER TABLE race_results ADD COLUMN passing_order VARCHAR;
```
