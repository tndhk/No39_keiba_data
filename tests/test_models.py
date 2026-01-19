"""Horse, Jockey, Trainer, Owner, Breeder, Race, RaceResultモデルのテスト

TDDのREDフェーズ: まずテストを作成し、FAILを確認する。
"""

from datetime import date, datetime

import pytest
from sqlalchemy import inspect, select

from keiba.db import get_engine, get_session, init_db
from keiba.models import (
    Breeder,
    Horse,
    Jockey,
    Owner,
    Race,
    RaceResult,
    Trainer,
)


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


class TestOwner:
    """Ownerモデルのテスト"""

    def test_create_instance(self):
        """Ownerインスタンスを作成できる"""
        owner = Owner(
            id="000001",
            name="テスト馬主",
        )
        assert owner.id == "000001"
        assert owner.name == "テスト馬主"

    def test_save_and_retrieve(self, initialized_engine):
        """OwnerをDBに保存して取得できる"""
        with get_session(initialized_engine) as session:
            owner = Owner(
                id="000001",
                name="テスト馬主",
            )
            session.add(owner)

        with get_session(initialized_engine) as session:
            result = session.execute(
                select(Owner).where(Owner.id == "000001")
            ).scalar_one()
            assert result.name == "テスト馬主"

    def test_created_at_default(self, initialized_engine):
        """created_atにデフォルト値が設定される"""
        before = datetime.utcnow()
        with get_session(initialized_engine) as session:
            owner = Owner(
                id="000001",
                name="テスト馬主",
            )
            session.add(owner)
            session.flush()
            assert owner.created_at is not None
            assert owner.created_at >= before

    def test_updated_at_default(self, initialized_engine):
        """updated_atにデフォルト値が設定される"""
        before = datetime.utcnow()
        with get_session(initialized_engine) as session:
            owner = Owner(
                id="000001",
                name="テスト馬主",
            )
            session.add(owner)
            session.flush()
            assert owner.updated_at is not None
            assert owner.updated_at >= before

    def test_repr(self):
        """__repr__が適切な文字列を返す"""
        owner = Owner(
            id="000001",
            name="テスト馬主",
        )
        repr_str = repr(owner)
        assert "Owner" in repr_str
        assert "000001" in repr_str
        assert "テスト馬主" in repr_str


class TestBreeder:
    """Breederモデルのテスト"""

    def test_create_instance(self):
        """Breederインスタンスを作成できる"""
        breeder = Breeder(
            id="000002",
            name="テスト生産者",
        )
        assert breeder.id == "000002"
        assert breeder.name == "テスト生産者"

    def test_save_and_retrieve(self, initialized_engine):
        """BreederをDBに保存して取得できる"""
        with get_session(initialized_engine) as session:
            breeder = Breeder(
                id="000002",
                name="テスト生産者",
            )
            session.add(breeder)

        with get_session(initialized_engine) as session:
            result = session.execute(
                select(Breeder).where(Breeder.id == "000002")
            ).scalar_one()
            assert result.name == "テスト生産者"

    def test_created_at_default(self, initialized_engine):
        """created_atにデフォルト値が設定される"""
        before = datetime.utcnow()
        with get_session(initialized_engine) as session:
            breeder = Breeder(
                id="000002",
                name="テスト生産者",
            )
            session.add(breeder)
            session.flush()
            assert breeder.created_at is not None
            assert breeder.created_at >= before

    def test_updated_at_default(self, initialized_engine):
        """updated_atにデフォルト値が設定される"""
        before = datetime.utcnow()
        with get_session(initialized_engine) as session:
            breeder = Breeder(
                id="000002",
                name="テスト生産者",
            )
            session.add(breeder)
            session.flush()
            assert breeder.updated_at is not None
            assert breeder.updated_at >= before

    def test_repr(self):
        """__repr__が適切な文字列を返す"""
        breeder = Breeder(
            id="000002",
            name="テスト生産者",
        )
        repr_str = repr(breeder)
        assert "Breeder" in repr_str
        assert "000002" in repr_str
        assert "テスト生産者" in repr_str


