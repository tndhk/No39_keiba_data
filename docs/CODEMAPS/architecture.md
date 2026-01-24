# Architecture Codemap

> Freshness: 2026-01-24 (Updated: test files for predict/review-day, fetch_payouts)

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

### Day Prediction & Review Pipeline (predict-day/review-day)

```
[race.netkeiba.com] (RaceListScraper)
    ↓ 指定日・競馬場のレースURL取得
[race_ids (venue code filter)]
    ↓ scrapers/shutuba.py (ShutubaScraper)
[ShutubaData per race]
    ↓ services/prediction_service.py
[Predictions]
    ↓ cli.py (_save_predictions_markdown)
[docs/predictions/YYYY-MM-DD-{venue}.md]

--- review-day ---

[docs/predictions/YYYY-MM-DD-{venue}.md]
    ↓ cli.py (_parse_predictions_markdown)
[Parsed Predictions]
    ↓ scrapers/race_detail.py (fetch_payouts)
[Actual Results + Fukusho Payouts]
    ↓ cli.py (_calculate_fukusho_simulation)
[Simulation Results]
    ↓ cli.py (_append_review_to_markdown)
[Updated Markdown with Review]
```

## CLI Commands

| Command | Handler | Description |
|---------|---------|-------------|
| `scrape` | `cli.scrape()` | 年月指定でレースデータ収集 |
| `scrape-horses` | `cli.scrape_horses()` | 馬詳細データ収集 |
| `analyze` | `cli.analyze()` | レース分析 + ML予測 |
| `predict` | `cli.predict()` | 出馬表URLからリアルタイム予測 |
| `predict-day` | `cli.predict_day()` | 指定日・競馬場の全レース予測（Markdown保存） |
| `review-day` | `cli.review_day()` | 予測結果と実際の結果を比較検証 |
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

## Test Structure

```
tests/
├── __init__.py
├── test_cli.py                      # CLIコマンド基本テスト
├── test_db.py                       # DB接続テスト
├── test_models.py                   # モデルテスト
├── test_scrapers.py                 # スクレイパー基本テスト
├── test_analyzers.py                # アナライザーテスト
├── test_utils.py                    # ユーティリティテスト
├── test_integration.py              # 統合テスト
├── test_db_indexes.py               # DBインデックステスト
├── test_pedigree_factor.py          # 血統ファクターテスト
├── test_running_style_factor.py     # 脚質ファクターテスト
├── test_integration_new_factors.py  # 新規ファクター統合テスト
├── cli/                             # CLIコマンドテスト
│   ├── __init__.py
│   ├── test_predict_day.py          # predict-dayコマンドテスト
│   ├── test_review_day.py           # review-dayコマンドテスト
│   └── test_predict_review.py       # predict/review統合テスト
├── scrapers/                        # スクレイパーテスト
│   ├── __init__.py
│   ├── test_shutuba.py              # 出馬表スクレイパーテスト
│   └── test_race_detail_payouts.py  # 複勝払戻金パースのテスト
├── services/                        # サービステスト
│   ├── __init__.py
│   └── test_prediction_service.py   # 予測サービステスト
├── models/                          # モデルテスト
│   ├── __init__.py
│   └── test_entry.py                # 出馬表DTOテスト
├── ml/                              # MLモジュールテスト
│   ├── __init__.py
│   ├── conftest.py                  # ML共通フィクスチャ
│   ├── test_feature_builder.py      # 特徴量ビルダーテスト
│   ├── test_predictor.py            # 予測器テスト
│   └── test_trainer.py              # 学習器テスト
└── backtest/                        # バックテストモジュールテスト
    ├── __init__.py
    ├── test_backtester.py           # バックテストエンジンテスト
    ├── test_metrics.py              # メトリクス計算テスト
    ├── test_reporter.py             # レポーターテスト
    ├── test_cache.py                # キャッシュテスト
    ├── test_cache_strategy.py       # キャッシュ戦略テスト
    └── test_cached_factor_calculator.py  # キャッシュ付きファクター計算テスト
```

## CLI Helper Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `_get_race_ids_for_venue()` | 競馬場コードでレースIDをフィルタリング | cli.py |
| `_save_predictions_markdown()` | 予測結果をMarkdownファイルに保存 | cli.py |
| `_parse_predictions_markdown()` | 予測MarkdownファイルをパースしてDict化 | cli.py |
| `_calculate_fukusho_simulation()` | 複勝シミュレーション（的中率/回収率）計算 | cli.py |
| `_append_review_to_markdown()` | 検証結果をMarkdownに追記 | cli.py |

## Constants

| Constant | Purpose | Location |
|----------|---------|----------|
| `VENUE_CODE_MAP` | 競馬場名→コード（2桁）マッピング | cli.py |
