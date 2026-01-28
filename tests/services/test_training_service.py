"""Tests for TrainingService"""

import pytest
from datetime import date
from keiba.services.training_service import get_horse_past_results
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


def test_get_horse_past_results_includes_all_required_fields(db_session):
    """get_horse_past_results()が全ての必須フィールドを含むことを検証"""
    # Arrange: テストデータを作成
    jockey = Jockey(
        id="jockey_001",
        name="Test Jockey"
    )

    trainer = Trainer(
        id="trainer_001",
        name="Test Trainer"
    )

    horse = Horse(
        id="horse_001",
        name="Test Horse",
        sex="牡",
        birth_year=2022,
        sire="Test Sire",
        dam_sire="Test Dam Sire"
    )

    race = Race(
        id="202501010101",
        name="Test Race",
        date=date(2025, 1, 1),
        course="Tokyo",
        race_number=1,
        surface="turf",
        distance=1600,
        track_condition="良"
    )

    race_result = RaceResult(
        race_id="202501010101",
        horse_id="horse_001",
        jockey_id="jockey_001",
        trainer_id="trainer_001",
        finish_position=1,
        bracket_number=1,
        horse_number=1,
        time="1:36.5",
        margin="",
        last_3f=35.2,
        odds=3.5,
        popularity=2,
        passing_order="01-01"
    )

    db_session.add(jockey)
    db_session.add(trainer)
    db_session.add(horse)
    db_session.add(race)
    db_session.add(race_result)
    db_session.commit()

    # Act: 過去成績を取得
    results = get_horse_past_results(db_session, "horse_001")

    # Assert: 全ての必須フィールドが含まれていることを検証
    assert len(results) == 1
    result = results[0]

    # 既存フィールド
    assert result["horse_id"] == "horse_001"
    assert result["finish_position"] == 1
    assert result["total_runners"] == 1
    assert result["surface"] == "turf"
    assert result["distance"] == 1600
    assert result["time"] == "1:36.5"
    assert result["last_3f"] == 35.2
    assert result["race_date"] == date(2025, 1, 1)

    # 追加すべきフィールド（現在は存在しないため失敗するはず）
    assert result["odds"] == 3.5
    assert result["popularity"] == 2
    assert result["passing_order"] == "01-01"
    assert result["course"] == "Tokyo"
    assert result["race_name"] == "Test Race"
    assert result["track_condition"] == "良"


def test_get_horse_past_results_handles_missing_optional_fields(db_session):
    """オプショナルなフィールドが欠損している場合の処理を検証"""
    # Arrange: 一部フィールドがNullのテストデータ
    jockey = Jockey(
        id="jockey_002",
        name="Test Jockey 2"
    )

    trainer = Trainer(
        id="trainer_002",
        name="Test Trainer 2"
    )

    horse = Horse(
        id="horse_002",
        name="Test Horse 2",
        sex="牝",
        birth_year=2021
    )

    race = Race(
        id="202501020101",
        name="Test Race 2",
        date=date(2025, 1, 2),
        course="Nakayama",
        race_number=2,
        surface="dirt",
        distance=1200
    )

    race_result = RaceResult(
        race_id="202501020101",
        horse_id="horse_002",
        jockey_id="jockey_002",
        trainer_id="trainer_002",
        finish_position=3,
        bracket_number=2,
        horse_number=2,
        time="1:12.0",
        margin="0.5",
        last_3f=None,
        odds=None,
        popularity=None,
        passing_order=None
    )

    db_session.add(jockey)
    db_session.add(trainer)
    db_session.add(horse)
    db_session.add(race)
    db_session.add(race_result)
    db_session.commit()

    # Act: 過去成績を取得
    results = get_horse_past_results(db_session, "horse_002")

    # Assert: Noneが正しく設定されることを検証
    assert len(results) == 1
    result = results[0]

    assert result["odds"] is None
    assert result["popularity"] is None
    assert result["passing_order"] is None
    assert result["course"] == "Nakayama"  # courseは必須フィールド
    assert result["race_name"] == "Test Race 2"  # race_nameは必須フィールド
    assert result["track_condition"] is None or result["track_condition"] == ""
