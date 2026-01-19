# 血統分析・脚質分析 TDD実装計画

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 既存の5因子に「血統分析（PedigreeFactor）」と「脚質分析（RunningStyleFactor）」の2因子を追加し、7因子体制の分析システムを構築する。

**Architecture:** BaseFactorを継承した新規Factorクラスを作成。血統分析は種牡馬→系統マッピングマスタと系統別適性マスタを使用。脚質分析は通過順位から脚質を判定し、コース別統計とマッチングする。

**Tech Stack:** Python 3.10+, SQLAlchemy 2.0, pytest

---

## Phase 1: 血統分析の基盤

### Task 1.1: 血統マスタデータの作成

**Files:**
- Create: `keiba/config/pedigree_master.py`
- Test: `tests/test_pedigree_factor.py`

**Step 1: テストファイルを作成（RED）**

```python
# tests/test_pedigree_factor.py
"""血統分析（PedigreeFactor）のテスト"""

import pytest


class TestSireLineMapping:
    """種牡馬→系統マッピングのテスト"""

    def test_deep_impact_is_sunday_silence_line(self):
        """ディープインパクトはサンデーサイレンス系"""
        from keiba.config.pedigree_master import get_sire_line

        assert get_sire_line("ディープインパクト") == "sunday_silence"

    def test_lord_kanaloa_is_kingmambo_line(self):
        """ロードカナロアはキングマンボ系"""
        from keiba.config.pedigree_master import get_sire_line

        assert get_sire_line("ロードカナロア") == "kingmambo"

    def test_unknown_sire_is_other(self):
        """未知の種牡馬はother"""
        from keiba.config.pedigree_master import get_sire_line

        assert get_sire_line("未登録の種牡馬") == "other"

    def test_stay_gold_is_sunday_silence_line(self):
        """ステイゴールドはサンデーサイレンス系"""
        from keiba.config.pedigree_master import get_sire_line

        assert get_sire_line("ステイゴールド") == "sunday_silence"

    def test_king_kamehameha_is_kingmambo_line(self):
        """キングカメハメハはキングマンボ系"""
        from keiba.config.pedigree_master import get_sire_line

        assert get_sire_line("キングカメハメハ") == "kingmambo"

    def test_brian_time_is_roberto_line(self):
        """ブライアンズタイムはロベルト系"""
        from keiba.config.pedigree_master import get_sire_line

        assert get_sire_line("ブライアンズタイム") == "roberto"
```

**Step 2: テストを実行して失敗を確認**

Run: `pytest tests/test_pedigree_factor.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'keiba.config.pedigree_master'"

**Step 3: マスタデータを実装（GREEN）**

```python
# keiba/config/pedigree_master.py
"""血統マスタデータ

種牡馬→系統マッピングと、系統別適性データを定義する。
"""

# 種牡馬→系統マッピング
SIRE_LINE_MAPPING: dict[str, str] = {
    # サンデーサイレンス系
    "サンデーサイレンス": "sunday_silence",
    "ディープインパクト": "sunday_silence",
    "ステイゴールド": "sunday_silence",
    "ハーツクライ": "sunday_silence",
    "ダイワメジャー": "sunday_silence",
    "マンハッタンカフェ": "sunday_silence",
    "ゼンノロブロイ": "sunday_silence",
    "アグネスタキオン": "sunday_silence",
    "スペシャルウィーク": "sunday_silence",
    "フジキセキ": "sunday_silence",
    "ネオユニヴァース": "sunday_silence",
    "キズナ": "sunday_silence",
    "オルフェーヴル": "sunday_silence",
    "ゴールドシップ": "sunday_silence",
    "ドゥラメンテ": "sunday_silence",
    "エピファネイア": "sunday_silence",
    "コントレイル": "sunday_silence",
    # キングマンボ系
    "キングマンボ": "kingmambo",
    "キングカメハメハ": "kingmambo",
    "ロードカナロア": "kingmambo",
    "ルーラーシップ": "kingmambo",
    "レイデオロ": "kingmambo",
    "ドゥラモンド": "kingmambo",
    # ノーザンダンサー系
    "ノーザンダンサー": "northern_dancer",
    "サドラーズウェルズ": "northern_dancer",
    "ガリレオ": "northern_dancer",
    "フランケル": "northern_dancer",
    "ニジンスキー": "northern_dancer",
    "リファール": "northern_dancer",
    # ミスタープロスペクター系（キングマンボ除く）
    "ミスタープロスペクター": "mr_prospector",
    "フォーティナイナー": "mr_prospector",
    "エンドスウィープ": "mr_prospector",
    "アドマイヤムーン": "mr_prospector",
    "ゴールドアリュール": "mr_prospector",
    "スマートファルコン": "mr_prospector",
    # ロベルト系
    "ロベルト": "roberto",
    "ブライアンズタイム": "roberto",
    "タニノギムレット": "roberto",
    "ウオッカ": "roberto",
    "シンボリクリスエス": "roberto",
    "エピカリス": "roberto",
    "モーリス": "roberto",
    "スクリーンヒーロー": "roberto",
    # ストームキャット系
    "ストームキャット": "storm_cat",
    "ヘネシー": "storm_cat",
    "テイルオブザキャット": "storm_cat",
    "ジャイアンツコーズウェイ": "storm_cat",
    "ヨハネスブルグ": "storm_cat",
    # ヘイルトゥリーズン系（サンデーサイレンス除く）
    "ヘイルトゥリーズン": "hail_to_reason",
    "リアルシャダイ": "hail_to_reason",
    "トニービン": "hail_to_reason",
    "ジャングルポケット": "hail_to_reason",
}

