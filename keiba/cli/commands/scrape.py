"""スクレイピングコマンド

レースデータと馬情報を収集するCLIコマンドを提供する。
"""

import calendar
from datetime import date, datetime

import click
from sqlalchemy import or_

from keiba.cli.utils.date_parser import parse_race_date
from keiba.cli.utils.url_parser import extract_race_id_from_url
from keiba.cli.utils.venue_filter import filter_race_ids_by_venue, get_race_ids_for_venue
from keiba.constants import VENUE_CODE_MAP
from keiba.db import get_engine, get_session, init_db
from keiba.models import Horse, Jockey, Race, RaceResult, Trainer
from keiba.scrapers import HorseDetailScraper, RaceDetailScraper, RaceListScraper
from keiba.scrapers.race_id_resolver import fetch_race_ids_for_date
from keiba.scrapers.shutuba import ShutubaScraper


@click.command()
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


@click.command()
@click.option("--db", required=True, type=click.Path(), help="DBファイルパス")
@click.option("--limit", default=100, type=int, help="取得する馬の数（デフォルト: 100）")
@click.option("--date", default=None, type=str, help="開催日（YYYY-MM-DD形式）")
@click.option("--venue", default=None, type=str, help="競馬場名（例: 中山）")
@click.option("--verbose", "-v", is_flag=True, default=False, help="詳細出力")
def scrape_horses(db: str, limit: int, date: str | None, venue: str | None, verbose: bool):
    """詳細未取得の馬情報を収集"""
    click.echo(f"馬詳細データ収集開始")
    click.echo(f"データベース: {db}")

    if date:
        click.echo(f"モード: 出馬表ベース ({date})")
        if venue:
            click.echo(f"会場: {venue}")
    else:
        click.echo(f"モード: 全馬対象")
        click.echo(f"取得上限: {limit}件")

    # DBを初期化
    engine = get_engine(db)
    init_db(engine)

    # スクレイパーを初期化
    horse_detail_scraper = HorseDetailScraper()

    # 統計情報
    total_processed = 0
    updated_horses = 0
    no_update_count = 0
    errors = 0

    with get_session(engine) as session:
        # 対象馬を収集
        if date:
            # 新モード: 出馬表ベースで対象馬を絞り込み
            target_horses = _collect_horses_from_shutuba(session, date, venue)
        else:
            # 既存モード: sireがNullの馬をlimit件取得
            target_horses = (
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

        if not target_horses:
            click.echo("対象の馬はありません。")
            return

        click.echo(f"対象馬: {len(target_horses)}件")
        click.echo("")

        for horse in target_horses:
            total_processed += 1
            click.echo(f"  [{total_processed}/{len(target_horses)}] {horse.name} ({horse.id})...")

            try:
                horse_data = horse_detail_scraper.fetch_horse_detail(horse.id)
                field_count = _update_horse(session, horse, horse_data)

                # parse_warnings を表示
                if horse_data.get("parse_warnings"):
                    for w in horse_data["parse_warnings"]:
                        click.echo(f"    警告: {w}")

                if field_count == 0:
                    click.echo(f"    警告: 更新フィールドなし（パース失敗の可能性）")
                    no_update_count += 1
                else:
                    updated_horses += 1
                    if verbose:
                        click.echo(f"    更新: {field_count}フィールド")
                        if horse_data.get("sire"):
                            click.echo(f"    血統: {horse_data.get('sire')} / {horse_data.get('dam')} / {horse_data.get('dam_sire')}")
            except Exception as e:
                errors += 1
                click.echo(f"    エラー: {e}")
                continue

    click.echo("")
    click.echo("=" * 50)
    click.echo(f"完了")
    click.echo(f"  処理数: {total_processed}")
    click.echo(f"  更新成功: {updated_horses}")
    click.echo(f"  更新なし: {no_update_count}")
    click.echo(f"  エラー: {errors}")


def _collect_horses_from_shutuba(
    session, date_str: str, venue: str | None
) -> list[Horse]:
    """出馬表から対象馬を収集する

    Args:
        session: SQLAlchemyセッション
        date_str: 日付文字列（YYYY-MM-DD形式）
        venue: 競馬場名（省略時は全JRA会場）

    Returns:
        sireが未取得の馬のリスト
    """
    # 日付を解析
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as e:
        click.echo(f"日付形式エラー: {e}")
        return []

    # レース一覧を取得
    try:
        race_ids = fetch_race_ids_for_date(
            target_date.year, target_date.month, target_date.day, jra_only=True
        )
    except Exception as e:
        click.echo(f"レース一覧取得エラー: {e}")
        return []

    # 会場でフィルタリング
    if venue:
        if venue not in VENUE_CODE_MAP:
            click.echo(f"無効な競馬場名: {venue}")
            return []
        venue_code = VENUE_CODE_MAP[venue]
        race_ids = filter_race_ids_by_venue(race_ids, venue_code)

    click.echo(f"対象レース数: {len(race_ids)}")

    # 各レースの出馬表から horse_id を収集
    shutuba_scraper = ShutubaScraper()
    horse_ids = set()

    for race_id in race_ids:
        try:
            shutuba_data = shutuba_scraper.fetch_shutuba(race_id)
            for entry in shutuba_data.entries:
                horse_ids.add(entry.horse_id)
        except Exception as e:
            click.echo(f"  出馬表取得エラー ({race_id}): {e}")
            continue

    click.echo(f"出走予定馬数: {len(horse_ids)}")

    # DB照合: sire IS NULL の馬だけを抽出（取得済みはスキップ）
    target_horses = []
    for horse_id in horse_ids:
        horse = session.get(Horse, horse_id)

        if not horse:
            # DB未登録の馬は仮レコードを作成
            horse = Horse(
                id=horse_id,
                name="未取得",
                sex="不明",
                birth_year=0,
            )
            session.add(horse)
            session.flush()  # IDを確定させる

        # sire が既に取得済みの馬はスキップ
        if horse.sire is not None:
            continue

        target_horses.append(horse)

    return target_horses


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


def _update_horse(session, horse: Horse, horse_data: dict) -> int:
    """馬情報を更新する

    Args:
        session: SQLAlchemyセッション
        horse: 更新対象のHorseオブジェクト
        horse_data: スクレイピングで取得した馬データ

    Returns:
        更新したフィールド数
    """
    updated_count = 0

    # 基本情報
    if horse_data.get("name"):
        horse.name = horse_data["name"]
        updated_count += 1
    if horse_data.get("sex"):
        horse.sex = horse_data["sex"]
        updated_count += 1
    if horse_data.get("birth_year"):
        horse.birth_year = horse_data["birth_year"]
        updated_count += 1

    # 血統情報
    if horse_data.get("sire"):
        horse.sire = horse_data["sire"]
        updated_count += 1
    if horse_data.get("dam"):
        horse.dam = horse_data["dam"]
        updated_count += 1
    if horse_data.get("dam_sire"):
        horse.dam_sire = horse_data["dam_sire"]
        updated_count += 1

    # 基本情報
    if horse_data.get("coat_color"):
        horse.coat_color = horse_data["coat_color"]
        updated_count += 1
    if horse_data.get("birthplace"):
        horse.birthplace = horse_data["birthplace"]
        updated_count += 1

    # 関連ID
    if horse_data.get("trainer_id"):
        horse.trainer_id = horse_data["trainer_id"]
        updated_count += 1
    if horse_data.get("owner_id"):
        horse.owner_id = horse_data["owner_id"]
        updated_count += 1
    if horse_data.get("breeder_id"):
        horse.breeder_id = horse_data["breeder_id"]
        updated_count += 1

    # 成績情報
    if horse_data.get("total_races") is not None:
        horse.total_races = horse_data["total_races"]
        updated_count += 1
    if horse_data.get("total_wins") is not None:
        horse.total_wins = horse_data["total_wins"]
        updated_count += 1
    if horse_data.get("total_earnings") is not None:
        horse.total_earnings = horse_data["total_earnings"]
        updated_count += 1

    return updated_count
