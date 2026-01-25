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

## アーキテクチャ

```
CLI (keiba/cli.py)
    │
    ├── Scrapers (keiba/scrapers/)
    │   ├── RaceListScraper      # db.netkeiba.com/race/list/
    │   ├── RaceDetailScraper    # db.netkeiba.com/race/
    │   ├── HorseDetailScraper   # db.netkeiba.com/horse/
    │   └── ShutubaScraper       # race.netkeiba.com/race/shutuba.html
    │
    ├── Services (keiba/services/)
    │   └── PredictionService    # ファクター計算とML予測のオーケストレーション
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
