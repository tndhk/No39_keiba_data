# Architecture Codemap

> Freshness: 2026-01-30 (Line counts verified, horse_detail AJAX pedigree, venue_filter expansion)

## System Overview

```
keiba/                        # 競馬データ収集・分析CLI
+-- cli/                      # CLIパッケージ (Click)
|   +-- __init__.py           # main, 後方互換性エクスポート (122行)
|   +-- commands/             # CLIコマンドモジュール
|   |   +-- __init__.py       # exports (5行)
|   |   +-- scrape.py         # scrape, scrape-horses (421行)
|   |   +-- analyze.py        # analyze (623行)
|   |   +-- predict.py        # predict, predict-day (314行)
|   |   +-- train.py          # train (78行)
|   |   +-- review.py         # review-day (206行)
|   |   +-- backtest.py       # backtest, backtest-fukusho/tansho/umaren/sanrenpuku/all (528行)
|   |   +-- migrate.py        # migrate-grades (50行)
|   +-- formatters/           # 出力フォーマッタ
|   |   +-- __init__.py       # exports (13行)
|   |   +-- markdown.py       # Markdown保存/パース (334行)
|   |   +-- simulation.py     # 馬券シミュレーション (338行)
|   +-- utils/                # CLIユーティリティ
|       +-- __init__.py       # empty (0行)
|       +-- url_parser.py      # URL解析 (33行)
|       +-- date_parser.py     # 日付パース (33行)
|       +-- date_range.py      # 日付範囲計算 (46行)
|       +-- model_resolver.py  # MLモデル解決 (18行)
|       +-- table_printer.py   # テーブル出力 (215行)
|       +-- table_formatter.py # バックテスト結果テーブル整形 (160行)
|       +-- venue_filter.py    # 会場フィルタリング (44行)
+-- cli.py                    # 後方互換性（レガシー、2606行）
+-- db.py                     # DB接続・セッション管理 (75行)
+-- constants.py              # 定数定義 (44行)
+-- models/                   # SQLAlchemy ORM
|   +-- entry.py              # 出馬表DTO（RaceEntry, ShutubaData） (66行)
|   +-- race.py               # Race (50行)
|   +-- horse.py              # Horse (67行)
|   +-- race_result.py        # RaceResult (93行)
|   +-- jockey.py, trainer.py, owner.py, breeder.py (各31行)
+-- scrapers/                 # Webスクレイパー
|   +-- base.py               # BaseScraper（グローバルレートリミッタ・指数バックオフ） (188行)
|   +-- race_list.py          # RaceListScraper (106行)
|   +-- race_detail.py        # RaceDetailScraper (853行)
|   +-- horse_detail.py       # HorseDetailScraper（パース警告・AJAX血統取得対応） (367行)
|   +-- shutuba.py            # ShutubaScraper (356行)
+-- services/                 # ビジネスロジックサービス
|   +-- __init__.py           # exports (21行)
|   +-- prediction_service.py # 予測サービス（7因子+ML） (410行)
|   +-- training_service.py   # 学習データ構築サービス (180行)
|   +-- analysis_service.py   # 過去レース分析サービス (235行)
|   +-- past_stats_calculator.py # 過去成績統計計算 (110行)
+-- repositories/             # リポジトリ層
|   +-- __init__.py           # exports (5行)
|   +-- race_result_repository.py # レース結果データアクセス (128行)
+-- analyzers/                # レース分析エンジン
|   +-- score_calculator.py   # 総合スコア算出 (43行)
|   +-- factors/              # スコア算出因子 (7種)
|       +-- past_results.py   # 直近成績 (112行)
|       +-- course_fit.py     # コース適性 (85行)
|       +-- time_index.py     # タイム指数 (101行)
|       +-- last_3f.py        # 上がり3F (57行)
|       +-- popularity.py     # 人気評価 (58行)
|       +-- pedigree.py       # 血統適性 (68行)
|       +-- running_style.py  # 脚質マッチ (126行)
+-- ml/                       # ML予測モジュール
|   +-- feature_builder.py    # 特徴量構築 (103行)
|   +-- trainer.py            # LightGBMモデル学習・保存 (193行)
|   +-- predictor.py          # 予測実行 (60行)
|   +-- model_utils.py        # モデルユーティリティ（最新モデル検索） (27行)
+-- backtest/                 # バックテストモジュール
|   +-- backtester.py         # BacktestEngine（ウォークフォワード検証） (1093行)
|   +-- base_simulator.py     # BaseSimulator（基底クラス・スクレイパー再利用） (175行)
|   +-- fukusho_simulator.py  # FukushoSimulator（複勝シミュレーション） (191行)
|   +-- tansho_simulator.py   # TanshoSimulator（単勝シミュレーション） (185行)
|   +-- umaren_simulator.py   # UmarenSimulator（馬連シミュレーション） (212行)
|   +-- sanrenpuku_simulator.py # SanrenpukuSimulator（三連複シミュレーション） (189行)
|   +-- metrics.py            # MetricsCalculator（精度評価指標） (198行)
|   +-- reporter.py           # BacktestReporter（結果出力） (168行)
|   +-- factor_calculator.py  # ファクター計算 (249行)
|   +-- cache.py              # キャッシュ機構 (125行)
+-- config/                   # 設定・マスタデータ
|   +-- weights.py            # ファクター重み (21行)
|   +-- pedigree_master.py    # 血統マスタ (127行)
+-- utils/                    # ユーティリティ
    +-- grade_extractor.py    # グレード抽出 (231行)
scripts/                      # 運用スクリプト
+-- add_indexes.py            # 既存DBへのインデックス追加
```

