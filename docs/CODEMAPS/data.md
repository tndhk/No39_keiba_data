# Data Models Codemap

> Freshness: 2026-01-30 (Verified: Line counts, repository expansion)

## Database Schema (SQLite)

### ER Diagram

```
+-------------------+     +-------------------+     +-------------------+
|     horses        |     |     races         |     |    jockeys        |
+-------------------+     +-------------------+     +-------------------+
| PK id (str)       |     | PK id (str)       |     | PK id (str)       |
| name              |     | name              |     | name              |
| sex               |     | date              |     | created_at        |
| birth_year        |     | course            |     | updated_at        |
| sire              |     | race_number       |     +-------------------+
| dam               |     | distance          |
| dam_sire          |     | surface           |     +-------------------+
| coat_color        |     | weather           |     |    trainers       |
| birthplace        |     | track_condition   |     +-------------------+
| trainer_id        |     | grade             |     | PK id (str)       |
| owner_id          |     | created_at        |     | name              |
| breeder_id        |     | updated_at        |     | created_at        |
| total_races       |     +-------------------+     | updated_at        |
| total_wins        |              |              +-------------------+
| total_earnings    |              |
| created_at        |              |              +-------------------+
| updated_at        |              |              |     owners        |
+-------------------+              |              +-------------------+
         |                         |              | PK id (str)       |
         |       +-----------------+----------+   | name              |
         |       |       race_results         |   | created_at        |
         |       +----------------------------+   | updated_at        |
         +------>| PK id (int, auto)          |   +-------------------+
                 | FK race_id -> races.id     |
                 | FK horse_id -> horses.id   |   +-------------------+
                 | FK jockey_id -> jockeys    |   |    breeders       |
                 | FK trainer_id -> trainers  |   +-------------------+
                 | finish_position            |   | PK id (str)       |
                 | bracket_number             |   | name              |
                 | horse_number               |   | created_at        |
                 | odds                       |   | updated_at        |
                 | popularity                 |   +-------------------+
                 | weight                     |
                 | weight_diff                |
                 | time                       |
                 | margin                     |
                 | last_3f                    |
                 | sex                        |
                 | age                        |
                 | impost                     |
                 | passing_order              |
                 | created_at                 |
                 | updated_at                 |
                 +----------------------------+
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

バックテストパフォーマンス最適化のため追加されたインデックス:

| Index Name | Table | Column | Purpose |
|------------|-------|--------|---------|
| ix_race_results_race_id | race_results | race_id | レース結果JOIN高速化 |
| ix_races_date | races | date | 日付範囲クエリ高速化 |
| ix_race_results_horse_id | race_results | horse_id | 馬の過去成績取得高速化 |
| ix_race_results_jockey_id | race_results | jockey_id | 騎手成績取得高速化 |
| ix_race_results_trainer_id | race_results | trainer_id | 調教師成績取得高速化 |

**パフォーマンス効果**: バックテスト実行時間 38分 -> 4分（約90%削減）

既存DBへのインデックス追加:
```bash
python scripts/add_indexes.py data/keiba.db
```

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

## Service Layer Data Structures

### PredictionResult

```python
# keiba/services/prediction_service.py

@dataclass(frozen=True)
class PredictionResult:
    """予測結果（イミュータブル）"""
    horse_number: int           # 馬番
    horse_name: str             # 馬名
    horse_id: str               # 馬ID
    ml_probability: float       # ML予測確率 (0.0-1.0)
    factor_scores: dict[str, float | None]  # 7因子スコア
    total_score: float | None   # 重み付き総合スコア (0-100)
    combined_score: float | None  # 複合スコア (幾何平均)  # NEW
    rank: int                   # 予測順位 (combined_score降順)
```

### Combined Score Formula

```python
def _calculate_combined_score(
    ml_probability: float,
    max_ml_probability: float,
    total_score: float | None,
) -> float | None:
    """
    normalized_ml = (ml_probability / max_ml_probability) * 100
    combined = sqrt(normalized_ml * total_score)
    """
```

## Backtest Data Structures

### PredictionResult (backtest/metrics.py)

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

### BacktestEngine Class Constants

```python
# keiba/backtest/backtester.py

MIN_TRAINING_SAMPLES = 100       # 学習に必要な最小サンプル数
MAX_PAST_RESULTS_PER_HORSE = 20  # 馬ごとの過去成績取得上限
DEFAULT_FINISH_POSITION = 99     # 着順不明時のデフォルト値
```

### BacktestEngine Batch Query Outputs

```python
# _get_horses_past_results_batch() の返却値
# horse_idをキー、過去成績リストを値とする辞書
dict[str, list[dict]]  # {horse_id: [{"race_id": ..., "finish_position": ..., ...}, ...]}

