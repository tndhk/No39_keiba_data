"""BaseSimulatorクラスのテスト"""

from datetime import date
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from keiba.backtest.base_simulator import BaseSimulator
from keiba.models.entry import ShutubaData
from keiba.models.race import Race
from keiba.models.race_result import RaceResult


class ConcreteSimulator(BaseSimulator):
    """テスト用の具象シミュレータ"""

    def simulate_race(self, race_id: str, **kwargs):
        """テスト用ダミー実装"""
        return {"race_id": race_id}

    def _build_summary(self, period_from: str, period_to: str, race_results: list):
        """テスト用ダミー実装"""
        return {
            "period_from": period_from,
            "period_to": period_to,
            "total_races": len(race_results),
        }


class TestBaseSimulator:
    """BaseSimulatorクラスのテスト"""

    @pytest.fixture
    def db_path(self, tmp_path):
        """テスト用DBパス"""
        return str(tmp_path / "test.db")

    @pytest.fixture
    def simulator(self, db_path):
        """テスト用シミュレータ"""
        return ConcreteSimulator(db_path)

    def test_get_session_returns_session(self, simulator):
        """_get_session()がSessionを返す"""
        session = simulator._get_session()
        assert isinstance(session, Session)
        session.close()

    def test_get_races_in_period_filters_by_date_range(
        self, simulator, db_path, sample_races
    ):
        """_get_races_in_period()が日付範囲でフィルタリング"""
        # DBにサンプルレースを追加
        engine = create_engine(f"sqlite:///{db_path}")
        from keiba.db import Base

        Base.metadata.create_all(engine)

        with Session(engine) as session:
            for race in sample_races:
                session.add(race)
            session.commit()

        # 2024-01-15〜2024-01-20の期間でフィルタ
        with simulator._get_session() as session:
            races = simulator._get_races_in_period(
                session, "2024-01-15", "2024-01-20", None
            )

        # 期間内の2レースのみ取得されることを確認
        assert len(races) == 2
        assert all(
            date(2024, 1, 15) <= race.date <= date(2024, 1, 20) for race in races
        )

    def test_get_races_in_period_filters_by_venue(
        self, simulator, db_path, sample_races
    ):
        """_get_races_in_period()が会場でフィルタリング"""
        # DBにサンプルレースを追加
        engine = create_engine(f"sqlite:///{db_path}")
        from keiba.db import Base

        Base.metadata.create_all(engine)

        with Session(engine) as session:
            for race in sample_races:
                session.add(race)
            session.commit()

        # 中山のみ取得
        with simulator._get_session() as session:
            races = simulator._get_races_in_period(
                session, "2024-01-01", "2024-12-31", ["中山"]
            )

        # 中山の2レースのみ取得されることを確認
        assert len(races) == 2
        assert all(race.course == "中山" for race in races)

    def test_build_shutuba_from_race_results_returns_immutable_entries(self, simulator):
        """_build_shutuba_from_race_results()がタプルのentriesを返す"""
        # モックレースとレース結果を作成
        race = Race(
            id="2024010501",
            name="テストレース",
            race_number=1,
            course="中山",
            distance=1600,
            surface="芝",
            date=date(2024, 1, 5),
            track_condition="良",
        )

        # モックホースとジョッキーを作成
        mock_horse = Mock()
        mock_horse.name = "テスト馬"
        mock_jockey = Mock()
        mock_jockey.name = "テスト騎手"

        result = RaceResult(
            race_id="2024010501",
            horse_id="TEST001",
            horse_number=1,
            bracket_number=1,
            jockey_id="JOC001",
            impost=54.0,
            sex="牡",
            age=3,
        )
        result.horse = mock_horse
        result.jockey = mock_jockey

        # ShutubaDataを構築
        shutuba_data = simulator._build_shutuba_from_race_results(race, [result])

        # entriesがタプルであることを確認（イミュータブル）
        assert isinstance(shutuba_data.entries, tuple)
        assert len(shutuba_data.entries) == 1
        assert shutuba_data.entries[0].horse_number == 1
        assert shutuba_data.entries[0].horse_name == "テスト馬"
        assert shutuba_data.entries[0].jockey_name == "テスト騎手"

    def test_build_shutuba_from_race_results_handles_missing_horse_info(
        self, simulator
    ):
        """_build_shutuba_from_race_results()が馬情報欠落時に空文字を返す"""
        race = Race(
            id="2024010501",
            name="テストレース",
            race_number=1,
            course="中山",
            distance=1600,
            surface="芝",
            date=date(2024, 1, 5),
            track_condition="良",
        )

        result = RaceResult(
            race_id="2024010501",
            horse_id="TEST001",
            horse_number=1,
            bracket_number=1,
            jockey_id="JOC001",
            impost=54.0,
            sex="牡",
            age=3,
        )
        result.horse = None  # 馬情報なし
        result.jockey = None  # 騎手情報なし

        shutuba_data = simulator._build_shutuba_from_race_results(race, [result])

        assert shutuba_data.entries[0].horse_name == ""
        assert shutuba_data.entries[0].jockey_name == ""


@pytest.fixture
def sample_races():
    """テスト用サンプルレース"""
    return [
        Race(
            id="2024011001",
            name="レース1",
            race_number=1,
            course="中山",
            distance=1600,
            surface="芝",
            date=date(2024, 1, 10),
            track_condition="良",
        ),
        Race(
            id="2024011601",
            name="レース2",
            race_number=1,
            course="中山",
            distance=2000,
            surface="芝",
            date=date(2024, 1, 16),
            track_condition="良",
        ),
        Race(
            id="2024011801",
            name="レース3",
            race_number=1,
            course="京都",
            distance=1800,
            surface="芝",
            date=date(2024, 1, 18),
            track_condition="良",
        ),
        Race(
            id="2024012501",
            name="レース4（期間外）",
            race_number=1,
            course="東京",
            distance=2400,
            surface="芝",
            date=date(2024, 1, 25),
            track_condition="良",
        ),
    ]