## Module Dependencies

```
cli/__init__.py (main)
+-- commands/scrape.py
|   +-- db.py (get_engine, get_session, init_db)
|   +-- models/ (Horse, Jockey, Race, RaceResult, Trainer)
|   +-- scrapers/ (RaceListScraper, RaceDetailScraper, HorseDetailScraper)
+-- commands/analyze.py
|   +-- services/analysis_service.py
|   +-- analyzers/factors/
|   +-- ml/ (Predictor, find_latest_model)
+-- commands/predict.py
|   +-- scrapers/shutuba.py (ShutubaScraper)
|   +-- services/prediction_service.py (PredictionService)
|   +-- repositories/race_result_repository.py
|   +-- formatters/markdown.py
+-- commands/train.py
|   +-- services/training_service.py (build_training_data)
|   +-- ml/ (FeatureBuilder, Trainer)
+-- commands/review.py
|   +-- formatters/markdown.py
|   +-- formatters/simulation.py
|   +-- scrapers/race_detail.py (fetch_payouts)
+-- commands/backtest.py
|   +-- backtest/ (BacktestEngine, Fukusho/Tansho/Umaren/SanrenpukuSimulator)
+-- commands/migrate.py
    +-- utils/grade_extractor.py

analyzers/score_calculator.py
+-- config/weights.py (FACTOR_WEIGHTS)

ml/trainer.py
+-- lightgbm (LGBMClassifier)
+-- sklearn (StratifiedKFold, metrics)
+-- joblib (model persistence)

ml/predictor.py
+-- lightgbm (LGBMClassifier)

ml/feature_builder.py
+-- (pure Python, no external deps)

ml/model_utils.py
+-- pathlib (Path)

services/prediction_service.py
+-- analyzers/factors/ (7 factors)
+-- analyzers/score_calculator.py
+-- models/entry.py (ShutubaData, RaceEntry)
+-- ml/feature_builder.py (FeatureBuilder)
+-- joblib (model loading)

services/training_service.py
+-- db.py (get_session)
+-- models/ (Race, RaceResult, Horse)
+-- ml/feature_builder.py (FeatureBuilder)

services/analysis_service.py
+-- analyzers/factors/ (7 factors)
+-- analyzers/score_calculator.py
+-- services/training_service.py (calculate_past_stats, get_horse_past_results)

repositories/race_result_repository.py
+-- sqlalchemy (Session, select)
+-- models/ (RaceResult, Race)

scrapers/base.py
+-- time (sleep, time)
+-- requests (Session, HTTPError)
+-- bs4 (BeautifulSoup)
    +-- クラス変数: _global_last_request_time (全インスタンス間のレート制限)
    +-- 指数バックオフ: [5s, 10s, 30s] (403/429/503に対して)
    +-- finally: タイマー更新（エラー時も含む）

backtest/backtester.py
+-- contextlib (contextmanager)
+-- db.py (get_engine, get_session)
+-- models/ (Race, RaceResult, Horse)
+-- analyzers/factors/ (7 factors)
+-- ml/ (Trainer, Predictor)
+-- lightgbm (LGBMClassifier) [optional]
    +-- BacktestEngine内部構造:
        +-- クラス定数: MIN_TRAINING_SAMPLES, MAX_PAST_RESULTS_PER_HORSE, DEFAULT_FINISH_POSITION
        +-- セッション管理: _open_session(), _close_session(), _with_session()

backtest/base_simulator.py
+-- abc (ABC, abstractmethod)
+-- sqlalchemy (create_engine, select, Session)
+-- models/entry.py (RaceEntry, ShutubaData)
+-- models/race.py (Race)
+-- models/race_result.py (RaceResult)
+-- scrapers/race_detail.py (RaceDetailScraper)
    +-- BaseSimulator内部構造:
        +-- _scraper: RaceDetailScraper (全レースで再利用)
        +-- _get_session(), _get_races_in_period()
        +-- _build_shutuba_from_race_results()
        +-- simulate_period() (テンプレートメソッド)
        +-- バッチクエリ: _get_horses_past_results_batch(), _get_horses_batch()

backtest/metrics.py
+-- (pure Python, no external deps)

backtest/reporter.py
+-- backtest/metrics.py (PredictionResult, RaceBacktestResult)

backtest/fukusho_simulator.py
+-- sqlalchemy (create_engine, select, Session)
+-- models/ (Race, RaceResult)
+-- models/entry.py (RaceEntry, ShutubaData)
+-- scrapers/race_detail.py (RaceDetailScraper.fetch_payouts)
+-- services/prediction_service.py (PredictionService)

backtest/tansho_simulator.py
+-- fukusho_simulator.py (_BacktestRaceResultRepository)
+-- scrapers/race_detail.py (RaceDetailScraper.fetch_tansho_payout)

backtest/umaren_simulator.py
+-- fukusho_simulator.py (_BacktestRaceResultRepository)
+-- scrapers/race_detail.py (RaceDetailScraper.fetch_umaren_payout)

backtest/sanrenpuku_simulator.py
+-- fukusho_simulator.py (_BacktestRaceResultRepository)
+-- scrapers/race_detail.py (RaceDetailScraper.fetch_sanrenpuku_payout)
```

