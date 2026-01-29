# 運用ガイド (Runbook)

競馬データ収集システムの運用手順書。

## データ収集手順

### レースデータの収集

指定した年月のレースデータをnetkeibaから収集してSQLiteに保存。

```bash
# 全競馬場（JRA + NAR）のレースを収集
keiba scrape --year 2024 --month 3 --db data/keiba.db

# 中央競馬（JRA）のみ収集（推奨：データ品質が高い）
keiba scrape --year 2024 --month 3 --db data/keiba.db --jra-only

# 出力例
# データ収集開始: 2024年3月 (中央競馬のみ)
# データベース: data/keiba.db
#   2024/03/01 のレースを取得中...
#     保存: 202403010101 - レース名
#   ...
# 完了: 2024年3月
#   総レース数: 150
#   保存済み: 145
#   スキップ: 5
```

JRA競馬場一覧:
- 札幌(01)、函館(02)、福島(03)、新潟(04)、東京(05)
- 中山(06)、中京(07)、京都(08)、阪神(09)、小倉(10)

### レース分析（ML予測付き）

収集したデータを基にレースを分析し、各馬のスコアとML予測を表示。

```bash
# 指定日・競馬場の全レースを分析（ML予測付き）
keiba analyze --db data/keiba.db --date 2024-01-06 --venue 中山

# 特定のレースのみ分析
keiba analyze --db data/keiba.db --date 2024-01-06 --venue 中山 --race 11

# ML予測なしで分析（従来の動作）
keiba analyze --db data/keiba.db --date 2024-01-06 --venue 中山 --no-predict

# 出力例（ML予測付き）
# ================================================================================
# 2024-01-06 中山 11R 第74回日刊スポ賞中山金杯 芝2000m
# 【ML予測】学習データ: 5,000件
# ================================================================================
# 予測 | 馬番 |    馬名     | 3着内確率 |  総合  |  過去  |  適性  | タイム |  上がり |  人気
# --------------------------------------------------------------------------------------------
#   1  |   5  |  ○○○○○○  |   62.3%  |  80.5  |  78.2  |  82.0  |  79.5  |  81.0  |  82.0
```

ML予測機能:
- 対象レース日より前のデータで自動学習
- LightGBMによる3着以内確率予測
- 学習データ100件以上で有効化
- 19特徴量（7因子スコア + 8生データ + 4派生特徴量）

分析ファクター（7因子）:
- 過去成績: 直近レースの着順ベースのスコア（14.3%）
- コース適性: 同一条件（芝/ダート、距離）での実績（14.3%）
- タイム指数: 過去のタイム実績（14.3%）
- 上がり3F: 末脚の評価（14.3%）
- 人気: オッズ・人気順ベースのスコア（14.3%）
- 血統: 父・母父系統の距離・馬場適性（14.3%）
- 脚質: 脚質傾向とコース有利脚質のマッチ度（14.2%）

複合スコア（combined_score）:
- ML確率と7因子総合スコアを幾何平均で統合した指標
- 計算式: sqrt((ML確率/最大ML確率 x 100) x 総合スコア)
- CLI表示で「複合」列として表示
- 予測結果のデフォルトソート順

### 出馬表予測（リアルタイム）

未開催レースの出馬表URLから予測を実行。netkeibaの出馬表ページをスクレイピングして各馬の7因子スコアを計算。

```bash
# 出馬表URLから予測（因子スコアのみ）
keiba predict --url "https://race.netkeiba.com/race/shutuba.html?race_id=202606010801" --db data/keiba.db --no-ml

# ML予測付きで実行（学習済みモデルがある場合）
keiba predict --url "https://race.netkeiba.com/race/shutuba.html?race_id=202606010801" --db data/keiba.db

# 出力例
# 出馬表予測: 202606010801
# 2026年1月19日 中山 1R 芝2000m
# サラ系3歳未勝利
# ================================================================================
# 順位 | 馬番 |    馬名     | ML確率 |  総合  |  過去  |  適性  | 指数 | 上り | 人気 | 血統 | 脚質
# --------------------------------------------------------------------------------------------
#   1  |   5  |  テストホース  |   -   |  75.2  |  70.5  |  80.0  | 72.0 | 78.5 | 65.0 | 82.0 | 74.0
```

データリーク防止:
- レース日より前の過去成績のみ使用
- 当日のオッズ・人気は使用しない（過去成績の人気を参照）

対応URL形式:
- `https://race.netkeiba.com/race/shutuba.html?race_id={race_id}`
- race_id形式: YYYYCCDDRRNN（年4桁 + 競馬場2桁 + 日程2桁 + レース番号2桁 + 枠番2桁）

### バックテスト実行

ML予測と7ファクタースコアの精度を過去データで検証。

