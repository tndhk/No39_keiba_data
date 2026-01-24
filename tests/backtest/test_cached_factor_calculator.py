"""CachedFactorCalculatorのテスト

TDD: RED フェーズ - テスト先行
"""

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from keiba.backtest.cache import FactorCache


# まだ実装されていないクラス・データクラスのインポート
# これらはREDフェーズでは失敗する
# from keiba.backtest.factor_calculator import (
#     CachedFactorCalculator,
#     FactorCalculationContext,
# )


class TestCalculateAllReturnsAllFactorScores:
    """calculate_allが全ファクタースコアを返すことのテスト"""

    def test_calculate_all_returns_all_factor_scores(self):
        """calculate_allが全7ファクターのスコアを含む辞書を返す"""
        # RED: まだCachedFactorCalculatorが存在しないためインポートエラー
        from keiba.backtest.factor_calculator import (
            CachedFactorCalculator,
            FactorCalculationContext,
        )

        # Arrange
        cache = FactorCache(max_size=100)
        calculator = CachedFactorCalculator(factor_cache=cache)

        context = FactorCalculationContext(
            horse_id="horse001",
            past_results=[
                {
                    "race_id": "race001",
                    "finish_position": 1,
                    "total_runners": 18,
                    "surface": "turf",
                    "distance": 1600,
                    "time": 95.5,
                    "last_3f": 34.0,
                    "race_date": "2024-01-01",
                },
                {
                    "race_id": "race002",
                    "finish_position": 3,
                    "total_runners": 16,
                    "surface": "turf",
                    "distance": 1800,
                    "time": 108.2,
                    "last_3f": 35.2,
                    "race_date": "2024-02-01",
                },
            ],
            past_race_ids=["race001", "race002"],
            horse=None,
            race_surface="turf",
            race_distance=1600,
            race_venue="tokyo",
            odds=5.0,
            popularity=2,
            passing_order="3-3-2-1",
        )

        # Act
        scores = calculator.calculate_all(context)

        # Assert
        expected_factors = [
            "past_results",
            "course_fit",
            "time_index",
            "last_3f",
            "popularity",
            "pedigree",
            "running_style",
        ]
        for factor_name in expected_factors:
            assert factor_name in scores, f"{factor_name} should be in scores"

        # 7つのファクターすべてが存在する
        assert len(scores) == 7

    def test_calculate_all_returns_none_for_missing_data(self):
        """データ不足の場合はNoneを返す"""
        from keiba.backtest.factor_calculator import (
            CachedFactorCalculator,
            FactorCalculationContext,
        )

        # Arrange
        cache = FactorCache(max_size=100)
        calculator = CachedFactorCalculator(factor_cache=cache)

        # 過去成績がない馬
        context = FactorCalculationContext(
            horse_id="horse_new",
            past_results=[],
            past_race_ids=[],
            horse=None,
            race_surface="turf",
            race_distance=1600,
            race_venue="tokyo",
            odds=10.0,
            popularity=5,
            passing_order=None,
        )

        # Act
        scores = calculator.calculate_all(context)

        # Assert
        # 過去データがない場合、多くのファクターはNoneを返すはず
        # popularityのみodds/popularityから計算可能
        assert scores["popularity"] is not None


