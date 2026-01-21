# Data Models Codemap

> Freshness: 2026-01-21T10:00:00+09:00

## Database Schema (SQLite)

### ER Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     horses      │     │     races       │     │    jockeys      │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ PK id (str)     │     │ PK id (str)     │     │ PK id (str)     │
│ name            │     │ name            │     │ name            │
│ sex             │     │ date            │     │ created_at      │
│ birth_year      │     │ course          │     │ updated_at      │
│ sire            │     │ race_number     │     └─────────────────┘
│ dam             │     │ distance        │
│ dam_sire        │     │ surface         │     ┌─────────────────┐
│ coat_color      │     │ weather         │     │    trainers     │
│ birthplace      │     │ track_condition │     ├─────────────────┤
│ trainer_id      │     │ grade           │     │ PK id (str)     │
│ owner_id        │     │ created_at      │     │ name            │
│ breeder_id      │     │ updated_at      │     │ created_at      │
│ total_races     │     └─────────────────┘     │ updated_at      │
│ total_wins      │              │              └─────────────────┘
│ total_earnings  │              │
│ created_at      │              │              ┌─────────────────┐
│ updated_at      │              │              │     owners      │
└─────────────────┘              │              ├─────────────────┤
         │                       │              │ PK id (str)     │
         │       ┌───────────────┴──────────┐   │ name            │
         │       │       race_results       │   │ created_at      │
         │       ├──────────────────────────┤   │ updated_at      │
         └──────→│ PK id (int, auto)        │   └─────────────────┘
                 │ FK race_id → races.id    │
                 │ FK horse_id → horses.id  │   ┌─────────────────┐
                 │ FK jockey_id → jockeys   │   │    breeders     │
                 │ FK trainer_id → trainers │   ├─────────────────┤
                 │ finish_position          │   │ PK id (str)     │
                 │ bracket_number           │   │ name            │
                 │ horse_number             │   │ created_at      │
                 │ odds                     │   │ updated_at      │
                 │ popularity               │   └─────────────────┘
                 │ weight                   │
                 │ weight_diff              │
                 │ time                     │
                 │ margin                   │
                 │ last_3f                  │
                 │ sex                      │
                 │ age                      │
                 │ impost                   │
                 │ passing_order            │
                 │ created_at               │
                 │ updated_at               │
                 └──────────────────────────┘