# 系統別適性データ
LINE_APTITUDE: dict[str, dict] = {
    "sunday_silence": {
        "distance": {"sprint": 0.6, "mile": 0.9, "middle": 1.0, "long": 0.8},
        "track": {"good": 1.0, "heavy": 0.7},
    },
    "kingmambo": {
        "distance": {"sprint": 0.8, "mile": 1.0, "middle": 0.9, "long": 0.6},
        "track": {"good": 0.9, "heavy": 0.9},
    },
    "northern_dancer": {
        "distance": {"sprint": 0.5, "mile": 0.8, "middle": 1.0, "long": 0.9},
        "track": {"good": 0.9, "heavy": 1.0},
    },
    "mr_prospector": {
        "distance": {"sprint": 1.0, "mile": 0.9, "middle": 0.7, "long": 0.5},
        "track": {"good": 0.9, "heavy": 1.0},
    },
    "roberto": {
        "distance": {"sprint": 0.6, "mile": 0.9, "middle": 1.0, "long": 0.8},
        "track": {"good": 0.8, "heavy": 1.0},
    },
    "storm_cat": {
        "distance": {"sprint": 1.0, "mile": 0.9, "middle": 0.6, "long": 0.4},
        "track": {"good": 1.0, "heavy": 0.6},
    },
    "hail_to_reason": {
        "distance": {"sprint": 0.5, "mile": 0.7, "middle": 0.9, "long": 1.0},
        "track": {"good": 0.9, "heavy": 0.8},
    },
    "other": {
        "distance": {"sprint": 0.7, "mile": 0.8, "middle": 0.8, "long": 0.7},
        "track": {"good": 0.9, "heavy": 0.9},
    },
}


def get_sire_line(sire_name: str) -> str:
    """種牡馬名から系統を取得する

    Args:
        sire_name: 種牡馬名

    Returns:
        系統名（未知の種牡馬は"other"）
    """
    return SIRE_LINE_MAPPING.get(sire_name, "other")


def get_line_aptitude(line: str) -> dict:
    """系統の適性データを取得する

    Args:
        line: 系統名

    Returns:
        適性データ（距離・馬場）
    """
    return LINE_APTITUDE.get(line, LINE_APTITUDE["other"])
```

**Step 4: テストを実行して成功を確認**

Run: `pytest tests/test_pedigree_factor.py::TestSireLineMapping -v`
Expected: PASS (6 tests)

**Step 5: コミット**

```bash
git add keiba/config/pedigree_master.py tests/test_pedigree_factor.py
git commit -m "feat: add pedigree master data with sire line mapping"
```

---

### Task 1.2: 血統適性スコア計算のテスト作成

**Files:**
- Modify: `tests/test_pedigree_factor.py`

**Step 1: 適性スコアのテストを追加（RED）**

```python
# tests/test_pedigree_factor.py に追加

class TestLineAptitude:
    """系統別適性データのテスト"""

    def test_sunday_silence_middle_distance_aptitude(self):
        """サンデーサイレンス系の中距離適性は1.0"""
        from keiba.config.pedigree_master import get_line_aptitude

        aptitude = get_line_aptitude("sunday_silence")
        assert aptitude["distance"]["middle"] == 1.0

    def test_storm_cat_sprint_aptitude(self):
        """ストームキャット系の短距離適性は1.0"""
        from keiba.config.pedigree_master import get_line_aptitude

        aptitude = get_line_aptitude("storm_cat")
        assert aptitude["distance"]["sprint"] == 1.0

    def test_roberto_heavy_track_aptitude(self):
        """ロベルト系の重馬場適性は1.0"""
        from keiba.config.pedigree_master import get_line_aptitude

        aptitude = get_line_aptitude("roberto")
        assert aptitude["track"]["heavy"] == 1.0

    def test_unknown_line_returns_other_aptitude(self):
        """未知の系統はother適性を返す"""
        from keiba.config.pedigree_master import get_line_aptitude

        aptitude = get_line_aptitude("unknown_line")
        assert aptitude == get_line_aptitude("other")
