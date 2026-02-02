# Backend Codemap

> Freshness: 2026-01-31 (Line counts verified, shutuba/markdown parser updates, race_list_sub/race_id_resolver added)

## Overview

バックエンド構造のコードマップ。CLI、サービス層、リポジトリ層、スクレイパーの詳細。

## CLI Package (keiba/cli/)

### Package Structure

```
keiba/cli/                       # 3588行合計
+-- __init__.py                  # main, 後方互換性エクスポート (122行)
+-- commands/                    # CLIコマンドモジュール (2220行)
|   +-- __init__.py              # exports (5行)
|   +-- scrape.py                # scrape, scrape-horses (421行)
|   +-- analyze.py               # analyze (623行)
|   +-- predict.py               # predict, predict-day (314行)
|   +-- train.py                 # train (78行)
|   +-- review.py                # review-day (206行)
|   +-- backtest.py              # backtest, backtest-fukusho/tansho/umaren/sanrenpuku/all (528行)
|   +-- migrate.py               # migrate-grades (50行)
+-- formatters/                  # 出力フォーマッタ (692行)
|   +-- __init__.py              # exports (13行)
|   +-- markdown.py              # Markdown保存/パース/追記 (341行)
|   +-- simulation.py            # 馬券シミュレーション計算 (338行)
+-- utils/                       # ユーティリティ (549行)
    +-- __init__.py              # empty (0行)
    +-- url_parser.py            # URL解析 (33行)
    +-- date_parser.py           # 日付パース (33行)
    +-- date_range.py            # 日付範囲計算 (46行)
    +-- model_resolver.py        # MLモデル解決 (18行)
    +-- table_printer.py         # テーブル出力 (215行)
    +-- table_formatter.py       # バックテスト結果テーブル整形 (160行)
    +-- venue_filter.py          # 会場フィルタリング (44行)
```

### Entry Point

```python
# keiba/cli/__init__.py
@click.group()
def main():
    """競馬データ収集・分析CLI"""

# コマンド登録
main.add_command(scrape)          # from commands/scrape.py
main.add_command(scrape_horses)   # from commands/scrape.py
main.add_command(analyze)         # from commands/analyze.py
main.add_command(predict)         # from commands/predict.py
main.add_command(predict_day)     # from commands/predict.py
main.add_command(train)           # from commands/train.py
main.add_command(review_day)      # from commands/review.py
main.add_command(backtest)        # from commands/backtest.py
main.add_command(backtest_fukusho)# from commands/backtest.py
main.add_command(backtest_tansho) # from commands/backtest.py
main.add_command(backtest_umaren) # from commands/backtest.py
main.add_command(backtest_sanrenpuku) # from commands/backtest.py
main.add_command(backtest_all)    # from commands/backtest.py
main.add_command(migrate_grades)  # from commands/migrate.py
```

### Commands

| Command | File | Lines | Description |
|---------|------|-------|-------------|
| scrape | commands/scrape.py | 421 | レースデータ収集（年月指定） |
| scrape-horses | commands/scrape.py | - | 馬詳細データ収集 |
| analyze | commands/analyze.py | 623 | レース分析 + ML予測 |
| predict | commands/predict.py | 314 | 出馬表URLから予測 |
| predict-day | commands/predict.py | - | 指定日・競馬場の全レース予測 |
| review-day | commands/review.py | 206 | 予測結果と実績比較（複勝・単勝・馬連・三連複シミュレーション） |
| migrate-grades | commands/migrate.py | 50 | グレード情報マイグレーション |
| backtest | commands/backtest.py | 528 | ML予測バックテスト |
| backtest-fukusho | commands/backtest.py | - | 複勝シミュレーション |
| backtest-tansho | commands/backtest.py | - | 単勝シミュレーション |
| backtest-umaren | commands/backtest.py | - | 馬連シミュレーション |
| backtest-sanrenpuku | commands/backtest.py | - | 三連複シミュレーション |
| backtest-all | commands/backtest.py | - | 全券種一括シミュレーション |
| train | commands/train.py | 78 | MLモデル学習・保存 |

### Formatters (keiba/cli/formatters/)

#### markdown.py (341行)

| Function | Purpose |
|----------|---------|
| `save_predictions_markdown()` | 予測結果をMarkdownファイルに保存 |
| `parse_predictions_markdown()` | 予測Markdownファイルをパース |
| `append_review_to_markdown()` | 検証結果をMarkdownに追記 |

#### simulation.py (338行)

