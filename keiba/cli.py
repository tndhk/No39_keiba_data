"""競馬データ収集CLI

clickを使用してCLIコマンドを提供する。
"""

import calendar
import re
from datetime import date
from datetime import datetime as dt
from datetime import timedelta

import click
from sqlalchemy import or_

from keiba.db import get_engine, get_session, init_db
from keiba.models import Horse, Jockey, Race, RaceResult, Trainer
from keiba.scrapers import HorseDetailScraper, RaceDetailScraper, RaceListScraper
from keiba.utils.grade_extractor import extract_grade

# 競馬場コードマッピング（race_idの5-6桁目）
VENUE_CODE_MAP = {
    "札幌": "01",
    "函館": "02",
    "福島": "03",
    "新潟": "04",
    "東京": "05",
    "中山": "06",
    "中京": "07",
    "京都": "08",
    "阪神": "09",
    "小倉": "10",
}


def extract_race_id_from_url(url: str) -> str:
    """URLからレースIDを抽出する

    Args:
        url: レースURL（例: https://race.netkeiba.com/race/202401010101.html）

    Returns:
        レースID（例: 202401010101）
    """
    match = re.search(r"/race/(\d+)/?", url)
    if match:
        return match.group(1)
    raise ValueError(f"Invalid race URL: {url}")


def extract_race_id_from_shutuba_url(url: str) -> str:
    """出馬表URLからレースIDを抽出する

    Args:
        url: 出馬表URL（例: https://race.netkeiba.com/race/shutuba.html?race_id=202606010802）

    Returns:
        レースID（例: 202606010802）
    """
    match = re.search(r"race_id=(\d+)", url)
    if match:
        return match.group(1)
    raise ValueError(f"Invalid shutuba URL: {url}")


def parse_race_date(date_str: str) -> date:
    """レース日付文字列をdateオブジェクトに変換する

    Args:
        date_str: 日付文字列（例: "2024年1月1日"）

    Returns:
        dateオブジェクト
    """
    match = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_str)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        return date(year, month, day)
    raise ValueError(f"Invalid date string: {date_str}")


@click.group()
def main():
    """競馬データ収集CLI"""
    pass


@main.command()
@click.option("--year", required=True, type=int, help="取得する年")
@click.option("--month", required=True, type=int, help="取得する月")
@click.option("--db", required=True, type=click.Path(), help="DBファイルパス")
@click.option("--jra-only", is_flag=True, default=False, help="中央競馬のみ取得")
def scrape(year: int, month: int, db: str, jra_only: bool):
    """指定した年月のレースデータを収集"""
    scope = "中央競馬のみ" if jra_only else "全競馬場"
    click.echo(f"データ収集開始: {year}年{month}月 ({scope})")
    click.echo(f"データベース: {db}")

    # DBを初期化
    engine = get_engine(db)
    init_db(engine)

    # スクレイパーを初期化
    race_list_scraper = RaceListScraper()
    race_detail_scraper = RaceDetailScraper()

    # 月の日数を取得
    _, days_in_month = calendar.monthrange(year, month)

    # 統計情報
    total_races = 0
    skipped_races = 0
    saved_races = 0

    with get_session(engine) as session:
        # 各日のレースを取得
        for day in range(1, days_in_month + 1):
            click.echo(f"  {year}/{month:02d}/{day:02d} のレースを取得中...")

            try:
                race_urls = race_list_scraper.fetch_race_urls(
                    year, month, day, jra_only=jra_only
                )
            except Exception as e:
                click.echo(f"    レース一覧取得エラー: {e}")
                continue

            for race_url in race_urls:
                total_races += 1
                race_id = extract_race_id_from_url(race_url)

                # 既存レースをチェック
                existing_race = session.get(Race, race_id)
                if existing_race:
                    click.echo(f"    スキップ: {race_id} (既存)")
                    skipped_races += 1
                    continue

                # レース詳細を取得
                try:
                    race_data = race_detail_scraper.fetch_race_detail(race_id)
                except Exception as e:
                    click.echo(f"    レース詳細取得エラー ({race_id}): {e}")
                    continue

                # レースデータを保存
                try:
                    _save_race_data(session, race_data)
                    saved_races += 1
                    click.echo(f"    保存: {race_id} - {race_data['race']['name']}")
                except Exception as e:
                    click.echo(f"    保存エラー ({race_id}): {e}")
                    continue

    click.echo("")
    click.echo("=" * 50)
    click.echo(f"完了: {year}年{month}月")
    click.echo(f"  総レース数: {total_races}")
    click.echo(f"  保存済み: {saved_races}")
    click.echo(f"  スキップ: {skipped_races}")