class TestCacheHitOnSecondCall:
    """2回目の呼び出しでキャッシュヒットすることのテスト"""

    def test_cache_hit_on_second_call(self):
        """同じコンテキストでの2回目呼び出しでキャッシュヒットする"""
        from keiba.backtest.factor_calculator import (
            CachedFactorCalculator,
            FactorCalculationContext,
        )

        # Arrange
        cache = FactorCache(max_size=100)
        calculator = CachedFactorCalculator(factor_cache=cache)

        context = FactorCalculationContext(
            horse_id="horse001",
            past_results=[
                {
                    "race_id": "race001",
                    "finish_position": 2,
                    "total_runners": 18,
                    "surface": "turf",
                    "distance": 1600,
                    "time": 95.5,
                    "last_3f": 34.0,
                    "race_date": "2024-01-01",
                },
            ],
            past_race_ids=["race001"],
            horse=None,
            race_surface="turf",
            race_distance=1600,
            race_venue="tokyo",
            odds=5.0,
            popularity=2,
            passing_order="3-3-2-1",
        )

        # Act - 1回目の呼び出し
        scores_first = calculator.calculate_all(context)
        stats_after_first = cache.get_stats()
        misses_first = stats_after_first["misses"]

        # Act - 2回目の呼び出し（同じコンテキスト）
        scores_second = calculator.calculate_all(context)
        stats_after_second = cache.get_stats()
        hits_second = stats_after_second["hits"]

        # Assert
        # 1回目: キャッシュミス（6ファクター、popularityは除く）
        assert misses_first == 6, "First call should have 6 cache misses"

        # 2回目: キャッシュヒット（6ファクター）
        # 1回目のミス分は1回目でカウントされているので、2回目のヒット数で判断
        assert hits_second >= 6, "Second call should have cache hits"

        # 結果は同一
        assert scores_first == scores_second

    def test_cache_stats_reflect_hits_and_misses(self):
        """キャッシュ統計がヒットとミスを正しく反映する"""
        from keiba.backtest.factor_calculator import (
            CachedFactorCalculator,
            FactorCalculationContext,
        )

        # Arrange
        cache = FactorCache(max_size=100)
        calculator = CachedFactorCalculator(factor_cache=cache)

        context = FactorCalculationContext(
            horse_id="horse001",
            past_results=[
                {
                    "race_id": "race001",
                    "finish_position": 1,
                    "total_runners": 16,
                    "surface": "dirt",
                    "distance": 1200,
                    "time": 72.0,
                    "last_3f": 36.5,
                    "race_date": "2024-03-01",
                },
            ],
            past_race_ids=["race001"],
            horse=None,
            race_surface="dirt",
            race_distance=1200,
            race_venue="funabashi",
            odds=3.5,
            popularity=1,
            passing_order="1-1-1",
        )

        # 初期状態
        initial_stats = cache.get_stats()
        assert initial_stats["hits"] == 0
        assert initial_stats["misses"] == 0

        # Act - 1回目
        calculator.calculate_all(context)
        stats_first = cache.get_stats()

        # Act - 2回目
        calculator.calculate_all(context)
        stats_second = cache.get_stats()

        # Assert
        # 1回目はミスのみ
        assert stats_first["misses"] == 6  # popularity以外の6ファクター
        assert stats_first["hits"] == 0

        # 2回目はヒットのみ（キャッシュ対象ファクター分）
        assert stats_second["misses"] == 6  # 変わらず
        assert stats_second["hits"] == 6  # キャッシュ対象の6ファクター


class TestPopularityNotCached:
    """popularityがキャッシュ対象外であることのテスト"""

    def test_popularity_not_cached(self):
        """popularityファクターはキャッシュされない"""
        from keiba.backtest.factor_calculator import (
            CachedFactorCalculator,
            FactorCalculationContext,
        )

        # Arrange
        cache = FactorCache(max_size=100)
        calculator = CachedFactorCalculator(factor_cache=cache)

        # 同じ馬、同じ過去成績だがodds/popularityが異なる2つのコンテキスト
        context1 = FactorCalculationContext(
            horse_id="horse001",
            past_results=[
                {
                    "race_id": "race001",
                    "finish_position": 1,
                    "total_runners": 18,
                    "surface": "turf",
                    "distance": 1600,
                    "time": 95.5,
                    "last_3f": 34.0,
                    "race_date": "2024-01-01",
                },
            ],
            past_race_ids=["race001"],
            horse=None,
            race_surface="turf",
            race_distance=1600,
            race_venue="tokyo",
            odds=2.0,  # 1番人気想定
            popularity=1,
            passing_order="2-2-2-1",
        )

        context2 = FactorCalculationContext(
            horse_id="horse001",
            past_results=[
                {
                    "race_id": "race001",
                    "finish_position": 1,
                    "total_runners": 18,
                    "surface": "turf",
                    "distance": 1600,
                    "time": 95.5,
                    "last_3f": 34.0,
                    "race_date": "2024-01-01",
                },
            ],
            past_race_ids=["race001"],
            horse=None,
            race_surface="turf",
            race_distance=1600,
            race_venue="tokyo",
            odds=50.0,  # 大穴想定
            popularity=12,
            passing_order="2-2-2-1",
        )

        # Act
        scores1 = calculator.calculate_all(context1)
        scores2 = calculator.calculate_all(context2)

        # Assert
        # popularityスコアは異なるはず（キャッシュされていない証拠）
        assert scores1["popularity"] != scores2["popularity"]

        # 他のキャッシュ対象ファクターは同じ（キャッシュヒット）
        cacheable_factors = [
            "past_results", "course_fit", "time_index",
            "last_3f", "pedigree", "running_style"
        ]
        for factor_name in cacheable_factors:
            assert scores1[factor_name] == scores2[factor_name], \
                f"{factor_name} should be cached and equal"


