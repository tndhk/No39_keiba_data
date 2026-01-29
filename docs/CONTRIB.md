# 開発者ガイド

競馬データ収集システムの開発ワークフローガイド。

> Freshness: 2026-01-29 (Verified: Rate limiting, BaseSimulator, parse warnings, CLI utils expansion)

## 環境セットアップ

### 必要要件

- Python 3.10以上
- pip または uv

### インストール

```bash
# リポジトリをクローン
git clone <repository-url>
cd No39_keiba

# 仮想環境を作成（推奨）
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 依存関係をインストール
pip install -e .

# 開発用依存関係もインストール
pip install -e ".[dev]"
```

## プロジェクト構成

```
keiba/
+-- cli/                    # CLIパッケージ
|   +-- __init__.py        # エントリーポイント（main）
|   +-- commands/          # CLIコマンドモジュール
|   |   +-- scrape.py     # scrape, scrape-horses（verbose/warnings対応）
|   |   +-- analyze.py    # analyze
|   |   +-- predict.py    # predict, predict-day
|   |   +-- train.py      # train
|   |   +-- review.py     # review-day
|   |   +-- backtest.py   # backtest, backtest-fukusho/tansho/umaren/sanrenpuku/all
|   |   +-- migrate.py    # migrate-grades
|   +-- formatters/        # 出力フォーマッタ
|   |   +-- markdown.py   # Markdown保存/パース
|   |   +-- simulation.py # 馬券シミュレーション計算
|   +-- utils/             # CLIユーティリティ
|       +-- url_parser.py      # URL解析
|       +-- date_parser.py     # 日付パース
|       +-- date_range.py      # 日付範囲計算（--from/--to/--last-week）
|       +-- model_resolver.py  # MLモデル解決（--model/自動検索）
|       +-- table_printer.py   # テーブル出力
|       +-- table_formatter.py # バックテスト結果テーブル整形
|       +-- venue_filter.py    # 会場フィルタリング
+-- models/                 # SQLAlchemyモデル定義
|   +-- entry.py           # 出馬表DTO（RaceEntry, ShutubaData）
+-- scrapers/               # Webスクレイパー
|   +-- base.py            # BaseScraper（グローバルレートリミッタ・指数バックオフ）
|   +-- shutuba.py         # 出馬表スクレイパー（ShutubaScraper）
+-- services/               # ビジネスロジックサービス
|   +-- prediction_service.py     # 予測サービス（PredictionService）
|   +-- training_service.py       # 学習データ構築サービス
|   +-- analysis_service.py       # 過去レース分析サービス
|   +-- past_stats_calculator.py  # 過去成績統計の計算
+-- repositories/           # リポジトリ層
|   +-- race_result_repository.py  # レース結果データアクセス
+-- analyzers/              # レース分析モジュール
|   +-- factors/           # スコア算出ファクター（7因子）
+-- ml/                     # 機械学習予測モジュール
|   +-- feature_builder.py # 特徴量構築
|   +-- trainer.py         # LightGBMモデル学習
|   +-- predictor.py       # 予測実行
|   +-- model_utils.py     # モデルユーティリティ（最新モデル検索等）
+-- backtest/               # バックテストモジュール
|   +-- backtester.py      # BacktestEngine（セッション管理、バッチクエリ）
|   +-- base_simulator.py  # BaseSimulator（基底クラス、スクレイパー再利用）
|   +-- fukusho_simulator.py    # 複勝シミュレーション
|   +-- tansho_simulator.py     # 単勝シミュレーション
|   +-- umaren_simulator.py     # 馬連シミュレーション
|   +-- sanrenpuku_simulator.py # 三連複シミュレーション
|   +-- factor_calculator.py    # ファクター計算
|   +-- cache.py           # キャッシュ機構
|   +-- metrics.py         # メトリクス計算
|   +-- reporter.py        # レポート出力
+-- config/                 # 設定（分析ウェイト、血統マスタ等）
+-- utils/                  # ユーティリティ
|   +-- grade_extractor.py # グレード抽出
+-- db.py                   # データベース接続
+-- cli.py                  # 後方互換性（cli/__init__.pyへリダイレクト）
scripts/
+-- add_indexes.py          # 既存DBへのインデックス追加スクリプト
tests/
+-- fixtures/               # テスト用HTMLフィクスチャ
+-- cli/                    # CLIコマンドテスト
+-- services/               # サービス層テスト
+-- ml/                     # ML関連テスト
+-- backtest/               # バックテストテスト
+-- test_db_indexes.py      # DBインデックス存在確認テスト
+-- test_*.py               # テストファイル
```