def _save_race_data(session, race_data: dict) -> None:
    """レースデータをDBに保存する

    Args:
        session: SQLAlchemyセッション
        race_data: レースデータ（race と results を含む辞書）
    """
    race_info = race_data["race"]
    results = race_data["results"]

    # レースを保存
    race = Race(
        id=race_info["id"],
        name=race_info["name"],
        date=parse_race_date(race_info["date"]),
        course=race_info["course"],
        race_number=race_info["race_number"],
        distance=race_info["distance"],
        surface=race_info["surface"],
        weather=race_info.get("weather"),
        track_condition=race_info.get("track_condition"),
        grade=race_info.get("grade"),
    )
    session.add(race)

    # 各結果を保存
    for result in results:
        # 馬を保存（存在しない場合）
        horse = session.get(Horse, result["horse_id"])
        if not horse:
            horse = Horse(
                id=result["horse_id"],
                name=result["horse_name"],
                sex="不明",  # レース結果からは性別が取得できない
                birth_year=0,  # レース結果からは生年が取得できない
            )
            session.add(horse)

        # 騎手を保存（存在しない場合）
        jockey = session.get(Jockey, result["jockey_id"])
        if not jockey:
            jockey = Jockey(
                id=result["jockey_id"],
                name=result["jockey_name"],
            )
            session.add(jockey)

        # 調教師を保存（存在しない場合）
        trainer = session.get(Trainer, result["trainer_id"])
        if not trainer:
            trainer = Trainer(
                id=result["trainer_id"],
                name=result["trainer_name"],
            )
            session.add(trainer)

        # finish_positionがNoneの場合（中止など）は0として保存
        finish_position = result["finish_position"]
        if finish_position is None:
            finish_position = 0

        # レース結果を保存
        race_result = RaceResult(
            race_id=race_info["id"],
            horse_id=result["horse_id"],
            jockey_id=result["jockey_id"],
            trainer_id=result["trainer_id"],
            finish_position=finish_position,
            bracket_number=result["bracket_number"],
            horse_number=result["horse_number"],
            odds=result["odds"],
            popularity=result["popularity"],
            weight=result["weight"],
            weight_diff=result["weight_diff"],
            time=result["time"],
            margin=result["margin"],
            last_3f=result.get("last_3f"),
            sex=result.get("sex"),
            age=result.get("age"),
            impost=result.get("impost"),
            passing_order=result.get("passing_order"),
        )
        session.add(race_result)


@main.command()
@click.option("--db", required=True, type=click.Path(), help="DBファイルパス")
@click.option("--limit", default=100, type=int, help="取得する馬の数（デフォルト: 100）")
def scrape_horses(db: str, limit: int):
    """詳細未取得の馬情報を収集"""
    click.echo(f"馬詳細データ収集開始")
    click.echo(f"データベース: {db}")
    click.echo(f"取得上限: {limit}件")

    # DBを初期化
    engine = get_engine(db)
    init_db(engine)

    # スクレイパーを初期化
    horse_detail_scraper = HorseDetailScraper()

    # 統計情報
    total_processed = 0
    updated_horses = 0
    errors = 0

    with get_session(engine) as session:
        # 詳細未取得の馬を取得（sireがNullの馬）
        horses = (
            session.query(Horse)
            .filter(
                or_(
                    Horse.sire.is_(None),
                    Horse.sex == "不明",
                )
            )
            .limit(limit)
            .all()
        )

        if not horses:
            click.echo("詳細未取得の馬はありません。")
            return

        click.echo(f"詳細未取得の馬: {len(horses)}件")
        click.echo("")

        for horse in horses:
            total_processed += 1
            click.echo(f"  [{total_processed}/{len(horses)}] {horse.name} ({horse.id})...")

            try:
                horse_data = horse_detail_scraper.fetch_horse_detail(horse.id)
                _update_horse(session, horse, horse_data)
                updated_horses += 1
                click.echo(f"    更新完了")
            except Exception as e:
                errors += 1
                click.echo(f"    エラー: {e}")
                continue

    click.echo("")
    click.echo("=" * 50)
    click.echo(f"完了")
    click.echo(f"  処理数: {total_processed}")
    click.echo(f"  更新成功: {updated_horses}")
    click.echo(f"  エラー: {errors}")


def _update_horse(session, horse: Horse, horse_data: dict) -> None:
    """馬情報を更新する

    Args:
        session: SQLAlchemyセッション
        horse: 更新対象のHorseオブジェクト
        horse_data: スクレイピングで取得した馬データ
    """
    # 基本情報
    if horse_data.get("name"):
        horse.name = horse_data["name"]
    if horse_data.get("sex"):
        horse.sex = horse_data["sex"]
    if horse_data.get("birth_year"):
        horse.birth_year = horse_data["birth_year"]

    # 血統情報
    if horse_data.get("sire"):
        horse.sire = horse_data["sire"]
    if horse_data.get("dam"):
        horse.dam = horse_data["dam"]
    if horse_data.get("dam_sire"):
        horse.dam_sire = horse_data["dam_sire"]

    # 基本情報
    if horse_data.get("coat_color"):
        horse.coat_color = horse_data["coat_color"]
    if horse_data.get("birthplace"):
        horse.birthplace = horse_data["birthplace"]

    # 関連ID
    if horse_data.get("trainer_id"):
        horse.trainer_id = horse_data["trainer_id"]
    if horse_data.get("owner_id"):
        horse.owner_id = horse_data["owner_id"]
    if horse_data.get("breeder_id"):
        horse.breeder_id = horse_data["breeder_id"]

    # 成績情報
    if horse_data.get("total_races") is not None:
        horse.total_races = horse_data["total_races"]
    if horse_data.get("total_wins") is not None:
        horse.total_wins = horse_data["total_wins"]
    if horse_data.get("total_earnings") is not None:
        horse.total_earnings = horse_data["total_earnings"]


@main.command()
@click.option("--db", required=True, type=click.Path(), help="DBファイルパス")
@click.option("--date", required=True, type=str, help="レース日付（YYYY-MM-DD）")
@click.option("--venue", required=True, type=str, help="競馬場名（例: 中山）")
@click.option("--race", type=int, default=None, help="レース番号（省略時は全レース）")
@click.option("--no-predict", is_flag=True, default=False, help="ML予測をスキップ")
def analyze(db: str, date: str, venue: str, race: int | None, no_predict: bool):
    """指定した日付・競馬場のレースを分析してスコアを表示"""
    from datetime import datetime as dt

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
    from keiba.ml.feature_builder import FeatureBuilder
    from keiba.ml.predictor import Predictor
    from keiba.ml.trainer import Trainer

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
    from keiba.analyzers.factors import (
        CourseFitFactor,
        Last3FFactor,
        PastResultsFactor,
        PopularityFactor,
        TimeIndexFactor,
    )
    from keiba.analyzers.score_calculator import ScoreCalculator

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


