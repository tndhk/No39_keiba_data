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
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

# インストール
pip install -e ".[dev]"
```

## 使用方法

```bash
# 2024年1月のレースデータを収集
keiba scrape --year 2024 --month 1 --db data/keiba.db --jra-only

# または
python3 -m keiba scrape --year 2024 --month 1 --db data/keiba.db --jra-only
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

#### predict-dayコマンド

指定日・競馬場の全レースを予測し、結果をMarkdownファイルに保存します。

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| --date    | No   | 今日 | 開催日（YYYY-MM-DD形式） |
| --venue   | Yes  | - | 競馬場名（例: 中山） |
| --db      | Yes  | - | DBファイルパス |
| --no-ml   | No   | False | ML予測をスキップ |

```bash
# 今日の中山全レースを予測
keiba predict-day --venue 中山 --db data/keiba.db

# 指定日の東京全レースを予測
keiba predict-day --date 2026-01-25 --venue 東京 --db data/keiba.db
```

予測結果は `docs/predictions/YYYY-MM-DD-{venue}.md` に保存されます。

#### review-dayコマンド

予測結果ファイルを読み込み、実際のレース結果と比較検証します。
複勝シミュレーション（的中率・回収率）を計算し、結果をMarkdownファイルに追記します。

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| --date    | No   | 今日 | 開催日（YYYY-MM-DD形式） |
| --venue   | Yes  | - | 競馬場名（例: 中山） |
| --db      | Yes  | - | DBファイルパス |

```bash
# 今日の中山の予測結果を検証
keiba review-day --venue 中山 --db data/keiba.db

# 指定日の予測結果を検証
keiba review-day --date 2026-01-24 --venue 中山 --db data/keiba.db
```

検証結果には以下が含まれます:
- 複勝シミュレーション（予測1位のみ、予測1-3位）
- 的中率・回収率
- レース別の予測結果と実際の結果の比較

#### backtest-fukushoコマンド

過去データを使用して複勝馬券の購入戦略をシミュレートし、回収率を計算します。

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| --from    | No   | 先週の月曜日 | 開始日（YYYY-MM-DD形式） |
| --to      | No   | 先週の日曜日 | 終了日（YYYY-MM-DD形式） |
| --last-week | No | True | 先週を対象（デフォルト） |
| --top-n   | No   | 3 | Top何頭に賭けるか |
| --venue   | No   | 全会場 | 競馬場フィルタ（複数可） |
| --db      | Yes  | - | DBファイルパス |
| -v, --verbose | No | False | レース別詳細表示 |

```bash
# 先週のバックテスト（デフォルト）
keiba backtest-fukusho --db data/keiba.db -v

# 期間指定
keiba backtest-fukusho --from 2026-01-18 --to 2026-01-19 --db data/keiba.db

# 競馬場フィルタ（複数指定可能）
keiba backtest-fukusho --from 2026-01-18 --to 2026-01-19 --venue 中山 --venue 京都 --db data/keiba.db

# Top5に賭ける戦略
keiba backtest-fukusho --top-n 5 --db data/keiba.db
```

シミュレーション結果には以下が含まれます:
- 対象レース数
- 総賭け数、的中数、的中率
- 投資額、払戻額、回収率

分析結果は以下のスコアを算出します：
- 過去成績: 直近レースの着順ベースのスコア
- コース適性: 同一条件（芝/ダート、距離）での実績
- タイム指数: 過去のタイム実績
- 上がり3F: 末脚の評価
- 人気: オッズ・人気順ベースのスコア
- 血統: 父・母父系統の距離・馬場適性
- 脚質: 脚質傾向とコース有利脚質のマッチ度

## データ運用

### 予測の仕組み

予測実行時、以下のデータが使用されます：

| データ | 取得元 | 用途 |
|:---|:---|:---|
| 出走馬情報 | netkeibaからリアルタイム取得 | 馬番、斤量など |
| 過去成績 | data/keiba.db | ファクタースコア計算 |

各馬の過去成績は最大20走分を参照し、直近5走を重視して評価します。

### 推奨データ量

- 2-3年分のデータがあれば十分
- 定期的に `keiba scrape` で最新月を追加

### モデルについて

- 学習済みモデルは19個の特徴量で構築
- DBを更新しても再学習は不要（特徴量定義が同じため）
- 新しい特徴量を追加する場合のみ再学習が必要

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
