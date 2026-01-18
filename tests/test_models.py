"""Horse, Jockey, Trainerモデルのテスト

TDDのREDフェーズ: まずテストを作成し、FAILを確認する。
"""

from datetime import datetime

import pytest
from sqlalchemy import select

from keiba.db import get_engine, get_session, init_db
from keiba.models import Horse, Jockey, Trainer


@pytest.fixture
def engine():
    """インメモリSQLiteエンジンを作成"""
    return get_engine(":memory:")


@pytest.fixture
def initialized_engine(engine):
    """テーブルが初期化されたエンジン"""
    init_db(engine)
    return engine


class TestHorse:
    """Horseモデルのテスト"""

    def test_create_instance(self):
        """Horseインスタンスを作成できる"""
        horse = Horse(
            id="2019104308",
            name="テスト馬",
            sex="牡",
            birth_year=2019,
        )
        assert horse.id == "2019104308"
        assert horse.name == "テスト馬"
        assert horse.sex == "牡"
        assert horse.birth_year == 2019

    def test_save_and_retrieve(self, initialized_engine):
        """HorseをDBに保存して取得できる"""
        with get_session(initialized_engine) as session:
            horse = Horse(
                id="2019104308",
                name="テスト馬",
                sex="牡",
                birth_year=2019,
            )
            session.add(horse)

        with get_session(initialized_engine) as session:
            result = session.execute(
                select(Horse).where(Horse.id == "2019104308")
            ).scalar_one()
            assert result.name == "テスト馬"
            assert result.sex == "牡"
            assert result.birth_year == 2019

    def test_created_at_default(self, initialized_engine):
        """created_atにデフォルト値が設定される"""
        before = datetime.utcnow()
        with get_session(initialized_engine) as session:
            horse = Horse(
                id="2019104308",
                name="テスト馬",
                sex="牡",
                birth_year=2019,
            )
            session.add(horse)
            session.flush()
            assert horse.created_at is not None
            assert horse.created_at >= before

    def test_updated_at_default(self, initialized_engine):
        """updated_atにデフォルト値が設定される"""
        before = datetime.utcnow()
        with get_session(initialized_engine) as session:
            horse = Horse(
                id="2019104308",
                name="テスト馬",
                sex="牡",
                birth_year=2019,
            )
            session.add(horse)
            session.flush()
            assert horse.updated_at is not None
            assert horse.updated_at >= before

    def test_repr(self):
        """__repr__が適切な文字列を返す"""
        horse = Horse(
            id="2019104308",
            name="テスト馬",
            sex="牡",
            birth_year=2019,
        )
        repr_str = repr(horse)
        assert "Horse" in repr_str
        assert "2019104308" in repr_str
        assert "テスト馬" in repr_str


class TestJockey:
    """Jockeyモデルのテスト"""

    def test_create_instance(self):
        """Jockeyインスタンスを作成できる"""
        jockey = Jockey(
            id="05203",
            name="テスト騎手",
        )
        assert jockey.id == "05203"
        assert jockey.name == "テスト騎手"

    def test_save_and_retrieve(self, initialized_engine):
        """JockeyをDBに保存して取得できる"""
        with get_session(initialized_engine) as session:
            jockey = Jockey(
                id="05203",
                name="テスト騎手",
            )
            session.add(jockey)

        with get_session(initialized_engine) as session:
            result = session.execute(
                select(Jockey).where(Jockey.id == "05203")
            ).scalar_one()
            assert result.name == "テスト騎手"

    def test_created_at_default(self, initialized_engine):
        """created_atにデフォルト値が設定される"""
        before = datetime.utcnow()
        with get_session(initialized_engine) as session:
            jockey = Jockey(
                id="05203",
                name="テスト騎手",
            )
            session.add(jockey)
            session.flush()
            assert jockey.created_at is not None
            assert jockey.created_at >= before

    def test_updated_at_default(self, initialized_engine):
        """updated_atにデフォルト値が設定される"""
        before = datetime.utcnow()
        with get_session(initialized_engine) as session:
            jockey = Jockey(
                id="05203",
                name="テスト騎手",
            )
            session.add(jockey)
            session.flush()
            assert jockey.updated_at is not None
            assert jockey.updated_at >= before

    def test_repr(self):
        """__repr__が適切な文字列を返す"""
        jockey = Jockey(
            id="05203",
            name="テスト騎手",
        )
        repr_str = repr(jockey)
        assert "Jockey" in repr_str
        assert "05203" in repr_str
        assert "テスト騎手" in repr_str


class TestTrainer:
    """Trainerモデルのテスト"""

    def test_create_instance(self):
        """Trainerインスタンスを作成できる"""
        trainer = Trainer(
            id="01084",
            name="テスト調教師",
        )
        assert trainer.id == "01084"
        assert trainer.name == "テスト調教師"

    def test_save_and_retrieve(self, initialized_engine):
        """TrainerをDBに保存して取得できる"""
        with get_session(initialized_engine) as session:
            trainer = Trainer(
                id="01084",
                name="テスト調教師",
            )
            session.add(trainer)

        with get_session(initialized_engine) as session:
            result = session.execute(
                select(Trainer).where(Trainer.id == "01084")
            ).scalar_one()
            assert result.name == "テスト調教師"

    def test_created_at_default(self, initialized_engine):
        """created_atにデフォルト値が設定される"""
        before = datetime.utcnow()
        with get_session(initialized_engine) as session:
            trainer = Trainer(
                id="01084",
                name="テスト調教師",
            )
            session.add(trainer)
            session.flush()
            assert trainer.created_at is not None
            assert trainer.created_at >= before

    def test_updated_at_default(self, initialized_engine):
        """updated_atにデフォルト値が設定される"""
        before = datetime.utcnow()
        with get_session(initialized_engine) as session:
            trainer = Trainer(
                id="01084",
                name="テスト調教師",
            )
            session.add(trainer)
            session.flush()
            assert trainer.updated_at is not None
            assert trainer.updated_at >= before

    def test_repr(self):
        """__repr__が適切な文字列を返す"""
        trainer = Trainer(
            id="01084",
            name="テスト調教師",
        )
        repr_str = repr(trainer)
        assert "Trainer" in repr_str
        assert "01084" in repr_str
        assert "テスト調教師" in repr_str