@main.command()
@click.option("--db", required=True, type=click.Path(exists=True), help="データベースファイルパス")
@click.option("--from", "from_date", type=str, help="開始日 (YYYY-MM-DD)")
@click.option("--to", "to_date", type=str, help="終了日 (YYYY-MM-DD)")
@click.option("--months", type=int, default=1, help="直近何ヶ月を対象とするか (default: 1)")
@click.option(
    "--retrain-interval",
    type=click.Choice(["daily", "weekly", "monthly"]),
    default="weekly",
    help="再学習間隔",
)
@click.option("-v", "--verbose", is_flag=True, help="詳細表示")
def backtest(
    db: str,
    from_date: str | None,
    to_date: str | None,
    months: int,
    retrain_interval: str,
    verbose: bool,
):
    """ML予測と7ファクタースコアの精度をバックテストで検証"""
    from keiba.backtest import BacktestEngine, BacktestReporter, MetricsCalculator

    click.echo("バックテスト開始")
    click.echo(f"データベース: {db}")

    # 日付範囲を決定
    if from_date and to_date:
        try:
            start_date = dt.strptime(from_date, "%Y-%m-%d").date()
            end_date = dt.strptime(to_date, "%Y-%m-%d").date()
        except ValueError:
            click.echo("日付形式が不正です（YYYY-MM-DD形式で指定してください）")
            return
    else:
        # monthsパラメータから計算
        end_date = dt.now().date()
        start_date = end_date - timedelta(days=months * 30)

    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    click.echo(f"期間: {start_date} ~ {end_date}")
    click.echo(f"再学習間隔: {retrain_interval}")
    click.echo("")

    backtest_engine = BacktestEngine(
        db_path=db,
        start_date=start_date_str,
        end_date=end_date_str,
        retrain_interval=retrain_interval,
    )

    results = list(backtest_engine.run())
    metrics = MetricsCalculator.calculate(results)
    reporter = BacktestReporter(
        start_date=start_date_str,
        end_date=end_date_str,
        retrain_interval=retrain_interval,
    )

    if verbose:
        for race_result in results:
            detail = reporter.print_race_detail(race_result)
            click.echo(detail)
            click.echo("")

    summary = reporter.print_summary(results, metrics)
    click.echo(summary)


@main.command("migrate-grades")
@click.option("--db", required=True, type=click.Path(), help="DBファイルパス")
def migrate_grades(db: str):
    """既存レースにグレード情報を追加する

    gradeがNullのレースに対して、レース名からグレードを抽出して更新する。
    """
    click.echo(f"グレード情報マイグレーション開始")
    click.echo(f"データベース: {db}")

    # DBに接続
    engine = get_engine(db)

    # 統計情報
    total_updated = 0

    with get_session(engine) as session:
        # gradeがNullのレースを取得
        races = session.query(Race).filter(Race.grade.is_(None)).all()

        if not races:
            click.echo("グレード未設定のレースはありません。")
            click.echo("")
            click.echo("完了")
            return

        click.echo(f"グレード未設定のレース: {len(races)}件")
        click.echo("")

        for race in races:
            grade = extract_grade(race.name)
            race.grade = grade
            total_updated += 1

            if total_updated % 100 == 0:
                click.echo(f"  {total_updated}件処理...")

    click.echo("")
    click.echo("=" * 50)
    click.echo("完了")
    click.echo(f"  更新したレース: {total_updated}件")


class SQLAlchemyRaceResultRepository:
    """SQLAlchemyを使用した過去成績リポジトリ"""

    def __init__(self, session):
        """初期化

        Args:
            session: SQLAlchemyセッション
        """
        self.session = session

    def get_past_results(
        self, horse_id: str, before_date: str, limit: int = 20
    ) -> list[dict]:
        """指定日より前の過去成績を取得

        Args:
            horse_id: 馬ID
            before_date: この日付より前の成績を取得（YYYY年M月D日形式）
            limit: 最大取得件数

        Returns:
            過去成績のリスト
        """
        # 日付を解析
        try:
            target_date = parse_race_date(before_date)
        except ValueError:
            # 解析失敗時は空リストを返す
            return []

        # 過去のレース結果を取得
        past_results_query = (
            self.session.query(RaceResult, Race)
            .join(Race, RaceResult.race_id == Race.id)
            .filter(RaceResult.horse_id == horse_id)
            .filter(Race.date < target_date)
            .order_by(Race.date.desc())
            .limit(limit)
        )

        results = []
        for race_result, race_info in past_results_query:
            # 同じレースの出走頭数を取得
            total_runners = (
                self.session.query(RaceResult)
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
                    "odds": race_result.odds,
                    "popularity": race_result.popularity,
                    "passing_order": race_result.passing_order,
                    "course": race_info.course,
                }
            )

        return results