class TestRace:
    """Raceモデルのテスト"""

    def test_create_instance(self):
        """Raceインスタンスを作成できる"""
        race = Race(
            id="202405020811",
            name="テストレース",
            date=date(2024, 5, 2),
            course="東京",
            race_number=8,
            distance=1600,
            surface="芝",
            weather="晴",
            track_condition="良",
        )
        assert race.id == "202405020811"
        assert race.name == "テストレース"
        assert race.date == date(2024, 5, 2)
        assert race.course == "東京"
        assert race.race_number == 8
        assert race.distance == 1600
        assert race.surface == "芝"
        assert race.weather == "晴"
        assert race.track_condition == "良"

    def test_save_and_retrieve(self, initialized_engine):
        """RaceをDBに保存して取得できる"""
        with get_session(initialized_engine) as session:
            race = Race(
                id="202405020811",
                name="テストレース",
                date=date(2024, 5, 2),
                course="東京",
                race_number=8,
                distance=1600,
                surface="芝",
                weather="晴",
                track_condition="良",
            )
            session.add(race)

        with get_session(initialized_engine) as session:
            result = session.execute(
                select(Race).where(Race.id == "202405020811")
            ).scalar_one()
            assert result.name == "テストレース"
            assert result.date == date(2024, 5, 2)
            assert result.course == "東京"

    def test_created_at_default(self, initialized_engine):
        """created_atにデフォルト値が設定される"""
        before = datetime.utcnow()
        with get_session(initialized_engine) as session:
            race = Race(
                id="202405020811",
                name="テストレース",
                date=date(2024, 5, 2),
                course="東京",
                race_number=8,
                distance=1600,
                surface="芝",
                weather="晴",
                track_condition="良",
            )
            session.add(race)
            session.flush()
            assert race.created_at is not None
            assert race.created_at >= before

    def test_updated_at_default(self, initialized_engine):
        """updated_atにデフォルト値が設定される"""
        before = datetime.utcnow()
        with get_session(initialized_engine) as session:
            race = Race(
                id="202405020811",
                name="テストレース",
                date=date(2024, 5, 2),
                course="東京",
                race_number=8,
                distance=1600,
                surface="芝",
                weather="晴",
                track_condition="良",
            )
            session.add(race)
            session.flush()
            assert race.updated_at is not None
            assert race.updated_at >= before

    def test_repr(self):
        """__repr__が適切な文字列を返す"""
        race = Race(
            id="202405020811",
            name="テストレース",
            date=date(2024, 5, 2),
            course="東京",
            race_number=8,
            distance=1600,
            surface="芝",
            weather="晴",
            track_condition="良",
        )
        repr_str = repr(race)
        assert "Race" in repr_str
        assert "202405020811" in repr_str
        assert "テストレース" in repr_str

    def test_grade_column_exists(self):
        """Raceにgradeカラムが存在する"""
        race = Race(
            id="202405020811",
            name="有馬記念(G1)",
            date=date(2024, 5, 2),
            course="中山",
            race_number=11,
            distance=2500,
            surface="芝",
            grade="G1",
        )
        assert race.grade == "G1"

    def test_grade_nullable(self, initialized_engine):
        """gradeはNullableである"""
        with get_session(initialized_engine) as session:
            race = Race(
                id="202405020811",
                name="テストレース",
                date=date(2024, 5, 2),
                course="東京",
                race_number=8,
                distance=1600,
                surface="芝",
            )
            session.add(race)
            session.flush()
            assert race.grade is None

    def test_grade_save_and_retrieve(self, initialized_engine):
        """gradeをDBに保存して取得できる"""
        with get_session(initialized_engine) as session:
            race = Race(
                id="202405020811",
                name="有馬記念(G1)",
                date=date(2024, 5, 2),
                course="中山",
                race_number=11,
                distance=2500,
                surface="芝",
                grade="G1",
            )
            session.add(race)

        with get_session(initialized_engine) as session:
            result = session.execute(
                select(Race).where(Race.id == "202405020811")
            ).scalar_one()
            assert result.grade == "G1"


