"""Tests for past_stats_calculator - 過去成績統計計算の純粋関数テスト"""

from datetime import date, datetime

from keiba.services.past_stats_calculator import calculate_past_stats


class TestCalculatePastStatsEmptyResults:
    """空リスト時の挙動テスト"""

    def test_returns_all_none_for_empty_list(self):
        """空リストの場合、全ての値がNoneの辞書を返す"""
        result = calculate_past_stats([], date(2025, 1, 1))

        assert result == {
            "win_rate": None,
            "top3_rate": None,
            "avg_finish_position": None,
            "days_since_last_race": None,
        }

    def test_returns_dict_with_expected_keys(self):
        """空リストでも4つのキーが全て含まれる"""
        result = calculate_past_stats([], date(2025, 1, 1))

        expected_keys = {"win_rate", "top3_rate", "avg_finish_position", "days_since_last_race"}
        assert set(result.keys()) == expected_keys


class TestCalculatePastStatsWinRate:
    """勝率計算テスト"""

    def test_all_wins(self):
        """全勝の場合は勝率1.0"""
        past_results = [
            {"horse_id": "h1", "finish_position": 1, "race_date": "2024-12-01"},
            {"horse_id": "h1", "finish_position": 1, "race_date": "2024-11-01"},
        ]
        result = calculate_past_stats(past_results, date(2025, 1, 1))
        assert result["win_rate"] == 1.0

    def test_no_wins(self):
        """勝利なしの場合は勝率0.0"""
        past_results = [
            {"horse_id": "h1", "finish_position": 3, "race_date": "2024-12-01"},
            {"horse_id": "h1", "finish_position": 5, "race_date": "2024-11-01"},
        ]
        result = calculate_past_stats(past_results, date(2025, 1, 1))
        assert result["win_rate"] == 0.0

    def test_partial_wins(self):
        """1勝3敗の場合は勝率0.25"""
        past_results = [
            {"horse_id": "h1", "finish_position": 1, "race_date": "2024-12-01"},
            {"horse_id": "h1", "finish_position": 3, "race_date": "2024-11-01"},
            {"horse_id": "h1", "finish_position": 5, "race_date": "2024-10-01"},
            {"horse_id": "h1", "finish_position": 8, "race_date": "2024-09-01"},
        ]
        result = calculate_past_stats(past_results, date(2025, 1, 1))
        assert result["win_rate"] == 0.25


class TestCalculatePastStatsTop3Rate:
    """3着以内率計算テスト"""

    def test_all_top3(self):
        """全て3着以内の場合はtop3_rate 1.0"""
        past_results = [
            {"horse_id": "h1", "finish_position": 1, "race_date": "2024-12-01"},
            {"horse_id": "h1", "finish_position": 2, "race_date": "2024-11-01"},
            {"horse_id": "h1", "finish_position": 3, "race_date": "2024-10-01"},
        ]
        result = calculate_past_stats(past_results, date(2025, 1, 1))
        assert result["top3_rate"] == 1.0

    def test_no_top3(self):
        """3着以内なしの場合はtop3_rate 0.0"""
        past_results = [
            {"horse_id": "h1", "finish_position": 5, "race_date": "2024-12-01"},
            {"horse_id": "h1", "finish_position": 8, "race_date": "2024-11-01"},
        ]
        result = calculate_past_stats(past_results, date(2025, 1, 1))
        assert result["top3_rate"] == 0.0

    def test_partial_top3(self):
        """2/4が3着以内の場合はtop3_rate 0.5"""
        past_results = [
            {"horse_id": "h1", "finish_position": 1, "race_date": "2024-12-01"},
            {"horse_id": "h1", "finish_position": 3, "race_date": "2024-11-01"},
            {"horse_id": "h1", "finish_position": 5, "race_date": "2024-10-01"},
            {"horse_id": "h1", "finish_position": 8, "race_date": "2024-09-01"},
        ]
        result = calculate_past_stats(past_results, date(2025, 1, 1))
        assert result["top3_rate"] == 0.5

    def test_finish_position_none_treated_as_not_top3(self):
        """finish_positionがNoneの場合は3着以内にカウントしない"""
        past_results = [
            {"horse_id": "h1", "finish_position": 1, "race_date": "2024-12-01"},
            {"horse_id": "h1", "finish_position": None, "race_date": "2024-11-01"},
        ]
        result = calculate_past_stats(past_results, date(2025, 1, 1))
        assert result["top3_rate"] == 0.5

    def test_finish_position_zero_treated_as_not_top3(self):
        """finish_positionが0の場合は3着以内にカウントしない"""
        past_results = [
            {"horse_id": "h1", "finish_position": 2, "race_date": "2024-12-01"},
            {"horse_id": "h1", "finish_position": 0, "race_date": "2024-11-01"},
        ]
        result = calculate_past_stats(past_results, date(2025, 1, 1))
        assert result["top3_rate"] == 0.5


