"""MetricsCalculatorのテスト

TDDのREDフェーズ: テストを作成し、FAILを確認する
"""

import pytest

from keiba.backtest.metrics import (
    MetricsCalculator,
    PredictionResult,
    RaceBacktestResult,
)


# === テストデータ生成ヘルパー ===


def make_prediction(
    horse_number: int,
    horse_name: str,
    ml_rank: int | None,
    factor_rank: int,
    actual_rank: int,
    ml_probability: float | None = None,
) -> PredictionResult:
    """テスト用PredictionResultを生成"""
    return PredictionResult(
        horse_number=horse_number,
        horse_name=horse_name,
        ml_probability=ml_probability,
        ml_rank=ml_rank,
        factor_rank=factor_rank,
        actual_rank=actual_rank,
    )


def make_race_result(
    race_id: str,
    predictions: list[PredictionResult],
    race_date: str = "2024-01-01",
    race_name: str = "テストレース",
    venue: str = "東京",
) -> RaceBacktestResult:
    """テスト用RaceBacktestResultを生成"""
    return RaceBacktestResult(
        race_id=race_id,
        race_date=race_date,
        race_name=race_name,
        venue=venue,
        predictions=predictions,
    )


# === データクラスのテスト ===


class TestPredictionResult:
    """PredictionResultデータクラスのテスト"""

    def test_create_instance(self):
        """PredictionResultインスタンスを作成できる"""
        result = PredictionResult(
            horse_number=1,
            horse_name="テスト馬",
            ml_probability=0.85,
            ml_rank=1,
            factor_rank=2,
            actual_rank=1,
        )
        assert result.horse_number == 1
        assert result.horse_name == "テスト馬"
        assert result.ml_probability == 0.85
        assert result.ml_rank == 1
        assert result.factor_rank == 2
        assert result.actual_rank == 1

    def test_ml_probability_can_be_none(self):
        """ml_probabilityはNoneを許容する"""
        result = PredictionResult(
            horse_number=1,
            horse_name="テスト馬",
            ml_probability=None,
            ml_rank=None,
            factor_rank=1,
            actual_rank=1,
        )
        assert result.ml_probability is None
        assert result.ml_rank is None


class TestRaceBacktestResult:
    """RaceBacktestResultデータクラスのテスト"""

    def test_create_instance(self):
        """RaceBacktestResultインスタンスを作成できる"""
        predictions = [
            make_prediction(1, "馬A", 1, 1, 1),
            make_prediction(2, "馬B", 2, 2, 2),
        ]
        result = make_race_result("202401010101", predictions)
        assert result.race_id == "202401010101"
        assert result.race_date == "2024-01-01"
        assert result.race_name == "テストレース"
        assert result.venue == "東京"
        assert len(result.predictions) == 2


# === MetricsCalculator.precision_at_k のテスト ===


