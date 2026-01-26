# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

競馬データ収集・分析システム。netkeibaからレースデータをスクレイピングし、SQLiteに保存、7つの分析ファクターとLightGBMによるML予測で馬券予測を行うCLIツール。

## コマンド

```bash
# 開発環境セットアップ
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# テスト実行
pytest tests/ -v                              # 全テスト
pytest tests/test_scrapers.py -v              # 単一ファイル
pytest tests/test_scrapers.py::test_xxx -v    # 単一テスト

# カバレッジ付きテスト
pytest tests/ --cov=keiba --cov-report=term-missing

# CLIコマンド例
keiba scrape --year 2024 --month 1 --db data/keiba.db --jra-only
keiba analyze --db data/keiba.db --date 2024-01-06 --venue 中山
keiba train --db data/keiba.db --output data/models/model.joblib
keiba predict-day --venue 中山 --db data/keiba.db
keiba review-day --venue 中山 --db data/keiba.db
keiba backtest-fukusho --db data/keiba.db -v
```

## 使用方法

### 基本ワークフロー

```
1. データ収集 → 2. モデル学習 → 3. 予測実行 → 4. 検証
```

### Step 1: データ収集

```bash
# レースデータ収集（必須）
keiba scrape --year 2024 --month 1 --db data/keiba.db --jra-only
# オプション: --jra-only（中央競馬のみ）

# 馬の血統情報補完（血統ファクター用、推奨）
keiba scrape-horses --db data/keiba.db --limit 500
# オプション: --limit <int>（取得馬数、デフォルト100）
```

### Step 2: モデル学習

```bash
keiba train --db data/keiba.db --output data/models/model.joblib
# オプション: --cutoff-date <YYYY-MM-DD>（学習データのカットオフ日）
```
- 学習データは最低100サンプル必要
- カットオフ日より前のレースのみ使用（データリーク防止）

### Step 3: 予測実行

```bash
# 日単位予測（推奨）- Markdown出力あり
keiba predict-day --venue 中山 --db data/keiba.db
# オプション: --date <YYYY-MM-DD>（デフォルト今日）, --no-ml（ML予測スキップ）
# 出力: docs/predictions/{YYYY-MM-DD}-{venue}.md

# 単一レース予測（出馬表URLから）
keiba predict --url "https://race.netkeiba.com/race/shutuba.html?race_id=XXXX" --db data/keiba.db
# オプション: --no-ml（ML予測スキップ）
```

### Step 4: 検証

```bash
# 予測検証（predict-day実行後）- 複勝・単勝シミュレーション付き
keiba review-day --venue 中山 --db data/keiba.db
# オプション: --date <YYYY-MM-DD>（デフォルト今日）
# 出力: 予測ファイルに検証結果（複勝・単勝の的中率・回収率）を追記

# 複勝シミュレーション（期間指定バックテスト）
keiba backtest-fukusho --db data/keiba.db -v
# オプション: --from/--to <YYYY-MM-DD>（期間指定）, --last-week, --top-n <int>（デフォルト3）, --venue <会場名>
```

### コマンドリファレンス

| コマンド | 説明 | 主要オプション |
|---------|------|---------------|
| scrape | レースデータ収集 | --year, --month, --db, --jra-only |
| scrape-horses | 馬の血統情報補完 | --db, --limit |
| train | MLモデル学習 | --db, --output, --cutoff-date |
| analyze | 過去レース分析 | --db, --date, --venue, --race, --no-predict |
| predict | 出馬表URL予測 | --url, --db, --no-ml |
| predict-day | 日単位予測 | --date, --venue, --db, --no-ml |
| review-day | 予測検証（複勝・単勝シミュレーション） | --date, --venue, --db |
| backtest | 期間バックテスト | --db, --from, --to, --months, --retrain-interval |
| backtest-fukusho | 複勝シミュレーション | --db, --from, --to, --last-week, --top-n, --venue |
| backtest-all | 全券種一括バックテスト | --db, --from, --to, --last-week, --top-n, --venue, -v |

### コマンド依存関係

```
scrape（必須）→ scrape-horses（推奨）→ train（ML予測に必要）→ predict-day → review-day
```

## 典型的なユースケース

### 日次ワークフロー（レース当日）

```bash
# 予測実行
keiba predict-day --venue 中山 --db data/keiba.db
# → docs/predictions/YYYY-MM-DD-nakayama.md が生成

# 検証（翌日以降、結果確定後）
keiba review-day --venue 中山 --date YYYY-MM-DD --db data/keiba.db
# → 予測ファイルに複勝・単勝シミュレーション結果を追記
```

### 週次ワークフロー

```bash
# 先週の全券種パフォーマンス評価（推奨）
keiba backtest-all --last-week --db data/keiba.db
# → 複勝・単勝・馬連・三連複の的中率・回収率を一覧比較

# 複勝のみの詳細評価
keiba backtest-fukusho --last-week --top-n 3 --db data/keiba.db -v
# → 複勝の的中率・回収率を確認
```

