"""ファクター重要度測定スクリプトのテスト

TDDのREDフェーズ: まずテストを作成し、FAILを確認する。
"""

import sys
from pathlib import Path

import pytest

# scriptsディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))


class TestCalculateFactorHitRate:
    """calculate_factor_hit_rate関数のテスト"""

    def test_returns_hit_rate_for_top3(self):
        """Top3的中率を正しく計算できる"""
        from factor_importance import calculate_factor_hit_rate

        # テストデータ: ファクタースコアと実際の着順
        test_data = [
            {"factor_score": 80.0, "finish_position": 1},  # 的中
            {"factor_score": 70.0, "finish_position": 2},  # 的中
            {"factor_score": 60.0, "finish_position": 5},  # 外れ
            {"factor_score": 50.0, "finish_position": 3},  # 的中
        ]

        # Top3的中率: 3/4 = 75%
        result = calculate_factor_hit_rate(test_data, top_n=3)
        assert result == 0.75

    def test_returns_hit_rate_for_top1(self):
        """Top1的中率を正しく計算できる"""
        from factor_importance import calculate_factor_hit_rate

        test_data = [
            {"factor_score": 80.0, "finish_position": 1},  # 的中
            {"factor_score": 70.0, "finish_position": 2},  # 外れ
            {"factor_score": 60.0, "finish_position": 1},  # 的中
            {"factor_score": 50.0, "finish_position": 5},  # 外れ
        ]

        # Top1的中率: 2/4 = 50%
        result = calculate_factor_hit_rate(test_data, top_n=1)
        assert result == 0.5

    def test_returns_zero_for_empty_data(self):
        """空データの場合は0.0を返す"""
        from factor_importance import calculate_factor_hit_rate

        result = calculate_factor_hit_rate([], top_n=3)
        assert result == 0.0

    def test_returns_one_for_all_hits(self):
        """全て的中の場合は1.0を返す"""
        from factor_importance import calculate_factor_hit_rate

        test_data = [
            {"factor_score": 80.0, "finish_position": 1},
            {"factor_score": 70.0, "finish_position": 2},
            {"factor_score": 60.0, "finish_position": 3},
        ]

        result = calculate_factor_hit_rate(test_data, top_n=3)
        assert result == 1.0

    def test_returns_zero_for_no_hits(self):
        """全て外れの場合は0.0を返す"""
        from factor_importance import calculate_factor_hit_rate

        test_data = [
            {"factor_score": 80.0, "finish_position": 4},
            {"factor_score": 70.0, "finish_position": 5},
            {"factor_score": 60.0, "finish_position": 6},
        ]

        result = calculate_factor_hit_rate(test_data, top_n=3)
        assert result == 0.0


class TestCalculateFactorRankingCorrelation:
    """calculate_factor_ranking_correlation関数のテスト"""

    def test_returns_negative_for_good_prediction(self):
        """予測が良い場合（スコア高い=着順良い）は負の相関を返す"""
        from factor_importance import calculate_factor_ranking_correlation

        # 完全に逆相関（スコア高い=着順良い）が理想
        test_data = [
            {"factor_score": 100.0, "finish_position": 1},
            {"factor_score": 80.0, "finish_position": 2},
            {"factor_score": 60.0, "finish_position": 3},
            {"factor_score": 40.0, "finish_position": 4},
        ]

        # スコアが高いほど着順が良い（負の相関）
        result = calculate_factor_ranking_correlation(test_data)
        assert result < -0.9  # 強い負の相関

    def test_returns_positive_for_bad_prediction(self):
        """予測が悪い場合（スコア高い=着順悪い）は正の相関を返す"""
        from factor_importance import calculate_factor_ranking_correlation

        # 正相関（スコア高い=着順悪い）= ダメな予測
        test_data = [
            {"factor_score": 100.0, "finish_position": 4},
            {"factor_score": 80.0, "finish_position": 3},
            {"factor_score": 60.0, "finish_position": 2},
            {"factor_score": 40.0, "finish_position": 1},
        ]

        result = calculate_factor_ranking_correlation(test_data)
        assert result > 0.9  # 強い正の相関（悪い予測）

    def test_returns_zero_for_insufficient_data(self):
        """データが不足の場合は0.0を返す"""
        from factor_importance import calculate_factor_ranking_correlation

        # 1件のみ
        test_data = [{"factor_score": 80.0, "finish_position": 1}]
        result = calculate_factor_ranking_correlation(test_data)
        assert result == 0.0

        # 空データ
        result_empty = calculate_factor_ranking_correlation([])
        assert result_empty == 0.0


