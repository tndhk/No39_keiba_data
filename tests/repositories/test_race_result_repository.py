"""RaceResultRepositoryのテスト"""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from keiba.db import Base
from keiba.models.horse import Horse
from keiba.models.race import Race
from keiba.models.race_result import RaceResult
from keiba.repositories.race_result_repository import SQLAlchemyRaceResultRepository


class TestSQLAlchemyRaceResultRepository:
    """SQLAlchemyRaceResultRepositoryのテスト"""

    @pytest.fixture
    def db_session(self, tmp_path):
        """テスト用DBセッション"""
        db_path = tmp_path / "test.db"
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        session = Session(engine)
        yield session
        session.close()

    @pytest.fixture
    def repository(self, db_session):
        """テスト用リポジトリ"""
        return SQLAlchemyRaceResultRepository(db_session)

    @pytest.fixture
    def sample_data(self, db_session):
        """サンプルデータをDBに追加"""
        # レース作成
        race1 = Race(
            id="2024010101",
            name="テストレース1",
            race_number=1,
            course="中山",
            distance=1600,
            surface="芝",
            date=date(2024, 1, 1),
            track_condition="良",
        )
        race2 = Race(
            id="2024011501",
            name="テストレース2",
            race_number=1,
            course="京都",
            distance=2000,
            surface="芝",
            date=date(2024, 1, 15),
            track_condition="良",
        )

        # 馬作成
        horse = Horse(
            id="TEST001",
            name="テスト馬",
            sex="牡",
            birth_year=2020,
            sire="テスト父",
            dam="テスト母",
            dam_sire="テスト母父",
        )

        # レース結果作成
        result1 = RaceResult(
            race_id="2024010101",
            horse_id="TEST001",
            jockey_id="JOC001",
            trainer_id="TRA001",
            horse_number=1,
            bracket_number=1,
            finish_position=3,
            time="1:35.2",
            margin="0.5",
            last_3f="35.8",
            odds=5.2,
            popularity=2,
            passing_order="3-3-3",
        )
        result2 = RaceResult(
            race_id="2024011501",
            horse_id="TEST001",
            jockey_id="JOC002",
            trainer_id="TRA002",
            horse_number=2,
            bracket_number=2,
            finish_position=1,
            time="2:01.5",
            margin="0.0",
            last_3f="34.5",
            odds=3.1,
            popularity=1,
            passing_order="1-1-1",
        )

        db_session.add_all([race1, race2, horse, result1, result2])
        db_session.commit()

    def test_get_past_results_with_iso_date_format(
        self, repository, db_session, sample_data
    ):
        """ISO形式の日付（YYYY-MM-DD）で過去成績を取得できる"""
        results = repository.get_past_results("TEST001", "2024-01-20")

        assert len(results) == 2
        assert results[0]["race_name"] == "テストレース2"
        assert results[1]["race_name"] == "テストレース1"

    def test_get_past_results_with_japanese_date_format(
        self, repository, db_session, sample_data
    ):
        """日本語形式の日付（YYYY年M月D日）で過去成績を取得できる"""
        results = repository.get_past_results("TEST001", "2024年1月20日")

        assert len(results) == 2
        assert results[0]["race_name"] == "テストレース2"
        assert results[1]["race_name"] == "テストレース1"

    def test_get_past_results_returns_race_name(
        self, repository, db_session, sample_data
    ):
        """get_past_results()がrace_nameフィールドを返す"""
        results = repository.get_past_results("TEST001", "2024-01-20")

        assert len(results) == 2
        assert "race_name" in results[0]
        assert results[0]["race_name"] == "テストレース2"

    def test_get_past_results_filters_by_date(
        self, repository, db_session, sample_data
    ):
        """指定日より前のレースのみ取得する"""
        results = repository.get_past_results("TEST001", "2024-01-10")

        assert len(results) == 1
        assert results[0]["race_name"] == "テストレース1"

    def test_get_past_results_returns_empty_for_invalid_date(self, repository):
        """不正な日付形式の場合は空リストを返す"""
        results = repository.get_past_results("TEST001", "invalid-date")

        assert results == []

    def test_get_past_results_includes_all_fields(
        self, repository, db_session, sample_data
    ):
        """get_past_results()が全ての必要なフィールドを返す"""
        results = repository.get_past_results("TEST001", "2024-01-20", limit=1)

        assert len(results) == 1
        result = results[0]

        # 必須フィールドの確認
        assert result["horse_id"] == "TEST001"
        assert result["finish_position"] == 1
        assert result["total_runners"] == 1
        assert result["surface"] == "芝"
        assert result["distance"] == 2000
        assert result["time"] == "2:01.5"
        assert result["last_3f"] == 34.5
        assert result["race_date"] == date(2024, 1, 15)
        assert result["odds"] == 3.1
        assert result["popularity"] == 1
        assert result["passing_order"] == "1-1-1"
        assert result["course"] == "京都"
        assert result["race_name"] == "テストレース2"

    def test_get_horse_info_returns_sire(self, repository, db_session, sample_data):
        """get_horse_info()がsireフィールドを返す"""
        info = repository.get_horse_info("TEST001")

        assert info is not None
        assert info["sire"] == "テスト父"
        assert info["dam_sire"] == "テスト母父"

    def test_get_horse_info_returns_none_for_nonexistent_horse(self, repository):
        """存在しない馬の場合はNoneを返す"""
        info = repository.get_horse_info("NONEXISTENT")

        assert info is None
