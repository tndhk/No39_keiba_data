# Backtest Codemap

> Freshness: 2026-01-29 (Verified: BaseSimulator, scraper reuse, rate limiting integration)

## Overview

バックテストモジュールのコードマップ。各券種シミュレータとバックテストエンジンの詳細。

## Package Structure

```
keiba/backtest/                        # 2400行+
+-- __init__.py                        # 公開API (53行)
+-- backtester.py                      # BacktestEngine (1093行)
+-- base_simulator.py                  # BaseSimulator（基底クラス・スクレイパー再利用） (176行)
+-- fukusho_simulator.py               # FukushoSimulator (367行)
+-- tansho_simulator.py                # TanshoSimulator (291行)
+-- umaren_simulator.py                # UmarenSimulator (316行)
+-- sanrenpuku_simulator.py            # SanrenpukuSimulator (290行)
+-- metrics.py                         # MetricsCalculator (198行)
+-- reporter.py                        # BacktestReporter (168行)
+-- factor_calculator.py               # ファクター計算 (249行)
+-- cache.py                           # キャッシュ機構 (125行)
```

## CLI Commands

| Command | Handler | Description | Options |
|---------|---------|-------------|---------|
| `backtest` | `commands/backtest.py:backtest()` | ML予測バックテスト | --db, --from, --to, --months, --retrain-interval, -v |
| `backtest-fukusho` | `commands/backtest.py:backtest_fukusho()` | 複勝シミュレーション | --db, --from, --to, --last-week, --top-n, --venue, -v |
| `backtest-tansho` | `commands/backtest.py:backtest_tansho()` | 単勝シミュレーション | --db, --from, --to, --last-week, --top-n, --venue, -v |
| `backtest-umaren` | `commands/backtest.py:backtest_umaren()` | 馬連シミュレーション | --db, --from, --to, --last-week, --venue, -v |
| `backtest-sanrenpuku` | `commands/backtest.py:backtest_sanrenpuku()` | 三連複シミュレーション | --db, --from, --to, --last-week, --venue, -v |
| `backtest-all` | `commands/backtest.py:backtest_all()` | 全券種一括バックテスト | --db, --from, --to, --last-week, --top-n, --venue, -v |

## Module Exports (__init__.py)

```python
__all__ = [
    # Core Engine
    "BacktestEngine",
    "RetrainInterval",

    # Metrics
    "PredictionResult",
    "RaceBacktestResult",
    "MetricsCalculator",
    "BacktestReporter",

    # Fukusho Simulator
    "FukushoRaceResult",
    "FukushoSimulator",
    "FukushoSummary",

    # Tansho Simulator
    "TanshoRaceResult",
    "TanshoSimulator",
    "TanshoSummary",

    # Umaren Simulator
    "UmarenRaceResult",
    "UmarenSimulator",
    "UmarenSummary",

    # Sanrenpuku Simulator
    "SanrenpukuRaceResult",
    "SanrenpukuSimulator",
    "SanrenpukuSummary",
]
```

## Simulators

### Common Architecture

全シミュレータは `BaseSimulator` を継承し、同一のアーキテクチャに従う。
`BaseSimulator` は単一の `RaceDetailScraper` インスタンスを保持し、全レースで再利用する。
これにより `BaseScraper._global_last_request_time` によるグローバルレート制限が自動適用される。

```
BaseSimulator (base_simulator.py)
+-- __init__(db_path: str)
|   +-- self._scraper = RaceDetailScraper()  # 再利用
+-- _get_session() -> Session
+-- _get_races_in_period(session, from_date, to_date, venues) -> list[Race]
+-- _build_shutuba_from_race_results(race, results) -> ShutubaData
+-- simulate_period(from_date, to_date, venues, ...) -> TSummary  # Template Method
+-- simulate_race(race_id, ...) -> TRaceResult  # abstract
+-- _build_summary(period_from, period_to, results) -> TSummary  # abstract

FukushoSimulator(BaseSimulator[FukushoRaceResult, FukushoSummary])
TanshoSimulator(BaseSimulator[TanshoRaceResult, TanshoSummary])
UmarenSimulator(BaseSimulator[UmarenRaceResult, UmarenSummary])
SanrenpukuSimulator(BaseSimulator[SanrenpukuRaceResult, SanrenpukuSummary])
```

### FukushoSimulator (367行)

複勝馬券シミュレータ。予測Top-Nの各馬に100円ずつ賭け、3着以内なら的中。

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

@dataclass(frozen=True)
class FukushoSummary:
    period_from: str
    period_to: str
    total_races: int
    total_bets: int
    total_hits: int
    hit_rate: float                     # 的中率 (0.0-1.0)
    total_investment: int
    total_payout: int
    return_rate: float                  # 回収率 (払戻/投資)
    race_results: tuple[FukushoRaceResult, ...]
