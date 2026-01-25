# Backend Codemap

> Freshness: 2026-01-25 (Verified: CLI commands, Services, Scrapers, Backtest, Tansho simulation)

## Overview

バックエンド構造のコードマップ。CLI、サービス層、スクレイパーの詳細。

## CLI (keiba/cli.py)

### Entry Point

```python
@click.group()
def main():
    """競馬データ収集CLI"""
```

### Commands

```
cli.py
├── scrape          # レースデータ収集（年月指定）
├── scrape-horses   # 馬詳細データ収集
├── analyze         # レース分析 + ML予測
├── predict         # 出馬表URLから予測
├── predict-day     # 指定日・競馬場の全レース予測
├── review-day      # 予測結果と実績比較（複勝・単勝シミュレーション）
├── migrate-grades  # グレード情報マイグレーション
├── backtest        # ML予測バックテスト
├── backtest-fukusho # 複勝シミュレーション
└── train           # MLモデル学習・保存
```

### Internal Classes

```python
class SQLAlchemyRaceResultRepository:
    """RaceResultRepositoryプロトコルの実装"""

    def __init__(self, session): ...

    def get_past_results(
        self, horse_id: str, before_date: str, limit: int = 20
    ) -> list[dict]:
        """指定日より前の過去成績を取得（データリーク防止）"""
```

### Helper Functions

| Function | Lines | Purpose |
|----------|-------|---------|
| `extract_race_id_from_url()` | 36-48 | レースURLからID抽出 |
| `extract_race_id_from_shutuba_url()` | 51-63 | 出馬表URLからID抽出 |
| `parse_race_date()` | 66-81 | 日付文字列パース |
| `_save_race_data()` | 165-247 | レースデータDB保存 |
| `_update_horse()` | 314-358 | 馬情報更新 |
| `_get_horse_past_results()` | 552-595 | 馬の過去成績取得 |
| `_build_training_data()` | 598-725 | ML学習データ構築 |
| `_calculate_past_stats()` | 728-764 | 派生特徴量計算 |
| `_print_score_table()` | 767-795 | スコアテーブル表示 |
| `_print_score_table_with_ml()` | 971-1009 | ML付きスコアテーブル表示 |
| `_print_prediction_table()` | 1256-1393 | 予測結果テーブル表示 |
| `_get_race_ids_for_venue()` | 1396-1417 | 競馬場コードフィルタ |
| `_save_predictions_markdown()` | 1420-1514 | 予測結果Markdown保存 |
| `_parse_predictions_markdown()` | 1673-1789 | 予測Markdownパース |
| `_calculate_fukusho_simulation()` | 1792-1906 | 複勝シミュレーション計算 |
| `_calculate_tansho_simulation()` | 1909-1988 | 単勝シミュレーション計算 |
| `_append_review_to_markdown()` | 1991- | 検証結果Markdown追記 |

## Services (keiba/services/)

### PredictionService

```
keiba/services/prediction_service.py
│
├── Imports
│   ├── analyzers/factors/ (7 factors)
│   ├── analyzers/score_calculator
│   └── models/entry (ShutubaData, RaceEntry)
│
├── PredictionResult (dataclass, frozen=True)
│   ├── horse_number: int
│   ├── horse_name: str
│   ├── horse_id: str
│   ├── ml_probability: float
│   ├── factor_scores: dict[str, float | None]
│   ├── total_score: float | None
│   ├── combined_score: float | None      # NEW
│   └── rank: int
│
├── RaceResultRepository (Protocol)
│   └── get_past_results(horse_id, before_date, limit) -> list
│
└── PredictionService (class)
    ├── FACTOR_NAMES = [7 factor names]
    ├── __init__(repository, model_path=None)
    ├── _load_model(model_path)
    ├── predict_from_shutuba(shutuba_data) -> list[PredictionResult]
    ├── _calculate_factor_scores(entry, past_results, race_info)
    ├── _calculate_ml_probability(entry, past_results, factor_scores, race_info)
    ├── _calculate_combined_score(ml_prob, max_ml_prob, total_score)  # NEW
    └── _calculate_past_stats(past_results, horse_id)
```

### Combined Score Calculation

```python
def _calculate_combined_score(
    self,
    ml_probability: float,
    max_ml_probability: float,
    total_score: float | None,
) -> float | None:
    """複合スコアを幾何平均で計算

    Formula:
        normalized_ml = (ml_probability / max_ml_probability) * 100
        combined = sqrt(normalized_ml * total_score)
    """
```

## Scrapers (keiba/scrapers/)

### Structure

```
keiba/scrapers/
├── __init__.py          # 公開インポート
├── base.py              # BaseScraper基底クラス
├── race_list.py         # RaceListScraper
├── race_detail.py       # RaceDetailScraper
├── horse_detail.py      # HorseDetailScraper
└── shutuba.py           # ShutubaScraper
```

### RaceListScraper

```python
class RaceListScraper:
    """db.netkeiba.com/race/list/からレース一覧を取得"""

    def fetch_race_urls(
        self, year: int, month: int, day: int, jra_only: bool = False
    ) -> list[str]:
        """指定日のレースURL一覧を取得"""
```

### RaceDetailScraper

```python
class RaceDetailScraper:
    """db.netkeiba.com/race/からレース詳細を取得"""

    def fetch_race_detail(self, race_id: str) -> dict:
        """レース詳細と結果を取得"""

    def fetch_payouts(self, race_id: str) -> list[dict]:
        """複勝払戻金を取得

        Returns:
            [{"horse_number": 5, "payout": 150}, ...]
        """

    def fetch_tansho_payout(self, race_id: str) -> dict | None:
        """単勝払戻金を取得

        Returns:
            {"horse_number": 5, "payout": 350} or None
        """
```

