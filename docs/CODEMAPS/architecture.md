# Architecture Codemap

> Freshness: 2026-01-25 (Verified: train, combined_score, model_utils, backtest-fukusho)

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
│   ├── feature_builder.py  # 特徴量構築
│   ├── trainer.py          # LightGBMモデル学習・保存
│   ├── predictor.py        # 予測実行
│   └── model_utils.py      # モデルユーティリティ（最新モデル検索）
├── backtest/            # バックテストモジュール
│   ├── __init__.py
│   ├── backtester.py    # BacktestEngine（ウォークフォワード検証）
│   ├── fukusho_simulator.py  # FukushoSimulator（複勝シミュレーション）
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
├── services/prediction_service.py (PredictionService, PredictionResult - combined_score含む)
├── analyzers/factors/ (7 factors)
├── analyzers/score_calculator.py
├── ml/ (FeatureBuilder, Trainer, Predictor, find_latest_model)
├── backtest/ (BacktestEngine, MetricsCalculator, BacktestReporter)
└── utils/grade_extractor.py

analyzers/score_calculator.py
└── config/weights.py (FACTOR_WEIGHTS)

ml/trainer.py
├── lightgbm (LGBMClassifier)
├── sklearn (StratifiedKFold, metrics)
└── joblib (model persistence)

ml/predictor.py
└── lightgbm (LGBMClassifier)

ml/feature_builder.py
└── (pure Python, no external deps)

ml/model_utils.py
└── pathlib (Path)

services/prediction_service.py
├── analyzers/factors/ (7 factors)
├── analyzers/score_calculator.py
├── models/entry.py (ShutubaData, RaceEntry)
├── ml/feature_builder.py (FeatureBuilder)
└── joblib (model loading)

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

backtest/fukusho_simulator.py
├── sqlalchemy (create_engine, select, Session)
├── models/ (Race, RaceResult)
├── models/entry.py (RaceEntry, ShutubaData)
├── scrapers/race_detail.py (RaceDetailScraper.fetch_payouts)
└── services/prediction_service.py (PredictionService)
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
    ├── ml/predictor (optional, via model_path)
    └── _calculate_combined_score() (幾何平均)
    ↓
[PredictionResult per horse (ml_probability, factor_scores, total_score, combined_score)]
    ↓ cli.py (predict command)
[Output: Prediction Table (combined_score降順)]
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

### Train Pipeline (train command)

```
[SQLite DB]
    ↓ cli.py (train)
[_build_training_data() - cutoff_date前のデータ]
    ↓ ml/feature_builder
[Features (19種)]
    ↓ ml/trainer (train_with_cv)
[LightGBM Model + CV Metrics]
    ↓ trainer.save_model()
[data/models/*.joblib]
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
| `backtest-fukusho` | `cli.backtest_fukusho()` | 複勝馬券バックテストシミュレーション |
| `train` | `cli.train()` | MLモデル学習・保存 |

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
| joblib | - | Model Persistence |
| numpy | - | Numerical Computing |

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
│   ├── test_predict_review.py       # predict/review統合テスト
│   └── test_train_command.py        # trainコマンドテスト
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
│   ├── test_trainer.py              # 学習器テスト
│   └── test_model_utils.py          # モデルユーティリティテスト
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
| `_build_training_data()` | ML学習用データ構築（cutoff date前） | cli.py |
| `_calculate_past_stats()` | 派生特徴量計算（勝率、Top3率等） | cli.py |

## Constants

| Constant | Purpose | Location |
|----------|---------|----------|
| `VENUE_CODE_MAP` | 競馬場名→コード（2桁）マッピング | cli.py |
| `JRA_COURSE_CODES` | JRA競馬場コード定義 | constants.py |

## Model Configuration

### Trainer Parameters

| Mode | num_leaves | learning_rate | n_estimators | Purpose |
|------|------------|---------------|--------------|---------|
| Normal | 31 | 0.05 | 100 | 本番学習用 |
| Lightweight | 15 | 0.1 | 50 | バックテスト用 |

### Model Storage

- 保存形式: `.joblib` (joblib.dump)
- デフォルトパス: `data/models/`
- 命名規則: タイムスタンプベース
- 最新モデル検索: `find_latest_model(model_dir)` (st_mtime順)
