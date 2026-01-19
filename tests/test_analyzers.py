"""分析モジュール（analyzers）のテスト

TDDのREDフェーズ: まずテストを作成し、FAILを確認する。
"""

from abc import ABC
from datetime import date

import pytest

from keiba.analyzers.factors.base import BaseFactor


class TestBaseFactor:
    """BaseFactor基底クラスのテスト"""

    def test_is_abstract_class(self):
        """BaseFactorは抽象クラスである"""
        assert issubclass(BaseFactor, ABC)

    def test_has_name_property(self):
        """BaseFactorはname属性を持つ"""

        class ConcreteFactor(BaseFactor):
            name = "test_factor"

            def calculate(self, horse_id: str, race_results: list) -> float | None:
                return 50.0

        factor = ConcreteFactor()
        assert factor.name == "test_factor"

    def test_has_calculate_method(self):
        """BaseFactorはcalculateメソッドを持つ"""

        class ConcreteFactor(BaseFactor):
            name = "test_factor"

            def calculate(self, horse_id: str, race_results: list) -> float | None:
                return 75.5

        factor = ConcreteFactor()
        result = factor.calculate("horse123", [])
        assert result == 75.5

    def test_calculate_returns_none_for_no_data(self):
        """データがない場合Noneを返す"""

        class ConcreteFactor(BaseFactor):
            name = "test_factor"

            def calculate(self, horse_id: str, race_results: list) -> float | None:
                if not race_results:
                    return None
                return 50.0

        factor = ConcreteFactor()
        result = factor.calculate("horse123", [])
        assert result is None

    def test_cannot_instantiate_directly(self):
        """BaseFactorは直接インスタンス化できない"""
        with pytest.raises(TypeError):
            BaseFactor()


class TestPastResultsFactor:
    """PastResultsFactor（過去成績）のテスト"""

    @pytest.fixture
    def factor(self):
        from keiba.analyzers.factors.past_results import PastResultsFactor

        return PastResultsFactor()

    def test_name_is_past_results(self, factor):
        """nameは'past_results'である"""
        assert factor.name == "past_results"

    def test_relative_score_18_runners_3rd(self, factor):
        """18頭立て3着の相対着順スコアは89点"""
        # スコア = (出走頭数 - 着順 + 1) / 出走頭数 × 100
        # = (18 - 3 + 1) / 18 × 100 = 88.89
        score = factor._calculate_relative_score(
            finish_position=3, total_runners=18
        )
        assert round(score, 1) == 88.9

    def test_relative_score_5_runners_3rd(self, factor):
        """5頭立て3着の相対着順スコアは60点"""
        # = (5 - 3 + 1) / 5 × 100 = 60
        score = factor._calculate_relative_score(finish_position=3, total_runners=5)
        assert score == 60.0

    def test_relative_score_first_place(self, factor):
        """1着のスコアは常に100点"""
        score = factor._calculate_relative_score(finish_position=1, total_runners=10)
        assert score == 100.0

    def test_relative_score_last_place(self, factor):
        """最下位のスコア"""
        # = (10 - 10 + 1) / 10 × 100 = 10
        score = factor._calculate_relative_score(finish_position=10, total_runners=10)
        assert round(score, 1) == 10.0

    def test_calculate_with_recent_5_races(self, factor):
        """直近5走の加重平均を計算する"""
        # テストデータ: horse_idに対する過去成績
        race_results = [
            # 直近のレース（最新）
            {
                "horse_id": "horse123",
                "finish_position": 1,
                "total_runners": 10,
                "race_date": date(2024, 1, 5),
            },
            {
                "horse_id": "horse123",
                "finish_position": 2,
                "total_runners": 12,
                "race_date": date(2024, 1, 4),
            },
            {
                "horse_id": "horse123",
                "finish_position": 3,
                "total_runners": 15,
                "race_date": date(2024, 1, 3),
            },
            {
                "horse_id": "horse123",
                "finish_position": 5,
                "total_runners": 18,
                "race_date": date(2024, 1, 2),
            },
            {
                "horse_id": "horse123",
                "finish_position": 4,
                "total_runners": 10,
                "race_date": date(2024, 1, 1),
            },
        ]
        result = factor.calculate("horse123", race_results)
        assert result is not None
        assert 0 <= result <= 100

    def test_calculate_with_less_than_5_races(self, factor):
        """5走未満でも計算可能"""
        race_results = [
            {
                "horse_id": "horse123",
                "finish_position": 1,
                "total_runners": 10,
                "race_date": date(2024, 1, 1),
            },
            {
                "horse_id": "horse123",
                "finish_position": 2,
                "total_runners": 10,
                "race_date": date(2024, 1, 2),
            },
        ]
        result = factor.calculate("horse123", race_results)
        assert result is not None
        assert 0 <= result <= 100

    def test_calculate_with_no_races(self, factor):
        """出走履歴がない場合はNoneを返す"""
        result = factor.calculate("horse123", [])
        assert result is None

    def test_calculate_ignores_disqualified(self, factor):
        """中止・除外（finish_position=0やNone）は除外して計算"""
        race_results = [
            {
                "horse_id": "horse123",
                "finish_position": 1,
                "total_runners": 10,
                "race_date": date(2024, 1, 3),
            },
            {
                "horse_id": "horse123",
                "finish_position": 0,  # 中止
                "total_runners": 10,
                "race_date": date(2024, 1, 2),
            },
            {
                "horse_id": "horse123",
                "finish_position": None,  # 除外
                "total_runners": 10,
                "race_date": date(2024, 1, 1),
            },
        ]
        result = factor.calculate("horse123", race_results)
        # 有効なレースは1着のみ → 100点
        assert result == 100.0


