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
        assert tendency == "escape"

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