## CLIコマンド

### keiba scrape

指定した年月のレースデータをnetkeibaから収集してSQLiteに保存。

```bash
# 基本使用法
keiba scrape --year 2024 --month 3 --db data/keiba.db

# 中央競馬（JRA）のみ取得
keiba scrape --year 2024 --month 3 --db data/keiba.db --jra-only
```

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| --year | Yes | - | 取得する年 |
| --month | Yes | - | 取得する月 |
| --db | Yes | - | DBファイルパス |
| --jra-only | No | False | 中央競馬（JRA）のみ取得。NAR（地方競馬）を除外 |

JRA競馬場（`--jra-only`対象）: 札幌、函館、福島、新潟、東京、中山、中京、京都、阪神、小倉

### keiba scrape-horses

詳細未取得の馬情報（血統・成績）を収集。レース結果から取得した馬IDに基づいて詳細を取得。

```bash
# デフォルト100件取得
keiba scrape-horses --db data/keiba.db

# 500件取得
keiba scrape-horses --db data/keiba.db --limit 500
```

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| --db | Yes | - | DBファイルパス |
| --limit | No | 100 | 取得する馬の数 |

### keiba analyze

指定した日付・競馬場のレースを分析してスコアを表示。LightGBMによるML予測付き。

```bash
# 指定日・競馬場の全レースを分析（ML予測付き）
keiba analyze --db data/keiba.db --date 2024-01-06 --venue 中山

# 特定のレースのみ分析
keiba analyze --db data/keiba.db --date 2024-01-06 --venue 中山 --race 11

# ML予測なしで分析（従来の動作）
keiba analyze --db data/keiba.db --date 2024-01-06 --venue 中山 --no-predict
```

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| --db | Yes | - | DBファイルパス |
| --date | Yes | - | レース日付（YYYY-MM-DD） |
| --venue | Yes | - | 競馬場名（例: 中山） |
| --race | No | 全レース | レース番号 |
| --no-predict | No | False | ML予測をスキップ |

ML予測は対象日より前のレースデータで学習を行い、各馬の「3着以内に入る確率」を予測。
学習データが100件未満の場合は自動的にスキップ。

### keiba migrate-grades

既存レースにグレード情報を追加するマイグレーションコマンド。

```bash
keiba migrate-grades --db data/keiba.db
```

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| --db | Yes | - | DBファイルパス |

### keiba predict

出馬表URLからリアルタイム予測を実行。未開催レースに対して7因子スコアとML予測を表示。

```bash
# 基本使用法（因子スコアのみ）
keiba predict --url "https://race.netkeiba.com/race/shutuba.html?race_id=202606010801" --db data/keiba.db --no-ml

# ML予測付き（モデルが必要）
keiba predict --url "https://race.netkeiba.com/race/shutuba.html?race_id=202606010801" --db data/keiba.db
```

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| --url | Yes | - | 出馬表ページURL（race.netkeiba.com） |
| --db | Yes | - | DBファイルパス |
| --no-ml | No | False | ML予測をスキップし因子スコアのみ表示 |

出馬表URLパターン: `https://race.netkeiba.com/race/shutuba.html?race_id={race_id}`

予測に使用するデータ:
- DB内の過去成績（レース日より前のデータのみ使用、データリーク防止）
- 7因子スコア（past_results, course_fit, time_index, last_3f, popularity, pedigree, running_style）
- ML予測（オプション、学習済みモデルが必要）