| Function | Purpose |
|----------|---------|
| `calculate_fukusho_simulation()` | 複勝シミュレーション計算 |
| `calculate_tansho_simulation()` | 単勝シミュレーション計算 |
| `calculate_umaren_simulation()` | 馬連シミュレーション計算 |
| `calculate_sanrenpuku_simulation()` | 三連複シミュレーション計算 |

### Utils (keiba/cli/utils/)

| Module | Lines | Functions | Purpose |
|--------|-------|-----------|---------|
| url_parser.py | 33 | `extract_race_id_from_url()`, `extract_race_id_from_shutuba_url()` | URL解析 |
| date_parser.py | 33 | `parse_race_date()` | 日付文字列パース |
| date_range.py | 46 | `resolve_date_range()` | 日付範囲計算（--from/--to/--last-week対応） |
| model_resolver.py | 18 | `resolve_model_path()` | MLモデルパス解決（--model/自動検索） |
| table_printer.py | 215 | `print_score_table()`, `print_score_table_with_ml()`, `print_prediction_table()` | テーブル出力 |
| table_formatter.py | 160 | バックテスト結果テーブル整形関数 | バックテスト結果の表整形 |
| venue_filter.py | 44 | 会場フィルタリング関数 | 会場名のフィルタリング |

### Backward Compatibility

`keiba/cli/__init__.py` で旧APIをエクスポート:

```python
# 旧名（_ 付き）のエイリアス
_save_predictions_markdown = save_predictions_markdown
_parse_predictions_markdown = parse_predictions_markdown
_append_review_to_markdown = append_review_to_markdown
_calculate_fukusho_simulation = calculate_fukusho_simulation
_calculate_tansho_simulation = calculate_tansho_simulation
_calculate_umaren_simulation = calculate_umaren_simulation
_calculate_sanrenpuku_simulation = calculate_sanrenpuku_simulation
_print_score_table = print_score_table
_print_score_table_with_ml = print_score_table_with_ml
_print_prediction_table = print_prediction_table
```

## Services (keiba/services/)

### Package Structure (956行)

```
keiba/services/
+-- __init__.py              # 公開API (21行)
+-- prediction_service.py    # 予測サービス (410行)
+-- training_service.py      # 学習データ構築サービス (180行)
+-- analysis_service.py      # 過去レース分析サービス (235行)
+-- past_stats_calculator.py # 過去成績統計計算 (110行)
```

### PastStatsCalculator (110行)

```
keiba/services/past_stats_calculator.py
|
+-- calculate_past_stats(past_results) -> dict
|   勝率、Top3率、平均着順などの派生特徴量を計算
|   PredictionService, TrainingServiceから共通利用
```

### PredictionService (401行)

```
keiba/services/prediction_service.py
|
+-- Imports
|   +-- analyzers/factors/ (7 factors)
|   +-- analyzers/score_calculator
|   +-- models/entry (ShutubaData, RaceEntry)
|
+-- PredictionResult (dataclass, frozen=True)
|   +-- horse_number: int
|   +-- horse_name: str
|   +-- horse_id: str
|   +-- ml_probability: float
|   +-- factor_scores: dict[str, float | None]
|   +-- total_score: float | None
|   +-- combined_score: float | None
|   +-- rank: int
|
+-- RaceResultRepository (Protocol)
|   +-- get_past_results(horse_id, before_date, limit) -> list
|
+-- PredictionService (class)
    +-- FACTOR_NAMES = [7 factor names]
    +-- __init__(repository, model_path=None)
    +-- _load_model(model_path)
    +-- predict_from_shutuba(shutuba_data) -> list[PredictionResult]
    +-- _calculate_factor_scores(entry, past_results, race_info)
    +-- _calculate_ml_probability(entry, past_results, factor_scores, race_info)
    +-- _calculate_combined_score(ml_prob, max_ml_prob, total_score)
    +-- _calculate_past_stats(past_results, horse_id)
```

### TrainingService (208行)

```
keiba/services/training_service.py
|
+-- build_training_data(session, cutoff_date) -> tuple[list, list]
|   ML学習用データを構築（cutoff_date前のデータのみ使用）
|
+-- calculate_past_stats(past_results) -> dict
|   派生特徴量を計算（勝率、Top3率、平均着順など）
|
+-- get_horse_past_results(session, horse_id, before_date, limit) -> list[dict]
|   馬の過去成績を取得
```

### AnalysisService (235行)

```
keiba/services/analysis_service.py
|
+-- analyze_race_scores(session, race) -> list[dict]
|   レースを分析してスコアを計算
|
+-- analyze_with_ml(session, race, model_path) -> list[dict]
|   ML予測を含むレース分析
```