```

### TanshoSimulator (291行)

単勝馬券シミュレータ。予測Top-Nの各馬に100円ずつ賭け、1着なら的中。

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

@dataclass(frozen=True)
class TanshoSummary:
    period_from: str
    period_to: str
    total_races: int
    total_bets: int
    total_hits: int
    hit_rate: float
    total_investment: int
    total_payout: int
    return_rate: float
    race_results: tuple[TanshoRaceResult, ...]
```

### UmarenSimulator (316行)

馬連馬券シミュレータ。予測Top3から3点買い（1-2, 1-3, 2-3）。

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

@dataclass(frozen=True)
class UmarenSummary:
    period_from: str
    period_to: str
    total_races: int
    total_hits: int
    hit_rate: float
    total_investment: int
    total_payout: int
    return_rate: float
    race_results: tuple[UmarenRaceResult, ...]
```

### SanrenpukuSimulator (290行)

三連複馬券シミュレータ。予測Top3の1点買い。

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

@dataclass(frozen=True)
class SanrenpukuSummary:
    period_from: str
    period_to: str
    total_races: int
    total_hits: int
    hit_rate: float
    total_investment: int
    total_payout: int
    return_rate: float
    race_results: tuple[SanrenpukuRaceResult, ...]
```

## BacktestEngine (1093行)

ウォークフォワード検証エンジン。MLモデルの再学習と予測精度の検証を行う。

```python
class BacktestEngine:
    """ウォークフォワード検証エンジン"""

    # クラス定数
    MIN_TRAINING_SAMPLES = 100       # 学習に必要な最小サンプル数
    MAX_PAST_RESULTS_PER_HORSE = 20  # 馬ごとの過去成績取得上限
    DEFAULT_FINISH_POSITION = 99     # 着順不明時のデフォルト値

    def __init__(
        self,
        db_path: str,
        start_date: str,
        end_date: str,
        retrain_interval: str,  # "daily" | "weekly" | "monthly"
    ): ...

    def run(self) -> Generator[RaceBacktestResult, None, None]:
        """バックテストを実行（レース単位でyield）"""
```

### Internal Methods

| Method | Purpose |
|--------|---------|
| `_open_session()` | DBセッションを開く |
| `_close_session()` | DBセッションを閉じる |
| `_with_session(func)` | セッション管理デコレータ |
| `_get_horses_past_results_batch(horse_ids, before_date)` | 複数馬の過去成績を一括取得 |
| `_get_horses_batch(horse_ids)` | 複数馬の情報を一括取得 |
| `_should_retrain(current_date)` | 再学習が必要かを判定 |
| `_train_model(cutoff_date)` | モデルを学習 |

## Metrics (198行)

バックテスト精度評価指標の計算。

```python
@dataclass
class PredictionResult:
    """1頭の予測結果"""
    horse_number: int
    horse_name: str
    ml_probability: float | None
    ml_rank: int | None
    factor_rank: int
    actual_rank: int

@dataclass
class RaceBacktestResult:
    """1レースのバックテスト結果"""
    race_id: str
    race_date: str
    race_name: str
    venue: str
    predictions: list[PredictionResult]

class MetricsCalculator:
    @staticmethod
    def calculate(results: list[RaceBacktestResult]) -> dict:
        """精度指標を計算

        Returns:
            {
                'ml': {
                    'precision_at_1': float,
                    'precision_at_3': float,
                    'hit_rate_rank_1': float,
                    'hit_rate_rank_2': float,
                    'hit_rate_rank_3': float,
                },
                'factor': { ... }  # 同構造
            }
        """
```

## Reporter (168行)

バックテスト結果のレポート出力。

```python
class BacktestReporter:
    def __init__(self, start_date: str, end_date: str, retrain_interval: str): ...

    def print_race_detail(self, result: RaceBacktestResult) -> str:
        """1レースの詳細を文字列化"""

    def print_summary(self, results: list[RaceBacktestResult], metrics: dict) -> str:
        """サマリーを文字列化"""
```

## Dependencies