class TestCalculatePastStatsAvgFinishPosition:
    """平均着順計算テスト"""

    def test_single_result(self):
        """1件の場合はその着順が平均"""
        past_results = [
            {"horse_id": "h1", "finish_position": 3, "race_date": "2024-12-01"},
        ]
        result = calculate_past_stats(past_results, date(2025, 1, 1))
        assert result["avg_finish_position"] == 3.0

    def test_multiple_results(self):
        """複数件の平均着順"""
        past_results = [
            {"horse_id": "h1", "finish_position": 1, "race_date": "2024-12-01"},
            {"horse_id": "h1", "finish_position": 3, "race_date": "2024-11-01"},
            {"horse_id": "h1", "finish_position": 5, "race_date": "2024-10-01"},
        ]
        result = calculate_past_stats(past_results, date(2025, 1, 1))
        assert result["avg_finish_position"] == 3.0

    def test_skips_none_finish_positions(self):
        """finish_positionがNoneのレコードは平均計算から除外"""
        past_results = [
            {"horse_id": "h1", "finish_position": 2, "race_date": "2024-12-01"},
            {"horse_id": "h1", "finish_position": None, "race_date": "2024-11-01"},
            {"horse_id": "h1", "finish_position": 4, "race_date": "2024-10-01"},
        ]
        result = calculate_past_stats(past_results, date(2025, 1, 1))
        assert result["avg_finish_position"] == 3.0

    def test_skips_zero_finish_positions(self):
        """finish_positionが0のレコードは平均計算から除外"""
        past_results = [
            {"horse_id": "h1", "finish_position": 2, "race_date": "2024-12-01"},
            {"horse_id": "h1", "finish_position": 0, "race_date": "2024-11-01"},
            {"horse_id": "h1", "finish_position": 4, "race_date": "2024-10-01"},
        ]
        result = calculate_past_stats(past_results, date(2025, 1, 1))
        assert result["avg_finish_position"] == 3.0


class TestCalculatePastStatsDaysSinceLastRace:
    """経過日数計算テスト"""

    def test_days_calculation_with_string_date(self):
        """race_dateが文字列(YYYY-MM-DD)の場合の経過日数計算"""
        past_results = [
            {"horse_id": "h1", "finish_position": 1, "race_date": "2024-12-12"},
        ]
        result = calculate_past_stats(past_results, date(2025, 1, 1))
        assert result["days_since_last_race"] == 20

    def test_days_calculation_with_date_object(self):
        """race_dateがdateオブジェクトの場合の経過日数計算"""
        past_results = [
            {"horse_id": "h1", "finish_position": 1, "race_date": date(2024, 12, 12)},
        ]
        result = calculate_past_stats(past_results, date(2025, 1, 1))
        assert result["days_since_last_race"] == 20

    def test_days_calculation_with_datetime_object(self):
        """race_dateがdatetimeオブジェクトの場合の経過日数計算"""
        past_results = [
            {"horse_id": "h1", "finish_position": 1, "race_date": datetime(2024, 12, 12, 10, 0, 0)},
        ]
        result = calculate_past_stats(past_results, date(2025, 1, 1))
        assert result["days_since_last_race"] == 20

    def test_days_none_when_race_date_missing(self):
        """race_dateがない場合はNone"""
        past_results = [
            {"horse_id": "h1", "finish_position": 1},
        ]
        result = calculate_past_stats(past_results, date(2025, 1, 1))
        assert result["days_since_last_race"] is None

    def test_uses_first_result_as_latest(self):
        """最初の要素（最新レース）を経過日数計算に使う"""
        past_results = [
            {"horse_id": "h1", "finish_position": 2, "race_date": "2024-12-25"},
            {"horse_id": "h1", "finish_position": 1, "race_date": "2024-11-01"},
        ]
        result = calculate_past_stats(past_results, date(2025, 1, 1))
        assert result["days_since_last_race"] == 7


class TestCalculatePastStatsWithHorseIdFilter:
    """horse_idフィルタリングテスト"""

    def test_filters_by_horse_id(self):
        """horse_id指定時はその馬のデータのみ使う"""
        past_results = [
            {"horse_id": "h1", "finish_position": 1, "race_date": "2024-12-01"},
            {"horse_id": "h2", "finish_position": 5, "race_date": "2024-12-01"},
            {"horse_id": "h1", "finish_position": 3, "race_date": "2024-11-01"},
            {"horse_id": "h2", "finish_position": 8, "race_date": "2024-11-01"},
        ]
        result = calculate_past_stats(past_results, date(2025, 1, 1), horse_id="h1")

        # h1のみ: 1勝/2走, top3: 2/2, 平均着順: (1+3)/2=2.0
        assert result["win_rate"] == 0.5
        assert result["top3_rate"] == 1.0
        assert result["avg_finish_position"] == 2.0

    def test_without_horse_id_uses_all(self):
        """horse_id未指定時は全データを使う"""
        past_results = [
            {"horse_id": "h1", "finish_position": 1, "race_date": "2024-12-01"},
            {"horse_id": "h2", "finish_position": 5, "race_date": "2024-12-01"},
        ]
        result = calculate_past_stats(past_results, date(2025, 1, 1))

        # 全データ: 1勝/2走, top3: 1/2
        assert result["win_rate"] == 0.5
        assert result["top3_rate"] == 0.5

    def test_horse_id_filter_with_no_matching_results_uses_all(self):
        """horse_idフィルタで該当なしの場合は全データにフォールバック"""
        past_results = [
            {"horse_id": "h1", "finish_position": 1, "race_date": "2024-12-01"},
            {"horse_id": "h2", "finish_position": 3, "race_date": "2024-11-01"},
        ]
        result = calculate_past_stats(past_results, date(2025, 1, 1), horse_id="h999")

        # フォールバック: 全データを使用
        assert result["win_rate"] == 0.5
        assert result["top3_rate"] == 1.0

    def test_horse_id_filter_days_since_last_race(self):
        """horse_idフィルタ時の経過日数はフィルタ後のデータで計算"""
        past_results = [
            {"horse_id": "h2", "finish_position": 1, "race_date": "2024-12-25"},
            {"horse_id": "h1", "finish_position": 3, "race_date": "2024-12-12"},
            {"horse_id": "h1", "finish_position": 5, "race_date": "2024-11-01"},
        ]
        result = calculate_past_stats(past_results, date(2025, 1, 1), horse_id="h1")

        # h1の最新レースは2024-12-12 -> 20日前
        assert result["days_since_last_race"] == 20