### Combined Score Calculation

```python
def _calculate_combined_score(
    self,
    ml_probability: float,
    max_ml_probability: float,
    total_score: float | None,
) -> float | None:
    """複合スコアを幾何平均で計算

    Formula:
        normalized_ml = (ml_probability / max_ml_probability) * 100
        combined = sqrt(normalized_ml * total_score)
    """
```

## Repositories (keiba/repositories/)

### Package Structure (133行)

```
keiba/repositories/
+-- __init__.py                    # 公開API (5行)
+-- race_result_repository.py      # レース結果リポジトリ (128行)
```

### SQLAlchemyRaceResultRepository (74行)

```python
class SQLAlchemyRaceResultRepository:
    """RaceResultRepositoryプロトコルの実装"""

    def __init__(self, session): ...

    def get_past_results(
        self, horse_id: str, before_date: str, limit: int = 20
    ) -> list[dict]:
        """指定日より前の過去成績を取得（データリーク防止）"""
```

## Scrapers (keiba/scrapers/)

### Structure (2069行)

```
keiba/scrapers/
+-- __init__.py          # 公開インポート (21行)
+-- base.py              # BaseScraper（グローバルレートリミッタ・指数バックオフ） (188行)
+-- race_list.py         # RaceListScraper（過去データ専用） (106行)
+-- race_list_sub.py     # RaceListSubScraper（未来日付対応） (95行)
+-- race_id_resolver.py  # fetch_race_ids_for_date（フォールバック: 未来→過去） (76行)
+-- race_detail.py       # RaceDetailScraper (853行)
+-- horse_detail.py      # HorseDetailScraper（パース警告・AJAX血統取得対応） (367行)
+-- shutuba.py           # ShutubaScraper (363行)
```

### BaseScraper (189行)

グローバルレートリミッタと指数バックオフを実装した基底クラス。

```python
class BaseScraper:
    # クラス変数: 全インスタンス間で共有されるレート制限タイマー
    _global_last_request_time: float | None = None

    def __init__(self, delay: float = 1.0): ...

    def fetch(self, url: str) -> str:
        """HTTP GETリクエスト（指数バックオフ付きリトライ）

        - 403/429/503エラー時に自動リトライ（最大3回）
        - バックオフ間隔: 5秒, 10秒, 30秒
        - finally: エラー時もグローバルタイマーを更新
        """

    def _apply_delay(self) -> None:
        """グローバルレートリミッタ

        全BaseScraper派生インスタンス間で最後のリクエスト
        からの経過時間をチェックし、delay未満の場合はsleep
        """
```

レート制限の動作:
- `_apply_delay()`: `BaseScraper._global_last_request_time` をチェックし、必要に応じてsleep
- `finally` ブロック: `_last_request_time`（インスタンス）と `_global_last_request_time`（クラス）の両方を更新
- HTTP 403/429/503: 5秒 -> 10秒 -> 30秒の指数バックオフでリトライ

### HorseDetailScraper (367行) -- パース警告 + AJAX血統取得

```python
class HorseDetailScraper(BaseScraper):
    BASE_URL = "https://db.netkeiba.com/horse/"
    PEDIGREE_AJAX_URL = "https://db.netkeiba.com/horse/ajax_horse_pedigree.html"

    def parse(self, soup) -> dict:
        """パース結果に parse_warnings リストを含む

        Returns:
            {"id": str, "name": str, ..., "parse_warnings": list[str]}
        """

    def _fetch_pedigree_ajax(self, horse_id: str) -> str | None:
        """AJAX APIから血統テーブルHTMLを取得（フォールバック）"""
```

### RaceListScraper (106行)

```python
class RaceListScraper:
    """db.netkeiba.com/race/list/からレース一覧を取得（過去データ専用）"""

    def fetch_race_urls(
        self, year: int, month: int, day: int, jra_only: bool = False
    ) -> list[str]:
        """指定日のレースURL一覧を取得"""
```

### RaceListSubScraper (95行)

```python
class RaceListSubScraper(BaseScraper):
    """race.netkeiba.com/top/race_list_sub.htmlから未来日付のレースを取得"""

    def fetch_race_ids(self, date: str) -> list[str]:
        """指定日のrace_idリストを取得（未来日付対応）"""
```

### race_id_resolver (76行)

```python
def fetch_race_ids_for_date(date: str, jra_only: bool = False) -> list[str]:
    """RaceListSubScraper -> RaceListScraper の自動フォールバックで
    指定日のrace_idリストを取得"""
```

### RaceDetailScraper (853行)