### keiba train

MLモデルを学習して保存する。

```bash
# 基本使用法
keiba train --db data/keiba.db --output data/models/model.joblib

# カットオフ日付を指定
keiba train --db data/keiba.db --output data/models/model.joblib --cutoff-date 2026-01-01
```

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| --db | Yes | - | DBファイルパス |
| --output | Yes | - | 出力モデルパス |
| --cutoff-date | No | 今日 | 学習データのカットオフ日（YYYY-MM-DD） |

学習完了時に以下のメトリクスが表示される:
- Precision@1: 予測1位の正解率
- Precision@3: 予測上位3位の正解率
- AUC-ROC: ROC曲線下面積

### keiba predict-day

指定日・競馬場の全レースを予測し、Markdownファイルに保存。

```bash
# 今日の中山全レースを予測
keiba predict-day --venue 中山 --db data/keiba.db

# 指定日の東京全レースを予測
keiba predict-day --date 2026-01-25 --venue 東京 --db data/keiba.db
```

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| --date | No | 今日 | 開催日（YYYY-MM-DD形式） |
| --venue | Yes | - | 競馬場名（例: 中山、東京、阪神など） |
| --db | Yes | - | DBファイルパス |
| --no-ml | No | False | ML予測をスキップ |

出力ファイル: `docs/predictions/YYYY-MM-DD-{venue}.md`

### keiba review-day

予測結果ファイルと実際のレース結果を比較検証。複勝・単勝シミュレーションを計算。

```bash
# 今日の中山の予測結果を検証
keiba review-day --venue 中山 --db data/keiba.db

# 指定日の予測結果を検証
keiba review-day --date 2026-01-24 --venue 中山 --db data/keiba.db
```

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| --date | No | 今日 | 開催日（YYYY-MM-DD形式） |
| --venue | Yes | - | 競馬場名 |
| --db | Yes | - | DBファイルパス |

検証内容:
- 予測ファイル（`docs/predictions/YYYY-MM-DD-{venue}.md`）を読み込み
- `RaceDetailScraper.fetch_payouts()`で複勝払戻金を取得
- `RaceDetailScraper.fetch_tansho_payout()`で単勝払戻金を取得
- 複勝シミュレーション（予測1位のみ、予測1-3位）を計算
- 単勝シミュレーション（予測1位のみ、予測1-3位）を計算
- 結果をMarkdownファイルに追記

シミュレーション種類:

| 券種 | 戦略 | 賭け方 | 的中条件 |
|------|------|--------|----------|
| 複勝 | 予測1位のみ | 予測1位に100円 | 3着以内 |
| 複勝 | 予測1-3位 | 予測1-3位に各100円（計300円） | いずれかが3着以内 |
| 単勝 | 予測1位のみ | 予測1位に100円 | 1着 |
| 単勝 | 予測1-3位 | 予測1-3位に各100円（計300円） | いずれかが1着 |

### keiba backtest

ML予測モデルのバックテストを実行。過去データに対してウォークフォワード方式で検証を行い、予測精度を評価。

```bash
# 基本（直近1ヶ月）
keiba backtest --db data/keiba.db

# 期間指定
keiba backtest --db data/keiba.db --from 2024-10-01 --to 2024-12-31

# 月数指定
keiba backtest --db data/keiba.db --months 3

# 詳細表示
keiba backtest --db data/keiba.db -v

# 再学習間隔指定
keiba backtest --db data/keiba.db --retrain-interval monthly
```

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| --db | Yes | - | DBファイルパス |
| --from | No | - | 開始日（YYYY-MM-DD） |
| --to | No | - | 終了日（YYYY-MM-DD） |
| --months | No | 1 | 直近何ヶ月を対象とするか |
| --retrain-interval | No | weekly | 再学習間隔（daily/weekly/monthly） |
| -v, --verbose | No | False | 詳細表示 |

### BacktestEngine アーキテクチャ

`BacktestEngine` クラスはウォークフォワード方式でML予測モデルを検証する。

