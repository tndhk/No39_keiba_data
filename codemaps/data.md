# Data Models Codemap

> Freshness: 2026-01-19T09:15:00+09:00

## Entity Relationship

```
┌─────────┐     ┌─────────────┐     ┌─────────┐
│  Race   │────<│ RaceResult  │>────│  Horse  │
└─────────┘     └──────┬──────┘     └────┬────┘
                       │                  │
              ┌────────┼────────┐         │
              ▼        ▼        ▼         │
         ┌────────┐┌────────┐┌────────┐   │
         │ Jockey ││Trainer ││ Owner  │   │
         └────────┘└────────┘└────────┘   │
                                          │
                                    ┌─────┴─────┐
                                    │  Breeder  │
                                    └───────────┘
```

## Models

### Race

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | String | PK | Race ID (e.g., 202403010101) |
| name | String | No | Race name |
| date | Date | No | Race date |
| course | String | No | Venue (e.g., 中山) |
| race_number | Integer | No | Race number (1-12) |
| distance | Integer | No | Distance in meters |
| surface | String | No | Track type (芝/ダート) |
| weather | String | Yes | Weather condition |
| track_condition | String | Yes | Track condition (良/稍/重/不) |

### Horse

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | String | PK | Horse ID |
| name | String | No | Horse name |
| sex | String | No | Gender (牡/牝/セ) |
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
| total_earnings | Integer | Yes | Total earnings (万円) |

### RaceResult

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | Integer | PK | Auto-increment |
| race_id | String | FK | Race ID |
| horse_id | String | FK | Horse ID |
| jockey_id | String | FK | Jockey ID |
| trainer_id | String | FK | Trainer ID |
| finish_position | Integer | No | Finish position (0=DNF) |
| bracket_number | Integer | Yes | Bracket number (1-8) |
| horse_number | Integer | Yes | Horse number |
| odds | Float | Yes | Win odds |
| popularity | Integer | Yes | Popularity rank |
| weight | Integer | Yes | Horse weight (kg) |
| weight_diff | Integer | Yes | Weight change |
| time | String | Yes | Finish time |
| margin | String | Yes | Margin from winner |

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

## Migration Notes

When adding columns to existing tables:
```sql
ALTER TABLE horses ADD COLUMN column_name TYPE;
```
