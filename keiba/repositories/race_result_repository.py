"""過去成績リポジトリ"""

from keiba.cli.utils.date_parser import parse_race_date
from keiba.models import Horse, Race, RaceResult


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

    def get_horse_info(self, horse_id: str) -> dict | None:
        """馬の基本情報と血統情報を取得

        Args:
            horse_id: 馬ID

        Returns:
            馬情報の辞書（存在しない場合はNone）
        """
        horse = self.session.query(Horse).filter(Horse.id == horse_id).first()
        if horse is None:
            return None

        return {
            "horse_id": horse.id,
            "name": horse.name,
            "sex": horse.sex,
            "birth_year": horse.birth_year,
            "sire": horse.sire,
            "dam": horse.dam,
            "dam_sire": horse.dam_sire,
        }