#### クラス定数

| 定数 | 値 | 説明 |
|------|-----|------|
| MIN_TRAINING_SAMPLES | 100 | モデル学習に必要な最小サンプル数 |
| MAX_PAST_RESULTS_PER_HORSE | 20 | 馬ごとの取得過去成績数上限 |
| DEFAULT_FINISH_POSITION | 99 | 着順不明時のデフォルト値 |

#### セッション管理

データベースセッションのライフサイクルを明示的に管理:

| メソッド | 説明 |
|----------|------|
| `_open_session()` | セッションを開始（既存セッションがあればそのまま利用） |
| `_close_session()` | セッションをクローズ |
| `_with_session(func)` | コンテキスト管理デコレータ（セッションの自動開閉） |

#### バッチクエリメソッド

N+1問題を解消するためのバッチ取得メソッド:

| メソッド | 説明 |
|----------|------|
| `_get_horses_past_results_batch(horse_ids, before_date)` | 複数馬の過去成績を一括取得 |
| `_get_horses_batch(horse_ids)` | 複数馬の基本情報を一括取得 |

## 分析ファクター

現在7因子で構成され、各因子均等（約14.3%）の重み配分。

| 因子 | 説明 | 重み |
|------|------|------|
| past_results | 直近レースの着順ベースのスコア | 14.3% |
| course_fit | 同一条件（芝/ダート、距離）での実績 | 14.3% |
| time_index | 過去のタイム実績 | 14.3% |
| last_3f | 末脚の評価（上がり3F） | 14.3% |
| popularity | オッズ・人気順ベースのスコア | 14.3% |
| pedigree | 血統分析（父・母父系統の距離・馬場適性） | 14.3% |
| running_style | 脚質分析（脚質傾向とコース有利脚質のマッチ度） | 14.2% |

### 複合スコア（combined_score）

ML予測確率と7因子総合スコアを統合した複合指標。幾何平均で計算される。

計算式:
```
normalized_ml = (対象馬のML確率 / レース内最大ML確率) x 100
combined_score = sqrt(normalized_ml x total_score)
```

特徴:
- ML予測と因子分析の両方を考慮したバランスの取れた指標
- 0-100のスケールで出力
- 予測結果はcombined_score降順でソートされる
- CLI表示では「複合」列に表示

### 血統分析（PedigreeFactor）

8系統に分類して距離・馬場適性を評価。

| 系統 | 主な種牡馬例 |
|------|-------------|
| sunday_silence | サンデーサイレンス、ディープインパクト、ステイゴールド |
| kingmambo | キングマンボ、キングカメハメハ、ロードカナロア |
| northern_dancer | ノーザンダンサー、サドラーズウェルズ、フランケル |
| mr_prospector | ミスタープロスペクター、フォーティナイナー |
| roberto | ロベルト、ブライアンズタイム、モーリス |
| storm_cat | ストームキャット、ヘネシー |
| hail_to_reason | ヘイルトゥリーズン、リアルシャダイ |
| other | 上記に該当しない場合 |

- 距離適性: sprint（〜1400m）、mile（1400-1800m）、middle（1800-2200m）、long（2200m〜）
- 馬場適性: good（良/稍重）、heavy（重/不良）
- 父:母父 = 7:3 の重み付け

### 脚質分析（RunningStyleFactor）

4分類で脚質を判定し、コース有利脚質とのマッチ度を計算。

| 脚質 | 判定基準（1コーナー通過順位/出走頭数） |
|------|--------------------------------------|
| escape（逃げ） | 〜15% |
| front（先行） | 15%〜40% |
| stalker（差し） | 40%〜70% |
| closer（追込） | 70%〜 |

- 過去5走の脚質から最頻出の脚質を傾向として判定
- コース別有利脚質統計とのマッチ度をスコア化

## 依存関係

### 本番依存

