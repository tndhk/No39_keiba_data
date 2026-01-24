# Data Models Codemap

> Freshness: 2026-01-24 (Verified against codebase)

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

+------------------+
| Entry DTOs (NEW) |
+------------------+
| RaceEntry        |
| ShutubaData      |
+------------------+
```

## ORM Models (SQLAlchemy)

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
| grade | String | Yes | Race grade (G1/G2/G3/L/OP/etc) |

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
| sex | String | Yes | Sex (Male/Female/Gelding) |
| age | Integer | Yes | Age |
| impost | Float | Yes | Impost weight (kg) |
| passing_order | String | Yes | Passing order (e.g., "2-1-1-1") |
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

## DTO Models (Dataclasses) - NEW

### RaceEntry (keiba/models/entry.py)

Immutable dataclass for race entry data from shutuba page.

| Field | Type | Optional | Description |
|-------|------|----------|-------------|
| horse_id | str | No | Horse ID |
| horse_name | str | No | Horse name |
| horse_number | int | No | Horse number in race |
| bracket_number | int | No | Bracket (waku) number |
| jockey_id | str | No | Jockey ID |
| jockey_name | str | No | Jockey name |
| impost | float | No | Weight carried (kg) |
| sex | str | Yes | Horse sex |
| age | int | Yes | Horse age |

```python
@dataclass(frozen=True)
class RaceEntry:
    horse_id: str
    horse_name: str
    horse_number: int
    bracket_number: int
    jockey_id: str
    jockey_name: str
    impost: float
    sex: Optional[str] = None
    age: Optional[int] = None
```

### ShutubaData (keiba/models/entry.py)

Immutable dataclass containing complete shutuba (race entry) data.

| Field | Type | Description |
|-------|------|-------------|
| race_id | str | Race ID |
| race_name | str | Race name |
| race_number | int | Race number (1-12) |
| course | str | Racecourse name |
| distance | int | Distance in meters |
| surface | str | Track surface |
| date | str | Race date (YYYY年M月D日 format) |
| entries | tuple[RaceEntry, ...] | Immutable tuple of entries |

```python
@dataclass(frozen=True)
class ShutubaData:
    race_id: str
    race_name: str
    race_number: int
    course: str
    distance: int
    surface: str
    date: str
    entries: tuple[RaceEntry, ...]
```

### PredictionResult (keiba/services/prediction_service.py)

Immutable dataclass for prediction results.

| Field | Type | Description |
|-------|------|-------------|
| horse_number | int | Horse number |
| horse_name | str | Horse name |
| horse_id | str | Horse ID |
| ml_probability | float | ML probability (0.0-1.0) |
| factor_scores | dict[str, float or None] | 7 factor scores |
| total_score | float or None | Weighted total score |
| rank | int | Prediction rank |

## Database

- Engine: SQLite
- ORM: SQLAlchemy 2.0+
- Default path: `data/keiba.db`

## Schema Changes History

### 2026-01-24: Entry DTOs Added

Added immutable DTOs for real-time prediction:

| DTO | Location | Purpose |
|-----|----------|---------|
| RaceEntry | keiba/models/entry.py | Single horse entry from shutuba |
| ShutubaData | keiba/models/entry.py | Complete shutuba page data |
| PredictionResult | keiba/services/prediction_service.py | Prediction output |

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

## Data Flow Patterns

### Historical Data (scrape command)

```
netkeiba.com/race/{id}
        |
        v
RaceDetailScraper.fetch_race_detail()
        |
        v
    dict (race + results)
        |
        v
CLI._save_race_data()
        |
        v
    Race + RaceResult (ORM)
        |
        v
    SQLite DB
```

### Real-time Prediction (predict command) - NEW

```
race.netkeiba.com/race/shutuba.html?race_id={id}
        |
        v
ShutubaScraper.fetch_shutuba()
        |
        v
    ShutubaData (DTO)
        |
        v
PredictionService.predict_from_shutuba()
        |
        +--> SQLAlchemyRaceResultRepository.get_past_results()
        |            |
        |            v
        |      list[dict] (past results from DB)
        |
        v
    PredictionResult (DTO)
```

## Migration Notes

When adding columns to existing tables:
```sql
ALTER TABLE race_results ADD COLUMN sex VARCHAR;
ALTER TABLE race_results ADD COLUMN age INTEGER;
ALTER TABLE race_results ADD COLUMN impost REAL;
ALTER TABLE race_results ADD COLUMN passing_order VARCHAR;
```

## Query Patterns

### Get horse past results (before specific date)

```python
session.query(RaceResult, Race)
    .join(Race, RaceResult.race_id == Race.id)
    .filter(RaceResult.horse_id == horse_id)
    .filter(Race.date < target_date)
    .order_by(Race.date.desc())
    .limit(20)
```

### Get races for analysis

```python
session.execute(
    select(Race)
    .where(Race.date == race_date, Race.course == venue)
    .order_by(Race.race_number)
).scalars().all()
```

### Get race results with field size

```python
session.query(RaceResult)
    .filter(RaceResult.race_id == race.id)
    .all()
```