@main.command()
@click.option("--url", required=True, type=str, help="出馬表ページURL")
@click.option("--db", required=True, type=click.Path(), help="DBファイルパス")
@click.option(
    "--no-ml", is_flag=True, default=False, help="ML予測をスキップし因子スコアのみ表示"
)
def predict(url: str, db: str, no_ml: bool):
    """出馬表URLから予測を実行"""
    from keiba.scrapers.shutuba import ShutubaScraper
    from keiba.services.prediction_service import PredictionService

    # URLからrace_idを抽出
    try:
        race_id = extract_race_id_from_shutuba_url(url)
    except ValueError as e:
        click.echo(f"URLエラー: {e}")
        return

    click.echo(f"出馬表予測: {race_id}")

    # DBに接続
    engine = get_engine(db)

    # 出馬表データを取得
    scraper = ShutubaScraper()
    try:
        shutuba_data = scraper.fetch_shutuba(race_id)
    except Exception as e:
        click.echo(f"出馬表取得エラー: {e}")
        return

    # レース情報ヘッダーを表示
    click.echo(
        f"{shutuba_data.date} {shutuba_data.course} {shutuba_data.race_number}R "
        f"{shutuba_data.surface}{shutuba_data.distance}m"
    )
    click.echo(f"{shutuba_data.race_name}")
    click.echo("=" * 80)

    with get_session(engine) as session:
        # リポジトリを作成
        repository = SQLAlchemyRaceResultRepository(session)

        # モデルパスの設定（ML予測を使用する場合）
        model_path = None if no_ml else None  # 現状はモデルパス未指定

        # PredictionServiceで予測を実行
        service = PredictionService(repository=repository, model_path=model_path)
        predictions = service.predict_from_shutuba(shutuba_data)

        # 結果を表形式で表示
        _print_prediction_table(predictions, with_ml=not no_ml)


def _print_prediction_table(predictions: list, with_ml: bool) -> None:
    """予測結果テーブルを表示する

    Args:
        predictions: PredictionResultのリスト
        with_ml: ML予測を含むかどうか
    """
    if with_ml:
        # ML予測あり
        click.echo(
            f"{'順位':^4} | {'馬番':^4} | {'馬名':^12} | {'ML確率':^8} | "
            f"{'総合':^6} | {'過去':^6} | {'適性':^6} | {'指数':^6} | {'上り':^6} | "
            f"{'人気':^6} | {'血統':^6} | {'脚質':^6}"
        )
        click.echo("-" * 110)

        for pred in predictions:
            rank = f"{pred.rank}"
            prob = f"{pred.ml_probability:.1%}" if pred.ml_probability > 0 else "-"
            total = f"{pred.total_score:.1f}" if pred.total_score is not None else "-"
            past = (
                f"{pred.factor_scores.get('past_results', 0):.1f}"
                if pred.factor_scores.get("past_results") is not None
                else "-"
            )
            course = (
                f"{pred.factor_scores.get('course_fit', 0):.1f}"
                if pred.factor_scores.get("course_fit") is not None
                else "-"
            )
            time_idx = (
                f"{pred.factor_scores.get('time_index', 0):.1f}"
                if pred.factor_scores.get("time_index") is not None
                else "-"
            )
            last_3f = (
                f"{pred.factor_scores.get('last_3f', 0):.1f}"
                if pred.factor_scores.get("last_3f") is not None
                else "-"
            )
            pop = (
                f"{pred.factor_scores.get('popularity', 0):.1f}"
                if pred.factor_scores.get("popularity") is not None
                else "-"
            )
            pedigree = (
                f"{pred.factor_scores.get('pedigree', 0):.1f}"
                if pred.factor_scores.get("pedigree") is not None
                else "-"
            )
            running = (
                f"{pred.factor_scores.get('running_style', 0):.1f}"
                if pred.factor_scores.get("running_style") is not None
                else "-"
            )

            # 馬名を12文字に切り詰め
            horse_name = (
                pred.horse_name[:12]
                if len(pred.horse_name) > 12
                else pred.horse_name
            )

            click.echo(
                f"{rank:^4} | {pred.horse_number:^4} | {horse_name:^12} | "
                f"{prob:^8} | {total:^6} | {past:^6} | {course:^6} | {time_idx:^6} | "
                f"{last_3f:^6} | {pop:^6} | {pedigree:^6} | {running:^6}"
            )
    else:
        # 因子スコアのみ（総合スコア順でソート）
        sorted_predictions = sorted(
            predictions,
            key=lambda x: x.total_score if x.total_score is not None else 0,
            reverse=True,
        )

        click.echo(
            f"{'順位':^4} | {'馬番':^4} | {'馬名':^12} | "
            f"{'総合':^6} | {'過去':^6} | {'適性':^6} | {'指数':^6} | {'上り':^6} | "
            f"{'人気':^6} | {'血統':^6} | {'脚質':^6}"
        )
        click.echo("-" * 100)

        for rank, pred in enumerate(sorted_predictions, 1):
            total = f"{pred.total_score:.1f}" if pred.total_score is not None else "-"
            past = (
                f"{pred.factor_scores.get('past_results', 0):.1f}"
                if pred.factor_scores.get("past_results") is not None
                else "-"
            )
            course = (
                f"{pred.factor_scores.get('course_fit', 0):.1f}"
                if pred.factor_scores.get("course_fit") is not None
                else "-"
            )
            time_idx = (
                f"{pred.factor_scores.get('time_index', 0):.1f}"
                if pred.factor_scores.get("time_index") is not None
                else "-"
            )
            last_3f = (
                f"{pred.factor_scores.get('last_3f', 0):.1f}"
                if pred.factor_scores.get("last_3f") is not None
                else "-"
            )
            pop = (
                f"{pred.factor_scores.get('popularity', 0):.1f}"
                if pred.factor_scores.get("popularity") is not None
                else "-"
            )
            pedigree = (
                f"{pred.factor_scores.get('pedigree', 0):.1f}"
                if pred.factor_scores.get("pedigree") is not None
                else "-"
            )
            running = (
                f"{pred.factor_scores.get('running_style', 0):.1f}"
                if pred.factor_scores.get("running_style") is not None
                else "-"
            )

            # 馬名を12文字に切り詰め
            horse_name = (
                pred.horse_name[:12]
                if len(pred.horse_name) > 12
                else pred.horse_name
            )

            click.echo(
                f"{rank:^4} | {pred.horse_number:^4} | {horse_name:^12} | "
                f"{total:^6} | {past:^6} | {course:^6} | {time_idx:^6} | "
                f"{last_3f:^6} | {pop:^6} | {pedigree:^6} | {running:^6}"
            )