```

**Step 2: テストを実行して成功を確認**

Run: `pytest tests/test_pedigree_factor.py::TestLineAptitude -v`
Expected: PASS (4 tests)

**Step 3: コミット**

```bash
git add tests/test_pedigree_factor.py
git commit -m "test: add line aptitude tests"
```

---

### Task 1.3: PedigreeFactor クラスの実装

**Files:**
- Create: `keiba/analyzers/factors/pedigree.py`
- Modify: `tests/test_pedigree_factor.py`

**Step 1: PedigreeFactorのテストを追加（RED）**

```python
# tests/test_pedigree_factor.py に追加

class TestPedigreeFactor:
    """PedigreeFactor（血統分析）のテスト"""

    @pytest.fixture
    def factor(self):
        from keiba.analyzers.factors.pedigree import PedigreeFactor

        return PedigreeFactor()

    def test_name_is_pedigree(self, factor):
        """nameは'pedigree'である"""
        assert factor.name == "pedigree"

    def test_calculate_with_deep_impact_middle_distance(self, factor):
        """ディープインパクト産駒の中距離レース"""
        # ディープインパクト = サンデーサイレンス系 = 中距離適性1.0
        result = factor.calculate(
            horse_id="horse123",
            race_results=[],
            sire="ディープインパクト",
            dam_sire="キングカメハメハ",
            distance=2000,
            track_condition="良",
        )
        assert result is not None
        assert result > 80  # 高適性

    def test_calculate_with_storm_cat_sprint(self, factor):
        """ストームキャット系産駒の短距離レース"""
        result = factor.calculate(
            horse_id="horse123",
            race_results=[],
            sire="ストームキャット",
            dam_sire="サンデーサイレンス",
            distance=1200,
            track_condition="良",
        )
        assert result is not None
        assert result > 80  # 高適性

    def test_calculate_with_unknown_sire(self, factor):
        """未知の種牡馬でも計算可能"""
        result = factor.calculate(
            horse_id="horse123",
            race_results=[],
            sire="未登録馬",
            dam_sire="未登録馬",
            distance=1600,
            track_condition="良",
        )
        assert result is not None

    def test_calculate_returns_none_without_sire(self, factor):
        """父情報がない場合はNoneを返す"""
        result = factor.calculate(
            horse_id="horse123",
            race_results=[],
            sire=None,
            dam_sire="キングカメハメハ",
            distance=1600,
            track_condition="良",
        )
        assert result is None

    def test_distance_band_classification(self, factor):
        """距離帯の分類"""
        assert factor._get_distance_band(1200) == "sprint"
        assert factor._get_distance_band(1600) == "mile"
        assert factor._get_distance_band(2000) == "middle"
        assert factor._get_distance_band(2400) == "long"

    def test_track_condition_mapping(self, factor):
        """馬場状態のマッピング"""
        assert factor._get_track_type("良") == "good"
        assert factor._get_track_type("稍重") == "good"
        assert factor._get_track_type("重") == "heavy"
        assert factor._get_track_type("不良") == "heavy"
        assert factor._get_track_type(None) == "good"  # 不明は良馬場扱い

    def test_sire_dam_sire_weight_ratio(self, factor):
        """父7:母父3の重み配分"""
        # 父: サンデーサイレンス系（中距離1.0）
        # 母父: ストームキャット系（中距離0.6）
        # 加重平均: 1.0 * 0.7 + 0.6 * 0.3 = 0.88
        result = factor.calculate(
            horse_id="horse123",
            race_results=[],
            sire="ディープインパクト",
            dam_sire="ストームキャット",
            distance=2000,
            track_condition="良",
        )
        # スコアは88点前後になるはず
        assert result is not None
        assert 85 <= result <= 92
```

**Step 2: テストを実行して失敗を確認**

Run: `pytest tests/test_pedigree_factor.py::TestPedigreeFactor -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'keiba.analyzers.factors.pedigree'"

**Step 3: PedigreeFactorを実装（GREEN）**

