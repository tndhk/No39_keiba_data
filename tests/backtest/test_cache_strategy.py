"""キャッシュ無効化戦略のテスト

再学習時のキャッシュ動作に関するテスト。
ファクター計算結果は馬の過去成績に基づいており、
モデル再学習後も変わらないため、キャッシュを保持すべき。
"""

from datetime import date as dt_date
from unittest.mock import patch

import pytest

from keiba.backtest.backtester import BacktestEngine
from keiba.backtest.cache import FactorCache


class TestCachePreservationOnRetrain:
    """再学習時のキャッシュ保持に関するテスト"""

    def test_cache_not_cleared_on_retrain(self, tmp_path):
        """再学習後もキャッシュが保持されることを確認

        ファクター計算結果はモデルとは独立しているため、
        再学習時にキャッシュをクリアする必要はない。
        キャッシュを保持することで、予測時の計算を省略できる。
        """
        from keiba.db import get_engine, get_session, init_db
        from keiba.models import Horse, Jockey, Race, RaceResult, Trainer

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
            horse = Horse(
                id="horse001",
                name="Test Horse",
                sex="牡",
                birth_year=2020,
                sire="Test Sire",
            )
            jockey = Jockey(id="jockey001", name="Test Jockey")
            trainer = Trainer(id="trainer001", name="Test Trainer")
            session.add_all([horse, jockey, trainer])

            # 学習用の過去レースを追加
            for i in range(5):
                race = Race(
                    id=f"2023120{i:02d}01",
                    name=f"Past Race {i}",
                    date=dt_date(2023, 12, i + 1),
                    course="Tokyo",
                    surface="芝",
                    distance=2000,
                    race_number=1,
                )
                session.add(race)

                result = RaceResult(
                    race_id=f"2023120{i:02d}01",
                    horse_id="horse001",
                    jockey_id="jockey001",
                    trainer_id="trainer001",
                    horse_number=1,
                    bracket_number=1,
                    finish_position=(i % 5) + 1,
                    odds=2.5,
                    popularity=1,
                    time="2:00.0",
                    margin="",
                )
                session.add(result)

            # テスト対象のレースを追加
            race = Race(
                id="2024010100",
                name="Test Race",
                date=dt_date(2024, 1, 1),
                course="Tokyo",
                surface="芝",
                distance=2000,
                race_number=1,
            )
            session.add(race)

            result = RaceResult(
                race_id="2024010100",
                horse_id="horse001",
                jockey_id="jockey001",
                trainer_id="trainer001",
                horse_number=1,
                bracket_number=1,
                finish_position=1,
                odds=2.5,
                popularity=1,
                time="2:00.0",
                margin="",
            )
            session.add(result)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # 予測を実行してキャッシュにデータを入れる
        race_data = {
            "race_id": "2024010100",
            "race_date": "2024-01-01",
            "race_name": "Test Race",
            "venue": "Tokyo",
            "surface": "芝",
            "distance": 2000,
            "horses": [
                {
                    "horse_number": 1,
                    "horse_name": "Test Horse",
                    "horse_id": "horse001",
                    "actual_rank": 1,
                    "odds": 2.5,
                    "popularity": 1,
                }
            ],
        }

        engine._calculate_predictions(race_data)
        stats_before_retrain = engine._factor_cache.get_stats()
        cache_size_before = stats_before_retrain["size"]
        assert cache_size_before > 0, "予測後にキャッシュにデータが存在すべき"

        # 再学習を実行
        with patch.object(engine, "_is_lightgbm_available", return_value=False):
            engine._train_model("2024-01-15")

        # 再学習後もキャッシュが保持されていることを確認
        stats_after_retrain = engine._factor_cache.get_stats()
        assert stats_after_retrain["size"] == cache_size_before, (
            f"再学習後もキャッシュサイズが保持されるべき: "
            f"before={cache_size_before}, after={stats_after_retrain['size']}"
        )

    def test_cached_factor_values_consistent_after_retrain(self, tmp_path):
        """再学習後もファクター計算結果が一貫していることを確認

        同じ馬・同じ過去成績に対するファクター計算結果は、
        モデルの再学習前後で変わらないことを検証する。
        """
        from keiba.db import get_engine, get_session, init_db
        from keiba.models import Horse, Jockey, Race, RaceResult, Trainer

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
            horse = Horse(
                id="horse002",
                name="Consistent Horse",
                sex="牝",
                birth_year=2019,
                sire="Consistent Sire",
            )
            jockey = Jockey(id="jockey002", name="Test Jockey 2")
            trainer = Trainer(id="trainer002", name="Test Trainer 2")
            session.add_all([horse, jockey, trainer])

            # 学習用の過去レースを追加
            for i in range(10):
                race = Race(
                    id=f"2023110{i:02d}01",
                    name=f"Past Race {i}",
                    date=dt_date(2023, 11, i + 1),
                    course="Nakayama",
                    surface="ダート",
                    distance=1800,
                    race_number=1,
                )
                session.add(race)

                result = RaceResult(
                    race_id=f"2023110{i:02d}01",
                    horse_id="horse002",
                    jockey_id="jockey002",
                    trainer_id="trainer002",
                    horse_number=1,
                    bracket_number=1,
                    finish_position=(i % 3) + 1,
                    odds=3.0,
                    popularity=2,
                    time="1:52.0",
                    margin="",
                )
                session.add(result)

            # テスト対象のレースを追加
            race = Race(
                id="2024020100",
                name="Target Race",
                date=dt_date(2024, 2, 1),
                course="Nakayama",
                surface="ダート",
                distance=1800,
                race_number=1,
            )
            session.add(race)

            result = RaceResult(
                race_id="2024020100",
                horse_id="horse002",
                jockey_id="jockey002",
                trainer_id="trainer002",
                horse_number=1,
                bracket_number=1,
                finish_position=2,
                odds=3.0,
                popularity=2,
                time="1:52.0",
                margin="",
            )
            session.add(result)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-02-01",
            end_date="2024-02-28",
            retrain_interval="weekly",
        )

        race_data = {
            "race_id": "2024020100",
            "race_date": "2024-02-01",
            "race_name": "Target Race",
            "venue": "Nakayama",
            "surface": "ダート",
            "distance": 1800,
            "horses": [
                {
                    "horse_number": 1,
                    "horse_name": "Consistent Horse",
                    "horse_id": "horse002",
                    "actual_rank": 2,
                    "odds": 3.0,
                    "popularity": 2,
                }
            ],
        }

        # 1回目の予測
        predictions_before = engine._calculate_predictions(race_data)
        factor_rank_before = predictions_before[0].factor_rank

        # 再学習を実行
        with patch.object(engine, "_is_lightgbm_available", return_value=False):
            engine._train_model("2024-02-15")

        # 2回目の予測（キャッシュヒットを期待）
        predictions_after = engine._calculate_predictions(race_data)
        factor_rank_after = predictions_after[0].factor_rank

        # ファクターランクが一貫していることを確認
        assert factor_rank_before == factor_rank_after, (
            f"再学習前後でファクターランクが一貫しているべき: "
            f"before={factor_rank_before}, after={factor_rank_after}"
        )

        # キャッシュヒットが発生していることを確認
        stats = engine._factor_cache.get_stats()
        assert stats["hits"] > 0, "2回目の予測ではキャッシュヒットが発生すべき"

    def test_cache_hit_rate_improves_without_clear(self, tmp_path):
        """キャッシュをクリアしないことでヒット率が向上することを確認

        同一馬が複数レースに出走する場合、キャッシュを保持することで
        ヒット率が向上し、パフォーマンスが改善される。
        """
        from keiba.db import get_engine, get_session, init_db
        from keiba.models import Horse, Jockey, Race, RaceResult, Trainer

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
            horse = Horse(
                id="horse003",
                name="Frequent Runner",
                sex="牡",
                birth_year=2020,
                sire="Fast Sire",
            )
            jockey = Jockey(id="jockey003", name="Test Jockey 3")
            trainer = Trainer(id="trainer003", name="Test Trainer 3")
            session.add_all([horse, jockey, trainer])

            # 学習用の過去レースを追加
            for i in range(5):
                race = Race(
                    id=f"2023100{i:02d}01",
                    name=f"Past Race {i}",
                    date=dt_date(2023, 10, i + 1),
                    course="Kyoto",
                    surface="芝",
                    distance=1600,
                    race_number=1,
                )
                session.add(race)

                result = RaceResult(
                    race_id=f"2023100{i:02d}01",
                    horse_id="horse003",
                    jockey_id="jockey003",
                    trainer_id="trainer003",
                    horse_number=1,
                    bracket_number=1,
                    finish_position=(i % 5) + 1,
                    odds=4.0,
                    popularity=3,
                    time="1:35.0",
                    margin="",
                )
                session.add(result)

            # テスト対象の連続レースを追加
            for week in range(1, 4):  # 3週連続で出走
                race = Race(
                    id=f"2024010{week}00",
                    name=f"Race Week {week}",
                    date=dt_date(2024, 1, week * 7),
                    course="Kyoto",
                    surface="芝",
                    distance=1600,
                    race_number=1,
                )
                session.add(race)

                result = RaceResult(
                    race_id=f"2024010{week}00",
                    horse_id="horse003",
                    jockey_id="jockey003",
                    trainer_id="trainer003",
                    horse_number=1,
                    bracket_number=1,
                    finish_position=week,
                    odds=4.0,
                    popularity=3,
                    time="1:35.0",
                    margin="",
                )
                session.add(result)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # バックテストを実行
        results = list(engine.run())

        # 結果が存在することを確認
        assert len(results) > 0, "バックテスト結果が存在すべき"

        # キャッシュ統計を確認
        stats = engine._factor_cache.get_stats()

        # キャッシュにエントリが存在することを確認
        assert stats["size"] > 0, "キャッシュにエントリが存在すべき"

        # 複数レースを処理した後、ヒット率が0より大きいことを確認
        # （同一馬が複数レースに出走するため、キャッシュヒットが発生するはず）
        if len(results) > 1:
            assert stats["hits"] > 0, (
                "複数レース処理後にキャッシュヒットが発生すべき "
                f"(hits={stats['hits']}, misses={stats['misses']})"
            )