class TestCourseFitFactor:
    """CourseFitFactor（コース適性）のテスト"""

    @pytest.fixture
    def factor(self):
        from keiba.analyzers.factors.course_fit import CourseFitFactor

        return CourseFitFactor()

    def test_name_is_course_fit(self, factor):
        """nameは'course_fit'である"""
        assert factor.name == "course_fit"

    def test_calculate_top3_rate(self, factor):
        """同条件での3着内率を計算する"""
        # 芝1600m での成績: 3戦2勝（3着以内2回）
        race_results = [
            {
                "horse_id": "horse123",
                "finish_position": 1,
                "surface": "芝",
                "distance": 1600,
                "race_date": date(2024, 1, 3),
            },
            {
                "horse_id": "horse123",
                "finish_position": 3,
                "surface": "芝",
                "distance": 1600,
                "race_date": date(2024, 1, 2),
            },
            {
                "horse_id": "horse123",
                "finish_position": 5,
                "surface": "芝",
                "distance": 1600,
                "race_date": date(2024, 1, 1),
            },
        ]
        # 同条件: 芝1600m → 3戦中2回が3着以内 = 66.7%
        result = factor.calculate(
            "horse123", race_results, target_surface="芝", target_distance=1600
        )
        assert result is not None
        assert round(result, 1) == 66.7

    def test_distance_band_short(self, factor):
        """距離帯の判定: 短距離（~1400m）"""
        assert factor._get_distance_band(1200) == "short"
        assert factor._get_distance_band(1400) == "short"

    def test_distance_band_mile(self, factor):
        """距離帯の判定: マイル（1401-1800m）"""
        assert factor._get_distance_band(1600) == "mile"
        assert factor._get_distance_band(1800) == "mile"

    def test_distance_band_middle(self, factor):
        """距離帯の判定: 中距離（1801-2200m）"""
        assert factor._get_distance_band(2000) == "middle"
        assert factor._get_distance_band(2200) == "middle"

    def test_distance_band_long(self, factor):
        """距離帯の判定: 長距離（2201m~）"""
        assert factor._get_distance_band(2400) == "long"
        assert factor._get_distance_band(3600) == "long"

    def test_calculate_with_no_matching_conditions(self, factor):
        """同条件のレースがない場合はNoneを返す"""
        race_results = [
            {
                "horse_id": "horse123",
                "finish_position": 1,
                "surface": "ダート",
                "distance": 1800,
                "race_date": date(2024, 1, 1),
            },
        ]
        # 芝1600mを検索 → ダート1800mしかない
        result = factor.calculate(
            "horse123", race_results, target_surface="芝", target_distance=1600
        )
        assert result is None