### 月次ワークフロー

```bash
# 1. 新月データ取得
keiba scrape --year 2026 --month 1 --db data/keiba.db --jra-only

# 2. 血統情報補完
keiba scrape-horses --db data/keiba.db --limit 500

# 3. モデル再学習
keiba train --db data/keiba.db --output data/models/model_202601.joblib
```

### ユースケース一覧

| 周期 | 目的 | コマンド |
|------|------|---------|
| 初回 | 初期セットアップ | scrape（複数月）, scrape-horses, train |
| 日次 | 当日予測 | predict-day |
| 翌日 | 結果検証 | review-day |
| 週次 | パフォーマンス評価 | backtest-all --last-week |
| 月次 | データ更新・再学習 | scrape, scrape-horses, train |
| 随時 | 過去分析 | analyze |
| 随時 | 単一レース予測 | predict |
| 随時 | 長期バックテスト | backtest |

## アーキテクチャ

```
CLI (keiba/cli/)
    │
    ├── commands/                # CLIコマンド
    │   ├── scrape.py           # scrape, scrape-horses
    │   ├── analyze.py          # analyze
    │   ├── predict.py          # predict, predict-day
    │   ├── train.py            # train
    │   ├── review.py           # review-day
    │   ├── backtest.py         # backtest, backtest-fukusho
    │   └── migrate.py          # migrate-grades
    │
    ├── formatters/              # 出力フォーマッタ
    │   ├── markdown.py         # Markdown保存/パース/追記
    │   └── simulation.py       # 複勝/単勝/馬連/三連複シミュレーション
    │
    └── utils/                   # CLIユーティリティ
        ├── url_parser.py       # URL解析
        ├── date_parser.py      # 日付パース
        └── table_printer.py    # テーブル出力
    │
    ├── Scrapers (keiba/scrapers/)
    │   ├── RaceListScraper      # db.netkeiba.com/race/list/
    │   ├── RaceDetailScraper    # db.netkeiba.com/race/
    │   ├── HorseDetailScraper   # db.netkeiba.com/horse/
    │   └── ShutubaScraper       # race.netkeiba.com/race/shutuba.html
    │
    ├── Services (keiba/services/)
    │   ├── PredictionService    # ファクター計算とML予測のオーケストレーション
    │   ├── TrainingService      # 学習データ構築
    │   └── AnalysisService      # 過去レース分析
    │
    ├── Repositories (keiba/repositories/)
    │   └── RaceResultRepository # レース結果データアクセス
    │
    ├── Analyzers (keiba/analyzers/)
    │   ├── ScoreCalculator      # 重み付き総合スコア算出
    │   └── factors/             # 7つの分析ファクター
    │       ├── PastResultsFactor   # 直近レース成績
    │       ├── CourseFitFactor     # コース適性
    │       ├── TimeIndexFactor     # タイム指数
    │       ├── Last3FFactor        # 上がり3F
    │       ├── PopularityFactor    # 人気評価
    │       ├── PedigreeFactor      # 血統適性
    │       └── RunningStyleFactor  # 脚質マッチ度
    │
    ├── ML (keiba/ml/)
    │   ├── FeatureBuilder       # 特徴量構築
    │   ├── Trainer              # LightGBMモデル学習
    │   ├── Predictor            # 3着以内確率予測
    │   └── model_utils          # モデルユーティリティ（最新モデル検索）
    │
    ├── Backtest (keiba/backtest/)
    │   ├── FukushoSimulator     # 複勝シミュレーション
    │   └── Backtester           # 過去データ検証
    │
    ├── Utils (keiba/utils/)
    │   └── grade_extractor      # グレード抽出
    │
    └── DB (keiba/db.py) → SQLite
```

## 重要な設計パターン

### データ取得時のリーク防止
予測時は `before_date` パラメータでレース日より前のデータのみ使用。当日オッズ・人気は使用しない。

### ファクターウェイト
`keiba/config/weights.py` で7ファクターの重み配分を管理（各14.2-14.3%）

### 血統マスター
`keiba/config/pedigree_master.py` で種牡馬の系統・距離適性を定義

### JRAコース判定
`keiba/constants.py` の `JRA_COURSE_CODES` でJRA/NAR判定。race_id形式: `YYYYPPNNRRXX`（PP=競馬場コード）

## テスト構成

- `tests/scrapers/` - スクレイパーテスト（HTMLフィクスチャ使用）
- `tests/ml/` - ML機能テスト
- `tests/backtest/` - バックテストテスト
- `tests/services/` - サービス層テスト
- `tests/cli/` - CLIコマンドテスト

## DB構造

主要テーブル: `races`, `horses`, `race_results`, `jockeys`, `trainers`

血統分析には `horses.sire`, `horses.dam_sire` が必要。
脚質分析には `race_results.passing_order` が必要。