```

## Table Details

### races

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | TEXT | PK | レースID (例: "202405020811") |
| name | TEXT | No | レース名 |
| date | DATE | No | 開催日 |
| course | TEXT | No | 競馬場名 |
| race_number | INT | No | レース番号 |
| distance | INT | No | 距離 (m) |
| surface | TEXT | No | 芝/ダート |
| weather | TEXT | Yes | 天候 |
| track_condition | TEXT | Yes | 馬場状態 |
| grade | TEXT | Yes | G1/G2/G3/L/OP/etc |

### horses

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | TEXT | PK | netkeiba馬ID |
| name | TEXT | No | 馬名 |
| sex | TEXT | No | 性別 |
| birth_year | INT | No | 生年 |
| sire | TEXT | Yes | 父名 |
| dam | TEXT | Yes | 母名 |
| dam_sire | TEXT | Yes | 母父名 |
| coat_color | TEXT | Yes | 毛色 |
| birthplace | TEXT | Yes | 産地 |
| trainer_id | TEXT | Yes | 調教師ID |
| owner_id | TEXT | Yes | 馬主ID |
| breeder_id | TEXT | Yes | 生産者ID |
| total_races | INT | Yes | 通算出走数 |
| total_wins | INT | Yes | 通算勝利数 |
| total_earnings | INT | Yes | 獲得賞金(万円) |

### race_results

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INT | PK | Auto-increment |
| race_id | TEXT | FK | races.id |
| horse_id | TEXT | FK | horses.id |
| jockey_id | TEXT | FK | jockeys.id |
| trainer_id | TEXT | FK | trainers.id |
| finish_position | INT | No | 着順 (0=中止等) |
| bracket_number | INT | No | 枠番 |
| horse_number | INT | No | 馬番 |
| odds | REAL | Yes | 単勝オッズ |
| popularity | INT | Yes | 人気 |
| weight | INT | Yes | 馬体重 |
| weight_diff | INT | Yes | 馬体重増減 |
| time | TEXT | No | タイム |
| margin | TEXT | No | 着差 |
| last_3f | REAL | Yes | 上がり3F(秒) |
| sex | TEXT | Yes | 性別 |
| age | INT | Yes | 年齢 |
| impost | REAL | Yes | 斤量 |
| passing_order | TEXT | Yes | 通過順位 (例: "2-1-1-1") |

### Indexes

- `ix_race_results_horse_id` on race_results(horse_id)
- `ix_race_results_jockey_id` on race_results(jockey_id)
- `ix_race_results_trainer_id` on race_results(trainer_id)

## ML Feature Schema

### Feature Categories (19 features)

| Category | Features | Source |
|----------|----------|--------|
| Factor Scores (7) | past_results, course_fit, time_index, last_3f, popularity, pedigree, running_style | analyzers/factors/ |
| Raw Data (8) | odds, popularity, weight, weight_diff, age, impost, horse_number, field_size | race_results |
| Derived (4) | win_rate, top3_rate, avg_finish_position, days_since_last_race | Computed |

### Feature Builder Output

```python
{
    # Factor scores (0-100 or None)
    "past_results_score": float | None,
    "course_fit_score": float | None,
    "time_index_score": float | None,
    "last_3f_score": float | None,
    "popularity_score": float | None,
    "pedigree_score": float | None,
    "running_style_score": float | None,

    # Raw data
    "odds": float | None,
    "popularity": int | None,
    "weight": int | None,
    "weight_diff": int | None,
    "age": int | None,
    "impost": float | None,
    "horse_number": int,
    "field_size": int,

    # Derived
    "win_rate": float | None,
    "top3_rate": float | None,
    "avg_finish_position": float | None,
    "days_since_last_race": int | None,
}
```

## Factor Weights Configuration

```python
# keiba/config/weights.py
FACTOR_WEIGHTS = {
    "past_results": 0.143,   # 14.3%
    "course_fit": 0.143,     # 14.3%
    "time_index": 0.143,     # 14.3%
    "last_3f": 0.143,        # 14.3%
    "popularity": 0.143,     # 14.3%
    "pedigree": 0.143,       # 14.3%
    "running_style": 0.142,  # 14.2% (端数調整)
}
# Total: 1.000
```

## Backtest Data Structures

### PredictionResult

```python
# keiba/backtest/metrics.py

@dataclass
class PredictionResult:
    """1頭の予測結果"""
    horse_number: int          # 馬番
    horse_name: str            # 馬名
    ml_probability: float | None  # ML予測確率
    ml_rank: int | None        # ML予測順位
    factor_rank: int           # 7ファクター順位
    actual_rank: int           # 実際の着順
```

### RaceBacktestResult

```python
# keiba/backtest/metrics.py

@dataclass
class RaceBacktestResult:
    """1レースのバックテスト結果"""
    race_id: str               # レースID
    race_date: str             # YYYY-MM-DD
    race_name: str             # レース名
    venue: str                 # 競馬場
    predictions: list[PredictionResult]  # 予測結果リスト
```

### Backtest Metrics Schema

```python
# MetricsCalculator.calculate() の出力

{
    'ml': {
        'precision_at_1': float,     # 1位予測の1着率
        'precision_at_3': float,     # 上位3頭予測の3着以内率
        'hit_rate_rank_1': float,    # 1位指名の3着以内率
        'hit_rate_rank_2': float,    # 2位指名の3着以内率
        'hit_rate_rank_3': float,    # 3位指名の3着以内率
    },
    'factor': {
        'precision_at_1': float,     # 同上（7ファクター版）
        'precision_at_3': float,
        'hit_rate_rank_1': float,
        'hit_rate_rank_2': float,
        'hit_rate_rank_3': float,
    }
}
```

### RetrainInterval Type

```python
# keiba/backtest/types.py

RetrainInterval = Literal["daily", "weekly", "monthly"]
```
