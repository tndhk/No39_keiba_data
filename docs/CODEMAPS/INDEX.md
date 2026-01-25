# Codemaps Index

> Freshness: 2026-01-25

競馬データ収集システムのコードマップ一覧。

## 概要

このプロジェクトは競馬データを収集・分析し、LightGBMによる機械学習予測を行うCLIツールです。

## コードマップ一覧

| ファイル | 内容 | 対象モジュール |
|----------|------|---------------|
| [architecture.md](./architecture.md) | システム全体構造 | keiba/, tests/ |
| [backend.md](./backend.md) | CLI/Services/Scrapers | keiba/cli.py, keiba/services/, keiba/scrapers/ |
| [data.md](./data.md) | データモデル/DB構造 | keiba/models/, DB Schema |

## システム構成図

```
CLI (keiba/cli.py)
    |
    +-- Scrapers (keiba/scrapers/)
    |   +-- RaceListScraper      # レース一覧取得
    |   +-- RaceDetailScraper    # レース詳細取得
    |   +-- HorseDetailScraper   # 馬詳細取得
    |   +-- ShutubaScraper       # 出馬表取得
    |
    +-- Services (keiba/services/)
    |   +-- PredictionService    # 予測オーケストレーション
    |
    +-- Analyzers (keiba/analyzers/)
    |   +-- ScoreCalculator      # 総合スコア算出
    |   +-- factors/             # 7つの分析ファクター
    |
    +-- ML (keiba/ml/)
    |   +-- FeatureBuilder       # 特徴量構築
    |   +-- Trainer              # LightGBMモデル学習
    |   +-- Predictor            # 予測実行
    |   +-- model_utils          # モデルユーティリティ
    |
    +-- Backtest (keiba/backtest/)
    |   +-- BacktestEngine       # ウォークフォワード検証
    |   +-- FukushoSimulator     # 複勝シミュレーション
    |   +-- MetricsCalculator    # 精度評価
    |   +-- BacktestReporter     # レポート出力
    |
    +-- DB (keiba/db.py) --> SQLite
```

## CLIコマンド一覧

| コマンド | 説明 |
|---------|------|
| scrape | レースデータ収集 |
| scrape-horses | 馬詳細データ収集 |
| analyze | 過去レース分析 |
| predict | 出馬表URL予測 |
| predict-day | 日単位予測 |
| review-day | 予測結果検証 |
| train | MLモデル学習 |
| backtest | ML予測バックテスト |
| backtest-fukusho | 複勝シミュレーション |
| migrate-grades | グレード情報マイグレーション |

## 関連ドキュメント

- [開発者ガイド (CONTRIB.md)](../CONTRIB.md) - 開発ワークフロー、テスト手順
- [運用ガイド (RUNBOOK.md)](../RUNBOOK.md) - 運用手順、トラブルシューティング
- [プロジェクト概要 (CLAUDE.md)](../../CLAUDE.md) - プロジェクト全体説明

## 技術スタック

| カテゴリ | 技術 |
|---------|------|
| 言語 | Python 3.10+ |
| CLI | Click |
| ORM | SQLAlchemy 2.0 |
| DB | SQLite |
| スクレイピング | requests, BeautifulSoup4 |
| 機械学習 | LightGBM, scikit-learn |
| テスト | pytest, pytest-cov |