class TestRaceResult:
    """RaceResultモデルのテスト"""

    @pytest.fixture
    def setup_related_data(self, initialized_engine):
        """RaceResultに必要な関連データを作成"""
        with get_session(initialized_engine) as session:
            horse = Horse(
                id="2019104308",
                name="テスト馬",
                sex="牡",
                birth_year=2019,
            )
            jockey = Jockey(id="05203", name="テスト騎手")
            trainer = Trainer(id="01084", name="テスト調教師")
            race = Race(
                id="202405020811",
                name="テストレース",
                date=date(2024, 5, 2),
                course="東京",
                race_number=8,
                distance=1600,
                surface="芝",
                weather="晴",
                track_condition="良",
            )
            session.add_all([horse, jockey, trainer, race])
        return initialized_engine

    def test_create_instance(self):
        """RaceResultインスタンスを作成できる"""
        result = RaceResult(
            race_id="202405020811",
            horse_id="2019104308",
            jockey_id="05203",
            trainer_id="01084",
            finish_position=1,
            bracket_number=3,
            horse_number=5,
            odds=2.5,
            popularity=1,
            weight=480,
            weight_diff=2,
            time="1:33.5",
            margin="アタマ",
        )
        assert result.race_id == "202405020811"
        assert result.horse_id == "2019104308"
        assert result.finish_position == 1
        assert result.odds == 2.5

    def test_save_and_retrieve(self, setup_related_data):
        """RaceResultをDBに保存して取得できる"""
        engine = setup_related_data
        with get_session(engine) as session:
            result = RaceResult(
                race_id="202405020811",
                horse_id="2019104308",
                jockey_id="05203",
                trainer_id="01084",
                finish_position=1,
                bracket_number=3,
                horse_number=5,
                odds=2.5,
                popularity=1,
                weight=480,
                weight_diff=2,
                time="1:33.5",
                margin="アタマ",
            )
            session.add(result)
            session.flush()
            result_id = result.id

        with get_session(engine) as session:
            retrieved = session.execute(
                select(RaceResult).where(RaceResult.id == result_id)
            ).scalar_one()
            assert retrieved.finish_position == 1
            assert retrieved.odds == 2.5
            assert retrieved.time == "1:33.5"

    def test_created_at_default(self, setup_related_data):
        """created_atにデフォルト値が設定される"""
        engine = setup_related_data
        before = datetime.utcnow()
        with get_session(engine) as session:
            result = RaceResult(
                race_id="202405020811",
                horse_id="2019104308",
                jockey_id="05203",
                trainer_id="01084",
                finish_position=1,
                bracket_number=3,
                horse_number=5,
                odds=2.5,
                popularity=1,
                weight=480,
                weight_diff=2,
                time="1:33.5",
                margin="アタマ",
            )
            session.add(result)
            session.flush()
            assert result.created_at is not None
            assert result.created_at >= before

    def test_updated_at_default(self, setup_related_data):
        """updated_atにデフォルト値が設定される"""
        engine = setup_related_data
        before = datetime.utcnow()
        with get_session(engine) as session:
            result = RaceResult(
                race_id="202405020811",
                horse_id="2019104308",
                jockey_id="05203",
                trainer_id="01084",
                finish_position=1,
                bracket_number=3,
                horse_number=5,
                odds=2.5,
                popularity=1,
                weight=480,
                weight_diff=2,
                time="1:33.5",
                margin="アタマ",
            )
            session.add(result)
            session.flush()
            assert result.updated_at is not None
            assert result.updated_at >= before

    def test_repr(self):
        """__repr__が適切な文字列を返す"""
        result = RaceResult(
            race_id="202405020811",
            horse_id="2019104308",
            jockey_id="05203",
            trainer_id="01084",
            finish_position=1,
            bracket_number=3,
            horse_number=5,
            odds=2.5,
            popularity=1,
            weight=480,
            weight_diff=2,
            time="1:33.5",
            margin="アタマ",
        )
        repr_str = repr(result)
        assert "RaceResult" in repr_str
        assert "202405020811" in repr_str
        assert "2019104308" in repr_str

    def test_indexes_exist(self, setup_related_data):
        """RaceResultテーブルに必要なインデックスが存在する"""
        engine = setup_related_data
        inspector = inspect(engine)
        indexes = inspector.get_indexes("race_results")
        index_names = {idx["name"] for idx in indexes}

        # 計画で指定されたインデックスが存在することを確認
        assert "ix_race_results_horse_id" in index_names
        assert "ix_race_results_jockey_id" in index_names
        assert "ix_race_results_trainer_id" in index_names

    def test_relationship_to_race(self, setup_related_data):
        """RaceResultからRaceへのリレーションが機能する"""
        engine = setup_related_data
        with get_session(engine) as session:
            result = RaceResult(
                race_id="202405020811",
                horse_id="2019104308",
                jockey_id="05203",
                trainer_id="01084",
                finish_position=1,
                bracket_number=3,
                horse_number=5,
                odds=2.5,
                popularity=1,
                weight=480,
                weight_diff=2,
                time="1:33.5",
                margin="アタマ",
            )
            session.add(result)
            session.flush()

            # リレーションシップを通じてRaceにアクセス
            assert result.race is not None
            assert result.race.name == "テストレース"

    def test_relationship_to_horse(self, setup_related_data):
        """RaceResultからHorseへのリレーションが機能する"""
        engine = setup_related_data
        with get_session(engine) as session:
            result = RaceResult(
                race_id="202405020811",
                horse_id="2019104308",
                jockey_id="05203",
                trainer_id="01084",
                finish_position=1,
                bracket_number=3,
                horse_number=5,
                odds=2.5,
                popularity=1,
                weight=480,
                weight_diff=2,
                time="1:33.5",
                margin="アタマ",
            )
            session.add(result)
            session.flush()

            # リレーションシップを通じてHorseにアクセス
            assert result.horse is not None
            assert result.horse.name == "テスト馬"

    def test_relationship_to_jockey(self, setup_related_data):
        """RaceResultからJockeyへのリレーションが機能する"""
        engine = setup_related_data
        with get_session(engine) as session:
            result = RaceResult(
                race_id="202405020811",
                horse_id="2019104308",
                jockey_id="05203",
                trainer_id="01084",
                finish_position=1,
                bracket_number=3,
                horse_number=5,
                odds=2.5,
                popularity=1,
                weight=480,
                weight_diff=2,
                time="1:33.5",
                margin="アタマ",
            )
            session.add(result)
            session.flush()

            # リレーションシップを通じてJockeyにアクセス
            assert result.jockey is not None
            assert result.jockey.name == "テスト騎手"

    def test_relationship_to_trainer(self, setup_related_data):
        """RaceResultからTrainerへのリレーションが機能する"""
        engine = setup_related_data
        with get_session(engine) as session:
            result = RaceResult(
                race_id="202405020811",
                horse_id="2019104308",
                jockey_id="05203",
                trainer_id="01084",
                finish_position=1,
                bracket_number=3,
                horse_number=5,
                odds=2.5,
                popularity=1,
                weight=480,
                weight_diff=2,
                time="1:33.5",
                margin="アタマ",
            )
            session.add(result)
            session.flush()

            # リレーションシップを通じてTrainerにアクセス
            assert result.trainer is not None
            assert result.trainer.name == "テスト調教師"

    def test_last_3f_column_exists(self):
        """RaceResultにlast_3fカラムが存在する"""
        result = RaceResult(
            race_id="202405020811",
            horse_id="2019104308",
            jockey_id="05203",
            trainer_id="01084",
            finish_position=1,
            bracket_number=3,
            horse_number=5,
            odds=2.5,
            popularity=1,
            weight=480,
            weight_diff=2,
            time="1:33.5",
            margin="アタマ",
            last_3f=34.5,
        )
        assert result.last_3f == 34.5

    def test_last_3f_nullable(self, setup_related_data):
        """last_3fはNullableである"""
        engine = setup_related_data
        with get_session(engine) as session:
            result = RaceResult(
                race_id="202405020811",
                horse_id="2019104308",
                jockey_id="05203",
                trainer_id="01084",
                finish_position=1,
                bracket_number=3,
                horse_number=5,
                odds=2.5,
                popularity=1,
                weight=480,
                weight_diff=2,
                time="1:33.5",
                margin="アタマ",
                # last_3fを指定しない
            )
            session.add(result)
            session.flush()
            assert result.last_3f is None

    def test_last_3f_save_and_retrieve(self, setup_related_data):
        """last_3fをDBに保存して取得できる"""
        engine = setup_related_data
        with get_session(engine) as session:
            result = RaceResult(
                race_id="202405020811",
                horse_id="2019104308",
                jockey_id="05203",
                trainer_id="01084",
                finish_position=1,
                bracket_number=3,
                horse_number=5,
                odds=2.5,
                popularity=1,
                weight=480,
                weight_diff=2,
                time="1:33.5",
                margin="アタマ",
                last_3f=33.8,
            )
            session.add(result)
            session.flush()
            result_id = result.id

        with get_session(engine) as session:
            retrieved = session.execute(
                select(RaceResult).where(RaceResult.id == result_id)
            ).scalar_one()
            assert retrieved.last_3f == 33.8

    def test_sex_column_exists(self):
        """RaceResultにsexカラムが存在する"""
        result = RaceResult(
            race_id="202405020811",
            horse_id="2019104308",
            jockey_id="05203",
            trainer_id="01084",
            finish_position=1,
            bracket_number=3,
            horse_number=5,
            time="1:33.5",
            margin="アタマ",
            sex="牡",
        )
        assert result.sex == "牡"

    def test_age_column_exists(self):
        """RaceResultにageカラムが存在する"""
        result = RaceResult(
            race_id="202405020811",
            horse_id="2019104308",
            jockey_id="05203",
            trainer_id="01084",
            finish_position=1,
            bracket_number=3,
            horse_number=5,
            time="1:33.5",
            margin="アタマ",
            age=5,
        )
        assert result.age == 5

    def test_impost_column_exists(self):
        """RaceResultにimpostカラムが存在する"""
        result = RaceResult(
            race_id="202405020811",
            horse_id="2019104308",
            jockey_id="05203",
            trainer_id="01084",
            finish_position=1,
            bracket_number=3,
            horse_number=5,
            time="1:33.5",
            margin="アタマ",
            impost=57.0,
        )
        assert result.impost == 57.0

    def test_passing_order_column_exists(self):
        """RaceResultにpassing_orderカラムが存在する"""
        result = RaceResult(
            race_id="202405020811",
            horse_id="2019104308",
            jockey_id="05203",
            trainer_id="01084",
            finish_position=1,
            bracket_number=3,
            horse_number=5,
            time="1:33.5",
            margin="アタマ",
            passing_order="5-5-4-3",
        )
        assert result.passing_order == "5-5-4-3"

    def test_new_columns_nullable(self, setup_related_data):
        """sex, age, impost, passing_orderはNullableである"""
        engine = setup_related_data
        with get_session(engine) as session:
            result = RaceResult(
                race_id="202405020811",
                horse_id="2019104308",
                jockey_id="05203",
                trainer_id="01084",
                finish_position=1,
                bracket_number=3,
                horse_number=5,
                time="1:33.5",
                margin="アタマ",
            )
            session.add(result)
            session.flush()
            assert result.sex is None
            assert result.age is None
            assert result.impost is None
            assert result.passing_order is None

    def test_new_columns_save_and_retrieve(self, setup_related_data):
        """sex, age, impost, passing_orderをDBに保存して取得できる"""
        engine = setup_related_data
        with get_session(engine) as session:
            result = RaceResult(
                race_id="202405020811",
                horse_id="2019104308",
                jockey_id="05203",
                trainer_id="01084",
                finish_position=1,
                bracket_number=3,
                horse_number=5,
                time="1:33.5",
                margin="アタマ",
                sex="牝",
                age=4,
                impost=55.0,
                passing_order="2-2-1-1",
            )
            session.add(result)
            session.flush()
            result_id = result.id

        with get_session(engine) as session:
            retrieved = session.execute(
                select(RaceResult).where(RaceResult.id == result_id)
            ).scalar_one()
            assert retrieved.sex == "牝"
            assert retrieved.age == 4
            assert retrieved.impost == 55.0
            assert retrieved.passing_order == "2-2-1-1"