```bash
# 直近1ヶ月のバックテスト
keiba backtest --db data/keiba.db

# 直近3ヶ月のバックテスト
keiba backtest --db data/keiba.db --months 3

# 期間指定
keiba backtest --db data/keiba.db --from 2024-10-01 --to 2024-12-31

# 詳細表示（各レースの予測結果を出力）
keiba backtest --db data/keiba.db -v

# 出力例
# ================================================================================
# バックテスト結果: 2024-10-01 ~ 2024-12-31
# ================================================================================
# 対象レース数: 1,234
# 対象出走馬数: 15,678
# 再学習間隔: weekly
#
# --------------------------------------------------------------------------------
#                      |    ML予測    |   7ファクター   |   差分
# --------------------------------------------------------------------------------
# Precision@1          |      32.5% |      28.1% |   +4.4%
# Precision@3          |      58.2% |      52.7% |   +5.5%
# --------------------------------------------------------------------------------
# 1位指名 的中率       |      35.2% |      30.5% |   +4.7%
# 2位指名 的中率       |      31.8% |      27.3% |   +4.5%
# 3位指名 的中率       |      28.4% |      25.1% |   +3.3%
# --------------------------------------------------------------------------------
```

再学習間隔オプション:
- `daily`: 毎日再学習（最も正確だが遅い）
- `weekly`（デフォルト）: 週次再学習（推奨：精度と速度のバランス）
- `monthly`: 月次再学習（高速だが精度低下の可能性）

パフォーマンス最適化:
- N+1問題解消: バッチクエリによる効率的なデータ取得
- セッション管理改善: DBセッションの再利用による接続オーバーヘッド削減
- クエリ最適化: 馬データ・レース結果の一括取得で大幅な速度向上

### 馬詳細データの収集

レース結果から取得した馬IDに基づき、馬の詳細情報（血統・成績）を収集。
血統分析を行うには馬詳細データ（sire, dam_sire）が必要。

```bash
# 基本コマンド（デフォルト100件）
keiba scrape-horses --db data/keiba.db

# 取得件数を指定
keiba scrape-horses --db data/keiba.db --limit 500

# 詳細表示（パース警告を表示）
keiba scrape-horses --db data/keiba.db --limit 500 -v

# 出力例
# 馬詳細データ収集開始
# データベース: data/keiba.db
# 取得上限: 100件
# 詳細未取得の馬: 50件
#   [1/50] ドウデュース (2019104251)...
#     更新完了
#   ...
# 完了
#   処理数: 50
#   更新成功: 48
#   エラー: 2
#   パース警告あり: 3件 (--verbose で詳細表示)
```

パース警告:
- `HorseDetailScraper` はHTMLの構造変更を検出して `parse_warnings` リストに記録
- `--verbose` / `-v` オプションで警告の詳細がCLI出力に表示される
- 警告が頻出する場合はnetkeibaのHTML構造変更を確認し、パーサーを更新する

### グレード情報のマイグレーション

既存レースにグレード情報（G1/G2/G3/L/OP等）を追加。

```bash
keiba migrate-grades --db data/keiba.db

# 出力例
# グレード情報マイグレーション開始
# データベース: data/keiba.db
# グレード未設定のレース: 1500件
#   100件処理...
#   200件処理...
# 完了
#   更新したレース: 1500件
```

### MLモデルの学習

予測に使用するLightGBMモデルを学習して保存。

```bash
# 基本使用法（今日以前のデータで学習）
keiba train --db data/keiba.db --output data/models/model.joblib

# カットオフ日付を指定（特定日以前のデータで学習）
keiba train --db data/keiba.db --output data/models/model.joblib --cutoff-date 2026-01-01

# 出力例
# 学習開始
# データベース: data/keiba.db
# 出力先: data/models/model.joblib
# カットオフ日付: 2026-01-25
#
# 学習データを構築中...
# 学習データ: 15000サンプル
# モデルを学習中...
#
# 学習完了
#   Precision@1: 35.2%
#   Precision@3: 58.4%
#   AUC-ROC: 0.725
#
# モデルを保存しました: data/models/model.joblib
```

推奨ワークフロー:
1. 週次で新しいモデルを学習（日曜日のレース終了後）
2. モデルファイルはタイムスタンプ付きで管理: `model-YYYYMMDD.joblib`
3. `predict`コマンドは`data/models/`から最新の`.joblib`を自動検出

## 定期実行の設定

### crontabでの設定例

