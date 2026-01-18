# keiba

競馬データ収集システム - netkeibaからレースデータを収集しSQLiteに保存するCLIツール

## 機能

- 指定した年月のレースデータを自動収集
- SQLiteデータベースに保存
- 既存データのスキップ（再実行可能）

## 必要条件

- Python 3.10以上

## インストール

```bash
# リポジトリクローン
git clone <repository-url>
cd keiba

# 仮想環境作成・有効化
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

# インストール
pip install -e ".[dev]"
```

## 使用方法

```bash
# 2024年1月のレースデータを収集
keiba scrape --year 2024 --month 1 --db data/keiba.db

# または
python -m keiba scrape --year 2024 --month 1 --db data/keiba.db
```

### オプション

| オプション | 必須 | 説明 |
|-----------|------|------|
| --year    | Yes  | 取得する年 |
| --month   | Yes  | 取得する月 |
| --db      | Yes  | DBファイルパス |

## データベース構造

以下のテーブルが作成されます：

| テーブル | 説明 |
|----------|------|
| horses | 競走馬 |
| jockeys | 騎手 |
| trainers | 調教師 |
| owners | 馬主 |
| breeders | 生産者 |
| races | レース |
| race_results | レース結果 |

## 開発

```bash
# テスト実行
pytest tests/ -v

# カバレッジ付きテスト
pytest tests/ --cov=keiba --cov-report=term-missing
```

## ライセンス

MIT License