# _get_horses_batch() の返却値
# horse_idをキー、Horseオブジェクトを値とする辞書
dict[str, Horse]  # {horse_id: Horse(id=..., name=..., sex=..., ...)}
```

## Entry DTOs (keiba/models/entry.py)

### RaceEntry

```python
@dataclass(frozen=True)
class RaceEntry:
    """出走馬エントリー（イミュータブル）"""
    horse_id: str           # 馬ID
    horse_name: str         # 馬名
    horse_number: int       # 馬番
    bracket_number: int     # 枠番
    jockey_id: str          # 騎手ID
    jockey_name: str        # 騎手名
    impost: float           # 斤量
    sex: Optional[str] = None   # 性別
    age: Optional[int] = None   # 年齢
```

### ShutubaData

```python
@dataclass(frozen=True)
class ShutubaData:
    """出馬表データ（イミュータブル）"""
    race_id: str                    # レースID
    race_name: str                  # レース名
    race_number: int                # レース番号 (1-12)
    course: str                     # 競馬場名
    distance: int                   # 距離 (m)
    surface: str                    # 芝/ダート
    date: str                       # 開催日
    entries: tuple[RaceEntry, ...]  # 出走馬リスト（イミュータブル）
```

## Scraper Methods

### RaceDetailScraper

| Method | Description | Returns |
|--------|-------------|---------|
| `fetch_race_detail(race_id)` | レース詳細と結果を取得 | `dict` (race info + results) |
| `fetch_payouts(race_id)` | 複勝払戻金を取得 | `list[dict]` (horse_number, payout) |

### fetch_payouts Output Schema

```python
# RaceDetailScraper.fetch_payouts() の返却値
[
    {"horse_number": 5, "payout": 150},   # 1着馬の複勝払戻金
    {"horse_number": 3, "payout": 280},   # 2着馬の複勝払戻金
    {"horse_number": 8, "payout": 190},   # 3着馬の複勝払戻金
]
```

## Prediction Markdown Schema

### Prediction File (docs/predictions/YYYY-MM-DD-{venue}.md)

```markdown
# YYYY-MM-DD {競馬場} 予測結果

生成日時: YYYY-MM-DD HH:MM:SS

## {N}R {レース名}
race_id: {race_id}
{surface}{distance}m

| 順位 | 馬番 | 馬名 | ML確率 | 総合 |
|:---:|:---:|:---|:---:|:---:|
| 1 | 5 | ホースA | 45.2% | 68.5 |
...

---

## 検証結果  (review-dayで追記)

検証日時: YYYY-MM-DD HH:MM:SS

### 複勝シミュレーション

#### 予測1位のみに賭けた場合
- 対象レース数: 12
- 的中数: 7
- 的中率: 58.3%
- 投資額: 1200円
- 払戻額: 1050円
- 回収率: 87.5%

#### 予測1-3位に各100円賭けた場合
...

### レース別結果
| R | 実際の3着以内 | 予測Top3 | Top1的中 | Top3的中数 |
...
```

## Fukusho Simulation Data Structures

### _calculate_fukusho_simulation Input/Output

```python
# Input: predictions (parsed from markdown)
predictions = {
    "races": [
        {
            "race_id": str,              # レースID (例: "202606010801")
            "race_number": int,          # レース番号
            "race_name": str,            # レース名
            "predictions": [
                {
                    "rank": int,         # 予測順位
                    "horse_number": int, # 馬番
                    "horse_name": str,   # 馬名
                    "ml_probability": float,  # ML確率 (0.0-1.0)
                }
            ]
        }
    ]
}

# Input: actual_results
actual_results = {
    race_number: [1着馬番, 2着馬番, 3着馬番],  # dict[int, list[int]]
}

# Input: payouts
payouts = {
    race_number: {馬番: 払戻金},  # dict[int, dict[int, int]]
}