class TestCalculateRecoveryRate:
    """calculate_recovery_rate関数のテスト"""

    def test_returns_recovery_rate(self):
        """回収率を正しく計算できる"""
        from factor_importance import calculate_recovery_rate

        # テストデータ: 馬番上位を買った場合のシミュレーション
        test_data = [
            {"factor_score": 80.0, "finish_position": 1, "odds": 3.5},  # 的中: 350円
            {"factor_score": 70.0, "finish_position": 4, "odds": 2.0},  # 外れ
            {"factor_score": 60.0, "finish_position": 2, "odds": 5.0},  # 的中: 500円
            {"factor_score": 50.0, "finish_position": 5, "odds": 10.0},  # 外れ
        ]

        # 投資: 400円、回収: 850円、回収率: 212.5%
        result = calculate_recovery_rate(test_data, top_n=3)
        assert result == pytest.approx(2.125, rel=0.01)

    def test_returns_zero_for_no_hits(self):
        """全て外れの場合は0.0を返す"""
        from factor_importance import calculate_recovery_rate

        test_data = [
            {"factor_score": 80.0, "finish_position": 4, "odds": 3.5},
            {"factor_score": 70.0, "finish_position": 5, "odds": 2.0},
        ]

        result = calculate_recovery_rate(test_data, top_n=3)
        assert result == 0.0

    def test_returns_zero_for_empty_data(self):
        """空データの場合は0.0を返す"""
        from factor_importance import calculate_recovery_rate

        result = calculate_recovery_rate([], top_n=3)
        assert result == 0.0

    def test_handles_none_odds(self):
        """オッズがNoneの場合も正しく処理する"""
        from factor_importance import calculate_recovery_rate

        test_data = [
            {"factor_score": 80.0, "finish_position": 1, "odds": None},  # 的中だがオッズなし
            {"factor_score": 70.0, "finish_position": 2, "odds": 5.0},  # 的中: 500円
        ]

        # 投資: 200円、回収: 500円（オッズなしは0扱い）、回収率: 250%
        result = calculate_recovery_rate(test_data, top_n=3)
        assert result == pytest.approx(2.5, rel=0.01)


class TestFactorImportanceResult:
    """FactorImportanceResult データクラスのテスト"""

    def test_can_create_result(self):
        """結果オブジェクトを生成できる"""
        from factor_importance import FactorImportanceResult

        result = FactorImportanceResult(
            factor_name="past_results",
            hit_rate_top1=0.25,
            hit_rate_top3=0.55,
            recovery_rate=0.85,
            correlation=-0.35,
            sample_count=100,
        )

        assert result.factor_name == "past_results"
        assert result.hit_rate_top1 == 0.25
        assert result.hit_rate_top3 == 0.55
        assert result.recovery_rate == 0.85
        assert result.correlation == -0.35
        assert result.sample_count == 100


class TestMeasureFactorImportance:
    """measure_factor_importance関数のテスト"""

    def test_returns_importance_result(self):
        """FactorImportanceResultを返す"""
        from factor_importance import FactorImportanceResult, measure_factor_importance

        # ファクタースコアと結果のペア
        test_data = [
            {"factor_score": 90.0, "finish_position": 1, "odds": 2.0},
            {"factor_score": 80.0, "finish_position": 2, "odds": 3.0},
            {"factor_score": 70.0, "finish_position": 4, "odds": 5.0},
            {"factor_score": 60.0, "finish_position": 3, "odds": 4.0},
        ]

        result = measure_factor_importance("past_results", test_data)

        assert isinstance(result, FactorImportanceResult)
        assert result.factor_name == "past_results"
        assert 0 <= result.hit_rate_top1 <= 1
        assert 0 <= result.hit_rate_top3 <= 1
        assert result.recovery_rate >= 0
        assert -1 <= result.correlation <= 1
        assert result.sample_count == 4


class TestPrintResults:
    """print_results関数のテスト"""

    def test_outputs_formatted_table(self, capsys):
        """結果をテーブル形式で出力する"""
        from factor_importance import FactorImportanceResult, print_results

        results = [
            FactorImportanceResult(
                factor_name="past_results",
                hit_rate_top1=0.25,
                hit_rate_top3=0.55,
                recovery_rate=0.85,
                correlation=-0.35,
                sample_count=100,
            ),
            FactorImportanceResult(
                factor_name="course_fit",
                hit_rate_top1=0.20,
                hit_rate_top3=0.50,
                recovery_rate=0.75,
                correlation=-0.25,
                sample_count=80,
            ),
        ]

        print_results(results)

        captured = capsys.readouterr()
        assert "ファクター重要度測定結果" in captured.out
        assert "past_results" in captured.out
        assert "course_fit" in captured.out
        assert "Top1的中率" in captured.out
        assert "Top3的中率" in captured.out
        assert "回収率" in captured.out
        assert "相関係数" in captured.out


class TestGetFactorKwargs:
    """_get_factor_kwargs関数のテスト"""

    def test_returns_empty_for_past_results(self):
        """past_resultsの場合は空のdictを返す"""
        from factor_importance import _get_factor_kwargs
        from unittest.mock import MagicMock

        race = MagicMock()
        race.surface = "芝"
        race.distance = 2000

        race_result = MagicMock()
        race_result.horse_id = "horse1"

        session = MagicMock()

        kwargs = _get_factor_kwargs("past_results", race, race_result, session)
        assert kwargs == {}

    def test_returns_surface_and_distance_for_course_fit(self):
        """course_fitの場合はsurfaceとdistanceを返す"""
        from factor_importance import _get_factor_kwargs
        from unittest.mock import MagicMock

        race = MagicMock()
        race.surface = "芝"
        race.distance = 2000

        race_result = MagicMock()
        race_result.horse_id = "horse1"

        session = MagicMock()

        kwargs = _get_factor_kwargs("course_fit", race, race_result, session)
        assert kwargs == {"surface": "芝", "distance": 2000}

    def test_returns_target_distance_for_running_style(self):
        """running_styleの場合はtarget_distanceを返す"""
        from factor_importance import _get_factor_kwargs
        from unittest.mock import MagicMock

        race = MagicMock()
        race.surface = "ダート"
        race.distance = 1600

        race_result = MagicMock()
        race_result.horse_id = "horse1"

        session = MagicMock()

        kwargs = _get_factor_kwargs("running_style", race, race_result, session)
        assert kwargs == {"target_distance": 1600}
