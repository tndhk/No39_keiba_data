"""過去成績リポジトリ"""

import re
from datetime import datetime

from keiba.models import Horse, Race, RaceResult


class SQLAlchemyRaceResultRepository:
    """SQLAlchemyを使用した過去成績リポジトリ"""

    def __init__(self, session):
        """初期化

        Args:
            session: SQLAlchemyセッション
        """
        self.session = session

    def _parse_date(self, date_str: str):
        """日付文字列を解析（マルチフォーマット対応）

        Args:
            date_str: 日付文字列（ISO形式 "YYYY-MM-DD" または 日本語形式 "YYYY年M月D日"）

        Returns:
            解析された日付オブジェクト

        Raises:
            ValueError: 日付の解析に失敗した場合
        """
        # ISO形式を試行
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

        # 日本語形式を試行
        match = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_str)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            return datetime(year, month, day).date()

        raise ValueError(f"Invalid date format: {date_str}")

    def get_past_results(
        self, horse_id: str, before_date: str, limit: int = 20
    ) -> list[dict]:
        """指定日より前の過去成績を取得

        Args:
            horse_id: 馬ID
            before_date: この日付より前の成績を取得（ISO形式 "YYYY-MM-DD" または 日本語形式 "YYYY年M月D日"）
            limit: 最大取得件数

        Returns:
            過去成績のリスト
        """
        # 日付を解析
        try:
            target_date = self._parse_date(before_date)
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
                    "race_name": race_info.name,
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
