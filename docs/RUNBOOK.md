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

### 馬詳細データの収集

レース結果から取得した馬IDに基づき、馬の詳細情報（血統・成績）を収集。

```bash
# 基本コマンド（デフォルト100件）
keiba scrape-horses --db data/keiba.db

# 取得件数を指定
keiba scrape-horses --db data/keiba.db --limit 500

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
```

## 定期実行の設定

### crontabでの設定例

```bash
# 毎月1日深夜2時に前月のJRAレースデータを収集
0 2 1 * * cd /path/to/No39_keiba && keiba scrape --year $(date -d "last month" +\%Y) --month $(date -d "last month" +\%m) --db data/keiba.db --jra-only >> logs/scrape.log 2>&1

# 毎月1日深夜2時に前月の全競馬場データを収集（NAR含む）
# 0 2 1 * * cd /path/to/No39_keiba && keiba scrape --year $(date -d "last month" +\%Y) --month $(date -d "last month" +\%m) --db data/keiba.db >> logs/scrape.log 2>&1

# 毎日深夜3時に馬詳細を100件ずつ収集
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
| horses | 馬情報 |
| jockeys | 騎手情報 |
| trainers | 調教師情報 |
| race_results | レース結果 |

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
sqlite3.OperationalError: no such column: horses.sire
```

原因: モデル変更後にDBマイグレーションが未実行

解決:
```bash
# 不足カラムを追加
sqlite3 data/keiba.db "ALTER TABLE horses ADD COLUMN sire TEXT;"
```

### 2. HTTPエラー (403/429)

症状:
```
requests.exceptions.HTTPError: 403 Client Error: Forbidden
```

原因: アクセス制限またはレート制限

解決:
- スクレイパーのdelayを増やす（デフォルト1秒）
- 時間をおいて再実行

### 3. パースエラー

症状:
```
AttributeError: 'NoneType' object has no attribute 'get_text'
```

原因: netkeibaのHTML構造変更

解決:
- `keiba/scrapers/` のパース処理を確認・修正
- テストフィクスチャを最新のHTMLで更新

### 4. 文字化け

症状: 馬名やレース名が文字化け

原因: EUC-JP エンコーディングの問題

解決:
- `BaseScraper.fetch()` で `db.netkeiba.com` の場合は `EUC-JP` を設定済み
- 問題が続く場合はエンコーディング処理を確認

## 監視項目

### 日次確認

- [ ] scrapeコマンドが正常終了したか
- [ ] エラー件数が異常に多くないか
- [ ] データベースサイズが急増していないか

### 週次確認

- [ ] 詳細未取得の馬の残数
- [ ] バックアップが正常に取れているか

### 月次確認

- [ ] データの整合性チェック
- [ ] 不要データのクリーンアップ

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