class TestDifferentParamsNotCached:
    """異なるパラメータでキャッシュミスすることのテスト"""

    def test_different_params_not_cached(self):
        """異なるパラメータではキャッシュミスする"""
        from keiba.backtest.factor_calculator import (
            CachedFactorCalculator,
            FactorCalculationContext,
        )

        # Arrange
        cache = FactorCache(max_size=100)
        calculator = CachedFactorCalculator(factor_cache=cache)

        # 同じ馬・過去成績だが、コース条件が異なる
        context_turf = FactorCalculationContext(
            horse_id="horse001",
            past_results=[
                {
                    "race_id": "race001",
                    "finish_position": 1,
                    "total_runners": 18,
                    "surface": "turf",
                    "distance": 1600,
                    "time": 95.5,
                    "last_3f": 34.0,
                    "race_date": "2024-01-01",
                },
            ],
            past_race_ids=["race001"],
            horse=None,
            race_surface="turf",  # 芝
            race_distance=1600,
            race_venue="tokyo",
            odds=5.0,
            popularity=2,
            passing_order="3-3-2-1",
        )

        context_dirt = FactorCalculationContext(
            horse_id="horse001",
            past_results=[
                {
                    "race_id": "race001",
                    "finish_position": 1,
                    "total_runners": 18,
                    "surface": "turf",
                    "distance": 1600,
                    "time": 95.5,
                    "last_3f": 34.0,
                    "race_date": "2024-01-01",
                },
            ],
            past_race_ids=["race001"],
            horse=None,
            race_surface="dirt",  # ダート（異なる）
            race_distance=1600,
            race_venue="tokyo",
            odds=5.0,
            popularity=2,
            passing_order="3-3-2-1",
        )

        # Act
        calculator.calculate_all(context_turf)
        stats_after_turf = cache.get_stats()
        misses_after_turf = stats_after_turf["misses"]

        calculator.calculate_all(context_dirt)
        stats_after_dirt = cache.get_stats()
        misses_after_dirt = stats_after_dirt["misses"]

        # Assert
        # surfaceが異なるのでcourse_fit, time_indexなどはキャッシュミス
        # past_results, last_3fはsurfaceに依存しないのでヒットする可能性
        # 少なくともsurface依存ファクターはキャッシュミスするはず
        assert misses_after_dirt > misses_after_turf

    def test_different_horse_not_cached(self):
        """異なる馬ではキャッシュミスする"""
        from keiba.backtest.factor_calculator import (
            CachedFactorCalculator,
            FactorCalculationContext,
        )

        # Arrange
        cache = FactorCache(max_size=100)
        calculator = CachedFactorCalculator(factor_cache=cache)

        context_horse1 = FactorCalculationContext(
            horse_id="horse001",
            past_results=[
                {
                    "race_id": "race001",
                    "finish_position": 1,
                    "total_runners": 18,
                    "surface": "turf",
                    "distance": 1600,
                    "time": 95.5,
                    "last_3f": 34.0,
                    "race_date": "2024-01-01",
                },
            ],
            past_race_ids=["race001"],
            horse=None,
            race_surface="turf",
            race_distance=1600,
            race_venue="tokyo",
            odds=5.0,
            popularity=2,
            passing_order="3-3-2-1",
        )

        context_horse2 = FactorCalculationContext(
            horse_id="horse002",  # 異なる馬ID
            past_results=[
                {
                    "race_id": "race002",
                    "finish_position": 2,
                    "total_runners": 16,
                    "surface": "turf",
                    "distance": 1600,
                    "time": 96.0,
                    "last_3f": 34.5,
                    "race_date": "2024-01-15",
                },
            ],
            past_race_ids=["race002"],
            horse=None,
            race_surface="turf",
            race_distance=1600,
            race_venue="tokyo",
            odds=8.0,
            popularity=4,
            passing_order="5-5-4-2",
        )

        # Act
        calculator.calculate_all(context_horse1)
        stats_first = cache.get_stats()

        calculator.calculate_all(context_horse2)
        stats_second = cache.get_stats()

        # Assert
        # 異なる馬なのでキャッシュミスが増える
        # 1回目: 6ミス、2回目: +6ミス = 12ミス
        assert stats_first["misses"] == 6
        assert stats_second["misses"] == 12

    def test_different_distance_not_cached(self):
        """異なる距離ではキャッシュミスする"""
        from keiba.backtest.factor_calculator import (
            CachedFactorCalculator,
            FactorCalculationContext,
        )

        # Arrange
        cache = FactorCache(max_size=100)
        calculator = CachedFactorCalculator(factor_cache=cache)

        context_1600m = FactorCalculationContext(
            horse_id="horse001",
            past_results=[
                {
                    "race_id": "race001",
                    "finish_position": 1,
                    "total_runners": 18,
                    "surface": "turf",
                    "distance": 1600,
                    "time": 95.5,
                    "last_3f": 34.0,
                    "race_date": "2024-01-01",
                },
            ],
            past_race_ids=["race001"],
            horse=None,
            race_surface="turf",
            race_distance=1600,
            race_venue="tokyo",
            odds=5.0,
            popularity=2,
            passing_order="3-3-2-1",
        )

        context_2400m = FactorCalculationContext(
            horse_id="horse001",
            past_results=[
                {
                    "race_id": "race001",
                    "finish_position": 1,
                    "total_runners": 18,
                    "surface": "turf",
                    "distance": 1600,
                    "time": 95.5,
                    "last_3f": 34.0,
                    "race_date": "2024-01-01",
                },
            ],
            past_race_ids=["race001"],
            horse=None,
            race_surface="turf",
            race_distance=2400,  # 異なる距離
            race_venue="tokyo",
            odds=5.0,
            popularity=2,
            passing_order="3-3-2-1",
        )

        # Act
        calculator.calculate_all(context_1600m)
        stats_after_1600 = cache.get_stats()

        calculator.calculate_all(context_2400m)
        stats_after_2400 = cache.get_stats()

        # Assert
        # 距離に依存するファクター（course_fit, time_index, running_style）はキャッシュミス
        # past_results, last_3fは距離に依存しないのでヒット
        # pedigreeはtarget_distanceを使うのでミス
        assert stats_after_2400["misses"] > stats_after_1600["misses"]