```
backtest/
+-- backtester.py
|   +-- db.py (get_engine, get_session)
|   +-- models/ (Race, RaceResult, Horse)
|   +-- analyzers/factors/ (7 factors)
|   +-- ml/ (Trainer, Predictor)
|
+-- base_simulator.py
|   +-- abc (ABC, abstractmethod)
|   +-- sqlalchemy (create_engine, select, Session)
|   +-- models/entry.py (RaceEntry, ShutubaData)
|   +-- models/race.py (Race)
|   +-- models/race_result.py (RaceResult)
|   +-- scrapers/race_detail.py (RaceDetailScraper) -- インスタンス再利用
|
+-- fukusho_simulator.py
|   +-- base_simulator.py (BaseSimulator)
|   +-- scrapers/race_detail.py (fetch_payouts) -- self._scraper経由
|   +-- services/prediction_service.py (PredictionService)
|
+-- tansho_simulator.py
|   +-- base_simulator.py (BaseSimulator)
|   +-- scrapers/race_detail.py (fetch_tansho_payout) -- self._scraper経由
|
+-- umaren_simulator.py
|   +-- base_simulator.py (BaseSimulator)
|   +-- scrapers/race_detail.py (fetch_umaren_payout) -- self._scraper経由
|
+-- sanrenpuku_simulator.py
    +-- base_simulator.py (BaseSimulator)
    +-- scrapers/race_detail.py (fetch_sanrenpuku_payout) -- self._scraper経由
```

## Internal Classes

### _BacktestRaceResultRepository

```python
# keiba/backtest/fukusho_simulator.py (共有)

class _BacktestRaceResultRepository:
    """バックテスト用のRaceResultRepositoryプロトコル実装

    PredictionServiceのrepository引数として使用。
    """

    def __init__(self, session: Session): ...

    def get_past_results(
        self, horse_id: str, before_date: str, limit: int = 20
    ) -> list[dict]:
        """指定日より前の過去成績を取得"""
```

## Data Flow

### Single Race Simulation

```
[race_id]
    | Simulator._get_session()
[Session]
    | Session.get(Race, race_id)
[Race + RaceResults]
    | Simulator._build_shutuba_from_race_results()
[ShutubaData]
    | PredictionService.predict_from_shutuba()
[list[PredictionResult]]
    | sorted by rank, [:top_n]
[top_n_predictions]
    | RaceDetailScraper.fetch_*_payout()
[Payout Data]
    | Hit determination
[*RaceResult]
```

### Period Simulation

```
[from_date, to_date, venues]
    | Simulator._get_races_in_period()
[list[Race]]
    | for race in races
        | Simulator.simulate_race(race.id)
[list[*RaceResult]]
    | aggregate totals
[*Summary]
```

### backtest-all Command

```
[CLI Options]
    | _resolve_date_range()
[from_date, to_date]
    | FukushoSimulator.simulate_period()
    | TanshoSimulator.simulate_period()
    | UmarenSimulator.simulate_period()
    | SanrenpukuSimulator.simulate_period()
[4 Summaries]
    | _format_results_table()
[Formatted Table]
    | aggregate totals
[Final Output]
```

## Test Structure

```
tests/backtest/
+-- __init__.py
+-- test_backtester.py              # BacktestEngineテスト
+-- test_base_simulator.py          # BaseSimulatorテスト
+-- test_backtest_repository.py     # バックテストリポジトリテスト
+-- test_metrics.py                 # MetricsCalculatorテスト
+-- test_reporter.py                # BacktestReporterテスト
+-- test_cache.py                   # キャッシュテスト
+-- test_cache_strategy.py          # キャッシュ戦略テスト
+-- test_cached_factor_calculator.py # キャッシュ付きファクター計算テスト

tests/cli/
+-- test_backtest_all.py            # backtest-allコマンドテスト

tests/scrapers/
+-- test_base_rate_limit.py         # レート制限テスト
```

## Betting Strategies

| 券種 | 購入点数 | 投資額/R | 的中条件 |
|------|----------|---------|---------|
| 複勝 | top_n点 | 100*top_n | Top-Nのいずれかが3着以内 |
| 単勝 | top_n点 | 100*top_n | Top-Nのいずれかが1着 |
| 馬連 | 3点 | 300円 | Top3の2頭が1-2着 |
| 三連複 | 1点 | 100円 | Top3の3頭が3着以内 |

## Output Format (backtest-all)

```
==========================================
全券種バックテスト: YYYY-MM-DD ~ YYYY-MM-DD
==========================================
対象レース数: N

+--------+--------+--------+-----------+-----------+--------+
| 券種   | 的中数 | 的中率 | 投資額    | 払戻額    | 回収率 |
+--------+--------+--------+-----------+-----------+--------+
| 複勝   |     XX |  XX.X% |    XX,XXX |    XX,XXX |  XX.X% |
| 単勝   |     XX |  XX.X% |    XX,XXX |    XX,XXX |  XX.X% |
| 馬連   |     XX |  XX.X% |    XX,XXX |    XX,XXX |  XX.X% |
| 三連複 |     XX |  XX.X% |    XX,XXX |    XX,XXX |  XX.X% |
+--------+--------+--------+-----------+-----------+--------+

総投資額: XX,XXX円
総払戻額: XX,XXX円
総回収率: XX.X%
```