class TestPrecisionAtK:
    """precision_at_kメソッドのテスト"""

    def test_precision_at_1_all_correct(self):
        """全レースで1位指名が1着: Precision@1 = 1.0"""
        # 3レース全てで、ML予測1位の馬が実際に1着
        results = [
            make_race_result(
                "race1",
                [
                    make_prediction(1, "馬A", ml_rank=1, factor_rank=2, actual_rank=1),
                    make_prediction(2, "馬B", ml_rank=2, factor_rank=1, actual_rank=2),
                ],
            ),
            make_race_result(
                "race2",
                [
                    make_prediction(3, "馬C", ml_rank=1, factor_rank=1, actual_rank=1),
                    make_prediction(4, "馬D", ml_rank=2, factor_rank=2, actual_rank=2),
                ],
            ),
            make_race_result(
                "race3",
                [
                    make_prediction(5, "馬E", ml_rank=1, factor_rank=3, actual_rank=1),
                    make_prediction(6, "馬F", ml_rank=2, factor_rank=1, actual_rank=2),
                ],
            ),
        ]

        precision = MetricsCalculator.precision_at_k(results, k=1, use_ml=True)
        assert precision == 1.0

    def test_precision_at_1_none_correct(self):
        """全レースで1位指名が外れ: Precision@1 = 0.0"""
        # 3レース全てで、ML予測1位の馬が1着ではない
        results = [
            make_race_result(
                "race1",
                [
                    make_prediction(1, "馬A", ml_rank=1, factor_rank=1, actual_rank=3),
                    make_prediction(2, "馬B", ml_rank=2, factor_rank=2, actual_rank=1),
                ],
            ),
            make_race_result(
                "race2",
                [
                    make_prediction(3, "馬C", ml_rank=1, factor_rank=1, actual_rank=5),
                    make_prediction(4, "馬D", ml_rank=2, factor_rank=2, actual_rank=1),
                ],
            ),
            make_race_result(
                "race3",
                [
                    make_prediction(5, "馬E", ml_rank=1, factor_rank=1, actual_rank=2),
                    make_prediction(6, "馬F", ml_rank=2, factor_rank=2, actual_rank=1),
                ],
            ),
        ]

        precision = MetricsCalculator.precision_at_k(results, k=1, use_ml=True)
        assert precision == 0.0

    def test_precision_at_3_partial(self):
        """上位3位指名のうち部分的に的中: Precision@3"""
        # 1レースで、ML予測1-3位のうち2頭が実際に3着以内
        results = [
            make_race_result(
                "race1",
                [
                    make_prediction(1, "馬A", ml_rank=1, factor_rank=1, actual_rank=1),
                    make_prediction(2, "馬B", ml_rank=2, factor_rank=2, actual_rank=5),
                    make_prediction(3, "馬C", ml_rank=3, factor_rank=3, actual_rank=2),
                    make_prediction(4, "馬D", ml_rank=4, factor_rank=4, actual_rank=3),
                ],
            ),
        ]

        # 予測上位3頭(馬A, 馬B, 馬C)のうち、3着以内は馬A(1着)と馬C(2着)の2頭
        # Precision@3 = 2/3 = 0.666...
        precision = MetricsCalculator.precision_at_k(results, k=3, use_ml=True)
        assert abs(precision - 2 / 3) < 0.001

    def test_precision_at_k_with_factor(self):
        """ファクター予測でのPrecision@1"""
        results = [
            make_race_result(
                "race1",
                [
                    make_prediction(1, "馬A", ml_rank=2, factor_rank=1, actual_rank=1),
                    make_prediction(2, "馬B", ml_rank=1, factor_rank=2, actual_rank=2),
                ],
            ),
        ]

        # ファクター予測1位の馬Aが1着
        precision = MetricsCalculator.precision_at_k(results, k=1, use_ml=False)
        assert precision == 1.0

    def test_precision_at_1_mixed_results(self):
        """3レース中2レースで的中: Precision@1 = 2/3"""
        results = [
            make_race_result(
                "race1",
                [
                    make_prediction(1, "馬A", ml_rank=1, factor_rank=1, actual_rank=1),
                    make_prediction(2, "馬B", ml_rank=2, factor_rank=2, actual_rank=2),
                ],
            ),
            make_race_result(
                "race2",
                [
                    make_prediction(3, "馬C", ml_rank=1, factor_rank=1, actual_rank=1),
                    make_prediction(4, "馬D", ml_rank=2, factor_rank=2, actual_rank=2),
                ],
            ),
            make_race_result(
                "race3",
                [
                    make_prediction(5, "馬E", ml_rank=1, factor_rank=1, actual_rank=3),
                    make_prediction(6, "馬F", ml_rank=2, factor_rank=2, actual_rank=1),
                ],
            ),
        ]

        precision = MetricsCalculator.precision_at_k(results, k=1, use_ml=True)
        assert abs(precision - 2 / 3) < 0.001


