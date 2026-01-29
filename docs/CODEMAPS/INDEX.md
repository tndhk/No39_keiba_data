# Codemaps Index

> Freshness: 2026-01-29 (Line counts verified, simulator refactoring, scraper updates)

競馬データ収集システムのコードマップ一覧。

## 概要

このプロジェクトは競馬データを収集・分析し、LightGBMによる機械学習予測を行うCLIツールです。

## コードマップ一覧

| ファイル | 内容 | 対象モジュール |
|----------|------|---------------|
| [architecture.md](./architecture.md) | システム全体構造 | keiba/, tests/ |
| [backend.md](./backend.md) | CLI/Services/Scrapers | keiba/cli/, keiba/services/, keiba/scrapers/ |
| [backtest.md](./backtest.md) | バックテストモジュール | keiba/backtest/, 4券種シミュレータ |
| [data.md](./data.md) | データモデル/DB構造 | keiba/models/, DB Schema |

## システム構成図

```
keiba/                           # 競馬データ収集・分析CLI
+-- cli/                         # CLIパッケージ (Click)
|   +-- __init__.py              # main, 後方互換性エクスポート (122行)
|   +-- commands/                # CLIコマンドモジュール
|   |   +-- scrape.py            # scrape, scrape-horses (429行)
|   |   +-- analyze.py           # analyze (623行)
|   |   +-- predict.py           # predict, predict-day (315行)
|   |   +-- train.py             # train (78行)
|   |   +-- review.py            # review-day (206行)
|   |   +-- backtest.py          # backtest, backtest-fukusho/tansho/umaren/sanrenpuku/all (528行)
|   |   +-- migrate.py           # migrate-grades (50行)
|   +-- formatters/              # 出力フォーマッタ
|   |   +-- markdown.py          # Markdown保存/パース (334行)
|   |   +-- simulation.py        # 馬券シミュレーション (338行)
|   +-- utils/                   # CLIユーティリティ
|       +-- url_parser.py        # URL解析 (33行)
|       +-- date_parser.py       # 日付パース (33行)
|       +-- date_range.py        # 日付範囲計算 (46行)
|       +-- model_resolver.py    # MLモデル解決 (18行)
|       +-- table_printer.py     # テーブル出力 (215行)
|       +-- table_formatter.py   # バックテスト結果テーブル整形 (160行)
|       +-- venue_filter.py      # 会場フィルタリング (27行)
|
+-- cli.py                       # 後方互換性エントリ (2606行, レガシー)
|
+-- services/                    # ビジネスロジック
|   +-- prediction_service.py    # 予測オーケストレーション (410行)
|   +-- training_service.py      # 学習データ構築 (180行)
|   +-- analysis_service.py      # 過去レース分析 (235行)
|   +-- past_stats_calculator.py # 過去成績統計計算 (110行)
|
+-- repositories/                # データアクセス層
|   +-- race_result_repository.py # レース結果リポジトリ (128行)
|
+-- scrapers/                    # Webスクレイパー
|   +-- race_list.py             # レース一覧取得 (106行)
|   +-- race_detail.py           # レース詳細取得 (853行)
|   +-- horse_detail.py          # 馬詳細取得（パース警告対応） (361行)
|   +-- shutuba.py               # 出馬表取得 (356行)
|   +-- base.py                  # 基底クラス（グローバルレートリミッタ・指数バックオフ） (188行)
|
+-- analyzers/                   # レース分析
|   +-- score_calculator.py      # 総合スコア算出 (43行)
|   +-- factors/                 # 7つの分析ファクター
|       +-- past_results.py      # 直近成績 (112行)
|       +-- course_fit.py        # コース適性 (85行)
|       +-- time_index.py        # タイム指数 (101行)
|       +-- last_3f.py           # 上がり3F (57行)
|       +-- popularity.py        # 人気評価 (58行)
|       +-- pedigree.py          # 血統適性 (68行)
|       +-- running_style.py     # 脚質マッチ (126行)
|
+-- ml/                          # 機械学習
|   +-- feature_builder.py       # 特徴量構築 (103行)
|   +-- trainer.py               # LightGBM学習 (193行)
|   +-- predictor.py             # 予測実行 (60行)
|   +-- model_utils.py           # モデルユーティリティ (27行)
|
+-- backtest/                    # バックテスト
|   +-- backtester.py            # ウォークフォワード検証 (1093行)
|   +-- base_simulator.py       # シミュレータ基底クラス（スクレイパー再利用） (175行)
|   +-- fukusho_simulator.py     # 複勝シミュレーション (191行)
|   +-- tansho_simulator.py      # 単勝シミュレーション (185行)
|   +-- umaren_simulator.py      # 馬連シミュレーション (212行)
|   +-- sanrenpuku_simulator.py  # 三連複シミュレーション (189行)
|   +-- metrics.py               # 精度評価 (198行)
|   +-- reporter.py              # レポート出力 (168行)
|   +-- factor_calculator.py     # ファクター計算 (249行)
|   +-- cache.py                 # キャッシュ機構 (125行)
|
+-- models/                      # SQLAlchemy ORM
|   +-- race.py, horse.py, race_result.py, entry.py, ...
|
+-- config/                      # 設定
|   +-- weights.py               # ファクター重み (21行)
|   +-- pedigree_master.py       # 血統マスタ (127行)
|
+-- utils/                       # ユーティリティ
|   +-- grade_extractor.py       # グレード抽出 (231行)
|
+-- db.py                        # DB接続・セッション管理 (75行)
+-- constants.py                 # 定数定義 (44行)
```

## CLIコマンド一覧

| コマンド | ファイル | 説明 |
|---------|---------|------|
| scrape | commands/scrape.py | レースデータ収集 |
| scrape-horses | commands/scrape.py | 馬詳細データ収集 |
| analyze | commands/analyze.py | 過去レース分析 |
| predict | commands/predict.py | 出馬表URL予測 |
| predict-day | commands/predict.py | 日単位予測 |
| review-day | commands/review.py | 予測結果検証（複勝・単勝シミュレーション） |
| train | commands/train.py | MLモデル学習 |
| backtest | commands/backtest.py | ML予測バックテスト |
| backtest-fukusho | commands/backtest.py | 複勝シミュレーション |
| backtest-tansho | commands/backtest.py | 単勝シミュレーション |
| backtest-umaren | commands/backtest.py | 馬連シミュレーション |
| backtest-sanrenpuku | commands/backtest.py | 三連複シミュレーション |
| backtest-all | commands/backtest.py | 全券種一括バックテスト |
| migrate-grades | commands/migrate.py | グレード情報マイグレーション |

## パッケージ依存関係

```
cli/__init__.py (main)
    |
    +-- commands/* (各コマンドモジュール)
    |   +-- services/ (ビジネスロジック)
    |   +-- repositories/ (データアクセス)
    |   +-- scrapers/ (Webスクレイピング)
    |   +-- formatters/ (出力整形)
    |   +-- utils/ (CLI用ユーティリティ)
    |
    +-- analyzers/factors/ (7ファクター計算)
    |
    +-- ml/ (機械学習モジュール)
    |
    +-- backtest/ (バックテストモジュール)
    |
    +-- models/ (SQLAlchemy ORM)
    |
    +-- db.py (データベース接続)
```

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