class TestTimeIndexFactor:
    """TimeIndexFactor（タイム指数）のテスト"""

    @pytest.fixture
    def factor(self):
        from keiba.analyzers.factors.time_index import TimeIndexFactor

        return TimeIndexFactor()

    def test_name_is_time_index(self, factor):
        """nameは'time_index'である"""
        assert factor.name == "time_index"

    def test_parse_time_string(self, factor):
        """タイム文字列を秒に変換"""
        assert factor._parse_time("1:33.5") == 93.5
        assert factor._parse_time("2:31.2") == 151.2

    def test_parse_time_seconds_only(self, factor):
        """秒のみのタイム文字列を変換"""
        assert factor._parse_time("59.8") == 59.8

    def test_calculate_index(self, factor):
        """タイム指数を計算（平均タイムとの比較）"""
        # 同条件での過去レース
        race_results = [
            {
                "horse_id": "horse123",
                "time": "1:33.5",
                "surface": "芝",
                "distance": 1600,
                "race_date": date(2024, 1, 3),
            },
            {
                "horse_id": "horse456",
                "time": "1:34.0",
                "surface": "芝",
                "distance": 1600,
                "race_date": date(2024, 1, 2),
            },
            {
                "horse_id": "horse789",
                "time": "1:33.0",
                "surface": "芝",
                "distance": 1600,
                "race_date": date(2024, 1, 1),
            },
        ]
        result = factor.calculate(
            "horse123", race_results, target_surface="芝", target_distance=1600
        )
        assert result is not None

    def test_calculate_returns_none_with_insufficient_data(self, factor):
        """同条件のレースが3件未満の場合はNoneを返す"""
        race_results = [
            {
                "horse_id": "horse123",
                "time": "1:33.5",
                "surface": "芝",
                "distance": 1600,
                "race_date": date(2024, 1, 1),
            },
        ]
        result = factor.calculate(
            "horse123", race_results, target_surface="芝", target_distance=1600
        )
        assert result is None


class TestLast3FFactor:
    """Last3FFactor（上がり3F）のテスト"""

    @pytest.fixture
    def factor(self):
        from keiba.analyzers.factors.last_3f import Last3FFactor

        return Last3FFactor()

    def test_name_is_last_3f(self, factor):
        """nameは'last_3f'である"""
        assert factor.name == "last_3f"

    def test_calculate_with_recent_last_3f(self, factor):
        """直近の上がり3Fからスコアを計算"""
        race_results = [
            {
                "horse_id": "horse123",
                "last_3f": 33.5,
                "race_date": date(2024, 1, 3),
            },
            {
                "horse_id": "horse123",
                "last_3f": 34.0,
                "race_date": date(2024, 1, 2),
            },
            {
                "horse_id": "horse123",
                "last_3f": 33.8,
                "race_date": date(2024, 1, 1),
            },
        ]
        result = factor.calculate("horse123", race_results)
        assert result is not None
        assert 0 <= result <= 100

    def test_calculate_returns_none_with_no_last_3f_data(self, factor):
        """上がり3Fデータがない場合はNoneを返す"""
        race_results = [
            {
                "horse_id": "horse123",
                "last_3f": None,
                "race_date": date(2024, 1, 1),
            },
        ]
        result = factor.calculate("horse123", race_results)
        assert result is None

    def test_faster_last_3f_scores_higher(self, factor):
        """上がり3Fが速いほど高スコア"""
        fast_results = [
            {"horse_id": "horse123", "last_3f": 32.0, "race_date": date(2024, 1, 1)}
        ]
        slow_results = [
            {"horse_id": "horse123", "last_3f": 38.0, "race_date": date(2024, 1, 1)}
        ]
        fast_score = factor.calculate("horse123", fast_results)
        slow_score = factor.calculate("horse123", slow_results)
        assert fast_score > slow_score