## Data Flow

### Main Pipeline (Scrape/Analyze)

```
[netkeiba.com]
    | scrapers/
[SQLite DB]
    | models/
[Race/Horse Data]
    | analyzers/factors/
[Factor Scores (7種)]
    | ml/feature_builder
[Features (19種)]
    | ml/trainer -> ml/predictor
[Top-3 Probability]
    | cli/commands/
[Output: Score Table + ML Prediction]
```

### Real-time Prediction Pipeline (predict command)

```
[race.netkeiba.com/shutuba.html]
    | scrapers/shutuba.py (ShutubaScraper)
[ShutubaData (race info + entries)]
    | services/prediction_service.py
[PredictionService]
    +-- RaceResultRepository (DB past results, データリーク防止: before_date)
    +-- analyzers/factors/ (7 factors)
    +-- ml/predictor (optional, via model_path)
    +-- _calculate_combined_score() (幾何平均)
    |
[PredictionResult per horse (ml_probability, factor_scores, total_score, combined_score)]
    | cli/commands/predict.py
[Output: Prediction Table (combined_score降順)]
```

### Backtest Pipeline

```
[SQLite DB]
    | backtest/backtester.py (walk-forward)
[Training Data (cutoff date)]
    | ml/trainer
[Model]
    | ml/predictor + analyzers/factors
[Predictions per Race]
    | backtest/metrics.py
[Precision@k, Hit Rate]
    | backtest/reporter.py
[Backtest Report]
```

### Day Prediction & Review Pipeline (predict-day/review-day)

```
[race.netkeiba.com] (RaceListScraper)
    | 指定日・競馬場のレースURL取得
[race_ids (venue code filter)]
    | scrapers/shutuba.py (ShutubaScraper)
[ShutubaData per race]
    | services/prediction_service.py
[Predictions]
    | cli/formatters/markdown.py (save_predictions_markdown)
[docs/predictions/YYYY-MM-DD-{venue}.md]

--- review-day ---

[docs/predictions/YYYY-MM-DD-{venue}.md]
    | cli/formatters/markdown.py (parse_predictions_markdown)
[Parsed Predictions]
    | scrapers/race_detail.py (fetch_payouts, fetch_tansho_payout)
[Actual Results + Payouts (複勝/単勝/馬連/三連複)]
    | cli/formatters/simulation.py (calculate_*_simulation)
[Simulation Results]
    | cli/formatters/markdown.py (append_review_to_markdown)
[Updated Markdown with Review]
```