# === MetricsCalculator.hit_rate_by_rank のテスト ===


class TestHitRateByRank:
    """hit_rate_by_rankメソッドのテスト"""

    def test_hit_rate_rank_1_all_in_top3(self):
        """全レースで1位指名が3着以内: hit_rate = 1.0"""
        results = [
            make_race_result(
                "race1",
                [
                    make_prediction(1, "馬A", ml_rank=1, factor_rank=1, actual_rank=2),
                    make_prediction(2, "馬B", ml_rank=2, factor_rank=2, actual_rank=1),
                ],
            ),
            make_race_result(
                "race2",
                [
                    make_prediction(3, "馬C", ml_rank=1, factor_rank=1, actual_rank=3),
                    make_prediction(4, "馬D", ml_rank=2, factor_rank=2, actual_rank=1),
                ],
            ),
        ]

        hit_rate = MetricsCalculator.hit_rate_by_rank(results, rank=1, use_ml=True)
        assert hit_rate == 1.0

    def test_hit_rate_rank_1_none_in_top3(self):
        """全レースで1位指名が3着以内に入らず: hit_rate = 0.0"""
        results = [
            make_race_result(
                "race1",
                [
                    make_prediction(1, "馬A", ml_rank=1, factor_rank=1, actual_rank=4),
                    make_prediction(2, "馬B", ml_rank=2, factor_rank=2, actual_rank=1),
                ],
            ),
            make_race_result(
                "race2",
                [
                    make_prediction(3, "馬C", ml_rank=1, factor_rank=1, actual_rank=5),
                    make_prediction(4, "馬D", ml_rank=2, factor_rank=2, actual_rank=1),
                ],
            ),
        ]

        hit_rate = MetricsCalculator.hit_rate_by_rank(results, rank=1, use_ml=True)
        assert hit_rate == 0.0

    def test_hit_rate_rank_2_partial(self):
        """2位指名の的中率: 2レース中1レースで3着以内"""
        results = [
            make_race_result(
                "race1",
                [
                    make_prediction(1, "馬A", ml_rank=1, factor_rank=1, actual_rank=1),
                    make_prediction(2, "馬B", ml_rank=2, factor_rank=2, actual_rank=2),
                ],
            ),
            make_race_result(
                "race2",
                [
                    make_prediction(3, "馬C", ml_rank=1, factor_rank=1, actual_rank=1),
                    make_prediction(4, "馬D", ml_rank=2, factor_rank=2, actual_rank=5),
                ],
            ),
        ]

        hit_rate = MetricsCalculator.hit_rate_by_rank(results, rank=2, use_ml=True)
        assert hit_rate == 0.5

    def test_hit_rate_with_factor(self):
        """ファクター予測での的中率"""
        results = [
            make_race_result(
                "race1",
                [
                    make_prediction(1, "馬A", ml_rank=2, factor_rank=1, actual_rank=1),
                    make_prediction(2, "馬B", ml_rank=1, factor_rank=2, actual_rank=4),
                ],
            ),
        ]

        # ファクター予測1位の馬Aが1着（3着以内）
        hit_rate = MetricsCalculator.hit_rate_by_rank(results, rank=1, use_ml=False)
        assert hit_rate == 1.0


# === MetricsCalculator.calculate のテスト ===