### HorseDetailScraper

```python
class HorseDetailScraper:
    """db.netkeiba.com/horse/から馬詳細を取得"""

    def fetch_horse_detail(self, horse_id: str) -> dict:
        """馬の詳細情報（血統含む）を取得"""
```

### ShutubaScraper

```python
class ShutubaScraper:
    """race.netkeiba.com/race/shutuba.htmlから出馬表を取得"""

    def fetch_shutuba(self, race_id: str) -> ShutubaData:
        """出馬表データを取得（イミュータブル）"""
```

## Database Layer (keiba/db.py)

### Functions

```python
def get_engine(db_path: str) -> Engine:
    """SQLiteエンジン作成"""

@contextmanager
def get_session(engine: Engine) -> Generator[Session, None, None]:
    """セッション取得（自動コミット/ロールバック）"""

def init_db(engine: Engine) -> None:
    """テーブル初期化（冪等）"""
```

## ML Layer (keiba/ml/)

### Structure

```
keiba/ml/
├── __init__.py
├── feature_builder.py   # 特徴量構築（19特徴量）
├── trainer.py           # LightGBMモデル学習
├── predictor.py         # 予測実行
└── model_utils.py       # ユーティリティ
```

### Trainer

```python
class Trainer:
    """LightGBMモデル学習"""

    MIN_SAMPLES = 100

    # Normal mode params
    _NORMAL_PARAMS = {
        "num_leaves": 31,
        "learning_rate": 0.05,
        "n_estimators": 100,
    }

    # Lightweight mode params (backtest)
    _LIGHTWEIGHT_PARAMS = {
        "num_leaves": 15,
        "learning_rate": 0.1,
        "n_estimators": 50,
    }

    def __init__(self, lightweight: bool = False): ...
    def train(self, X, y): ...
    def train_with_cv(self, X, y, n_splits=5) -> dict: ...
    def get_feature_importance(self) -> np.ndarray: ...
    def save_model(self, path: str) -> None: ...
```

### Model Utils

```python
def find_latest_model(model_dir: str) -> str | None:
    """最新の.joblibファイルを検索（st_mtime順）"""
```

## Backtest Layer (keiba/backtest/)

### Structure

```
keiba/backtest/
├── __init__.py
├── backtester.py        # BacktestEngine
├── fukusho_simulator.py # FukushoSimulator
├── metrics.py           # MetricsCalculator
├── reporter.py          # BacktestReporter
├── factor_calculator.py # ファクター計算
└── cache.py             # キャッシュ機構
```

### FukushoSimulator

```python
class FukushoSimulator:
    """複勝馬券シミュレータ"""

    def __init__(self, db_path: str): ...

    def simulate_race(self, race_id: str, top_n: int = 3) -> FukushoRaceResult:
        """1レースのシミュレーション"""

    def simulate_period(
        self,
        from_date: str,
        to_date: str,
        venues: list[str] | None = None,
        top_n: int = 3,
    ) -> FukushoSummary:
        """期間シミュレーション"""
```

### BacktestEngine

```python
class BacktestEngine:
    """ウォークフォワード検証エンジン"""

    MIN_TRAINING_SAMPLES = 100
    MAX_PAST_RESULTS_PER_HORSE = 20
    DEFAULT_FINISH_POSITION = 99

    def __init__(
        self,
        db_path: str,
        start_date: str,
        end_date: str,
        retrain_interval: str,
    ): ...

    def run(self) -> Generator[RaceBacktestResult, None, None]: ...
```

## Constants (keiba/constants.py)

```python
JRA_COURSE_CODES: dict[str, str] = {
    "01": "札幌",
    "02": "函館",
    "03": "福島",
    "04": "新潟",
    "05": "東京",
    "06": "中山",
    "07": "中京",
    "08": "京都",
    "09": "阪神",
    "10": "小倉",
}
```

## Configuration (keiba/config/)

### weights.py

```python
FACTOR_WEIGHTS = {
    "past_results": 0.143,
    "course_fit": 0.143,
    "time_index": 0.143,
    "last_3f": 0.143,
    "popularity": 0.143,
    "pedigree": 0.143,
    "running_style": 0.142,
}
# Total: 1.000
```

### pedigree_master.py

種牡馬の系統・距離適性マスターデータ。

## Request/Response Flow

### predict command

```
1. URL解析 → race_id抽出
2. ShutubaScraper.fetch_shutuba(race_id) → ShutubaData
3. SQLAlchemyRaceResultRepository作成
4. find_latest_model() → model_path
5. PredictionService(repository, model_path)
6. service.predict_from_shutuba(shutuba_data) → list[PredictionResult]
7. _print_prediction_table(predictions)
```

### train command

```
1. get_engine(db) → Engine
2. get_session(engine) → Session
3. _build_training_data(session, cutoff_date) → (features, labels)
4. FeatureBuilder().get_feature_names() → feature_names
5. np.array(features) → X, np.array(labels) → y
6. Trainer().train_with_cv(X, y, n_splits=5) → metrics
7. trainer.save_model(output) → .joblib file
```

## Error Handling

- スクレイピングエラー: 個別レースをスキップ、継続処理
- DB接続エラー: 例外をre-raise、セッションロールバック
- モデルロードエラー: self._model = None、因子スコアのみで予測
- 日付パースエラー: SystemExit(1)で終了、エラーメッセージ表示
