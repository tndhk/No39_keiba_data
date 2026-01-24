# Architecture Codemap

> Freshness: 2026-01-24 (Updated: predict command, services/, shutuba.py)

## System Overview

```
keiba/                    # 競馬データ収集・分析CLI
├── cli.py               # CLIエントリーポイント (Click)
├── db.py                # DB接続・セッション管理
├── constants.py         # 定数定義
├── models/              # SQLAlchemy ORM
│   └── entry.py         # 出馬表DTO（RaceEntry, ShutubaData）
├── scrapers/            # Webスクレイパー
│   └── shutuba.py       # 出馬表スクレイパー（race.netkeiba.com）
├── services/            # ビジネスロジックサービス
│   └── prediction_service.py  # 予測サービス（7因子+ML）
├── analyzers/           # レース分析エンジン
│   └── factors/         # スコア算出因子 (7種)
├── ml/                  # ML予測モジュール
├── backtest/            # バックテストモジュール
│   ├── __init__.py
│   ├── backtester.py    # BacktestEngine（ウォークフォワード検証）
│   ├── metrics.py       # MetricsCalculator（精度評価指標）
│   └── reporter.py      # BacktestReporter（結果出力）
├── config/              # 設定・マスタデータ
└── utils/               # ユーティリティ
scripts/                  # 運用スクリプト
└── add_indexes.py       # 既存DBへのインデックス追加
```

## Module Dependencies

```
cli.py
├── db.py (get_engine, get_session, init_db)
├── models/ (Horse, Jockey, Race, RaceResult, Trainer)
├── models/entry.py (RaceEntry, ShutubaData) - DTOs
├── scrapers/ (HorseDetailScraper, RaceDetailScraper, RaceListScraper)
├── scrapers/shutuba.py (ShutubaScraper) - 出馬表スクレイピング
├── services/prediction_service.py (PredictionService, PredictionResult)
├── analyzers/factors/ (7 factors)
├── analyzers/score_calculator.py
├── ml/ (FeatureBuilder, Trainer, Predictor)
├── backtest/ (BacktestEngine, MetricsCalculator, BacktestReporter)
└── utils/grade_extractor.py

analyzers/score_calculator.py
└── config/weights.py (FACTOR_WEIGHTS)

ml/trainer.py
├── lightgbm (LGBMClassifier)
└── sklearn (StratifiedKFold, metrics)

ml/predictor.py
└── lightgbm (LGBMClassifier)

ml/feature_builder.py
└── (pure Python, no external deps)

backtest/backtester.py
├── contextlib (contextmanager)
├── db.py (get_engine, get_session)
├── models/ (Race, RaceResult, Horse)
├── analyzers/factors/ (7 factors)
├── ml/ (Trainer, Predictor)
└── lightgbm (LGBMClassifier) [optional]
    └── BacktestEngine内部構造:
        ├── クラス定数: MIN_TRAINING_SAMPLES, MAX_PAST_RESULTS_PER_HORSE, DEFAULT_FINISH_POSITION
        ├── セッション管理: _open_session(), _close_session(), _with_session()
        └── バッチクエリ: _get_horses_past_results_batch(), _get_horses_batch()

backtest/metrics.py
└── (pure Python, no external deps)

backtest/reporter.py
└── backtest/metrics.py (PredictionResult, RaceBacktestResult)
```

## Data Flow

### Main Pipeline (Scrape/Analyze)

```
[netkeiba.com]
    ↓ scrapers/
[SQLite DB]
    ↓ models/
[Race/Horse Data]
    ↓ analyzers/factors/
[Factor Scores (7種)]
    ↓ ml/feature_builder
[Features (19種)]
    ↓ ml/trainer → ml/predictor
[Top-3 Probability]
    ↓ cli.py
[Output: Score Table + ML Prediction]
```

### Real-time Prediction Pipeline (predict command)

```
[race.netkeiba.com/shutuba.html]
    ↓ scrapers/shutuba.py (ShutubaScraper)
[ShutubaData (race info + entries)]
    ↓ services/prediction_service.py
[PredictionService]
    ├── RaceResultRepository (DB past results, データリーク防止: before_date)
    ├── analyzers/factors/ (7 factors)
    └── ml/predictor (optional)
    ↓
[PredictionResult per horse]
    ↓ cli.py (predict command)
[Output: Prediction Table]
```

### Backtest Pipeline

```
[SQLite DB]
    ↓ backtest/backtester.py (walk-forward)
[Training Data (cutoff date)]
    ↓ ml/trainer
[Model]
    ↓ ml/predictor + analyzers/factors
[Predictions per Race]
    ↓ backtest/metrics.py
[Precision@k, Hit Rate]
    ↓ backtest/reporter.py
[Backtest Report]
```

## CLI Commands

| Command | Handler | Description |
|---------|---------|-------------|
| `scrape` | `cli.scrape()` | 年月指定でレースデータ収集 |
| `scrape-horses` | `cli.scrape_horses()` | 馬詳細データ収集 |
| `analyze` | `cli.analyze()` | レース分析 + ML予測 |
| `predict` | `cli.predict()` | 出馬表URLからリアルタイム予測 |
| `migrate-grades` | `cli.migrate_grades()` | グレード情報マイグレーション |
| `backtest` | `cli.backtest()` | ML予測のバックテスト検証 |

## External Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| sqlalchemy | >=2.0 | ORM |
| requests | >=2.28 | HTTP |
| beautifulsoup4 | >=4.11 | HTML Parser |
| lxml | >=4.9 | XML/HTML |
| click | >=8.0 | CLI |
| lightgbm | >=4.0.0 | ML (Gradient Boosting) |
| scikit-learn | >=1.3.0 | ML Utilities |