```bash
# 毎月1日深夜2時に前月のJRAレースデータを収集
0 2 1 * * cd /path/to/No39_keiba && keiba scrape --year $(date -d "last month" +\%Y) --month $(date -d "last month" +\%m) --db data/keiba.db --jra-only >> logs/scrape.log 2>&1

# 毎月1日深夜2時に前月の全競馬場データを収集（NAR含む）
# 0 2 1 * * cd /path/to/No39_keiba && keiba scrape --year $(date -d "last month" +\%Y) --month $(date -d "last month" +\%m) --db data/keiba.db >> logs/scrape.log 2>&1

# 毎日深夜3時に馬詳細を100件ずつ収集（血統分析に必要）
0 3 * * * cd /path/to/No39_keiba && keiba scrape-horses --db data/keiba.db --limit 100 >> logs/horses.log 2>&1
```

## データベース管理

### スキーマ確認

```bash
sqlite3 data/keiba.db ".schema"
```

### テーブル一覧

| テーブル | 内容 |
|---------|------|
| races | レース情報 |
| horses | 馬情報（血統含む） |
| jockeys | 騎手情報 |
| trainers | 調教師情報 |
| race_results | レース結果（通過順位含む） |
| owners | 馬主情報 |
| breeders | 生産者情報 |

### horsesテーブルの血統関連カラム

血統分析（PedigreeFactor）に必要なカラム:

| カラム | 型 | 説明 |
|--------|------|------|
| sire | TEXT | 父名 |
| dam | TEXT | 母名 |
| dam_sire | TEXT | 母父名 |

### race_resultsテーブルの拡張カラム

脚質分析（RunningStyleFactor）に必要なカラム:

| カラム | 型 | 説明 |
|--------|------|------|
| last_3f | REAL | 上がり3F（秒） |
| sex | TEXT | 性別（牡/牝/セ） |
| age | INTEGER | 年齢 |
| impost | REAL | 斤量 |
| passing_order | TEXT | 通過順位（例: "2-1-1-1"） |

### racesテーブルの拡張カラム

| カラム | 型 | 説明 |
|--------|------|------|
| grade | TEXT | グレード/クラス（G1, G2, G3, L, OP, 1WIN等） |

### データ件数確認

```bash
sqlite3 data/keiba.db "
SELECT 'races' as table_name, COUNT(*) as count FROM races
UNION ALL
SELECT 'horses', COUNT(*) FROM horses
UNION ALL
SELECT 'race_results', COUNT(*) FROM race_results;
"
```

### インデックス確認

```bash
# インデックス一覧を確認
sqlite3 data/keiba.db "SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name LIKE 'ix_%';"

# 期待されるインデックス:
# ix_race_results_race_id | race_results
# ix_races_date           | races
```

### インデックス追加

バックテストのパフォーマンスを改善するため、既存DBにインデックスを追加:

```bash
# スクリプトで追加（推奨）
python scripts/add_indexes.py data/keiba.db

# 出力例:
# データベース: data/keiba.db
# --------------------------------------------------
# [OK] ix_race_results_race_id (race_results.race_id)
# [OK] ix_races_date (races.date)
# --------------------------------------------------
# インデックス追加が完了しました
```

**効果**: バックテスト実行時間 38分 -> 4分（約90%削減）

### 血統データ取得状況の確認

```bash
# 血統情報が取得済みの馬の数
sqlite3 data/keiba.db "SELECT COUNT(*) FROM horses WHERE sire IS NOT NULL;"

# 血統情報が未取得の馬の数
sqlite3 data/keiba.db "SELECT COUNT(*) FROM horses WHERE sire IS NULL;"
```

### バックアップ

```bash
# 日付付きでバックアップ
cp data/keiba.db data/keiba_$(date +%Y%m%d).db

# gzip圧縮してバックアップ
sqlite3 data/keiba.db ".backup data/backup.db" && gzip data/backup.db
```

## よくある問題と解決策

### 1. カラムが存在しないエラー

症状:
```
sqlite3.OperationalError: no such column: races.grade
```

原因: モデル変更後にDBマイグレーションが未実行

解決方法1: 不足カラムを追加
```bash
# racesテーブルにgradeカラムを追加
sqlite3 data/keiba.db "ALTER TABLE races ADD COLUMN grade TEXT;"

# race_resultsテーブルに拡張カラムを追加
sqlite3 data/keiba.db "ALTER TABLE race_results ADD COLUMN last_3f REAL;"
sqlite3 data/keiba.db "ALTER TABLE race_results ADD COLUMN sex TEXT;"
sqlite3 data/keiba.db "ALTER TABLE race_results ADD COLUMN age INTEGER;"
sqlite3 data/keiba.db "ALTER TABLE race_results ADD COLUMN impost REAL;"
sqlite3 data/keiba.db "ALTER TABLE race_results ADD COLUMN passing_order TEXT;"

# horsesテーブルに血統カラムを追加
sqlite3 data/keiba.db "ALTER TABLE horses ADD COLUMN sire TEXT;"
sqlite3 data/keiba.db "ALTER TABLE horses ADD COLUMN dam TEXT;"
sqlite3 data/keiba.db "ALTER TABLE horses ADD COLUMN dam_sire TEXT;"
```