```python
class RaceDetailScraper:
    """db.netkeiba.com/race/からレース詳細を取得"""

    def fetch_race_detail(self, race_id: str) -> dict:
        """レース詳細と結果を取得"""

    def fetch_payouts(self, race_id: str) -> list[dict]:
        """複勝払戻金を取得

        Returns:
            [{"horse_number": 5, "payout": 150}, ...]
        """

    def fetch_tansho_payout(self, race_id: str) -> dict | None:
        """単勝払戻金を取得

        Returns:
            {"horse_number": 5, "payout": 350} or None
        """

    def fetch_umaren_payout(self, race_id: str) -> dict | None:
        """馬連払戻金を取得

        Returns:
            {"combination": [5, 8], "payout": 1500} or None
        """

    def fetch_sanrenpuku_payout(self, race_id: str) -> dict | None:
        """三連複払戻金を取得

        Returns:
            {"combination": [3, 5, 8], "payout": 3200} or None
        """
```

### HorseDetailScraper (280行)

```python
class HorseDetailScraper:
    """db.netkeiba.com/horse/から馬詳細を取得"""

    def fetch_horse_detail(self, horse_id: str) -> dict:
        """馬の詳細情報（血統含む）を取得"""
```

### ShutubaScraper (363行)

```python
class ShutubaScraper:
    """race.netkeiba.com/race/shutuba.htmlから出馬表を取得"""

    def fetch_shutuba(self, race_id: str) -> ShutubaData:
        """出馬表データを取得（イミュータブル）
        race_number取得失敗時はrace_idからフォールバック推測"""
```

## Database Layer (keiba/db.py) (75行)

### Functions

```python
def get_engine(db_path: str) -> Engine:
    """SQLiteエンジン作成"""

@contextmanager
def get_session(engine: Engine) -> Generator[Session, None, None]:
    """セッション取得（自動コミット/ロールバック）"""

def init_db(engine: Engine) -> None:
    """テーブル初期化（冪等）"""
```

## ML Layer (keiba/ml/)

### Structure (409行)

```
keiba/ml/
+-- __init__.py          # 公開API (26行)
+-- feature_builder.py   # 特徴量構築（19特徴量） (103行)
+-- trainer.py           # LightGBMモデル学習 (193行)
+-- predictor.py         # 予測実行 (60行)
+-- model_utils.py       # ユーティリティ (27行)
```

### Trainer (189行)

```python
class Trainer:
    """LightGBMモデル学習"""

    MIN_SAMPLES = 100

    # Normal mode params
    _NORMAL_PARAMS = {
        "num_leaves": 31,
        "learning_rate": 0.05,
        "n_estimators": 100,
    }

    # Lightweight mode params (backtest)
    _LIGHTWEIGHT_PARAMS = {
        "num_leaves": 15,
        "learning_rate": 0.1,
        "n_estimators": 50,
    }

    def __init__(self, lightweight: bool = False): ...
    def train(self, X, y): ...
    def train_with_cv(self, X, y, n_splits=5) -> dict: ...
    def get_feature_importance(self) -> np.ndarray: ...
    def save_model(self, path: str) -> None: ...
```

### Model Utils

```python
def find_latest_model(model_dir: str) -> str | None:
    """最新の.joblibファイルを検索（st_mtime順）"""
```

## Backtest Layer (keiba/backtest/)

### Structure (2640行)

```
keiba/backtest/
+-- __init__.py             # 公開API (55行)
+-- backtester.py           # BacktestEngine (1093行)
+-- base_simulator.py       # BaseSimulator（基底クラス・スクレイパー再利用） (175行)
+-- fukusho_simulator.py    # FukushoSimulator (191行)
+-- tansho_simulator.py     # TanshoSimulator (185行)
+-- umaren_simulator.py     # UmarenSimulator (212行)
+-- sanrenpuku_simulator.py # SanrenpukuSimulator (189行)
+-- metrics.py              # MetricsCalculator (198行)
+-- reporter.py             # BacktestReporter (168行)
+-- factor_calculator.py    # ファクター計算 (249行)
+-- cache.py                # キャッシュ機構 (125行)
```

### BaseSimulator (176行)

4券種シミュレータの共通基底クラス。Template Methodパターンを使用。