| パッケージ | バージョン | 用途 |
|-----------|-----------|------|
| sqlalchemy | >=2.0 | ORM・データベース操作 |
| requests | >=2.28 | HTTPリクエスト |
| beautifulsoup4 | >=4.11 | HTMLパース |
| lxml | >=4.9 | HTMLパーサー |
| click | >=8.0 | CLI構築 |
| lightgbm | >=4.0.0 | 勾配ブースティング（ML予測） |
| scikit-learn | >=1.3.0 | 機械学習ユーティリティ |

### 開発依存

| パッケージ | バージョン | 用途 |
|-----------|-----------|------|
| pytest | >=7.0 | テストフレームワーク |
| pytest-cov | >=4.0 | カバレッジ計測 |

## テスト実行

```bash
# 全テスト実行
pytest

# 詳細出力
pytest -v

# カバレッジなしで実行（高速）
pytest --override-ini="addopts=" -v

# 特定のテストファイルのみ
pytest tests/test_scrapers.py -v

# 特定のテストクラスのみ
pytest tests/test_scrapers.py::TestHorseDetailScraperParse -v

# 分析因子関連のテスト
pytest tests/test_pedigree_factor.py tests/test_running_style_factor.py -v

# ML関連のテスト
pytest tests/ml/ -v
```

カバレッジ目標: 80%以上

## 開発ワークフロー

### 1. 新機能の追加

1. 新しいブランチを作成
2. モデル変更が必要な場合は `keiba/models/` を更新
3. スクレイパーを `keiba/scrapers/` に追加
4. `keiba/scrapers/__init__.py` でエクスポート
5. CLIコマンドを `keiba/cli/commands/` に追加
6. `keiba/cli/__init__.py` でコマンドを登録
7. テストを `tests/` に追加
8. 全テストがパスすることを確認

### CLIコマンド追加例

```python
# keiba/cli/commands/new_command.py
import click
from keiba.db import get_engine, get_session

@click.command()
@click.option("--db", required=True, help="DBファイルパス")
def new_command(db: str):
    """新しいコマンドの説明"""
    engine = get_engine(db)
    with get_session(engine) as session:
        # 処理
        pass

# keiba/cli/__init__.py に追加
from keiba.cli.commands.new_command import new_command
main.add_command(new_command)
```

### 2. 分析ファクターの追加

1. `keiba/analyzers/factors/` に新しいファクタークラスを作成
2. `BaseFactor` を継承し、`name` と `calculate()` を実装
3. `keiba/analyzers/factors/__init__.py` でエクスポート
4. `keiba/config/weights.py` に重みを追加（合計1.0）
5. 必要に応じてマスタデータを `keiba/config/` に追加
6. テストを `tests/test_<factor_name>_factor.py` に追加

### 3. ML特徴量の追加

1. `keiba/ml/feature_builder.py` の `_get_feature_config()` に特徴量を追加
2. `build_features()` で新しい特徴量の値を計算
3. テストを `tests/ml/test_feature_builder.py` に追加
4. 必要に応じて `keiba/services/training_service.py` の `build_training_data()` を更新

### 4. サービス層への機能追加

ビジネスロジックはサービス層（`keiba/services/`）に実装:

```python
# keiba/services/new_service.py
def new_business_logic(session, ...):
    """ビジネスロジックの実装"""
    pass

# keiba/services/__init__.py でエクスポート
from keiba.services.new_service import new_business_logic
__all__ = [..., "new_business_logic"]
```

### 5. リポジトリ層への機能追加

データアクセスロジックはリポジトリ層（`keiba/repositories/`）に実装:

```python
# keiba/repositories/new_repository.py
class NewRepository:
    def __init__(self, session):
        self._session = session

    def get_data(self, ...):
        """データ取得ロジック"""
        pass
```

### 6. テストの書き方

```python
# tests/fixtures/ にHTMLフィクスチャを追加
@pytest.fixture
def my_fixture_html():
    fixture_path = Path(__file__).parent / "fixtures" / "my_fixture.html"
    return fixture_path.read_text(encoding="utf-8")

# mockを使用してHTTPリクエストをモック
@patch.object(MyScraper, "fetch")
def test_my_scraper(self, mock_fetch, my_fixture_html):
    mock_fetch.return_value = my_fixture_html
    # テスト実装
```

