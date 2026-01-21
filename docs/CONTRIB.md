# 開発者ガイド

競馬データ収集システムの開発ワークフローガイド。

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
├── models/       # SQLAlchemyモデル定義
├── scrapers/     # Webスクレイパー
├── analyzers/    # レース分析モジュール
│   └── factors/  # スコア算出ファクター（7因子）
├── ml/           # 機械学習予測モジュール
│   ├── feature_builder.py  # 特徴量構築
│   ├── trainer.py          # LightGBMモデル学習
│   └── predictor.py        # 予測実行
├── backtest/     # バックテストモジュール
│   ├── backtester.py  # BacktestEngine
│   ├── metrics.py     # メトリクス計算
│   └── reporter.py    # レポート出力
├── config/       # 設定（分析ウェイト、血統マスタ等）
├── utils/        # ユーティリティ（グレード抽出等）
├── db.py         # データベース接続
└── cli.py        # CLIエントリーポイント
tests/
├── fixtures/     # テスト用HTMLフィクスチャ
├── ml/           # ML関連テスト
└── test_*.py     # テストファイル
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
5. CLI コマンドを `keiba/cli.py` に追加
6. テストを `tests/` に追加
7. 全テストがパスすることを確認

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
4. 必要に応じて `cli.py` の `_build_training_data()` を更新

### 4. テストの書き方

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

### 5. データベースマイグレーション

モデルにカラムを追加した場合、既存DBには以下でカラムを追加:

```bash
sqlite3 data/keiba.db "ALTER TABLE tablename ADD COLUMN columnname TYPE;"
```

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