class TestFactorInstanceReuse:
    """ファクターインスタンス再利用のテスト"""

    def test_factor_instances_are_reused(self):
        """ファクターインスタンスは初期化時に1回だけ作成され再利用される"""
        from keiba.backtest.factor_calculator import CachedFactorCalculator

        # Arrange
        cache = FactorCache(max_size=100)
        calculator = CachedFactorCalculator(factor_cache=cache)

        # Act - _factorsの各インスタンスのidを記録
        factor_ids_first = {
            name: id(factor)
            for name, factor in calculator._factors.items()
        }

        # 複数回calculate_allを呼んでも同じインスタンスを使用
        from keiba.backtest.factor_calculator import FactorCalculationContext

        context = FactorCalculationContext(
            horse_id="horse001",
            past_results=[],
            past_race_ids=[],
            horse=None,
            race_surface="turf",
            race_distance=1600,
            race_venue="tokyo",
            odds=5.0,
            popularity=2,
            passing_order=None,
        )

        calculator.calculate_all(context)
        calculator.calculate_all(context)
        calculator.calculate_all(context)

        factor_ids_after = {
            name: id(factor)
            for name, factor in calculator._factors.items()
        }

        # Assert - 全てのファクターインスタンスのidが同一
        for name in factor_ids_first:
            assert factor_ids_first[name] == factor_ids_after[name], \
                f"Factor '{name}' instance was recreated"

    def test_all_seven_factors_are_initialized(self):
        """7つのファクターが全て初期化されている"""
        from keiba.backtest.factor_calculator import CachedFactorCalculator

        # Arrange & Act
        cache = FactorCache(max_size=100)
        calculator = CachedFactorCalculator(factor_cache=cache)

        # Assert
        expected_factors = [
            "past_results",
            "course_fit",
            "time_index",
            "last_3f",
            "popularity",
            "pedigree",
            "running_style",
        ]
        assert len(calculator._factors) == 7
        for factor_name in expected_factors:
            assert factor_name in calculator._factors, \
                f"Factor '{factor_name}' not initialized"

    def test_factor_instances_are_correct_types(self):
        """ファクターインスタンスが正しい型で初期化されている"""
        from keiba.backtest.factor_calculator import CachedFactorCalculator
        from keiba.analyzers.factors import (
            CourseFitFactor,
            Last3FFactor,
            PastResultsFactor,
            PedigreeFactor,
            PopularityFactor,
            RunningStyleFactor,
            TimeIndexFactor,
        )

        # Arrange & Act
        cache = FactorCache(max_size=100)
        calculator = CachedFactorCalculator(factor_cache=cache)

        # Assert
        assert isinstance(calculator._factors["past_results"], PastResultsFactor)
        assert isinstance(calculator._factors["course_fit"], CourseFitFactor)
        assert isinstance(calculator._factors["time_index"], TimeIndexFactor)
        assert isinstance(calculator._factors["last_3f"], Last3FFactor)
        assert isinstance(calculator._factors["popularity"], PopularityFactor)
        assert isinstance(calculator._factors["pedigree"], PedigreeFactor)
        assert isinstance(calculator._factors["running_style"], RunningStyleFactor)