```python
# keiba/analyzers/factors/pedigree.py
"""PedigreeFactor - 血統分析Factor"""

from keiba.analyzers.factors.base import BaseFactor
from keiba.config.pedigree_master import get_line_aptitude, get_sire_line


class PedigreeFactor(BaseFactor):
    """血統に基づくスコア計算

    父と母父の系統から、レース条件（距離・馬場）への適性を計算する。
    父:母父 = 7:3 の重み付けで合算。
    """

    name = "pedigree"

    def _get_distance_band(self, distance: int) -> str:
        """距離から距離帯を判定する

        Args:
            distance: 距離（メートル）

        Returns:
            距離帯（sprint/mile/middle/long）
        """
        if distance <= 1400:
            return "sprint"
        elif distance <= 1800:
            return "mile"
        elif distance <= 2200:
            return "middle"
        else:
            return "long"

    def _get_track_type(self, track_condition: str | None) -> str:
        """馬場状態をタイプに変換する

        Args:
            track_condition: 馬場状態（良/稍重/重/不良）

        Returns:
            馬場タイプ（good/heavy）
        """
        if track_condition is None:
            return "good"
        if track_condition in ("重", "不良"):
            return "heavy"
        return "good"

    def calculate(
        self, horse_id: str, race_results: list, **kwargs
    ) -> float | None:
        """血統適性スコアを計算する

        Args:
            horse_id: 馬ID
            race_results: レース結果のリスト（未使用）
            **kwargs:
                sire: 父
                dam_sire: 母父
                distance: レース距離
                track_condition: 馬場状態

        Returns:
            0-100の範囲のスコア、データ不足の場合はNone
        """
        sire = kwargs.get("sire")
        dam_sire = kwargs.get("dam_sire")
        distance = kwargs.get("distance")
        track_condition = kwargs.get("track_condition")

        # 父情報がない場合は計算不可
        if sire is None:
            return None

        # 距離情報がない場合は計算不可
        if distance is None:
            return None

        # 系統を取得
        sire_line = get_sire_line(sire)
        dam_sire_line = get_sire_line(dam_sire) if dam_sire else "other"

        # 適性データを取得
        sire_aptitude = get_line_aptitude(sire_line)
        dam_sire_aptitude = get_line_aptitude(dam_sire_line)

        # 距離帯と馬場タイプを判定
        distance_band = self._get_distance_band(distance)
        track_type = self._get_track_type(track_condition)

        # 距離適性を計算（父7:母父3）
        sire_distance_apt = sire_aptitude["distance"][distance_band]
        dam_sire_distance_apt = dam_sire_aptitude["distance"][distance_band]
        distance_score = sire_distance_apt * 0.7 + dam_sire_distance_apt * 0.3

        # 馬場適性を計算（父7:母父3）
        sire_track_apt = sire_aptitude["track"][track_type]
        dam_sire_track_apt = dam_sire_aptitude["track"][track_type]
        track_score = sire_track_apt * 0.7 + dam_sire_track_apt * 0.3

        # 総合スコア（距離と馬場を均等に）
        total_aptitude = (distance_score + track_score) / 2

        # 0-100スケールに変換
        return round(total_aptitude * 100, 1)
```

**Step 4: テストを実行して成功を確認**

Run: `pytest tests/test_pedigree_factor.py::TestPedigreeFactor -v`
Expected: PASS (9 tests)

**Step 5: コミット**

```bash
git add keiba/analyzers/factors/pedigree.py tests/test_pedigree_factor.py
git commit -m "feat: add PedigreeFactor for pedigree analysis"
```

---

### Task 1.4: PedigreeFactorをモジュールに登録

**Files:**
- Modify: `keiba/analyzers/factors/__init__.py`

**Step 1: __init__.pyを更新**

```python
# keiba/analyzers/factors/__init__.py
"""Factor modules"""

from keiba.analyzers.factors.base import BaseFactor
from keiba.analyzers.factors.course_fit import CourseFitFactor
from keiba.analyzers.factors.last_3f import Last3FFactor
from keiba.analyzers.factors.past_results import PastResultsFactor
from keiba.analyzers.factors.pedigree import PedigreeFactor
from keiba.analyzers.factors.popularity import PopularityFactor
from keiba.analyzers.factors.time_index import TimeIndexFactor

__all__ = [
    "BaseFactor",
    "CourseFitFactor",
    "Last3FFactor",
    "PastResultsFactor",
    "PedigreeFactor",
    "PopularityFactor",
    "TimeIndexFactor",
]
```

**Step 2: インポートテストを実行**

Run: `python -c "from keiba.analyzers.factors import PedigreeFactor; print('OK')"`
Expected: "OK"

**Step 3: コミット**

```bash
git add keiba/analyzers/factors/__init__.py
git commit -m "feat: register PedigreeFactor in factors module"
```

---

## Phase 2: 脚質分析の基盤

### Task 2.1: 脚質判定ロジックのテスト作成

**Files:**
- Create: `tests/test_running_style_factor.py`
- Create: `keiba/analyzers/factors/running_style.py`

**Step 1: テストファイルを作成（RED）**

