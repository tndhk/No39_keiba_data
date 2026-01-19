"""競馬データ収集CLI

clickを使用してCLIコマンドを提供する。
"""

import calendar
import re
from datetime import date

import click
from sqlalchemy import or_

from keiba.db import get_engine, get_session, init_db
from keiba.models import Horse, Jockey, Race, RaceResult, Trainer
from keiba.scrapers import HorseDetailScraper, RaceDetailScraper, RaceListScraper


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
