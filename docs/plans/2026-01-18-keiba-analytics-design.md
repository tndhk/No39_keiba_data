# 競馬データ収集・分析システム設計書

## 概要

netkeibaからデータを収集し、SQLiteに蓄積する競馬データ収集システム。
段階的にデータ収集 → 統計分析 → 機械学習予測へと発展させる。

## 要件

- データソース: netkeiba.com
- 収集データ: レース結果、馬情報、騎手、調教師、馬主、生産者、オッズ
- データ範囲: 過去5年分
- 言語: Python
- DB: SQLite
- 実行方法: CLI（将来的に自動化）

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    keiba-analytics                          │
├─────────────────────────────────────────────────────────────┤
│  CLI Layer                                                  │
│  └── scrape      # データ収集コマンド                        │
├─────────────────────────────────────────────────────────────┤
│  Core Layer                                                 │
│  ├── scrapers/   # netkeiba用スクレイパー                    │
│  └── models/     # データモデル（SQLAlchemy）                │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                 │
│  └── SQLite Database (keiba.db)                             │
└─────────────────────────────────────────────────────────────┘
```

## データモデル

### horses（馬）

| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER | PRIMARY KEY |
| netkeiba_id | TEXT | netkeibaのID（UNIQUE） |
| name | TEXT | 馬名 |
| birth_year | INTEGER | 生年 |
| sex | TEXT | 性別（牡/牝/セ） |
| sire | TEXT | 父 |
| dam | TEXT | 母 |
| dam_sire | TEXT | 母父 |
| sire_of_sire | TEXT | 父父 |
| dam_of_sire | TEXT | 父母 |
| breeder | TEXT | 生産者（牧場） |
| owner | TEXT | 馬主 |
| birthplace | TEXT | 産地 |
| coat_color | TEXT | 毛色 |
| sale_price | INTEGER | セリ取引価格（万円） |
| total_races | INTEGER | 通算出走数 |
| total_wins | INTEGER | 通算勝利数 |
| total_earnings | INTEGER | 獲得賞金（万円） |
| created_at | DATETIME | 作成日時 |
| updated_at | DATETIME | 更新日時 |

### jockeys（騎手）

| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER | PRIMARY KEY |
| netkeiba_id | TEXT | netkeibaのID（UNIQUE） |
| name | TEXT | 騎手名 |
| created_at | DATETIME | 作成日時 |
| updated_at | DATETIME | 更新日時 |

### trainers（調教師）

| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER | PRIMARY KEY |
| netkeiba_id | TEXT | netkeibaのID（UNIQUE） |
| name | TEXT | 調教師名 |
| created_at | DATETIME | 更新日時 |
| updated_at | DATETIME | 更新日時 |

### owners（馬主）

| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER | PRIMARY KEY |
| netkeiba_id | TEXT | netkeibaのID（UNIQUE） |
| name | TEXT | 馬主名 |
| created_at | DATETIME | 作成日時 |
| updated_at | DATETIME | 更新日時 |

### breeders（生産者）

| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER | PRIMARY KEY |
| netkeiba_id | TEXT | netkeibaのID（UNIQUE） |
| name | TEXT | 生産者名 |
| location | TEXT | 所在地 |
| created_at | DATETIME | 作成日時 |
| updated_at | DATETIME | 更新日時 |

### races（レース）

| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER | PRIMARY KEY |
| netkeiba_id | TEXT | レースID（UNIQUE） |
| name | TEXT | レース名 |
| date | DATE | 開催日 |
| venue | TEXT | 開催場（東京、中山等） |
| race_number | INTEGER | レース番号 |
| course_type | TEXT | 芝/ダート |
| distance | INTEGER | 距離（メートル） |
| weather | TEXT | 天候 |
| track_condition | TEXT | 馬場状態 |
| grade | TEXT | グレード（G1, G2, OP等） |
| created_at | DATETIME | 作成日時 |
| updated_at | DATETIME | 更新日時 |

### race_results（レース結果）

| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER | PRIMARY KEY |
| race_id | INTEGER | FK → races |
| horse_id | INTEGER | FK → horses |
| jockey_id | INTEGER | FK → jockeys |
| trainer_id | INTEGER | FK → trainers |
| post_position | INTEGER | 枠番 |
| horse_number | INTEGER | 馬番 |
| finish_position | INTEGER | 着順 |
| finish_time | TEXT | タイム |
| margin | TEXT | 着差 |
| weight | INTEGER | 馬体重 |
| weight_change | INTEGER | 馬体重増減 |
| odds | REAL | 単勝オッズ |
| popularity | INTEGER | 人気 |
| created_at | DATETIME | 作成日時 |
| updated_at | DATETIME | 更新日時 |

## スクレイピング設計

### モジュール構成

```
scrapers/
├── base.py           # 共通処理（リクエスト、パース、レート制限）
├── race_list.py      # レース一覧取得（年/月単位）
├── race_detail.py    # レース詳細・結果取得
├── horse.py          # 馬詳細取得
├── jockey.py         # 騎手詳細取得
└── trainer.py        # 調教師詳細取得
```

### 収集フロー

```
1. race_list: 指定期間のレースID一覧を取得
       ↓
2. race_detail: 各レースの詳細・出走馬・結果を取得
       ↓
3. horse/jockey/trainer: 未取得の馬・騎手・調教師の詳細を取得
```

### レート制限対策

- リクエスト間隔: 1〜2秒
- 中断・再開機能: 途中で止めても続きから再開可能
- エラーリトライ: 3回まで自動リトライ

## CLIコマンド

```bash
# 2024年のレースデータを収集
python -m keiba scrape --year 2024

# 特定の月を収集
python -m keiba scrape --year 2024 --month 6

# 馬詳細を追加収集
python -m keiba scrape --type horses --limit 100
```

## プロジェクト構成

```
keiba/
├── pyproject.toml        # 依存関係管理
├── keiba/
│   ├── __init__.py
│   ├── __main__.py       # CLIエントリーポイント
│   ├── cli.py            # コマンド定義
│   ├── db.py             # DB接続・セッション管理
│   ├── models/           # SQLAlchemyモデル
│   │   ├── __init__.py
│   │   ├── horse.py
│   │   ├── race.py
│   │   ├── jockey.py
│   │   ├── trainer.py
│   │   ├── owner.py
│   │   └── breeder.py
│   └── scrapers/         # スクレイパー
│       ├── __init__.py
│       ├── base.py
│       ├── race_list.py
│       ├── race_detail.py
│       └── horse.py
├── data/
│   └── keiba.db          # SQLiteデータベース
└── tests/
    └── ...
```

## 依存ライブラリ

- requests: HTTPリクエスト
- beautifulsoup4: HTMLパース
- sqlalchemy: ORM
- click: CLI
- lxml: 高速HTMLパーサー（オプション）

## 開発フェーズ

### Phase 1: データ収集基盤（今回のスコープ）

- DBモデル定義
- レース一覧スクレイパー
- レース詳細スクレイパー
- 馬詳細スクレイパー
- CLIコマンド

### Phase 2: 分析機能（後日）

- 分析ロジック
- 出力形式（決まってから実装）

### Phase 3: 自動化（後日）

- スケジューラ対応
- 定期収集

### Phase 4: 機械学習予測（後日）

- 統計分析で傾向を掴んでから検討
