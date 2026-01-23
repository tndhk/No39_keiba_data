"""ファクター計算の一元管理モジュール

キャッシュ付きファクター計算を提供する。
"""

from dataclasses import dataclass, field
from typing import Any, Callable

from keiba.analyzers.factors import (
    CourseFitFactor,
    Last3FFactor,
    PastResultsFactor,
    PedigreeFactor,
    PopularityFactor,
    RunningStyleFactor,
    TimeIndexFactor,
)
from keiba.backtest.cache import FactorCache
from keiba.models import Horse


def _convert_to_tuple(items: list[dict]) -> tuple[tuple[tuple[str, Any], ...], ...]:
    """listのdictをtupleに変換してハッシュ可能にする"""
    return tuple(tuple(sorted(d.items())) for d in items)


@dataclass(frozen=True)
class FactorCalculationContext:
    """ファクター計算に必要なコンテキスト情報（immutable）

    Attributes:
        horse_id: 馬ID
        past_results: 過去成績のリスト（frozenのため内部でtupleに変換）
        past_race_ids: 過去レースIDのタプル
        horse: 馬情報（血統情報取得用）
        race_surface: レース馬場（turf/dirt）
        race_distance: レース距離
        race_venue: 開催場所
        odds: オッズ
        popularity: 人気順
        passing_order: 通過順位
    """

    horse_id: str
    past_results: list[dict] = field(default_factory=list)
    past_race_ids: list[str] = field(default_factory=list)
    horse: Horse | None = None
    race_surface: str = ""
    race_distance: int = 0
    race_venue: str = ""
    odds: float | None = None
    popularity: int | None = None
    passing_order: str | None = None

    def get_past_race_ids_list(self) -> list[str]:
        """キャッシュキー生成用に過去レースIDのリストを返す"""
        return list(self.past_race_ids)


class CachedFactorCalculator:
    """キャッシュ付きファクター計算を一元管理

    既存のFactorCacheを注入して使用する。
    7つのファクター（past_results, course_fit, time_index, last_3f,
    popularity, pedigree, running_style）の計算を提供する。

    Attributes:
        _cache: FactorCacheインスタンス
        _factors: ファクター計算クラスの辞書
    """

    def __init__(self, factor_cache: FactorCache):
        """既存のFactorCacheを注入

        Args:
            factor_cache: FactorCacheインスタンス
        """
        self._cache = factor_cache
        self._factors = {
            "past_results": PastResultsFactor(),
            "course_fit": CourseFitFactor(),
            "time_index": TimeIndexFactor(),
            "last_3f": Last3FFactor(),
            "popularity": PopularityFactor(),
            "pedigree": PedigreeFactor(),
            "running_style": RunningStyleFactor(),
        }

    def calculate_all(
        self, context: FactorCalculationContext
    ) -> dict[str, float | None]:
        """全ファクターを計算してスコア辞書を返す

        Args:
            context: ファクター計算コンテキスト

        Returns:
            ファクター名をキー、スコアを値とする辞書
        """
        scores: dict[str, float | None] = {}
        past_race_ids = context.get_past_race_ids_list()

        # past_results ファクター
        scores["past_results"] = self._calc_with_cache(
            factor_name="past_results",
            context=context,
            extra_params={},
            calc_fn=lambda: self._factors["past_results"].calculate(
                context.horse_id, context.past_results
            ),
            past_race_ids=past_race_ids,
        )

        # course_fit ファクター
        scores["course_fit"] = self._calc_with_cache(
            factor_name="course_fit",
            context=context,
            extra_params={
                "target_surface": context.race_surface,
                "target_distance": context.race_distance,
            },
            calc_fn=lambda: self._factors["course_fit"].calculate(
                context.horse_id,
                context.past_results,
                target_surface=context.race_surface,
                target_distance=context.race_distance,
            ),
            past_race_ids=past_race_ids,
        )

        # time_index ファクター
        scores["time_index"] = self._calc_with_cache(
            factor_name="time_index",
            context=context,
            extra_params={
                "target_surface": context.race_surface,
                "target_distance": context.race_distance,
            },
            calc_fn=lambda: self._factors["time_index"].calculate(
                context.horse_id,
                context.past_results,
                target_surface=context.race_surface,
                target_distance=context.race_distance,
            ),
            past_race_ids=past_race_ids,
        )

        # last_3f ファクター
        scores["last_3f"] = self._calc_with_cache(
            factor_name="last_3f",
            context=context,
            extra_params={},
            calc_fn=lambda: self._factors["last_3f"].calculate(
                context.horse_id, context.past_results
            ),
            past_race_ids=past_race_ids,
        )

        # popularity ファクター（キャッシュ対象外：リアルタイムデータ依存）
        scores["popularity"] = self._factors["popularity"].calculate(
            context.horse_id,
            [],
            odds=context.odds,
            popularity=context.popularity,
        )

        # pedigree ファクター
        sire = context.horse.sire if context.horse else None
        dam_sire = context.horse.dam_sire if context.horse else None
        scores["pedigree"] = self._calc_with_cache(
            factor_name="pedigree",
            context=context,
            extra_params={
                "sire": sire,
                "dam_sire": dam_sire,
                "target_surface": context.race_surface,
                "target_distance": context.race_distance,
            },
            calc_fn=lambda: self._factors["pedigree"].calculate(
                context.horse_id,
                [],
                sire=sire,
                dam_sire=dam_sire,
                target_surface=context.race_surface,
                target_distance=context.race_distance,
            ),
            past_race_ids=past_race_ids,
        )

        # running_style ファクター
        scores["running_style"] = self._calc_with_cache(
            factor_name="running_style",
            context=context,
            extra_params={
                "passing_order": context.passing_order,
                "course": context.race_venue,
                "distance": context.race_distance,
            },
            calc_fn=lambda: self._factors["running_style"].calculate(
                context.horse_id,
                context.past_results,
                passing_order=context.passing_order,
                course=context.race_venue,
                distance=context.race_distance,
            ),
            past_race_ids=past_race_ids,
        )

        return scores

    def _calc_with_cache(
        self,
        factor_name: str,
        context: FactorCalculationContext,
        extra_params: dict,
        calc_fn: Callable[[], float | None],
        past_race_ids: list[str],
    ) -> float | None:
        """キャッシュ付き計算の共通処理

        Args:
            factor_name: ファクター名
            context: 計算コンテキスト
            extra_params: 追加パラメータ（キャッシュキー生成用）
            calc_fn: 計算関数
            past_race_ids: 過去レースIDリスト

        Returns:
            計算結果（キャッシュヒット時はキャッシュ値）
        """
        # キャッシュキー生成
        cache_key = FactorCache._make_key(
            factor_name=factor_name,
            horse_id=context.horse_id,
            past_race_ids=past_race_ids,
            **extra_params,
        )

        # キャッシュチェック
        hit, cached_value = self._cache.get(cache_key)
        if hit:
            return cached_value

        # ミス時は計算してキャッシュに保存
        # Noneの場合もキャッシュに保存する（重複計算回避のため）
        value = calc_fn()
        self._cache.set(cache_key, value)

        return value
