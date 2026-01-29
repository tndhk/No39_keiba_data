"""バックテストシミュレータの基底クラス

4つのシミュレータ（複勝・単勝・馬連・三連複）の共通機能を提供する抽象基底クラス
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Generic, TypeVar

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from keiba.models.entry import RaceEntry, ShutubaData
from keiba.models.race import Race
from keiba.models.race_result import RaceResult
from keiba.scrapers.race_detail import RaceDetailScraper

logger = logging.getLogger(__name__)

# ジェネリック型変数
TRaceResult = TypeVar("TRaceResult")
TSummary = TypeVar("TSummary")


class BaseSimulator(ABC, Generic[TRaceResult, TSummary]):
    """バックテストシミュレータの基底クラス

    各シミュレータ（複勝・単勝・馬連・三連複）で共通する機能を提供する。
    サブクラスは simulate_race() と _build_summary() を実装する必要がある。
    """

    def __init__(self, db_path: str) -> None:
        """シミュレータを初期化

        Args:
            db_path: データベースファイルのパス
        """
        self._db_path = db_path
        self._scraper = RaceDetailScraper()  # スクレイパーインスタンスを再利用

    def _get_session(self) -> Session:
        """DBセッションを取得

        Returns:
            Session: SQLAlchemyセッション
        """
        engine = create_engine(f"sqlite:///{self._db_path}")
        return Session(engine)

    def _get_races_in_period(
        self, session: Session, from_date: str, to_date: str, venues: list[str] | None
    ) -> list[Race]:
        """期間内のレースを取得

        Args:
            session: DBセッション
            from_date: 開始日 (YYYY-MM-DD形式)
            to_date: 終了日 (YYYY-MM-DD形式)
            venues: 対象会場リスト（Noneの場合は全会場）

        Returns:
            list[Race]: 対象レースのリスト
        """
        from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
        to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()

        stmt = select(Race).where(Race.date >= from_dt, Race.date <= to_dt)
        if venues:
            stmt = stmt.where(Race.course.in_(venues))
        stmt = stmt.order_by(Race.date, Race.race_number)

        return list(session.execute(stmt).scalars().all())

    def _build_shutuba_from_race_results(
        self, race: Race, results: list[RaceResult]
    ) -> ShutubaData:
        """RaceResultのリストからShutubaDataを構築する

        Args:
            race: Raceオブジェクト
            results: RaceResultのリスト

        Returns:
            ShutubaData: 出馬表データ（entriesはイミュータブルなタプル）
        """
        # タプル内包表記でイミュータブルに構築
        entries = tuple(
            RaceEntry(
                horse_id=result.horse_id,
                horse_name=result.horse.name if result.horse else "",
                horse_number=result.horse_number,
                bracket_number=result.bracket_number,
                jockey_id=result.jockey_id,
                jockey_name=result.jockey.name if result.jockey else "",
                impost=result.impost if result.impost is not None else 0.0,
                sex=result.sex,
                age=result.age,
            )
            for result in results
        )

        return ShutubaData(
            race_id=race.id,
            race_name=race.name,
            race_number=race.race_number,
            course=race.course,
            distance=race.distance,
            surface=race.surface,
            date=race.date.strftime("%Y-%m-%d"),
            entries=entries,
            track_condition=race.track_condition,
        )

    def simulate_period(
        self,
        from_date: str,
        to_date: str,
        venues: list[str] | None = None,
        **kwargs,
    ) -> TSummary:
        """期間シミュレーションを実行

        Args:
            from_date: 開始日 (YYYY-MM-DD形式)
            to_date: 終了日 (YYYY-MM-DD形式)
            venues: 対象会場リスト（Noneの場合は全会場）
            **kwargs: サブクラス固有のパラメータ

        Returns:
            TSummary: 期間サマリー
        """
        race_results = []

        with self._get_session() as session:
            races = self._get_races_in_period(session, from_date, to_date, venues)

        for race in races:
            try:
                result = self.simulate_race(race.id, **kwargs)
                race_results.append(result)
            except Exception as e:
                logger.warning(f"Race {race.id} simulation failed: {e}")
                continue

        return self._build_summary(from_date, to_date, race_results)

    @abstractmethod
    def simulate_race(self, race_id: str, **kwargs) -> TRaceResult:
        """1レースのシミュレーションを実行

        Args:
            race_id: レースID
            **kwargs: サブクラス固有のパラメータ

        Returns:
            TRaceResult: シミュレーション結果
        """
        ...

    @abstractmethod
    def _build_summary(
        self, period_from: str, period_to: str, race_results: list[TRaceResult]
    ) -> TSummary:
        """期間サマリーを構築

        Args:
            period_from: 期間開始日
            period_to: 期間終了日
            race_results: レース別結果のリスト

        Returns:
            TSummary: 期間サマリー
        """
        ...
