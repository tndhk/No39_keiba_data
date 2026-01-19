# 分析因子追加設計書

## 概要

既存の5因子に「血統分析」と「脚質分析」の2因子を追加し、7因子体制とする。

## 新規因子

### 1. 血統分析（PedigreeFactor）

#### 系統分類（8系統）

| 系統名 | 主な種牡馬例 |
|--------|-------------|
| sunday_silence | サンデーサイレンス、ディープインパクト、ステイゴールド |
| kingmambo | キングマンボ、キングカメハメハ、ロードカナロア |
| northern_dancer | ノーザンダンサー、サドラーズウェルズ |
| mr_prospector | ミスタープロスペクター、フォーティナイナー |
| roberto | ロベルト、ブライアンズタイム、タニノギムレット |
| storm_cat | ストームキャット、ヘネシー、テイルオブザキャット |
| hail_to_reason | ヘイルトゥリーズン、リアルシャダイ |
| other | 上記に該当しない場合 |

#### 評価特性

- 距離適性: sprint（〜1400m）、mile（1400-1800m）、middle（1800-2200m）、long（2200m〜）
- 馬場適性: good（良）、heavy（重/不良）

#### スコア計算

- 父系統の適性と母父系統の適性を7:3で合算
- 対象レースの距離・馬場との適合度を0-100で返す
- データが溜まれば種牡馬個別の統計に移行

### 2. 脚質分析（RunningStyleFactor）

#### 脚質分類（4分類）

| 脚質 | 判定基準（1コーナー通過順位/出走頭数） |
|------|--------------------------------------|
| escape（逃げ） | 〜15% |
| front（先行） | 15%〜40% |
| stalker（差し） | 40%〜70% |
| closer（追込） | 70%〜 |

#### 馬の脚質傾向

過去5走の脚質を集計し、最頻出の脚質をその馬の傾向とする。

#### コース別有利脚質

- 競馬場×距離ごとに各脚質の勝率・連対率を算出
- 統計データが10件未満の場合は全体平均を使用

#### スコア計算

馬の脚質傾向とコースの有利脚質のマッチ度を0-100で返す。

## ファイル構成

```
keiba/
├── analyzers/
│   ├── factors/
│   │   ├── pedigree.py          # 新規: 血統分析
│   │   └── running_style.py     # 新規: 脚質分析
│   └── cache/
│       └── running_style_stats.py  # 新規: コース別統計キャッシュ
├── config/
│   ├── weights.py               # 更新: 7因子均等
│   └── pedigree_master.py       # 新規: 系統マッピング・適性マスタ
```

## 重み配分

7因子均等（各約14.3%）:

```python
FACTOR_WEIGHTS = {
    "past_results": 0.143,
    "course_fit": 0.143,
    "time_index": 0.143,
    "last_3f": 0.143,
    "popularity": 0.143,
    "pedigree": 0.143,
    "running_style": 0.143,
}
```

## エラーハンドリング

### 血統分析
- 馬の血統情報が未取得 → Noneを返す（スコア計算から除外）
- 未知の種牡馬 → "other"系統として処理
- 馬場状態が不明 → "good"（良馬場）として計算

### 脚質分析
- passing_orderが空/不正 → Noneを返す
- 過去走が0件 → Noneを返す
- コースの統計データが不足（10件未満） → 全体平均を使用

## 実装フェーズ（TDD）

### Phase 1: 血統分析の基盤
1. [RED] PedigreeFactorのテスト作成（失敗する）
2. [GREEN] 種牡馬→系統マッピングマスタ作成
3. [GREEN] 系統別適性マスタ作成
4. [GREEN] PedigreeFactorクラス実装（テスト通過）
5. [REFACTOR] コード整理

### Phase 2: 脚質分析の基盤
1. [RED] RunningStyleFactorのテスト作成（失敗する）
2. [GREEN] 脚質判定ロジック実装
3. [GREEN] コース別統計キャッシュ実装
4. [GREEN] RunningStyleFactorクラス実装（テスト通過）
5. [REFACTOR] コード整理

### Phase 3: 統合
1. [RED] 統合テスト作成（失敗する）
2. [GREEN] weights.py更新（7因子均等）
3. [GREEN] analyzeコマンドに新因子を組み込み
4. [GREEN] 統合テスト通過
5. [REFACTOR] 全体整理

### Phase 4: 検証
1. カバレッジ80%以上を確認
2. 既存データで動作確認
3. スコア分布の妥当性確認

## テスト構成

```
tests/
├── test_pedigree_factor.py
│   ├── test_sire_line_mapping   # 系統マッピング
│   ├── test_aptitude_score      # 適性スコア計算
│   └── test_edge_cases          # 異常系
├── test_running_style_factor.py
│   ├── test_classify_style      # 脚質判定
│   ├── test_course_stats        # コース統計
│   └── test_score_calculation   # スコア計算
└── test_integration_new_factors.py  # 統合テスト
```

カバレッジ目標: 80%以上