class TestCalculate:
    """calculateメソッドのテスト"""

    def test_calculate_returns_all_metrics(self):
        """全メトリクスを含む辞書を返す"""
        results = [
            make_race_result(
                "race1",
                [
                    make_prediction(
                        1, "馬A", ml_rank=1, factor_rank=1, actual_rank=1, ml_probability=0.8
                    ),
                    make_prediction(
                        2, "馬B", ml_rank=2, factor_rank=2, actual_rank=2, ml_probability=0.5
                    ),
                    make_prediction(
                        3, "馬C", ml_rank=3, factor_rank=3, actual_rank=3, ml_probability=0.3
                    ),
                ],
            ),
        ]

        metrics = MetricsCalculator.calculate(results)

        # MLメトリクスの存在確認
        assert "ml" in metrics
        assert "precision_at_1" in metrics["ml"]
        assert "precision_at_3" in metrics["ml"]
        assert "hit_rate_rank_1" in metrics["ml"]
        assert "hit_rate_rank_2" in metrics["ml"]
        assert "hit_rate_rank_3" in metrics["ml"]

        # ファクターメトリクスの存在確認
        assert "factor" in metrics
        assert "precision_at_1" in metrics["factor"]
        assert "precision_at_3" in metrics["factor"]
        assert "hit_rate_rank_1" in metrics["factor"]
        assert "hit_rate_rank_2" in metrics["factor"]
        assert "hit_rate_rank_3" in metrics["factor"]

    def test_calculate_correct_values(self):
        """calculateが正しい値を計算する"""
        # 完璧な予測: ML/ファクター両方で予測順位=実際の着順
        results = [
            make_race_result(
                "race1",
                [
                    make_prediction(1, "馬A", ml_rank=1, factor_rank=1, actual_rank=1),
                    make_prediction(2, "馬B", ml_rank=2, factor_rank=2, actual_rank=2),
                    make_prediction(3, "馬C", ml_rank=3, factor_rank=3, actual_rank=3),
                ],
            ),
        ]

        metrics = MetricsCalculator.calculate(results)

        # 完璧な予測なので全て1.0
        assert metrics["ml"]["precision_at_1"] == 1.0
        assert metrics["ml"]["precision_at_3"] == 1.0
        assert metrics["ml"]["hit_rate_rank_1"] == 1.0
        assert metrics["ml"]["hit_rate_rank_2"] == 1.0
        assert metrics["ml"]["hit_rate_rank_3"] == 1.0


# === エッジケースのテスト ===


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_empty_results(self):
        """空の結果リストの場合"""
        results: list[RaceBacktestResult] = []

        # 空の場合は0.0を返す（ゼロ除算を避ける）
        precision = MetricsCalculator.precision_at_k(results, k=1, use_ml=True)
        assert precision == 0.0

        hit_rate = MetricsCalculator.hit_rate_by_rank(results, rank=1, use_ml=True)
        assert hit_rate == 0.0

    def test_race_with_no_predictions(self):
        """予測が空のレース"""
        results = [
            make_race_result("race1", []),
        ]

        # 予測がない場合も0.0
        precision = MetricsCalculator.precision_at_k(results, k=1, use_ml=True)
        assert precision == 0.0

    def test_ml_rank_is_none(self):
        """ML予測がNoneの場合はスキップ"""
        results = [
            make_race_result(
                "race1",
                [
                    make_prediction(1, "馬A", ml_rank=None, factor_rank=1, actual_rank=1),
                    make_prediction(2, "馬B", ml_rank=None, factor_rank=2, actual_rank=2),
                ],
            ),
        ]

        # MLランクがNoneの場合、ML予測は計算不可
        precision = MetricsCalculator.precision_at_k(results, k=1, use_ml=True)
        assert precision == 0.0

        # ファクターは計算可能
        precision_factor = MetricsCalculator.precision_at_k(results, k=1, use_ml=False)
        assert precision_factor == 1.0

    def test_k_larger_than_predictions(self):
        """kが予測数より大きい場合"""
        results = [
            make_race_result(
                "race1",
                [
                    make_prediction(1, "馬A", ml_rank=1, factor_rank=1, actual_rank=1),
                    make_prediction(2, "馬B", ml_rank=2, factor_rank=2, actual_rank=2),
                ],
            ),
        ]

        # k=5だが予測は2頭のみ: 2頭とも3着以内なので precision = 2/2 = 1.0
        precision = MetricsCalculator.precision_at_k(results, k=5, use_ml=True)
        assert precision == 1.0
