# keiba

競馬データ収集システム - netkeibaからレースデータを収集しSQLiteに保存するCLIツール

## 機能

- 指定した年月のレースデータを自動収集
- SQLiteデータベースに保存
- 既存データのスキップ（再実行可能）
- 馬の詳細情報（血統等）の収集
- レース分析機能（スコア算出）

### 収集データ

レース結果には以下の情報が含まれます：
- 基本情報: 着順、枠番、馬番、タイム、着差
- 馬情報: 性別、年齢、馬体重、馬体重増減
- レース情報: 斤量、通過順位、上がり3F
- オッズ情報: 単勝オッズ、人気

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

#### scrapeコマンド

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| --year    | Yes  | - | 取得する年 |
| --month   | Yes  | - | 取得する月 |
| --db      | Yes  | - | DBファイルパス |
| --jra-only | No  | False | 中央競馬（JRA）のみ取得 |

#### JRA vs NAR フィルタリング

`--jra-only`オプションを指定すると、中央競馬（JRA）のレースのみを収集します。
NAR（地方競馬）を含めたい場合はこのオプションを省略してください。

JRA競馬場一覧:
- 札幌、函館、福島、新潟、東京、中山、中京、京都、阪神、小倉

```bash
# 中央競馬のみ収集
keiba scrape --year 2024 --month 1 --db data/keiba.db --jra-only

# 全競馬場（JRA + NAR）を収集
keiba scrape --year 2024 --month 1 --db data/keiba.db
```

#### scrape-horsesコマンド

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| --db      | Yes  | - | DBファイルパス |
| --limit   | No   | 100 | 取得する馬の数 |

```bash
# 詳細未取得の馬情報を収集
keiba scrape-horses --db data/keiba.db --limit 500
```

#### analyzeコマンド

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| --db      | Yes  | - | DBファイルパス |
| --date    | Yes  | - | レース日付（YYYY-MM-DD） |
| --venue   | Yes  | - | 競馬場名（例: 中山） |
| --race    | No   | 全レース | レース番号 |
| --no-predict | No | False | ML予測を無効化 |

```bash
# 指定日・競馬場の全レースを分析
keiba analyze --db data/keiba.db --date 2024-01-06 --venue 中山

# 特定のレースのみ分析
keiba analyze --db data/keiba.db --date 2024-01-06 --venue 中山 --race 11
```

#### レース分析（ML予測付き）

```bash
# ML予測付きでレース分析
keiba analyze --db keiba.db --date 2024-01-06 --venue 中山

# ML予測なしで分析（従来の動作）
keiba analyze --db keiba.db --date 2024-01-06 --venue 中山 --no-predict
```

ML予測機能は、過去のレース結果を学習データとしてLightGBMモデルを構築し、
各馬の「3着以内に入る確率」を予測します。

**必要条件:**
- 対象レース日より前に100レース以上のデータが必要
- データが不足している場合はML予測がスキップされます

分析結果は以下のスコアを算出します：
- 過去成績（過去）: 直近レースの着順ベースのスコア
- コース適性（適性）: 同一条件（芝/ダート、距離）での実績
- タイム指数（タイム）: 過去のタイム実績
- 上がり3F（上がり）: 末脚の評価
- 人気（人気）: オッズ・人気順ベースのスコア

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

### race_resultsテーブル詳細

レース結果テーブルには以下のカラムが含まれます：

| カラム | 型 | 説明 |
|--------|------|------|
| id | INTEGER | 自動採番ID（主キー） |
| race_id | TEXT | レースID（外部キー） |
| horse_id | TEXT | 馬ID（外部キー） |
| jockey_id | TEXT | 騎手ID（外部キー） |
| trainer_id | TEXT | 調教師ID（外部キー） |
| finish_position | INTEGER | 着順（中止等は0） |
| bracket_number | INTEGER | 枠番 |
| horse_number | INTEGER | 馬番 |
| odds | REAL | 単勝オッズ |
| popularity | INTEGER | 人気 |
| weight | INTEGER | 馬体重 |
| weight_diff | INTEGER | 馬体重増減 |
| time | TEXT | タイム |
| margin | TEXT | 着差 |
| last_3f | REAL | 上がり3F（秒） |
| sex | TEXT | 性別（牡/牝/セ） |
| age | INTEGER | 年齢 |
| impost | REAL | 斤量 |
| passing_order | TEXT | 通過順位（例: "2-1-1-1"） |
| created_at | DATETIME | 作成日時 |
| updated_at | DATETIME | 更新日時 |

## 開発

```bash
# テスト実行
pytest tests/ -v

# カバレッジ付きテスト
pytest tests/ --cov=keiba --cov-report=term-missing
```

## ライセンス

MIT License