# Output: simulation result
{
    "top1": {
        "hits": int,           # 的中数
        "total_races": int,    # 対象レース数
        "hit_rate": float,     # 的中率 (0.0-1.0)
        "payout": int,         # 払戻額合計
        "investment": int,     # 投資額合計
        "return_rate": float,  # 回収率 (払戻/投資)
    },
    "top3": {
        "hits": int,           # 的中数
        "total_bets": int,     # 賭け数
        "hit_rate": float,     # 的中率 (0.0-1.0)
        "payout": int,         # 払戻額合計
        "investment": int,     # 投資額合計
        "return_rate": float,  # 回収率 (払戻/投資)
    },
    "race_results": [
        {
            "race_number": int,
            "actual_top3": list[int],     # 実際の3着以内馬番
            "predicted_top3": list[int],  # 予測Top3馬番
            "top1_hit": bool,             # Top1的中フラグ
            "top3_hits": int,             # Top3中何頭的中したか
        }
    ]
}
```

## CLI Internal Data Structures

### VENUE_CODE_MAP

```python
# keiba/cli.py
VENUE_CODE_MAP = {
    "札幌": "01",
    "函館": "02",
    "福島": "03",
    "新潟": "04",
    "東京": "05",
    "中山": "06",
    "中京": "07",
    "京都": "08",
    "阪神": "09",
    "小倉": "10",
}
```

### race_id Format

```
202606010801
|  | | | |+-- レース番号 (01-12)
|  | | |+---- 開催日数 (01-12)
|  | |+------ 開催回数 (01-05)
|  |+-------- 競馬場コード (01-10)
+--+--------- 年 (西暦4桁)
```

## Simulator Data Structures

詳細は [backtest.md](./backtest.md) を参照。

### Summary of Simulator Types

| Simulator | RaceResult Type | Summary Type |
|-----------|-----------------|--------------|
| FukushoSimulator | FukushoRaceResult | FukushoSummary |
| TanshoSimulator | TanshoRaceResult | TanshoSummary |
| UmarenSimulator | UmarenRaceResult | UmarenSummary |
| SanrenpukuSimulator | SanrenpukuRaceResult | SanrenpukuSummary |

### Common Summary Fields

全Summaryクラスに共通するフィールド:

```python
@dataclass(frozen=True)
class *Summary:
    period_from: str           # 期間開始日 (YYYY-MM-DD)
    period_to: str             # 期間終了日 (YYYY-MM-DD)
    total_races: int           # 総レース数
    total_hits: int            # 総的中数
    hit_rate: float            # 的中率 (0.0-1.0)
    total_investment: int      # 総投資額
    total_payout: int          # 総払戻額
    return_rate: float         # 回収率 (払戻/投資)
    race_results: tuple[*RaceResult, ...]  # レース別結果
```

### FukushoRaceResult (複勝)

```python
@dataclass(frozen=True)
class FukushoRaceResult:
    race_id: str
    race_name: str
    venue: str
    race_date: str
    top_n_predictions: tuple[int, ...]  # 予測top-n馬番
    fukusho_horses: tuple[int, ...]     # 複勝対象馬番（3着以内）
    hits: tuple[int, ...]               # 的中した馬番
    payouts: tuple[int, ...]            # 的中した払戻額
    investment: int                     # 投資額（100 * top_n）
    payout_total: int                   # 払戻総額
```

### TanshoRaceResult (単勝)

```python
@dataclass(frozen=True)
class TanshoRaceResult:
    race_id: str
    race_name: str
    venue: str
    race_date: str
    top_n_predictions: tuple[int, ...]  # 予測top-n馬番
    winning_horse: int | None           # 1着馬の馬番
    hit: bool                           # 的中したかどうか
    payout: int                         # 払戻額（外れは0）
    investment: int                     # 投資額（100 * top_n）
```

### UmarenRaceResult (馬連)

```python
@dataclass(frozen=True)
class UmarenRaceResult:
    race_id: str
    race_name: str
    venue: str
    race_date: str
    bet_combinations: tuple[tuple[int, int], ...]  # 購入組み合わせ（3点）
    actual_pair: tuple[int, int] | None            # 実際の1-2着
    hit: bool
    payout: int
    investment: int                                # 300円固定（3点x100円）
```

### SanrenpukuRaceResult (三連複)

```python
@dataclass(frozen=True)
class SanrenpukuRaceResult:
    race_id: str
    race_name: str
    venue: str
    race_date: str
    predicted_trio: tuple[int, int, int]       # 予測Top3馬番（昇順）
    actual_trio: tuple[int, int, int] | None   # 実際の3着以内（昇順）
    hit: bool
    payout: int
    investment: int                            # 100円固定（1点買い）
```

## Model Storage

### File Format

```
data/models/
└── model_YYYYMMDD_HHMMSS.joblib  # LightGBM model (joblib serialized)
```

### Model Loading

```python
# keiba/ml/model_utils.py
def find_latest_model(model_dir: str) -> str | None:
    """最新の.joblibファイルパスを返す（st_mtime順）"""

# keiba/services/prediction_service.py
def _load_model(self, model_path: str) -> None:
    """joblib.loadでモデルをロード"""
    import joblib
    self._model = joblib.load(model_path)
```

### Model Saving

```python
# keiba/ml/trainer.py
def save_model(self, path: str) -> None:
    """joblib.dumpでモデルを保存"""
    import joblib
    joblib.dump(self.model, path)
```
