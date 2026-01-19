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
├── db.py         # データベース接続
└── cli.py        # CLIエントリーポイント
tests/
├── fixtures/     # テスト用HTMLフィクスチャ
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

## 依存関係

### 本番依存

| パッケージ | バージョン | 用途 |
|-----------|-----------|------|
| sqlalchemy | >=2.0 | ORM・データベース操作 |
| requests | >=2.28 | HTTPリクエスト |
| beautifulsoup4 | >=4.11 | HTMLパース |
| lxml | >=4.9 | HTMLパーサー |
| click | >=8.0 | CLI構築 |

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
```

## 開発ワークフロー

### 1. 新機能の追加

1. 新しいブランチを作成
2. モデル変更が必要な場合は `keiba/models/` を更新
3. スクレイパーを `keiba/scrapers/` に追加
4. `keiba/scrapers/__init__.py` でエクスポート
5. CLI コマンドを `keiba/cli.py` に追加
6. テストを `tests/` に追加
7. 全テストがパスすることを確認

### 2. テストの書き方

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

### 3. データベースマイグレーション

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