```python
# tests/test_running_style_factor.py
"""脚質分析（RunningStyleFactor）のテスト"""

import pytest


class TestRunningStyleClassification:
    """脚質判定のテスト"""

    @pytest.fixture
    def factor(self):
        from keiba.analyzers.factors.running_style import RunningStyleFactor

        return RunningStyleFactor()

    def test_classify_escape_first_position(self, factor):
        """1番手通過は逃げ"""
        style = factor._classify_running_style("1-1-1-1", total_horses=18)
        assert style == "escape"

    def test_classify_escape_15_percent(self, factor):
        """15%以内は逃げ（18頭中2番手まで）"""
        style = factor._classify_running_style("2-2-2-2", total_horses=18)
        assert style == "escape"

    def test_classify_front_40_percent(self, factor):
        """15%-40%は先行（18頭中3-7番手）"""
        style = factor._classify_running_style("5-5-4-3", total_horses=18)
        assert style == "front"

    def test_classify_stalker_70_percent(self, factor):
        """40%-70%は差し（18頭中8-12番手）"""
        style = factor._classify_running_style("10-10-8-5", total_horses=18)
        assert style == "stalker"

    def test_classify_closer_last(self, factor):
        """70%以上は追込（18頭中13番手以降）"""
        style = factor._classify_running_style("15-15-12-8", total_horses=18)
        assert style == "closer"

    def test_classify_with_invalid_passing_order(self, factor):
        """不正な通過順位はNoneを返す"""
        style = factor._classify_running_style("", total_horses=18)
        assert style is None
        style = factor._classify_running_style(None, total_horses=18)
        assert style is None

    def test_classify_with_single_position(self, factor):
        """単一の通過順位でも判定可能"""
        style = factor._classify_running_style("1", total_horses=10)
        assert style == "escape"


class TestHorseRunningStyleTendency:
    """馬の脚質傾向判定のテスト"""

    @pytest.fixture
    def factor(self):
        from keiba.analyzers.factors.running_style import RunningStyleFactor

        return RunningStyleFactor()

    def test_determine_tendency_from_5_races(self, factor):
        """過去5走から最頻出の脚質を傾向とする"""
        race_results = [
            {"horse_id": "horse123", "passing_order": "1-1-1-1", "total_runners": 18},
            {"horse_id": "horse123", "passing_order": "2-2-2-1", "total_runners": 16},
            {"horse_id": "horse123", "passing_order": "1-1-1-1", "total_runners": 14},
            {"horse_id": "horse123", "passing_order": "5-5-4-3", "total_runners": 18},
            {"horse_id": "horse123", "passing_order": "1-1-1-1", "total_runners": 12},
        ]
        tendency = factor._get_horse_tendency("horse123", race_results)
        assert tendency == "escape"  # 逃げが3回で最多

    def test_determine_tendency_with_no_races(self, factor):
        """過去走がない場合はNoneを返す"""
        tendency = factor._get_horse_tendency("horse123", [])
        assert tendency is None


class TestRunningStyleFactor:
    """RunningStyleFactor（脚質分析）のテスト"""

    @pytest.fixture
    def factor(self):
        from keiba.analyzers.factors.running_style import RunningStyleFactor

        return RunningStyleFactor()

    def test_name_is_running_style(self, factor):
        """nameは'running_style'である"""
        assert factor.name == "running_style"

    def test_calculate_with_matching_style(self, factor):
        """馬の脚質とコース有利脚質がマッチする場合"""
        # 逃げ馬が逃げ有利コースを走る
        race_results = [
            {"horse_id": "horse123", "passing_order": "1-1-1-1", "total_runners": 18},
            {"horse_id": "horse123", "passing_order": "1-1-1-1", "total_runners": 16},
            {"horse_id": "horse123", "passing_order": "2-2-2-1", "total_runners": 14},
        ]
        result = factor.calculate(
            horse_id="horse123",
            race_results=race_results,
            course="東京",
            distance=1600,
            course_stats={"escape": 0.25, "front": 0.35, "stalker": 0.30, "closer": 0.10},
        )
        assert result is not None
        # 逃げの勝率25%は良好なので高スコア

    def test_calculate_returns_none_without_tendency(self, factor):
        """馬の脚質傾向が判定できない場合はNoneを返す"""
        result = factor.calculate(
            horse_id="horse123",
            race_results=[],
            course="東京",
            distance=1600,
        )
        assert result is None

    def test_calculate_uses_default_stats_when_not_provided(self, factor):
        """コース統計がない場合はデフォルト統計を使用"""
        race_results = [
            {"horse_id": "horse123", "passing_order": "1-1-1-1", "total_runners": 18},
            {"horse_id": "horse123", "passing_order": "1-1-1-1", "total_runners": 16},
        ]
        result = factor.calculate(
            horse_id="horse123",
            race_results=race_results,
            course="東京",
            distance=1600,
        )
        assert result is not None
```

**Step 2: テストを実行して失敗を確認**

Run: `pytest tests/test_running_style_factor.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: RunningStyleFactorを実装（GREEN）**

```python
# keiba/analyzers/factors/running_style.py
"""RunningStyleFactor - 脚質分析Factor"""

from collections import Counter

from keiba.analyzers.factors.base import BaseFactor


# デフォルトのコース別脚質統計（全体平均）
DEFAULT_COURSE_STATS = {
    "escape": 0.15,
    "front": 0.35,
    "stalker": 0.35,
    "closer": 0.15,
}


