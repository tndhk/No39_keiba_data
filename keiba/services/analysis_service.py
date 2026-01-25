"""分析サービス"""

from typing import Any

import numpy as np

from keiba.analyzers.factors import (
    CourseFitFactor,
    Last3FFactor,
    PastResultsFactor,
    PedigreeFactor,
    PopularityFactor,
    RunningStyleFactor,
    TimeIndexFactor,
)
from keiba.analyzers.score_calculator import ScoreCalculator
from keiba.ml.feature_builder import FeatureBuilder
from keiba.models import Horse, Race, RaceResult
from keiba.services.training_service import calculate_past_stats, get_horse_past_results


def analyze_race_scores(session, race: Race) -> list[dict]:
    """レースを分析してスコアを計算する

    Args:
        session: SQLAlchemyセッション
        race: レースオブジェクト

    Returns:
        スコアリスト（馬番順）
    """
    results = (
        session.query(RaceResult)
        .filter(RaceResult.race_id == race.id)
        .all()
    )

    if not results:
        return []

    calculator = ScoreCalculator()
    factors = {
        "past_results": PastResultsFactor(),
        "course_fit": CourseFitFactor(),
        "time_index": TimeIndexFactor(),
        "last_3f": Last3FFactor(),
        "popularity": PopularityFactor(),
    }

    scores = []
    for result in results:
        past_results = get_horse_past_results(session, result.horse_id)

        factor_scores = {
            "past_results": factors["past_results"].calculate(
                result.horse_id, past_results
            ),
            "course_fit": factors["course_fit"].calculate(
                result.horse_id,
                past_results,
                target_surface=race.surface,
                target_distance=race.distance,
            ),
            "time_index": factors["time_index"].calculate(
                result.horse_id,
                past_results,
                target_surface=race.surface,
                target_distance=race.distance,
            ),
            "last_3f": factors["last_3f"].calculate(result.horse_id, past_results),
            "popularity": factors["popularity"].calculate(
                result.horse_id,
                [],
                odds=result.odds,
                popularity=result.popularity,
            ),
        }

        total_score = calculator.calculate_total(factor_scores)

        scores.append(
            {
                "horse_number": result.horse_number,
                "horse_name": result.horse.name if result.horse else "不明",
                "total": total_score,
                "past_results": factor_scores["past_results"],
                "course_fit": factor_scores["course_fit"],
                "time_index": factor_scores["time_index"],
                "last_3f": factor_scores["last_3f"],
                "popularity": factor_scores["popularity"],
            }
        )

    scores.sort(key=lambda x: x["total"] or 0, reverse=True)
    return scores


def analyze_race_with_ml_scores(
    session, race: Race, predictor: Any, training_count: int
) -> list[dict]:
    """レースを分析してスコアとML予測を計算する

    Args:
        session: SQLAlchemyセッション
        race: レースオブジェクト
        predictor: Predictorインスタンス（Noneの場合はML予測スキップ）
        training_count: 学習データ数

    Returns:
        スコアリスト（ML予測順またはスコア順）
    """
    results = (
        session.query(RaceResult)
        .filter(RaceResult.race_id == race.id)
        .all()
    )

    if not results:
        return []

    calculator = ScoreCalculator()
    factors = {
        "past_results": PastResultsFactor(),
        "course_fit": CourseFitFactor(),
        "time_index": TimeIndexFactor(),
        "last_3f": Last3FFactor(),
        "popularity": PopularityFactor(),
        "pedigree": PedigreeFactor(),
        "running_style": RunningStyleFactor(),
    }
    feature_builder = FeatureBuilder()

    scores = []
    ml_features = []
    horse_ids = []

    for result in results:
        past_results = get_horse_past_results(session, result.horse_id)
        horse = session.get(Horse, result.horse_id)

        factor_scores = {
            "past_results": factors["past_results"].calculate(
                result.horse_id, past_results
            ),
            "course_fit": factors["course_fit"].calculate(
                result.horse_id,
                past_results,
                target_surface=race.surface,
                target_distance=race.distance,
            ),
            "time_index": factors["time_index"].calculate(
                result.horse_id,
                past_results,
                target_surface=race.surface,
                target_distance=race.distance,
            ),
            "last_3f": factors["last_3f"].calculate(result.horse_id, past_results),
            "popularity": factors["popularity"].calculate(
                result.horse_id,
                [],
                odds=result.odds,
                popularity=result.popularity,
            ),
            "pedigree": factors["pedigree"].calculate(
                result.horse_id, [],
                sire=horse.sire if horse else None,
                dam_sire=horse.dam_sire if horse else None,
                target_surface=race.surface,
                target_distance=race.distance,
            ),
            "running_style": factors["running_style"].calculate(
                result.horse_id, past_results,
                passing_order=result.passing_order,
                course=race.course,
                distance=race.distance,
            ),
        }

        total_score = calculator.calculate_total(factor_scores)

        if predictor:
            past_stats = calculate_past_stats(past_results, race.date)
            race_result_data = {
                "horse_id": result.horse_id,
                "odds": result.odds,
                "popularity": result.popularity,
                "weight": result.weight,
                "weight_diff": result.weight_diff,
                "age": result.age,
                "impost": result.impost,
                "horse_number": result.horse_number,
            }
            features = feature_builder.build_features(
                race_result=race_result_data,
                factor_scores=factor_scores,
                field_size=len(results),
                past_stats=past_stats,
            )
            feature_names = feature_builder.get_feature_names()
            ml_features.append([features[name] for name in feature_names])
            horse_ids.append(result.horse_id)

        scores.append(
            {
                "horse_id": result.horse_id,
                "horse_number": result.horse_number,
                "horse_name": result.horse.name if result.horse else "不明",
                "total": total_score,
                "past_results": factor_scores["past_results"],
                "course_fit": factor_scores["course_fit"],
                "time_index": factor_scores["time_index"],
                "last_3f": factor_scores["last_3f"],
                "popularity": factor_scores["popularity"],
                "probability": None,
                "ml_rank": None,
            }
        )

    if predictor and ml_features:
        X = np.array(ml_features)
        predictions = predictor.predict_with_ranking(X, horse_ids)

        pred_map = {p["horse_id"]: p for p in predictions}
        for score in scores:
            pred = pred_map.get(score["horse_id"])
            if pred:
                score["probability"] = pred["probability"]
                score["ml_rank"] = pred["rank"]

    if predictor:
        scores.sort(key=lambda x: x["ml_rank"] if x["ml_rank"] else 999)
    else:
        scores.sort(key=lambda x: x["total"] or 0, reverse=True)

    return scores