def _get_race_ids_for_venue(race_urls: list[str], venue_code: str) -> list[str]:
    """指定競馬場のレースIDをフィルタリングする

    Args:
        race_urls: レースURLのリスト
        venue_code: 競馬場コード（2桁の文字列、例: "06"）

    Returns:
        指定競馬場のレースIDリスト
    """
    race_ids = []

    for url in race_urls:
        # URLからレースIDを抽出
        match = re.search(r"/race/(\d{12})/?", url)
        if match:
            race_id = match.group(1)
            # race_idの5-6桁目が競馬場コード
            if len(race_id) >= 6 and race_id[4:6] == venue_code:
                race_ids.append(race_id)

    return race_ids


def _save_predictions_markdown(
    predictions_data: list,
    date_str: str,
    venue: str,
    output_dir: str | None = None,
) -> str:
    """予測結果をMarkdownファイルに保存する

    Args:
        predictions_data: 予測データのリスト
        date_str: 日付文字列（YYYY-MM-DD形式）
        venue: 競馬場名
        output_dir: 出力ディレクトリ（Noneの場合はdocs/predictions）

    Returns:
        保存したファイルパス
    """
    from pathlib import Path

    # 出力ディレクトリを決定
    if output_dir is None:
        base_path = Path(__file__).parent.parent / "docs" / "predictions"
    else:
        base_path = Path(output_dir)

    # ディレクトリが存在しない場合は作成
    base_path.mkdir(parents=True, exist_ok=True)

    # ファイル名を生成（日本語競馬場名をローマ字に変換）
    venue_romanized = {
        "札幌": "sapporo",
        "函館": "hakodate",
        "福島": "fukushima",
        "新潟": "niigata",
        "東京": "tokyo",
        "中山": "nakayama",
        "中京": "chukyo",
        "京都": "kyoto",
        "阪神": "hanshin",
        "小倉": "kokura",
    }
    venue_name = venue_romanized.get(venue, venue.lower())
    filename = f"{date_str}-{venue_name}.md"
    filepath = base_path / filename

    # Markdownコンテンツを生成
    lines = [
        f"# {date_str} {venue} 予測結果",
        "",
        f"生成日時: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    for race_data in predictions_data:
        race_id = race_data.get("race_id", "")
        race_number = race_data.get("race_number", "?")
        race_name = race_data.get("race_name", "")
        surface = race_data.get("surface", "")
        distance = race_data.get("distance", "")

        lines.append(f"## {race_number}R {race_name}")
        if race_id:
            lines.append(f"race_id: {race_id}")
        if surface and distance:
            lines.append(f"{surface}{distance}m")
        lines.append("")

        predictions = race_data.get("predictions", [])
        if predictions:
            lines.append("| 順位 | 馬番 | 馬名 | ML確率 | 総合 |")
            lines.append("|:---:|:---:|:---|:---:|:---:|")

            for pred in predictions[:5]:  # 上位5頭のみ
                rank = pred.get("rank", "")
                horse_number = pred.get("horse_number", "")
                horse_name = pred.get("horse_name", "")
                ml_prob = pred.get("ml_probability", 0)
                total_score = pred.get("total_score")

                prob_str = f"{ml_prob:.1%}" if ml_prob > 0 else "-"
                total_str = f"{total_score:.1f}" if total_score else "-"

                lines.append(
                    f"| {rank} | {horse_number} | {horse_name} | {prob_str} | {total_str} |"
                )
        else:
            lines.append("予測データなし")

        lines.append("")

    # ファイルに書き込み
    content = "\n".join(lines)
    filepath.write_text(content, encoding="utf-8")

    return str(filepath)


@main.command("predict-day")
@click.option("--date", "date_str", type=str, default=None, help="開催日（YYYY-MM-DD形式）")
@click.option("--venue", required=True, type=str, help="競馬場名（例: 中山）")
@click.option("--db", required=True, type=click.Path(), help="DBファイルパス")
@click.option("--no-ml", is_flag=True, default=False, help="ML予測をスキップ")
def predict_day(date_str: str | None, venue: str, db: str, no_ml: bool):
    """指定日・競馬場の全レースを予測"""
    from keiba.scrapers.shutuba import ShutubaScraper
    from keiba.services.prediction_service import PredictionService

    # 日付を決定（デフォルトは今日）
    if date_str is None:
        target_date = date.today()
        date_str = target_date.strftime("%Y-%m-%d")
    else:
        try:
            target_date = dt.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            click.echo(f"日付形式が不正です: {date_str}（YYYY-MM-DD形式で指定してください）")
            raise SystemExit(1)

    # 競馬場コードを取得
    if venue not in VENUE_CODE_MAP:
        valid_venues = ", ".join(VENUE_CODE_MAP.keys())
        click.echo(f"無効な競馬場名: {venue}")
        click.echo(f"有効な競馬場: {valid_venues}")
        raise SystemExit(1)

    venue_code = VENUE_CODE_MAP[venue]

    click.echo(f"予測開始: {date_str} {venue}")
    click.echo(f"データベース: {db}")
    click.echo("")

    # DBに接続
    engine = get_engine(db)

    # レース一覧を取得
    race_list_scraper = RaceListScraper()
    try:
        race_urls = race_list_scraper.fetch_race_urls(
            target_date.year, target_date.month, target_date.day, jra_only=True
        )
    except Exception as e:
        click.echo(f"レース一覧取得エラー: {e}")
        raise SystemExit(1)

    # 指定競馬場のレースをフィルタリング
    race_ids = _get_race_ids_for_venue(race_urls, venue_code)

    if not race_ids:
        click.echo(f"{date_str} {venue}のレースは見つかりませんでした")
        raise SystemExit(0)

    click.echo(f"対象レース数: {len(race_ids)}")
    click.echo("")

    # 各レースの予測を実行
    shutuba_scraper = ShutubaScraper()
    predictions_data = []
    notable_horses = []  # 注目馬リスト

    with get_session(engine) as session:
        repository = SQLAlchemyRaceResultRepository(session)
        service = PredictionService(repository=repository, model_path=None)

        for race_id in sorted(race_ids):
            try:
                # 出馬表を取得
                shutuba_data = shutuba_scraper.fetch_shutuba(race_id)

                click.echo(
                    f"{shutuba_data.race_number}R {shutuba_data.race_name} "
                    f"{shutuba_data.surface}{shutuba_data.distance}m"
                )

                # 予測を実行
                predictions = service.predict_from_shutuba(shutuba_data)

                # 予測データを収集
                race_predictions = {
                    "race_id": race_id,
                    "race_number": shutuba_data.race_number,
                    "race_name": shutuba_data.race_name,
                    "surface": shutuba_data.surface,
                    "distance": shutuba_data.distance,
                    "predictions": [
                        {
                            "rank": p.rank,
                            "horse_number": p.horse_number,
                            "horse_name": p.horse_name,
                            "ml_probability": p.ml_probability,
                            "total_score": p.total_score,
                        }
                        for p in predictions
                    ],
                }
                predictions_data.append(race_predictions)

                # 注目馬を抽出（上位3頭、または確率50%以上）
                for p in predictions[:3]:
                    if p.total_score and p.total_score > 50:
                        notable_horses.append(
                            {
                                "race_number": shutuba_data.race_number,
                                "race_name": shutuba_data.race_name,
                                "horse_name": p.horse_name,
                                "horse_number": p.horse_number,
                                "ml_probability": p.ml_probability,
                                "total_score": p.total_score,
                            }
                        )

            except Exception as e:
                click.echo(f"  エラー: {e}")
                continue

    # Markdownファイルに保存
    if predictions_data:
        filepath = _save_predictions_markdown(
            predictions_data=predictions_data,
            date_str=date_str,
            venue=venue,
        )
        click.echo("")
        click.echo(f"予測結果を保存しました: {filepath}")

    # 注目馬サマリーを表示
    if notable_horses:
        click.echo("")
        click.echo("=" * 60)
        click.echo("注目馬サマリー")
        click.echo("=" * 60)

        for h in notable_horses:
            prob_str = f"{h['ml_probability']:.1%}" if h["ml_probability"] > 0 else "-"
            score_str = f"{h['total_score']:.1f}" if h["total_score"] else "-"
            click.echo(
                f"{h['race_number']}R {h['horse_number']}番 {h['horse_name']} "
                f"(ML: {prob_str}, 総合: {score_str})"
            )

    click.echo("")
    click.echo("完了")


def _parse_predictions_markdown(filepath: str) -> dict:
    """予測結果Markdownファイルをパースする

    Args:
        filepath: Markdownファイルパス

    Returns:
        パースされた予測データ
        {
            "races": [
                {
                    "race_id": str,
                    "race_number": int,
                    "race_name": str,
                    "predictions": [
                        {"horse_number": int, "horse_name": str, "rank": int, "ml_probability": float}
                    ]
                }
            ]
        }
    """
    from pathlib import Path

    result = {"races": []}

    path = Path(filepath)
    if not path.exists():
        return result

    content = path.read_text(encoding="utf-8")
    lines = content.split("\n")

    current_race = None
    in_table = False
    header_skipped = False

    for line in lines:
        line = line.strip()

        # レースヘッダー（## 1R テストレース）
        if line.startswith("## ") and "R " in line:
            # 前のレースがあれば保存
            if current_race is not None:
                result["races"].append(current_race)

            # レース番号とレース名を抽出
            race_header = line[3:]  # "## "を除去
            race_match = re.match(r"(\d+)R\s+(.+)", race_header)
            if race_match:
                race_number = int(race_match.group(1))
                race_name = race_match.group(2)
            else:
                race_number = 0
                race_name = race_header

            current_race = {
                "race_id": "",
                "race_number": race_number,
                "race_name": race_name,
                "predictions": [],
            }
            in_table = False
            header_skipped = False

        # race_id行を検出（race_id: 202606010801）
        elif line.startswith("race_id:") and current_race is not None:
            race_id_match = re.match(r"race_id:\s*(\d+)", line)
            if race_id_match:
                current_race["race_id"] = race_id_match.group(1)

        # テーブル開始検出
        elif line.startswith("|") and "順位" in line:
            in_table = True
            header_skipped = False

        # テーブルヘッダー区切り行をスキップ
        elif in_table and line.startswith("|") and "---" in line:
            header_skipped = True

        # テーブルデータ行
        elif in_table and header_skipped and line.startswith("|") and current_race is not None:
            cells = [c.strip() for c in line.split("|")]
            # 空セルを除去（先頭と末尾の"|"による）
            cells = [c for c in cells if c]

            if len(cells) >= 4:
                try:
                    rank = int(cells[0])
                    horse_number = int(cells[1])
                    horse_name = cells[2]

                    # ML確率をパース（"-"の場合は0.0）
                    ml_prob_str = cells[3].replace("%", "")
                    if ml_prob_str == "-":
                        ml_probability = 0.0
                    else:
                        ml_probability = float(ml_prob_str) / 100.0

                    current_race["predictions"].append({
                        "rank": rank,
                        "horse_number": horse_number,
                        "horse_name": horse_name,
                        "ml_probability": ml_probability,
                    })
                except (ValueError, IndexError):
                    # パースエラーはスキップ
                    pass

        # 空行でテーブル終了
        elif in_table and not line:
            in_table = False

    # 最後のレースを保存
    if current_race is not None:
        result["races"].append(current_race)

    return result


def _calculate_fukusho_simulation(
    predictions: dict,
    actual_results: dict,
    payouts: dict,
) -> dict:
    """複勝シミュレーションを計算する

    Args:
        predictions: パースされた予測データ
        actual_results: レース番号 -> [1着馬番, 2着馬番, 3着馬番] のマップ
        payouts: レース番号 -> {馬番: 払戻金} のマップ

    Returns:
        シミュレーション結果
        {
            "top1": {
                "hits": int,
                "total_races": int,
                "hit_rate": float,
                "payout": int,
                "investment": int,
                "return_rate": float,
            },
            "top3": {
                "hits": int,
                "total_bets": int,
                "hit_rate": float,
                "payout": int,
                "investment": int,
                "return_rate": float,
            },
            "race_results": [...]
        }
    """
    result = {
        "top1": {
            "hits": 0,
            "total_races": 0,
            "hit_rate": 0.0,
            "payout": 0,
            "investment": 0,
            "return_rate": 0.0,
        },
        "top3": {
            "hits": 0,
            "total_bets": 0,
            "hit_rate": 0.0,
            "payout": 0,
            "investment": 0,
            "return_rate": 0.0,
        },
        "race_results": [],
    }

    races = predictions.get("races", [])
    if not races:
        return result

    for race in races:
        race_number = race.get("race_number")
        race_predictions = race.get("predictions", [])

        if not race_predictions or race_number not in actual_results:
            continue

        actual_top3 = actual_results[race_number]
        race_payouts = payouts.get(race_number, {})

        # 予測上位3頭の馬番
        predicted_top3 = [p["horse_number"] for p in race_predictions[:3]]

        # Top1シミュレーション（予測1位に100円賭け）
        result["top1"]["total_races"] += 1
        result["top1"]["investment"] += 100

        if race_predictions:
            top1_horse = race_predictions[0]["horse_number"]
            if top1_horse in actual_top3:
                result["top1"]["hits"] += 1
                result["top1"]["payout"] += race_payouts.get(top1_horse, 0)

        # Top3シミュレーション（予測1-3位に各100円賭け）
        race_top3_hits = 0
        for pred in race_predictions[:3]:
            horse_num = pred["horse_number"]
            result["top3"]["total_bets"] += 1
            result["top3"]["investment"] += 100

            if horse_num in actual_top3:
                result["top3"]["hits"] += 1
                result["top3"]["payout"] += race_payouts.get(horse_num, 0)
                race_top3_hits += 1

        # レース結果を記録
        result["race_results"].append({
            "race_number": race_number,
            "actual_top3": actual_top3,
            "predicted_top3": predicted_top3,
            "top1_hit": (race_predictions[0]["horse_number"] in actual_top3) if race_predictions else False,
            "top3_hits": race_top3_hits,
        })

    # 的中率と回収率を計算
    if result["top1"]["total_races"] > 0:
        result["top1"]["hit_rate"] = result["top1"]["hits"] / result["top1"]["total_races"]
        result["top1"]["return_rate"] = result["top1"]["payout"] / result["top1"]["investment"]

    if result["top3"]["total_bets"] > 0:
        result["top3"]["hit_rate"] = result["top3"]["hits"] / result["top3"]["total_bets"]
        result["top3"]["return_rate"] = result["top3"]["payout"] / result["top3"]["investment"]

    return result


def _append_review_to_markdown(filepath: str, review_data: dict) -> None:
    """検証結果をMarkdownファイルに追記する

    Args:
        filepath: Markdownファイルパス
        review_data: 検証結果データ
    """
    from pathlib import Path

    path = Path(filepath)
    if not path.exists():
        return

    original_content = path.read_text(encoding="utf-8")

    # 検証結果セクションを生成
    lines = [
        "",
        "---",
        "",
        "## 検証結果",
        "",
        f"検証日時: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "### 複勝シミュレーション",
        "",
        "#### 予測1位のみに賭けた場合",
        "",
        f"- 対象レース数: {review_data['top1']['total_races']}",
        f"- 的中数: {review_data['top1']['hits']}",
        f"- 的中率: {review_data['top1']['hit_rate'] * 100:.1f}%",
        f"- 投資額: {review_data['top1']['investment']}円",
        f"- 払戻額: {review_data['top1']['payout']}円",
        f"- 回収率: {review_data['top1']['return_rate'] * 100:.1f}%",
        "",
        "#### 予測1-3位に各100円賭けた場合",
        "",
        f"- 賭け数: {review_data['top3']['total_bets']}",
        f"- 的中数: {review_data['top3']['hits']}",
        f"- 的中率: {review_data['top3']['hit_rate'] * 100:.1f}%",
        f"- 投資額: {review_data['top3']['investment']}円",
        f"- 払戻額: {review_data['top3']['payout']}円",
        f"- 回収率: {review_data['top3']['return_rate'] * 100:.1f}%",
        "",
        "### レース別結果",
        "",
        "| R | 実際の3着以内 | 予測Top3 | Top1的中 | Top3的中数 |",
        "|:---:|:---|:---|:---:|:---:|",
    ]

    for race_result in review_data.get("race_results", []):
        race_num = race_result["race_number"]
        actual = ", ".join(str(h) for h in race_result["actual_top3"])
        predicted = ", ".join(str(h) for h in race_result["predicted_top3"])
        top1_hit = "O" if race_result["top1_hit"] else "X"
        top3_hits = race_result["top3_hits"]
        lines.append(f"| {race_num} | {actual} | {predicted} | {top1_hit} | {top3_hits} |")

    lines.append("")

    # ファイルに追記
    new_content = original_content + "\n".join(lines)
    path.write_text(new_content, encoding="utf-8")


@main.command("review-day")
@click.option("--date", "date_str", type=str, default=None, help="開催日（YYYY-MM-DD形式）")
@click.option("--venue", required=True, type=str, help="競馬場名（例: 中山）")
@click.option("--db", required=True, type=click.Path(), help="DBファイルパス")
def review_day(date_str: str | None, venue: str, db: str):
    """予測結果と実際の結果を比較検証する"""
    from pathlib import Path

    # 日付を決定（デフォルトは今日）
    if date_str is None:
        target_date = date.today()
        date_str = target_date.strftime("%Y-%m-%d")
    else:
        try:
            target_date = dt.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            click.echo(f"日付形式が不正です: {date_str}（YYYY-MM-DD形式で指定してください）")
            raise SystemExit(1)

    # 競馬場名をローマ字に変換
    venue_romanized = {
        "札幌": "sapporo",
        "函館": "hakodate",
        "福島": "fukushima",
        "新潟": "niigata",
        "東京": "tokyo",
        "中山": "nakayama",
        "中京": "chukyo",
        "京都": "kyoto",
        "阪神": "hanshin",
        "小倉": "kokura",
    }
    venue_name = venue_romanized.get(venue, venue.lower())

    # 予測ファイルパスを構築
    base_path = Path(__file__).parent.parent / "docs" / "predictions"
    prediction_file = base_path / f"{date_str}-{venue_name}.md"

    click.echo(f"検証開始: {date_str} {venue}")
    click.echo(f"予測ファイル: {prediction_file}")
    click.echo("")

    # 予測ファイルを読み込み
    if not prediction_file.exists():
        click.echo(f"予測ファイルが見つかりません: {prediction_file}")
        raise SystemExit(1)

    predictions = _parse_predictions_markdown(str(prediction_file))

    if not predictions["races"]:
        click.echo("予測データがありません")
        raise SystemExit(1)

    # レース結果と払戻金を取得
    scraper = RaceDetailScraper()
    actual_results = {}
    payouts = {}

    for race in predictions["races"]:
        race_number = race["race_number"]
        race_id = race.get("race_id", "")

        # race_idが予測ファイルに保存されていない場合はスキップ
        if not race_id:
            click.echo(f"{race_number}R: race_idが予測ファイルに含まれていません。スキップします。")
            continue

        try:
            # 払戻金を取得
            payout_data = scraper.fetch_payouts(race_id)

            # 払戻金データを辞書形式に変換
            race_payouts = {}
            actual_top3 = []
            for p in payout_data:
                horse_num = p["horse_number"]
                race_payouts[horse_num] = p["payout"]
                actual_top3.append(horse_num)

            if actual_top3:
                actual_results[race_number] = actual_top3
                payouts[race_number] = race_payouts
                click.echo(f"{race_number}R: 結果取得完了 - 3着以内: {actual_top3}")
            else:
                click.echo(f"{race_number}R: 結果データなし")

        except Exception as e:
            click.echo(f"{race_number}R: 結果取得エラー - {e}")

    click.echo("")

    # シミュレーションを計算
    review_data = _calculate_fukusho_simulation(predictions, actual_results, payouts)

    # 検証結果をMarkdownに追記
    _append_review_to_markdown(str(prediction_file), review_data)
    click.echo(f"検証結果をファイルに追記しました: {prediction_file}")

    # サマリーを表示
    click.echo("")
    click.echo("=" * 60)
    click.echo("検証サマリー")
    click.echo("=" * 60)
    click.echo("")
    click.echo("【予測1位のみに賭けた場合】")
    click.echo(f"  対象レース数: {review_data['top1']['total_races']}")
    click.echo(f"  的中数: {review_data['top1']['hits']}")
    click.echo(f"  的中率: {review_data['top1']['hit_rate'] * 100:.1f}%")
    click.echo(f"  投資額: {review_data['top1']['investment']}円")
    click.echo(f"  払戻額: {review_data['top1']['payout']}円")
    click.echo(f"  回収率: {review_data['top1']['return_rate'] * 100:.1f}%")
    click.echo("")
    click.echo("【予測1-3位に各100円賭けた場合】")
    click.echo(f"  賭け数: {review_data['top3']['total_bets']}")
    click.echo(f"  的中数: {review_data['top3']['hits']}")
    click.echo(f"  的中率: {review_data['top3']['hit_rate'] * 100:.1f}%")
    click.echo(f"  投資額: {review_data['top3']['investment']}円")
    click.echo(f"  払戻額: {review_data['top3']['payout']}円")
    click.echo(f"  回収率: {review_data['top3']['return_rate'] * 100:.1f}%")
    click.echo("")
    click.echo("完了")