class RunningStyleFactor(BaseFactor):
    """脚質に基づくスコア計算

    馬の脚質傾向とコースの有利脚質をマッチングしてスコア化する。
    """

    name = "running_style"

    def _classify_running_style(
        self, passing_order: str | None, total_horses: int
    ) -> str | None:
        """通過順位から脚質を判定する

        Args:
            passing_order: 通過順位（"1-1-1-1"形式）
            total_horses: 出走頭数

        Returns:
            脚質（escape/front/stalker/closer）、判定不可の場合はNone
        """
        if not passing_order or total_horses == 0:
            return None

        try:
            # 最初のコーナー通過順位を取得
            first_corner = int(passing_order.split("-")[0])
        except (ValueError, IndexError):
            return None

        # 相対位置を計算
        position_ratio = first_corner / total_horses

        if position_ratio <= 0.15:
            return "escape"
        elif position_ratio <= 0.40:
            return "front"
        elif position_ratio <= 0.70:
            return "stalker"
        else:
            return "closer"

    def _get_horse_tendency(
        self, horse_id: str, race_results: list
    ) -> str | None:
        """馬の脚質傾向を判定する

        Args:
            horse_id: 馬ID
            race_results: レース結果のリスト

        Returns:
            最頻出の脚質、判定不可の場合はNone
        """
        # 対象馬のレースを抽出
        horse_races = [
            r for r in race_results
            if r.get("horse_id") == horse_id
            and r.get("passing_order")
            and r.get("total_runners")
        ]

        if not horse_races:
            return None

        # 直近5走を取得
        recent_races = horse_races[:5]

        # 各レースの脚質を判定
        styles = []
        for race in recent_races:
            style = self._classify_running_style(
                race.get("passing_order"),
                race.get("total_runners", 18),
            )
            if style:
                styles.append(style)

        if not styles:
            return None

        # 最頻出の脚質を返す
        counter = Counter(styles)
        return counter.most_common(1)[0][0]

    def calculate(
        self, horse_id: str, race_results: list, **kwargs
    ) -> float | None:
        """脚質適性スコアを計算する

        Args:
            horse_id: 馬ID
            race_results: レース結果のリスト
            **kwargs:
                course: 競馬場名
                distance: レース距離
                course_stats: コース別脚質統計（オプション）

        Returns:
            0-100の範囲のスコア、データ不足の場合はNone
        """
        # 馬の脚質傾向を判定
        tendency = self._get_horse_tendency(horse_id, race_results)
        if tendency is None:
            return None

        # コース統計を取得（なければデフォルト）
        course_stats = kwargs.get("course_stats", DEFAULT_COURSE_STATS)

        # 脚質の勝率を取得
        win_rate = course_stats.get(tendency, 0.25)

        # スコアに変換（勝率を0-100スケールに）
        # 勝率0.40以上 → 100点、勝率0.05以下 → 0点
        score = min(100, max(0, (win_rate - 0.05) / 0.35 * 100))

        return round(score, 1)
```

**Step 4: テストを実行して成功を確認**

Run: `pytest tests/test_running_style_factor.py -v`
Expected: PASS (13 tests)

**Step 5: コミット**

```bash
git add keiba/analyzers/factors/running_style.py tests/test_running_style_factor.py
git commit -m "feat: add RunningStyleFactor for running style analysis"
```

---

### Task 2.2: RunningStyleFactorをモジュールに登録

**Files:**
- Modify: `keiba/analyzers/factors/__init__.py`

**Step 1: __init__.pyを更新**

```python
# keiba/analyzers/factors/__init__.py
"""Factor modules"""

from keiba.analyzers.factors.base import BaseFactor
from keiba.analyzers.factors.course_fit import CourseFitFactor
from keiba.analyzers.factors.last_3f import Last3FFactor
from keiba.analyzers.factors.past_results import PastResultsFactor
from keiba.analyzers.factors.pedigree import PedigreeFactor
from keiba.analyzers.factors.popularity import PopularityFactor
from keiba.analyzers.factors.running_style import RunningStyleFactor
from keiba.analyzers.factors.time_index import TimeIndexFactor

__all__ = [
    "BaseFactor",
    "CourseFitFactor",
    "Last3FFactor",
    "PastResultsFactor",
    "PedigreeFactor",
    "PopularityFactor",
    "RunningStyleFactor",
    "TimeIndexFactor",
]
```

**Step 2: インポートテストを実行**

Run: `python -c "from keiba.analyzers.factors import RunningStyleFactor; print('OK')"`
Expected: "OK"

**Step 3: コミット**

```bash
git add keiba/analyzers/factors/__init__.py
git commit -m "feat: register RunningStyleFactor in factors module"
```

---

## Phase 3: 統合

### Task 3.1: 重み設定の更新

**Files:**
- Modify: `keiba/config/weights.py`
- Modify: `tests/test_analyzers.py`

**Step 1: 重みテストを更新（RED）**

```python
# tests/test_analyzers.py の TestWeightsConfig クラスを更新