class TestPopularityFactor:
    """PopularityFactor（人気）のテスト"""

    @pytest.fixture
    def factor(self):
        from keiba.analyzers.factors.popularity import PopularityFactor

        return PopularityFactor()

    def test_name_is_popularity(self, factor):
        """nameは'popularity'である"""
        assert factor.name == "popularity"

    def test_calculate_from_odds(self, factor):
        """オッズから人気スコアを計算"""
        # 低オッズ（人気馬）= 高スコア
        result = factor.calculate("horse123", [], odds=2.5)
        assert result is not None
        assert result > 80

    def test_calculate_from_popularity_rank(self, factor):
        """人気順位からスコアを計算"""
        result = factor.calculate("horse123", [], popularity=1)
        assert result is not None
        assert result == 100  # 1番人気は100点

    def test_lower_popularity_scores_lower(self, factor):
        """人気が低いほど低スコア"""
        pop1 = factor.calculate("horse123", [], popularity=1)
        pop5 = factor.calculate("horse123", [], popularity=5)
        pop10 = factor.calculate("horse123", [], popularity=10)
        assert pop1 > pop5 > pop10

    def test_returns_none_with_no_odds_or_popularity(self, factor):
        """オッズも人気も指定されていない場合はNoneを返す"""
        result = factor.calculate("horse123", [])
        assert result is None


class TestScoreCalculator:
    """ScoreCalculator（重み付きスコア計算）のテスト"""

    @pytest.fixture
    def calculator(self):
        from keiba.analyzers.score_calculator import ScoreCalculator

        return ScoreCalculator()

    def test_calculate_total_score(self, calculator):
        """重み付き合計スコアを計算する"""
        factor_scores = {
            "past_results": 80.0,
            "course_fit": 70.0,
            "time_index": 85.0,
            "last_3f": 75.0,
            "popularity": 90.0,
        }
        result = calculator.calculate_total(factor_scores)
        # 80*0.25 + 70*0.20 + 85*0.20 + 75*0.20 + 90*0.15
        # = 20 + 14 + 17 + 15 + 13.5 = 79.5
        assert result is not None
        assert round(result, 1) == 79.5

    def test_handles_missing_factors(self, calculator):
        """一部のFactorがNoneの場合は残りで正規化して計算"""
        factor_scores = {
            "past_results": 80.0,
            "course_fit": None,  # データなし
            "time_index": 85.0,
            "last_3f": None,  # データなし
            "popularity": 90.0,
        }
        result = calculator.calculate_total(factor_scores)
        assert result is not None
        # past_results: 25%, time_index: 20%, popularity: 15% = 60%
        # 正規化: 25/60, 20/60, 15/60
        # 80*(25/60) + 85*(20/60) + 90*(15/60)
        # = 80*0.417 + 85*0.333 + 90*0.25
        # = 33.3 + 28.3 + 22.5 = 84.2

    def test_returns_none_if_all_factors_none(self, calculator):
        """全てのFactorがNoneの場合はNoneを返す"""
        factor_scores = {
            "past_results": None,
            "course_fit": None,
            "time_index": None,
            "last_3f": None,
            "popularity": None,
        }
        result = calculator.calculate_total(factor_scores)
        assert result is None

    def test_get_weights(self, calculator):
        """重み設定を取得できる"""
        weights = calculator.get_weights()
        assert weights["past_results"] == 0.25
        assert weights["course_fit"] == 0.20
        assert weights["time_index"] == 0.20
        assert weights["last_3f"] == 0.20
        assert weights["popularity"] == 0.15


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
        ]
        for factor in required_factors:
            assert factor in FACTOR_WEIGHTS
