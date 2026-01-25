"""レース分析コマンド"""

from datetime import date

import click
import numpy as np
from sqlalchemy import select

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
from keiba.db import get_engine, get_session
from keiba.ml.feature_builder import FeatureBuilder
from keiba.ml.predictor import Predictor
from keiba.ml.trainer import Trainer
from keiba.models import Horse, Race, RaceResult


@click.command()
@click.option("--db", required=True, type=click.Path(), help="DBファイルパス")
@click.option("--date", required=True, type=str, help="レース日付（YYYY-MM-DD）")
@click.option("--venue", required=True, type=str, help="競馬場名（例: 中山）")
@click.option("--race", type=int, default=None, help="レース番号（省略時は全レース）")
@click.option("--no-predict", is_flag=True, default=False, help="ML予測をスキップ")
def analyze(db: str, date: str, venue: str, race: int | None, no_predict: bool):
    """指定した日付・競馬場のレースを分析してスコアを表示"""
    from datetime import datetime as dt

    # 日付をパース
    try:
        race_date = dt.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        click.echo(f"日付形式が不正です: {date}（YYYY-MM-DD形式で指定してください）")
        return

    click.echo(f"分析開始: {race_date} {venue}")
    click.echo(f"データベース: {db}")

    # DBに接続
    engine = get_engine(db)

    with get_session(engine) as session:
        # ML予測の準備（--no-predictでない場合）
        predictor = None
        training_count = 0

        if not no_predict:
            click.echo("")
            click.echo("ML予測モデルを学習中...")

            features_list, labels = _build_training_data(session, race_date)
            training_count = len(features_list)

            if training_count >= 100:
                feature_builder = FeatureBuilder()
                feature_names = feature_builder.get_feature_names()

                X = np.array([[f[name] for name in feature_names] for f in features_list])
                y = np.array(labels)

                trainer = Trainer()
                metrics = trainer.train_with_cv(X, y, n_splits=5)

                click.echo(f"学習完了: {training_count}サンプル")
                if metrics['precision_at_1']:
                    click.echo(f"  Precision@1: {metrics['precision_at_1']:.1%}")
                else:
                    click.echo("  Precision@1: N/A")
                if metrics['precision_at_3']:
                    click.echo(f"  Precision@3: {metrics['precision_at_3']:.1%}")
                else:
                    click.echo("  Precision@3: N/A")

                predictor = Predictor(trainer.model)
            else:
                click.echo(f"学習データ不足（{training_count}サンプル）: ML予測をスキップ")

        click.echo("")

        # 対象レースを取得
        stmt = select(Race).where(Race.date == race_date, Race.course == venue)
        if race is not None:
            stmt = stmt.where(Race.race_number == race)
        stmt = stmt.order_by(Race.race_number)

        races = session.execute(stmt).scalars().all()

        if not races:
            click.echo(f"レースが見つかりません: {race_date} {venue}")
            return

        # 各レースを分析
        for target_race in races:
            _analyze_race_with_ml(session, target_race, predictor, training_count)


def _analyze_race(session, race: Race) -> None:
    """レースを分析してスコアを表示する

    Args:
        session: SQLAlchemyセッション
        race: レースオブジェクト
    """
    click.echo("=" * 70)
    click.echo(f"{race.date} {race.course} {race.race_number}R {race.name} {race.surface}{race.distance}m")
    click.echo("=" * 70)

    # レース結果を取得
    results = (
        session.query(RaceResult)
        .filter(RaceResult.race_id == race.id)
        .all()
    )

    if not results:
        click.echo("出走馬情報がありません")
        click.echo("")
        return

    # 各馬のスコアを計算
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
        # 過去成績を取得
        past_results = _get_horse_past_results(session, result.horse_id)

        # 各Factorスコアを計算
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

    # スコアでソート（高い順）
    scores.sort(key=lambda x: x["total"] or 0, reverse=True)

    # 表形式で出力
    _print_score_table(scores)
    click.echo("")


def _get_horse_past_results(session, horse_id: str) -> list[dict]:
    """馬の過去成績を取得する

    Args:
        session: SQLAlchemyセッション
        horse_id: 馬ID

    Returns:
        過去成績のリスト
    """
    from sqlalchemy import func

    # 過去のレース結果を取得
    past_results_query = (
        session.query(RaceResult, Race, func.count(RaceResult.id).over().label("total_runners"))
        .join(Race, RaceResult.race_id == Race.id)
        .filter(RaceResult.horse_id == horse_id)
        .order_by(Race.date.desc())
        .limit(20)
    )

    results = []
    for race_result, race_info, _ in past_results_query:
        # 同じレースの出走頭数を取得
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


def _build_training_data(session, target_date: date) -> tuple[list[dict], list[int]]:
    """ML学習用のデータを構築する

    Args:
        session: SQLAlchemyセッション
        target_date: 対象レース日（この日より前のデータを使用）

    Returns:
        (特徴量リスト, ラベルリスト)のタプル
    """
    # 対象日より前のレースを取得
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
            # 中止（finish_position=0）は除外
            if result.finish_position == 0:
                continue

            # 過去成績を取得
            horse_past = _get_horse_past_results(session, result.horse_id)

            # 馬情報を取得
            horse = session.get(Horse, result.horse_id)

            # ファクタースコアを計算
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

            # 派生特徴量を計算
            past_stats = _calculate_past_stats(horse_past, race.date)

            # 生データ
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

            # ラベル: 3着以内=1, 4着以下=0
            label = 1 if result.finish_position <= 3 else 0
            labels.append(label)

    return features_list, labels


def _calculate_past_stats(past_results: list[dict], current_date: date) -> dict:
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

    # 前走からの日数
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