解決方法2: DBを削除して再作成（データが少ない場合）
```bash
rm data/keiba.db
keiba scrape --year 2024 --month 1 --db data/keiba.db --jra-only
```

### 2. 血統分析でNoneが返る

症状: 血統分析のスコアがNoneになる

原因: 馬の血統情報（sire）が未取得

解決:
```bash
# 馬詳細データを収集
keiba scrape-horses --db data/keiba.db --limit 500
```

### 3. 脚質分析でNoneが返る

症状: 脚質分析のスコアがNoneになる

原因: 過去のレース結果にpassing_orderが含まれていない

解決: passing_orderはレース詳細取得時に自動保存される。古いデータの場合は再取得が必要。

### 4. HTTPエラー (403/429/503)

症状:
```
requests.exceptions.HTTPError: 403 Client Error: Forbidden
```

原因: アクセス制限またはレート制限

自動対策（v1.x以降）:
- `BaseScraper` がHTTP 403/429/503エラー時に指数バックオフで自動リトライ
- リトライ間隔: 5秒, 10秒, 30秒（最大3回）
- グローバルレートリミッタにより全スクレイパーインスタンス間でリクエスト間隔を制御
- HTTPエラー時もレート制限タイマーが更新されるため、連続リクエストによるブロックを防止

手動対策:
- 上記リトライでも解決しない場合は、時間をおいて再実行
- `BaseScraper(delay=2.0)` のようにdelayを増やすことも可能（デフォルト1秒）

### 5. パースエラー

症状:
```
AttributeError: 'NoneType' object has no attribute 'get_text'
```

原因: netkeibaのHTML構造変更

解決:
- `keiba/scrapers/` のパース処理を確認・修正
- テストフィクスチャを最新のHTMLで更新

### 6. 文字化け

症状: 馬名やレース名が文字化け

原因: EUC-JP エンコーディングの問題

解決:
- `BaseScraper.fetch()` で `db.netkeiba.com` の場合は `EUC-JP` を設定済み
- 問題が続く場合はエンコーディング処理を確認

### 7. ML予測がスキップされる

症状: 「学習データ不足（N件）: ML予測をスキップ」と表示される

原因: 対象レース日より前のデータが100件未満

解決:
```bash
# より多くのレースデータを収集
keiba scrape --year 2023 --month 12 --db data/keiba.db --jra-only
keiba scrape --year 2023 --month 11 --db data/keiba.db --jra-only
```

### 8. LightGBMインポートエラー

症状: 「No module named 'lightgbm'」または libomp関連エラー

原因: LightGBMがインストールされていない、または依存ライブラリの問題

解決:
```bash
# LightGBMを再インストール
pip uninstall lightgbm
pip install lightgbm

# macOS（Homebrew）の場合
brew install libomp
pip install lightgbm

# または--no-predictオプションでML予測をスキップ
keiba analyze --db data/keiba.db --date 2024-01-06 --venue 中山 --no-predict
```

### 9. バックテストが遅い

症状: バックテストに時間がかかりすぎる

原因: 再学習間隔が短い、または対象期間が長い

解決:
```bash
# 再学習間隔を長くする
keiba backtest --db data/keiba.db --months 3 --retrain-interval monthly

# 対象期間を短くする
keiba backtest --db data/keiba.db --months 1
```

注記: v1.x以降ではN+1問題の解消とバッチクエリ最適化により、バックテスト速度が大幅に改善されています。上記の解決策を試す前に、最新バージョンにアップデートすることを推奨します。

追加のパフォーマンス改善:
```bash
# DBインデックスを追加（既存DBの場合）
python scripts/add_indexes.py data/keiba.db
```

DBインデックス追加により、バックテスト実行時間が38分から4分に短縮（約90%削減）されます。

## 監視項目

### 日次確認

- [ ] scrapeコマンドが正常終了したか
- [ ] エラー件数が異常に多くないか
- [ ] データベースサイズが急増していないか

### 週次確認

- [ ] 詳細未取得の馬の残数
- [ ] バックアップが正常に取れているか
- [ ] 血統情報の取得進捗

### 月次確認

- [ ] データの整合性チェック
- [ ] 不要データのクリーンアップ
- [ ] 分析結果の妥当性確認

## ロールバック手順

### データベースの復元

```bash
# 最新のバックアップから復元
cp data/keiba_YYYYMMDD.db data/keiba.db

# または gzip圧縮からの復元
gunzip -c data/backup.db.gz > data/keiba.db
```

### 特定データの削除

```bash
# 特定日のレースを削除（関連データも削除）
sqlite3 data/keiba.db "
DELETE FROM race_results WHERE race_id LIKE '202403%';
DELETE FROM races WHERE id LIKE '202403%';
"
```

---
Freshness: 2026-01-29