class TestWeightsConfig:
    """重み設定のテスト"""

    def test_weights_sum_to_one(self):
        """重みの合計は1.0である"""
        from keiba.config.weights import FACTOR_WEIGHTS

        total = sum(FACTOR_WEIGHTS.values())
        assert round(total, 2) == 1.0

    def test_all_factors_have_weights(self):
        """全てのFactorに重みが設定されている"""
        from keiba.config.weights import FACTOR_WEIGHTS

        required_factors = [
            "past_results",
            "course_fit",
            "time_index",
            "last_3f",
            "popularity",
            "pedigree",
            "running_style",
        ]
        for factor in required_factors:
            assert factor in FACTOR_WEIGHTS

    def test_weights_are_equal(self):
        """7因子が均等に配分されている"""
        from keiba.config.weights import FACTOR_WEIGHTS

        expected_weight = round(1.0 / 7, 3)
        for weight in FACTOR_WEIGHTS.values():
            assert abs(weight - expected_weight) < 0.01
```

**Step 2: テストを実行して失敗を確認**

Run: `pytest tests/test_analyzers.py::TestWeightsConfig -v`
Expected: FAIL (pedigree/running_style not in FACTOR_WEIGHTS)

**Step 3: weights.pyを更新（GREEN）**

```python
# keiba/config/weights.py
"""Factor重み設定

各Factorの重みを定義する。合計は1.0になる必要がある。
"""

FACTOR_WEIGHTS = {
    "past_results": 0.143,    # 過去成績: 14.3%
    "course_fit": 0.143,      # コース適性: 14.3%
    "time_index": 0.143,      # タイム指数: 14.3%
    "last_3f": 0.143,         # 上がり3F: 14.3%
    "popularity": 0.143,      # 人気: 14.3%
    "pedigree": 0.143,        # 血統: 14.3%
    "running_style": 0.142,   # 脚質: 14.2%（端数調整）
}
```

**Step 4: テストを実行して成功を確認**

Run: `pytest tests/test_analyzers.py::TestWeightsConfig -v`
Expected: PASS (3 tests)

**Step 5: コミット**

```bash
git add keiba/config/weights.py tests/test_analyzers.py
git commit -m "feat: update weights to 7-factor equal distribution"
```

---

### Task 3.2: ScoreCalculatorのテスト更新

**Files:**
- Modify: `tests/test_analyzers.py`

**Step 1: ScoreCalculatorのテストを更新**

```python
# tests/test_analyzers.py の TestScoreCalculator クラスを更新

class TestScoreCalculator:
    """ScoreCalculator（重み付きスコア計算）のテスト"""

    @pytest.fixture
    def calculator(self):
        from keiba.analyzers.score_calculator import ScoreCalculator

        return ScoreCalculator()

    def test_calculate_total_score_with_7_factors(self, calculator):
        """7因子の重み付き合計スコアを計算する"""
        factor_scores = {
            "past_results": 80.0,
            "course_fit": 70.0,
            "time_index": 85.0,
            "last_3f": 75.0,
            "popularity": 90.0,
            "pedigree": 82.0,
            "running_style": 78.0,
        }
        result = calculator.calculate_total(factor_scores)
        assert result is not None
        # 全て同じ重み（約0.143）なので、平均に近い値になる
        # 平均 = (80+70+85+75+90+82+78) / 7 = 80
        assert 79 <= result <= 81

    def test_handles_missing_new_factors(self, calculator):
        """新因子がNoneの場合も正規化して計算"""
        factor_scores = {
            "past_results": 80.0,
            "course_fit": 70.0,
            "time_index": 85.0,
            "last_3f": 75.0,
            "popularity": 90.0,
            "pedigree": None,  # データなし
            "running_style": None,  # データなし
        }
        result = calculator.calculate_total(factor_scores)
        assert result is not None

    def test_get_weights_returns_7_factors(self, calculator):
        """重み設定に7因子が含まれる"""
        weights = calculator.get_weights()
        assert len(weights) == 7
        assert "pedigree" in weights
        assert "running_style" in weights
```

**Step 2: テストを実行して成功を確認**

Run: `pytest tests/test_analyzers.py::TestScoreCalculator -v`
Expected: PASS

**Step 3: コミット**

```bash
git add tests/test_analyzers.py
git commit -m "test: update ScoreCalculator tests for 7 factors"
```

---

### Task 3.3: 統合テストの作成

**Files:**
- Create: `tests/test_integration_new_factors.py`

**Step 1: 統合テストを作成**

```python
# tests/test_integration_new_factors.py
"""新因子（血統・脚質）の統合テスト"""

import pytest

