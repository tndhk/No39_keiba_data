"""学習サービス"""

from datetime import date

from keiba.models import Horse, Race, RaceResult


def get_horse_past_results(session, horse_id: str) -> list[dict]:
    """馬の過去成績を取得する

    Args:
        session: SQLAlchemyセッション
        horse_id: 馬ID

    Returns:
        過去成績のリスト
    """
    from sqlalchemy import func

    past_results_query = (
        session.query(RaceResult, Race, func.count(RaceResult.id).over().label("total_runners"))
        .join(Race, RaceResult.race_id == Race.id)
        .filter(RaceResult.horse_id == horse_id)
        .order_by(Race.date.desc())
        .limit(20)
    )

    results = []
    for race_result, race_info, _ in past_results_query:
        total_runners = (
            session.query(RaceResult)
            .filter(RaceResult.race_id == race_info.id)
            .count()
        )

        results.append(
            {
                "horse_id": race_result.horse_id,
                "finish_position": race_result.finish_position,
                "total_runners": total_runners,
                "surface": race_info.surface,
                "distance": race_info.distance,
                "time": race_result.time,
                "last_3f": race_result.last_3f,
                "race_date": race_info.date,
            }
        )

    return results


def calculate_past_stats(past_results: list[dict], current_date: date) -> dict:
    """派生特徴量を計算する

    Args:
        past_results: 過去成績リスト
        current_date: 現在のレース日

    Returns:
        派生特徴量の辞書
    """
    if not past_results:
        return {
            "win_rate": None,
            "top3_rate": None,
            "avg_finish_position": None,
            "days_since_last_race": None,
        }

    total = len(past_results)
    wins = sum(1 for r in past_results if r.get("finish_position") == 1)
    top3 = sum(1 for r in past_results if r.get("finish_position", 99) <= 3)
    positions = [r.get("finish_position", 0) for r in past_results if r.get("finish_position", 0) > 0]

    days_since = None
    if past_results and past_results[0].get("race_date"):
        last_date = past_results[0]["race_date"]
        if hasattr(last_date, "date"):
            last_date = last_date.date()
        days_since = (current_date - last_date).days

    return {
        "win_rate": wins / total if total > 0 else None,
        "top3_rate": top3 / total if total > 0 else None,
        "avg_finish_position": sum(positions) / len(positions) if positions else None,
        "days_since_last_race": days_since,
    }


def build_training_data(session, target_date: date) -> tuple[list[dict], list[int]]:
    """ML学習用のデータを構築する

    Args:
        session: SQLAlchemyセッション
        target_date: 対象レース日（この日より前のデータを使用）

    Returns:
        (特徴量リスト, ラベルリスト)のタプル
    """
    from keiba.analyzers.factors import (
        CourseFitFactor,
        Last3FFactor,
        PastResultsFactor,
        PedigreeFactor,
        PopularityFactor,
        RunningStyleFactor,
        TimeIndexFactor,
    )
    from keiba.ml.feature_builder import FeatureBuilder

    past_races = (
        session.query(Race)
        .filter(Race.date < target_date)
        .order_by(Race.date.desc())
        .all()
    )

    if not past_races:
        return [], []

    feature_builder = FeatureBuilder()
    factors = {
        "past_results": PastResultsFactor(),
        "course_fit": CourseFitFactor(),
        "time_index": TimeIndexFactor(),
        "last_3f": Last3FFactor(),
        "popularity": PopularityFactor(),
        "pedigree": PedigreeFactor(),
        "running_style": RunningStyleFactor(),
    }

    features_list = []
    labels = []

    for race in past_races:
        results = (
            session.query(RaceResult)
            .filter(RaceResult.race_id == race.id)
            .all()
        )

        field_size = len(results)

        for result in results:
            if result.finish_position == 0:
                continue

            horse_past = get_horse_past_results(session, result.horse_id)
            horse = session.get(Horse, result.horse_id)

            factor_scores = {
                "past_results": factors["past_results"].calculate(
                    result.horse_id, horse_past
                ),
                "course_fit": factors["course_fit"].calculate(
                    result.horse_id, horse_past,
                    target_surface=race.surface, target_distance=race.distance
                ),
                "time_index": factors["time_index"].calculate(
                    result.horse_id, horse_past,
                    target_surface=race.surface, target_distance=race.distance
                ),
                "last_3f": factors["last_3f"].calculate(result.horse_id, horse_past),
                "popularity": factors["popularity"].calculate(
                    result.horse_id, [],
                    odds=result.odds, popularity=result.popularity
                ),
                "pedigree": factors["pedigree"].calculate(
                    result.horse_id, [],
                    sire=horse.sire if horse else None,
                    dam_sire=horse.dam_sire if horse else None,
                    target_surface=race.surface,
                    target_distance=race.distance,
                ),
                "running_style": factors["running_style"].calculate(
                    result.horse_id, horse_past,
                    passing_order=result.passing_order,
                    course=race.course,
                    distance=race.distance,
                ),
            }

            past_stats = calculate_past_stats(horse_past, race.date)

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
                field_size=field_size,
                past_stats=past_stats,
            )

            features_list.append(features)

            label = 1 if result.finish_position <= 3 else 0
            labels.append(label)

    return features_list, labels
