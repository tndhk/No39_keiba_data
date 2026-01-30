"""予測コマンド（predict, predict-day）の実装"""

from datetime import date
from datetime import datetime as dt
from pathlib import Path

import click

from keiba.cli.formatters.markdown import save_predictions_markdown
from keiba.cli.utils.table_printer import print_prediction_table
from keiba.cli.utils.url_parser import extract_race_id_from_shutuba_url
from keiba.cli.utils.venue_filter import filter_race_ids_by_venue, get_race_ids_for_venue
from keiba.constants import VENUE_CODE_MAP
from keiba.db import get_engine, get_session
from keiba.ml.model_utils import find_latest_model
from keiba.scrapers import RaceListScraper
from keiba.scrapers.race_id_resolver import fetch_race_ids_for_date
from keiba.scrapers.shutuba import ShutubaScraper
from keiba.services.prediction_service import PredictionService


class SQLAlchemyRaceResultRepository:
    """SQLAlchemyを使用した過去成績リポジトリ"""

    def __init__(self, session):
        """初期化

        Args:
            session: SQLAlchemyセッション
        """
        from keiba.models import Race, RaceResult

        self.session = session
        self.RaceResult = RaceResult
        self.Race = Race

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
        from keiba.cli.utils.date_parser import parse_race_date

        # 日付を解析
        try:
            target_date = parse_race_date(before_date)
        except ValueError:
            # 解析失敗時は空リストを返す
            return []

        # 過去のレース結果を取得
        past_results_query = (
            self.session.query(self.RaceResult, self.Race)
            .join(self.Race, self.RaceResult.race_id == self.Race.id)
            .filter(self.RaceResult.horse_id == horse_id)
            .filter(self.Race.date < target_date)
            .order_by(self.Race.date.desc())
            .limit(limit)
        )

        results = []
        for race_result, race_info in past_results_query:
            # 同じレースの出走頭数を取得
            total_runners = (
                self.session.query(self.RaceResult)
                .filter(self.RaceResult.race_id == race_info.id)
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




@click.command()
@click.option("--url", required=True, type=str, help="出馬表ページURL")
@click.option("--db", required=True, type=click.Path(), help="DBファイルパス")
@click.option(
    "--no-ml", is_flag=True, default=False, help="ML予測をスキップし因子スコアのみ表示"
)
def predict(url: str, db: str, no_ml: bool):
    """出馬表URLから予測を実行"""
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
        model_path = None
        if not no_ml:
            db_path = Path(db).resolve()
            model_dir = db_path.parent / "models"
            model_path = find_latest_model(str(model_dir))

        # PredictionServiceで予測を実行
        service = PredictionService(repository=repository, model_path=model_path)
        predictions = service.predict_from_shutuba(shutuba_data)

        # 結果を表形式で表示
        print_prediction_table(predictions, with_ml=not no_ml)


@click.command("predict-day")
@click.option("--date", "date_str", type=str, default=None, help="開催日（YYYY-MM-DD形式）")
@click.option("--venue", required=True, type=str, help="競馬場名（例: 中山）")
@click.option("--db", required=True, type=click.Path(), help="DBファイルパス")
@click.option("--no-ml", is_flag=True, default=False, help="ML予測をスキップ")
def predict_day(date_str: str | None, venue: str, db: str, no_ml: bool):
    """指定日・競馬場の全レースを予測"""
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
    try:
        race_ids = fetch_race_ids_for_date(
            target_date.year, target_date.month, target_date.day, jra_only=True
        )
    except Exception as e:
        click.echo(f"レース一覧取得エラー: {e}")
        raise SystemExit(1)

    # 指定競馬場のレースをフィルタリング
    race_ids = filter_race_ids_by_venue(race_ids, venue_code)

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

        # モデルパスの設定（ML予測を使用する場合）
        model_path = None
        if not no_ml:
            db_path = Path(db).resolve()
            model_dir = db_path.parent / "models"
            model_path = find_latest_model(str(model_dir))

        service = PredictionService(repository=repository, model_path=model_path)

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

                # 新馬戦の場合（空リスト）はスキップ
                if not predictions:
                    click.echo(f"  {shutuba_data.race_number}R: 新馬戦のため予測対象外")
                    predictions_data.append({
                        "race_id": race_id,
                        "race_number": shutuba_data.race_number,
                        "race_name": shutuba_data.race_name,
                        "surface": shutuba_data.surface,
                        "distance": shutuba_data.distance,
                        "predictions": [],
                        "skipped": True,
                    })
                    continue

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
                            "combined_score": p.combined_score,
                            "total_score": p.total_score,
                        }
                        for p in predictions
                    ],
                    "skipped": False,
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
        filepath = save_predictions_markdown(
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