from keiba.analyzers.factors import PedigreeFactor, RunningStyleFactor
from keiba.analyzers.score_calculator import ScoreCalculator
from keiba.config.weights import FACTOR_WEIGHTS


class TestNewFactorsIntegration:
    """新因子の統合テスト"""

    def test_pedigree_factor_is_registered(self):
        """PedigreeFactorがfactorsモジュールに登録されている"""
        from keiba.analyzers.factors import PedigreeFactor

        factor = PedigreeFactor()
        assert factor.name == "pedigree"

    def test_running_style_factor_is_registered(self):
        """RunningStyleFactorがfactorsモジュールに登録されている"""
        from keiba.analyzers.factors import RunningStyleFactor

        factor = RunningStyleFactor()
        assert factor.name == "running_style"

    def test_weights_include_new_factors(self):
        """重み設定に新因子が含まれている"""
        assert "pedigree" in FACTOR_WEIGHTS
        assert "running_style" in FACTOR_WEIGHTS

    def test_score_calculator_with_all_factors(self):
        """全7因子でスコア計算が可能"""
        calculator = ScoreCalculator()
        factor_scores = {
            "past_results": 75.0,
            "course_fit": 80.0,
            "time_index": 70.0,
            "last_3f": 85.0,
            "popularity": 60.0,
            "pedigree": 90.0,
            "running_style": 72.0,
        }
        result = calculator.calculate_total(factor_scores)
        assert result is not None
        assert 0 <= result <= 100

    def test_end_to_end_analysis_flow(self):
        """エンドツーエンドの分析フロー"""
        # 1. 各Factorでスコアを計算
        pedigree_factor = PedigreeFactor()
        running_style_factor = RunningStyleFactor()

        # テストデータ
        race_results = [
            {
                "horse_id": "horse123",
                "passing_order": "3-3-2-1",
                "total_runners": 18,
            },
            {
                "horse_id": "horse123",
                "passing_order": "4-4-3-2",
                "total_runners": 16,
            },
            {
                "horse_id": "horse123",
                "passing_order": "5-5-4-3",
                "total_runners": 14,
            },
        ]

        # 血統スコア
        pedigree_score = pedigree_factor.calculate(
            horse_id="horse123",
            race_results=[],
            sire="ディープインパクト",
            dam_sire="キングカメハメハ",
            distance=2000,
            track_condition="良",
        )
        assert pedigree_score is not None

        # 脚質スコア
        running_style_score = running_style_factor.calculate(
            horse_id="horse123",
            race_results=race_results,
            course="東京",
            distance=1600,
        )
        assert running_style_score is not None

        # 2. ScoreCalculatorで合計スコアを計算
        calculator = ScoreCalculator()
        factor_scores = {
            "past_results": 75.0,
            "course_fit": 80.0,
            "time_index": 70.0,
            "last_3f": 85.0,
            "popularity": 60.0,
            "pedigree": pedigree_score,
            "running_style": running_style_score,
        }
        total_score = calculator.calculate_total(factor_scores)
        assert total_score is not None
        assert 0 <= total_score <= 100
```

**Step 2: テストを実行して成功を確認**

Run: `pytest tests/test_integration_new_factors.py -v`
Expected: PASS (5 tests)

**Step 3: コミット**

```bash
git add tests/test_integration_new_factors.py
git commit -m "test: add integration tests for new factors"
```

---

## Phase 4: 検証

### Task 4.1: 全テストとカバレッジ確認

**Step 1: 全テストを実行**

Run: `pytest --cov=keiba --cov-report=term-missing`
Expected: PASS, Coverage >= 80%

**Step 2: カバレッジレポートを確認**

新規ファイルのカバレッジが80%以上であることを確認:
- `keiba/analyzers/factors/pedigree.py`
- `keiba/analyzers/factors/running_style.py`
- `keiba/config/pedigree_master.py`

---

### Task 4.2: 最終コミットとマージ準備

**Step 1: すべての変更をコミット（未コミットがあれば）**

```bash
git status
git add -A
git commit -m "chore: final cleanup for analysis factors feature"
```

**Step 2: ブランチをプッシュ**

```bash
git push -u origin feature/analysis-factors
```

---

## 完了チェックリスト

- [ ] Task 1.1: 血統マスタデータ作成
- [ ] Task 1.2: 血統適性スコアテスト
- [ ] Task 1.3: PedigreeFactor実装
- [ ] Task 1.4: PedigreeFactor登録
- [ ] Task 2.1: 脚質判定ロジック実装
- [ ] Task 2.2: RunningStyleFactor登録
- [ ] Task 3.1: 重み設定更新
- [ ] Task 3.2: ScoreCalculatorテスト更新
- [ ] Task 3.3: 統合テスト作成
- [ ] Task 4.1: 全テスト・カバレッジ確認
- [ ] Task 4.2: マージ準備