### Train Pipeline (train command)

```
[SQLite DB]
    | cli/commands/train.py
[services/training_service.py (build_training_data) - cutoff_date前のデータ]
    | ml/feature_builder
[Features (19種)]
    | ml/trainer (train_with_cv)
[LightGBM Model + CV Metrics]
    | trainer.save_model()
[data/models/*.joblib]
```

## CLI Commands

| Command | Handler | Description |
|---------|---------|-------------|
| `scrape` | `commands/scrape.py:scrape()` | 年月指定でレースデータ収集 |
| `scrape-horses` | `commands/scrape.py:scrape_horses()` | 馬詳細データ収集 |
| `analyze` | `commands/analyze.py:analyze()` | レース分析 + ML予測 |
| `predict` | `commands/predict.py:predict()` | 出馬表URLからリアルタイム予測 |
| `predict-day` | `commands/predict.py:predict_day()` | 指定日・競馬場の全レース予測（Markdown保存） |
| `review-day` | `commands/review.py:review_day()` | 予測結果と実際の結果を比較検証 |
| `migrate-grades` | `commands/migrate.py:migrate_grades()` | グレード情報マイグレーション |
| `backtest` | `commands/backtest.py:backtest()` | ML予測のバックテスト検証 |
| `backtest-fukusho` | `commands/backtest.py:backtest_fukusho()` | 複勝馬券バックテストシミュレーション |
| `backtest-tansho` | `commands/backtest.py:backtest_tansho()` | 単勝馬券バックテストシミュレーション |
| `backtest-umaren` | `commands/backtest.py:backtest_umaren()` | 馬連馬券バックテストシミュレーション |
| `backtest-sanrenpuku` | `commands/backtest.py:backtest_sanrenpuku()` | 三連複馬券バックテストシミュレーション |
| `backtest-all` | `commands/backtest.py:backtest_all()` | 全券種一括バックテストシミュレーション |
| `train` | `commands/train.py:train()` | MLモデル学習・保存 |

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
+-- __init__.py
+-- conftest.py                      # 共通フィクスチャ
+-- fixtures/                        # テスト用HTMLフィクスチャ
+-- test_cli.py                      # CLIコマンド基本テスト
+-- test_db.py                       # DB接続テスト
+-- test_models.py                   # モデルテスト
+-- test_scrapers.py                 # スクレイパー基本テスト
+-- test_analyzers.py                # アナライザーテスト
+-- test_utils.py                    # ユーティリティテスト
+-- test_integration.py              # 統合テスト
+-- test_db_indexes.py               # DBインデックステスト
+-- test_pedigree_factor.py          # 血統ファクターテスト
+-- test_running_style_factor.py     # 脚質ファクターテスト
+-- test_integration_new_factors.py  # 新規ファクター統合テスト
+-- test_cli_backtest_fukusho.py     # 複勝バックテストCLIテスト（ルート）
+-- cli/                             # CLIコマンドテスト
|   +-- __init__.py
|   +-- test_predict_day.py          # predict-dayコマンドテスト
|   +-- test_review_day.py           # review-dayコマンドテスト
|   +-- test_predict_review.py       # predict/review統合テスト
|   +-- test_train_command.py        # trainコマンドテスト
|   +-- test_backtest.py             # backtest CLIテスト
|   +-- test_backtest_all.py         # backtest-allコマンドテスト
|   +-- test_scrape_horses.py        # scrape-horsesコマンドテスト
|   +-- test_date_parser.py          # 日付パーステスト
|   +-- utils/                       # CLIユーティリティテスト
|       +-- test_date_range.py       # 日付範囲計算テスト
|       +-- test_model_resolver.py   # MLモデル解決テスト
|       +-- test_table_formatter.py  # テーブル整形テスト
|       +-- test_venue_filter.py     # 会場フィルタリングテスト
+-- scrapers/                        # スクレイパーテスト
|   +-- __init__.py
|   +-- test_shutuba.py              # 出馬表スクレイパーテスト
|   +-- test_race_detail_payouts.py  # 複勝払戻金パースのテスト
|   +-- test_base_rate_limit.py      # レート制限テスト
|   +-- test_base_retry.py           # リトライ機構テスト
|   +-- test_base_fetch_json.py      # JSON取得テスト
|   +-- test_update_horse.py         # 馬詳細更新テスト
|   +-- test_horse_pedigree_ajax.py  # 馬血統Ajax取得テスト
|   +-- test_horse_detail_new_html.py # 馬詳細新HTML対応テスト
|   +-- test_race_id_resolver.py     # レースID解決テスト
|   +-- test_race_list_sub.py        # レース一覧サブテスト
|   +-- test_url_parser.py           # URL解析テスト
+-- services/                        # サービステスト
|   +-- __init__.py
|   +-- test_prediction_service.py   # 予測サービステスト
|   +-- test_past_stats_calculator.py # 過去成績統計テスト
|   +-- test_training_service.py     # 学習データ構築テスト
|   +-- test_factor_consistency.py   # ファクター整合性テスト
+-- models/                          # モデルテスト
|   +-- __init__.py
|   +-- test_entry.py                # 出馬表DTOテスト
+-- ml/                              # MLモジュールテスト
|   +-- __init__.py
|   +-- conftest.py                  # ML共通フィクスチャ
|   +-- test_feature_builder.py      # 特徴量ビルダーテスト
|   +-- test_predictor.py            # 予測器テスト
|   +-- test_trainer.py              # 学習器テスト
|   +-- test_model_utils.py          # モデルユーティリティテスト
+-- backtest/                        # バックテストモジュールテスト
|   +-- __init__.py
|   +-- test_backtester.py           # バックテストエンジンテスト
|   +-- test_base_simulator.py       # BaseSimulatorテスト
|   +-- test_backtest_repository.py  # バックテストリポジトリテスト
|   +-- test_metrics.py              # メトリクス計算テスト
|   +-- test_reporter.py             # レポーターテスト
|   +-- test_cache.py                # キャッシュテスト
|   +-- test_cache_strategy.py       # キャッシュ戦略テスト
|   +-- test_cached_factor_calculator.py  # キャッシュ付きファクター計算テスト
|   +-- test_fukusho_simulator.py    # 複勝シミュレータテスト
|   +-- test_tansho_simulator.py     # 単勝シミュレータテスト
|   +-- test_umaren_simulator.py     # 馬連シミュレータテスト
|   +-- test_sanrenpuku_simulator.py # 三連複シミュレータテスト
|   +-- test_simulator_scraper_reuse.py # シミュレータスクレイパー再利用テスト
+-- scripts/
|   +-- test_factor_importance.py    # ファクター重要度テスト
+-- config/
|   +-- test_weights.py              # ファクター重みテスト
+-- repositories/
    +-- test_race_result_repository.py # リポジトリテスト
