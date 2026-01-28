"""Tests for SQLAlchemyRaceResultRepository (backtest usage)"""

import pytest
from datetime import date
from keiba.repositories.race_result_repository import SQLAlchemyRaceResultRepository
from keiba.models import Horse, Race, RaceResult, Jockey, Trainer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db_session():
    """テスト用のインメモリDBセッションを作成"""
    from keiba.db import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()


def test_get_past_results_includes_race_name(db_session):
    """get_past_results()がrace_nameフィールドを含むことを検証"""
    # Arrange: テストデータを作成
    jockey = Jockey(id="jockey_001", name="Test Jockey")
    trainer = Trainer(id="trainer_001", name="Test Trainer")
    horse = Horse(
        id="horse_001",
        name="Test Horse",
        sex="牡",
        birth_year=2022,
        sire="Test Sire",
        dam_sire="Test Dam Sire",
    )

    race = Race(
        id="202501010101",
        name="G1 Test Stakes",
        date=date(2025, 1, 1),
        course="Tokyo",
        race_number=11,
        surface="turf",
        distance=2000,
        track_condition="良",
    )

    race_result = RaceResult(
        race_id="202501010101",
        horse_id="horse_001",
        jockey_id="jockey_001",
        trainer_id="trainer_001",
        finish_position=1,
        bracket_number=5,
        horse_number=9,
        time="2:01.2",
        margin="",
        last_3f=33.8,
        odds=3.5,
        popularity=2,
        passing_order="05-05-03",
    )

    db_session.add(jockey)
    db_session.add(trainer)
    db_session.add(horse)
    db_session.add(race)
    db_session.add(race_result)
    db_session.commit()

    # Act: リポジトリを使って過去成績を取得
    repository = SQLAlchemyRaceResultRepository(db_session)
    results = repository.get_past_results(
        horse_id="horse_001", before_date="2025-01-10", limit=20
    )

    # Assert: race_nameフィールドが含まれることを検証（現在は存在しないため失敗するはず）
    assert len(results) == 1
    result = results[0]

    # 既存フィールド
    assert result["horse_id"] == "horse_001"
    assert result["course"] == "Tokyo"

    # 追加すべきフィールド（現在は存在しないため失敗するはず）
    assert result["race_name"] == "G1 Test Stakes"


def test_get_horse_info_returns_pedigree(db_session):
    """get_horse_info()が血統情報を返すことを検証"""
    # Arrange: テストデータを作成
    horse = Horse(
        id="horse_002",
        name="Test Horse 2",
        sex="牝",
        birth_year=2021,
        sire="Deep Impact",
        dam="Test Dam",
        dam_sire="Sunday Silence",
    )

    db_session.add(horse)
    db_session.commit()

    # Act: リポジトリを使って馬の情報を取得
    repository = SQLAlchemyRaceResultRepository(db_session)
    horse_info = repository.get_horse_info("horse_002")

    # Assert: 血統情報が含まれることを検証
    assert horse_info is not None
    assert horse_info["horse_id"] == "horse_002"
    assert horse_info["name"] == "Test Horse 2"
    assert horse_info["sire"] == "Deep Impact"
    assert horse_info["dam_sire"] == "Sunday Silence"


def test_get_horse_info_returns_none_for_nonexistent_horse(db_session):
    """get_horse_info()が存在しない馬に対してNoneを返すことを検証"""
    # Act: 存在しない馬IDで取得
    repository = SQLAlchemyRaceResultRepository(db_session)
    horse_info = repository.get_horse_info("nonexistent_horse")

    # Assert: Noneが返されることを検証
    assert horse_info is None