def _print_score_table(scores: list[dict]) -> None:
    """スコアテーブルを表示する

    Args:
        scores: スコアリスト
    """
    # ヘッダー
    click.echo(
        f"{'順位':^4} | {'馬番':^4} | {'馬名':^12} | {'総合':^6} | {'過去':^6} | "
        f"{'適性':^6} | {'タイム':^6} | {'上がり':^6} | {'人気':^6}"
    )
    click.echo("-" * 82)

    # 各馬のスコア
    for rank, score in enumerate(scores, 1):
        total = f"{score['total']:.1f}" if score["total"] is not None else "-"
        past = f"{score['past_results']:.1f}" if score["past_results"] is not None else "-"
        course = f"{score['course_fit']:.1f}" if score["course_fit"] is not None else "-"
        time_idx = f"{score['time_index']:.1f}" if score["time_index"] is not None else "-"
        last_3f = f"{score['last_3f']:.1f}" if score["last_3f"] is not None else "-"
        pop = f"{score['popularity']:.1f}" if score["popularity"] is not None else "-"

        # 馬名を12文字に切り詰め
        horse_name = score["horse_name"][:12] if len(score["horse_name"]) > 12 else score["horse_name"]

        click.echo(
            f"{rank:^4} | {score['horse_number']:^4} | {horse_name:^12} | "
            f"{total:^6} | {past:^6} | {course:^6} | {time_idx:^6} | {last_3f:^6} | {pop:^6}"
        )


def _analyze_race_with_ml(
    session, race: Race, predictor, training_count: int
) -> None:
    """レースを分析してスコアとML予測を表示する

    Args:
        session: SQLAlchemyセッション
        race: レースオブジェクト
        predictor: Predictorインスタンス（Noneの場合はML予測スキップ）
        training_count: 学習データ数
    """
    click.echo("=" * 80)
    click.echo(f"{race.date} {race.course} {race.race_number}R {race.name} {race.surface}{race.distance}m")

    if predictor:
        click.echo(f"【ML予測】学習データ: {training_count:,}件")

    click.echo("=" * 80)

    # レース結果を取得
    results = (
        session.query(RaceResult)
        .filter(RaceResult.race_id == race.id)
        .all()
    )

    if not results:
        click.echo("出走馬情報がありません")
        click.echo("")
        return

    # 各馬のスコアを計算
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
        # 過去成績を取得
        past_results = _get_horse_past_results(session, result.horse_id)

        # 馬情報を取得
        horse = session.get(Horse, result.horse_id)

        # 各Factorスコアを計算
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

        # ML用特徴量を構築
        if predictor:
            past_stats = _calculate_past_stats(past_results, race.date)
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
                "probability": None,  # 後で設定
                "ml_rank": None,  # 後で設定
            }
        )

    # ML予測を実行
    if predictor and ml_features:
        X = np.array(ml_features)
        predictions = predictor.predict_with_ranking(X, horse_ids)

        # 予測結果をscoresにマージ
        pred_map = {p["horse_id"]: p for p in predictions}
        for score in scores:
            pred = pred_map.get(score["horse_id"])
            if pred:
                score["probability"] = pred["probability"]
                score["ml_rank"] = pred["rank"]

    # ML予測ランキング順でソート（予測がある場合）、なければ総合スコア順
    if predictor:
        scores.sort(key=lambda x: x["ml_rank"] if x["ml_rank"] else 999)
    else:
        scores.sort(key=lambda x: x["total"] or 0, reverse=True)

    # 表形式で出力
    _print_score_table_with_ml(scores, predictor is not None)
    click.echo("")


def _print_score_table_with_ml(scores: list[dict], with_ml: bool) -> None:
    """スコアテーブルを表示する（ML予測付き）

    Args:
        scores: スコアリスト
        with_ml: ML予測を含むかどうか
    """
    if with_ml:
        # ML予測あり
        click.echo(
            f"{'予測':^4} | {'馬番':^4} | {'馬名':^12} | {'3着内確率':^8} | "
            f"{'総合':^6} | {'過去':^6} | {'適性':^6} | {'タイム':^6} | {'上がり':^6} | {'人気':^6}"
        )
        click.echo("-" * 100)

        for score in scores:
            rank = f"{score['ml_rank']}" if score["ml_rank"] else "-"
            prob = f"{score['probability']:.1%}" if score["probability"] is not None else "-"
            total = f"{score['total']:.1f}" if score["total"] is not None else "-"
            past = f"{score['past_results']:.1f}" if score["past_results"] is not None else "-"
            course = f"{score['course_fit']:.1f}" if score["course_fit"] is not None else "-"
            time_idx = f"{score['time_index']:.1f}" if score["time_index"] is not None else "-"
            last_3f = f"{score['last_3f']:.1f}" if score["last_3f"] is not None else "-"
            pop = f"{score['popularity']:.1f}" if score["popularity"] is not None else "-"

            horse_name = score["horse_name"][:12] if len(score["horse_name"]) > 12 else score["horse_name"]

            click.echo(
                f"{rank:^4} | {score['horse_number']:^4} | {horse_name:^12} | "
                f"{prob:^8} | {total:^6} | {past:^6} | {course:^6} | {time_idx:^6} | {last_3f:^6} | {pop:^6}"
            )

        # 確率50%以上の馬数
        high_prob_count = sum(1 for s in scores if s["probability"] and s["probability"] >= 0.5)
        if high_prob_count > 0:
            click.echo(f"\n※ 確率50%以上: {high_prob_count}頭")
    else:
        # 従来のスコアのみ表示
        _print_score_table(scores)