```

## CLI Backward Compatibility

`keiba/cli/__init__.py` で旧APIとの後方互換性を維持:

| Old API | New Location |
|---------|-------------|
| `_save_predictions_markdown` | `cli.formatters.markdown.save_predictions_markdown` |
| `_parse_predictions_markdown` | `cli.formatters.markdown.parse_predictions_markdown` |
| `_append_review_to_markdown` | `cli.formatters.markdown.append_review_to_markdown` |
| `_calculate_fukusho_simulation` | `cli.formatters.simulation.calculate_fukusho_simulation` |
| `_calculate_tansho_simulation` | `cli.formatters.simulation.calculate_tansho_simulation` |
| `_calculate_umaren_simulation` | `cli.formatters.simulation.calculate_umaren_simulation` |
| `_calculate_sanrenpuku_simulation` | `cli.formatters.simulation.calculate_sanrenpuku_simulation` |
| `_print_score_table` | `cli.utils.table_printer.print_score_table` |
| `_print_score_table_with_ml` | `cli.utils.table_printer.print_score_table_with_ml` |
| `_print_prediction_table` | `cli.utils.table_printer.print_prediction_table` |
| `extract_race_id_from_url` | `cli.utils.url_parser.extract_race_id_from_url` |
| `extract_race_id_from_shutuba_url` | `cli.utils.url_parser.extract_race_id_from_shutuba_url` |
| `parse_race_date` | `cli.utils.date_parser.parse_race_date` |
| `get_engine`, `get_session`, `init_db` | `db.py` |
| `RaceDetailScraper`, `RaceListScraper`, `HorseDetailScraper` | `scrapers/` |

## Constants

| Constant | Purpose | Location |
|----------|---------|----------|
| `VENUE_CODE_MAP` | 競馬場名->コード（2桁）マッピング | cli/commands/predict.py |
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
