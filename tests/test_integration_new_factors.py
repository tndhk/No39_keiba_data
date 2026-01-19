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
        pedigree_factor = PedigreeFactor()
        running_style_factor = RunningStyleFactor()

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

        pedigree_score = pedigree_factor.calculate(
            horse_id="horse123",
            race_results=[],
            sire="ディープインパクト",
            dam_sire="キングカメハメハ",
            distance=2000,
            track_condition="良",
        )
        assert pedigree_score is not None

        running_style_score = running_style_factor.calculate(
            horse_id="horse123",
            race_results=race_results,
            course="東京",
            distance=1600,
        )
        assert running_style_score is not None

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