### 7. パフォーマンス最適化

#### N+1問題の解消

ループ内で個別クエリを発行せず、バッチクエリでまとめて取得する:

```python
# BAD: N+1問題
for horse_id in horse_ids:
    results = session.query(PastResult).filter_by(horse_id=horse_id).all()

# GOOD: バッチクエリ
results = session.query(PastResult).filter(
    PastResult.horse_id.in_(horse_ids)
).all()
# 結果をhorse_idでグループ化
grouped = defaultdict(list)
for r in results:
    grouped[r.horse_id].append(r)
```

#### バッチクエリ実装パターン

1. 対象IDリストを収集
2. `IN` 句で一括取得
3. 結果を辞書でグループ化
4. 呼び出し元で辞書から参照

```python
def _get_horses_batch(self, horse_ids: list[str]) -> dict[str, Horse]:
    """複数馬の情報を一括取得"""
    horses = self._session.query(Horse).filter(
        Horse.id.in_(horse_ids)
    ).all()
    return {h.id: h for h in horses}
```

### 8. データベースマイグレーション

モデルにカラムを追加した場合、既存DBには以下でカラムを追加:

```bash
sqlite3 data/keiba.db "ALTER TABLE tablename ADD COLUMN columnname TYPE;"
```

### 9. DBインデックス追加

バックテストや大量クエリのパフォーマンス改善のため、インデックスを追加する場合:

```bash
# スクリプトを使用（推奨）
python scripts/add_indexes.py data/keiba.db

# 手動で追加する場合
sqlite3 data/keiba.db "CREATE INDEX IF NOT EXISTS ix_race_results_race_id ON race_results(race_id);"
sqlite3 data/keiba.db "CREATE INDEX IF NOT EXISTS ix_races_date ON races(date);"
```

インデックス追加後は `tests/test_db_indexes.py` でインデックスの存在を検証可能。

**注意**: 新規にテーブル作成する場合は、モデル定義（`keiba/models/`）にインデックスを追加すること。
`scripts/add_indexes.py` は既存DBへの後付けインデックス用。

## スクレイピングのレート制限

### グローバルレートリミッタ

`BaseScraper` はクラス変数 `_global_last_request_time` で全インスタンス間のリクエスト間隔を制御する。

```python
# 全スクレイパーインスタンスで共有されるタイマー
BaseScraper._global_last_request_time: float | None = None

# _apply_delay() で最後のリクエストからの経過時間をチェック
# delay未満の場合は残り時間をsleep
```

ポイント:
- 異なるスクレイパークラス（RaceListScraper、RaceDetailScraper等）間でもレート制限が共有される
- バックテストシミュレータでは `BaseSimulator._scraper` で単一インスタンスを再利用
- `finally` ブロックでタイマー更新するため、HTTPエラー時もレート制限タイマーが正しく更新される

### 指数バックオフ（リトライ機構）

HTTPエラー 403/429/503 発生時に指数バックオフでリトライ:

```python
# backoff_delays = [5, 10, 30]  # 秒
# max_retries = 3
# 対象: "403", "429", "503"
```

### パース警告

`HorseDetailScraper` は `parse_warnings` リストを返却値に含む。
HTML構造の変更を早期検出するため、パースできなかった要素について警告を収集する。

```python
result = {"id": horse_id, "parse_warnings": []}
# 各パースメソッドで warnings.append("element not found") を呼び出し
```

`scrape-horses --verbose` オプションで警告をCLI出力に表示可能。

## コーディング規約

- 型ヒントを使用
- docstringは日本語または英語で記述
- 関数は50行以下を目安
- ファイルは800行以下を目安
- イミュータブルなパターンを推奨

## トラブルシューティング

### ModuleNotFoundError

```bash
pip install -e .
```

### データベースカラムエラー

モデル変更後に発生。ALTER TABLEでカラムを追加するか、DBを再作成。