```python
class BaseSimulator(ABC, Generic[TRaceResult, TSummary]):
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._scraper = RaceDetailScraper()  # スクレイパーインスタンスを再利用

    def _get_session(self) -> Session: ...
    def _get_races_in_period(session, from_date, to_date, venues) -> list[Race]: ...
    def _build_shutuba_from_race_results(race, results) -> ShutubaData: ...
    def simulate_period(from_date, to_date, venues, **kwargs) -> TSummary: ...

    @abstractmethod
    def simulate_race(self, race_id: str, **kwargs) -> TRaceResult: ...

    @abstractmethod
    def _build_summary(self, period_from, period_to, race_results) -> TSummary: ...
```

設計ポイント:
- 単一の `RaceDetailScraper` インスタンスで全レースの払戻金取得を実行
- `BaseScraper._global_last_request_time` によりレート制限が自動適用
- `simulate_period()` がTemplate Methodとして動作し、サブクラスは `simulate_race()` と `_build_summary()` のみ実装

詳細は [backtest.md](./backtest.md) を参照。

### Simulators Overview

| Simulator | 券種 | 購入点数 | 的中条件 |
|-----------|------|----------|---------|
| FukushoSimulator | 複勝 | top_n点 | Top-Nのいずれかが3着以内 |
| TanshoSimulator | 単勝 | top_n点 | Top-Nのいずれかが1着 |
| UmarenSimulator | 馬連 | 3点 | Top3の2頭が1-2着 |
| SanrenpukuSimulator | 三連複 | 1点 | Top3の3頭が3着以内 |

### BacktestEngine (1093行)

```python
class BacktestEngine:
    """ウォークフォワード検証エンジン"""

    MIN_TRAINING_SAMPLES = 100
    MAX_PAST_RESULTS_PER_HORSE = 20
    DEFAULT_FINISH_POSITION = 99

    def __init__(
        self,
        db_path: str,
        start_date: str,
        end_date: str,
        retrain_interval: str,
    ): ...

    def run(self) -> Generator[RaceBacktestResult, None, None]: ...
```

## Constants (keiba/constants.py) (44行)

```python
JRA_COURSE_CODES: dict[str, str] = {
    "01": "札幌",
    "02": "函館",
    "03": "福島",
    "04": "新潟",
    "05": "東京",
    "06": "中山",
    "07": "中京",
    "08": "京都",
    "09": "阪神",
    "10": "小倉",
}
```

## Configuration (keiba/config/)

### weights.py

```python
FACTOR_WEIGHTS = {
    "past_results": 0.143,
    "course_fit": 0.143,
    "time_index": 0.143,
    "last_3f": 0.143,
    "popularity": 0.143,
    "pedigree": 0.143,
    "running_style": 0.142,
}
# Total: 1.000
```

### pedigree_master.py (127行)

種牡馬の系統・距離適性マスターデータ。

## Request/Response Flow

### predict command

```
1. URL解析 -> race_id抽出
2. ShutubaScraper.fetch_shutuba(race_id) -> ShutubaData
3. SQLAlchemyRaceResultRepository作成
4. find_latest_model() -> model_path
5. PredictionService(repository, model_path)
6. service.predict_from_shutuba(shutuba_data) -> list[PredictionResult]
7. print_prediction_table(predictions)
```

### train command

```
1. get_engine(db) -> Engine
2. get_session(engine) -> Session
3. build_training_data(session, cutoff_date) -> (features, labels)
4. FeatureBuilder().get_feature_names() -> feature_names
5. np.array(features) -> X, np.array(labels) -> y
6. Trainer().train_with_cv(X, y, n_splits=5) -> metrics
7. trainer.save_model(output) -> .joblib file
```

### review-day command

```
1. 予測ファイル読み込み -> parse_predictions_markdown()
2. レース結果取得 -> RaceDetailScraper
3. 払戻金取得 -> fetch_payouts(), fetch_tansho_payout(), etc.
4. シミュレーション計算 -> calculate_*_simulation()
5. 結果追記 -> append_review_to_markdown()
```

## Error Handling

- スクレイピングエラー: 個別レースをスキップ、継続処理
- DB接続エラー: 例外をre-raise、セッションロールバック
- モデルロードエラー: self._model = None、因子スコアのみで予測
- 日付パースエラー: SystemExit(1)で終了、エラーメッセージ表示

## File Size Summary

| Category | Total Lines | Files |
|----------|-------------|-------|
| CLI Package | 3588 | 20 |
| Services | 956 | 5 |
| Repositories | 133 | 2 |
| Scrapers | 2069 | 8 |
| ML | 409 | 5 |
| Backtest | 2640 | 11 |
| Analyzers | 597 | 9 |
| Models | 437 | 9 |
| Config | 153 | 3 |
| Utils | 236 | 2 |
| DB | 75 | 1 |
| Constants | 44 | 1 |