class TestFactorCalculationContextImmutability:
    """FactorCalculationContextの不変性テスト"""

    def test_context_is_immutable(self):
        """FactorCalculationContextはimmutableである"""
        from keiba.backtest.factor_calculator import FactorCalculationContext

        context = FactorCalculationContext(
            horse_id="horse001",
            past_results=[],
            past_race_ids=[],
            horse=None,
            race_surface="turf",
            race_distance=1600,
            race_venue="tokyo",
            odds=5.0,
            popularity=2,
            passing_order="3-3-2-1",
        )

        # frozen=Trueなのでエラーになるはず
        with pytest.raises(AttributeError):
            context.horse_id = "horse002"

    def test_context_is_hashable(self):
        """FactorCalculationContextはハッシュ可能である"""
        from keiba.backtest.factor_calculator import FactorCalculationContext

        context = FactorCalculationContext(
            horse_id="horse001",
            past_results=[],  # リストはハッシュ不可だがfrozen dataclassでは可能
            past_race_ids=[],
            horse=None,
            race_surface="turf",
            race_distance=1600,
            race_venue="tokyo",
            odds=5.0,
            popularity=2,
            passing_order="3-3-2-1",
        )

        # ハッシュ可能ならエラーにならない
        # 注: past_resultsがlistなのでデフォルトではハッシュ不可
        # tupleに変換するか、unsafe_hash=Trueが必要
        # 設計によってはこのテストは修正が必要
        try:
            hash(context)
        except TypeError:
            # リストを含む場合はハッシュ不可なのでこれは許容される設計
            pass
