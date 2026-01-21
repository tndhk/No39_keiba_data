"""BacktestEngineのテスト

TDD: RED フェーズ - テスト先行
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from keiba.backtest.backtester import BacktestEngine, RetrainInterval
from keiba.backtest.metrics import PredictionResult, RaceBacktestResult


class TestShouldRetrain:
    """_should_retrain メソッドのテスト"""

    def test_should_retrain_weekly_first_race(self):
        """週次再学習: 最初のレースでは再学習が必要"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )
        # 初回は _last_train_date が None なので再学習必要
        assert engine._should_retrain("2024-01-01") is True

    def test_should_retrain_weekly_same_week(self):
        """週次再学習: 同じ週内では再学習不要"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )
        engine._last_train_date = "2024-01-01"  # 月曜に学習済み
        # 同じ週の日曜まで再学習不要
        assert engine._should_retrain("2024-01-07") is False

    def test_should_retrain_weekly_next_week(self):
        """週次再学習: 翌週に入ったら再学習必要"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )
        engine._last_train_date = "2024-01-01"  # 月曜に学習済み
        # 翌週の月曜は再学習必要
        assert engine._should_retrain("2024-01-08") is True

    def test_should_retrain_monthly_same_month(self):
        """月次再学習: 同じ月内では再学習不要"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-03-31",
            retrain_interval="monthly",
        )
        engine._last_train_date = "2024-01-01"
        # 同じ月の末日まで再学習不要
        assert engine._should_retrain("2024-01-31") is False

    def test_should_retrain_monthly_next_month(self):
        """月次再学習: 翌月に入ったら再学習必要"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-03-31",
            retrain_interval="monthly",
        )
        engine._last_train_date = "2024-01-15"
        # 翌月は再学習必要
        assert engine._should_retrain("2024-02-01") is True

    def test_should_retrain_daily(self):
        """日次再学習: 日付が変わったら再学習必要"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="daily",
        )
        engine._last_train_date = "2024-01-01"
        # 同日は再学習不要
        assert engine._should_retrain("2024-01-01") is False
        # 翌日は再学習必要
        assert engine._should_retrain("2024-01-02") is True


class TestNoFutureDataLeakage:
    """未来データ漏洩防止のテスト"""

    def test_no_future_data_leakage(self):
        """_train_model は cutoff_date より前のデータのみを使用"""
        # このテストはモックを使って検証
        # _train_model が呼ばれた際に、cutoff_date 以降のデータを使わないことを確認
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-15",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # モックでDBセッションを差し替え
        # LightGBMのインポートエラーを回避するため_is_lightgbm_availableもモック
        with patch.object(
            engine, "_is_lightgbm_available", return_value=True
        ), patch.object(engine, "_get_training_races") as mock_get_races:
            mock_get_races.return_value = []

            # cutoff_date = "2024-01-15" で学習
            engine._train_model("2024-01-15")

            # _get_training_races が cutoff_date を引数に呼ばれたことを確認
            mock_get_races.assert_called_once()
            call_args = mock_get_races.call_args
            # 引数が cutoff_date であることを確認
            assert call_args[0][0] == "2024-01-15"


class TestRunChronologicalOrder:
    """run メソッドの時系列順テスト"""

    def test_run_yields_in_chronological_order(self):
        """run は時系列順に結果をyieldする"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # モックで _get_races_in_period を差し替え
        mock_races = [
            {"race_id": "race1", "race_date": "2024-01-10"},
            {"race_id": "race2", "race_date": "2024-01-05"},  # 意図的に順序を逆に
            {"race_id": "race3", "race_date": "2024-01-20"},
        ]

        with patch.object(engine, "_get_races_in_period") as mock_get_races, patch.object(
            engine, "_train_model"
        ) as mock_train, patch.object(
            engine, "_predict_race"
        ) as mock_predict:
            # _get_races_in_period は日付順でソートされた結果を返すべき
            sorted_races = sorted(mock_races, key=lambda r: r["race_date"])
            mock_get_races.return_value = sorted_races

            mock_predict.side_effect = [
                RaceBacktestResult(
                    race_id=r["race_id"],
                    race_date=r["race_date"],
                    race_name=f"Race {r['race_id']}",
                    venue="Tokyo",
                    predictions=[],
                )
                for r in sorted_races
            ]

            results = list(engine.run())

            # 時系列順であることを確認
            dates = [r.race_date for r in results]
            assert dates == sorted(dates), "Results should be in chronological order"


class TestEmptyPeriod:
    """空期間のテスト"""

    def test_empty_period_yields_nothing(self):
        """期間内にレースがない場合は空のイテレータ"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-12-25",  # 年末年始はレースがない可能性
            end_date="2024-12-26",
            retrain_interval="weekly",
        )

        with patch.object(engine, "_get_races_in_period") as mock_get_races:
            mock_get_races.return_value = []

            results = list(engine.run())

            assert results == [], "Empty period should yield no results"


class TestPredictRace:
    """_predict_race メソッドのテスト"""

    def test_predict_race_returns_backtest_result(self):
        """_predict_race は RaceBacktestResult を返す"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # 実際のDBを使わずにモックで検証
        with patch.object(engine, "_get_race_data") as mock_get_race, patch.object(
            engine, "_calculate_predictions"
        ) as mock_calc:
            mock_get_race.return_value = {
                "race_id": "202401010101",
                "race_date": "2024-01-01",
                "race_name": "Test Race",
                "venue": "Tokyo",
                "horses": [
                    {"horse_number": 1, "horse_name": "Horse1", "actual_rank": 1},
                    {"horse_number": 2, "horse_name": "Horse2", "actual_rank": 2},
                ],
            }

            mock_calc.return_value = [
                PredictionResult(
                    horse_number=1,
                    horse_name="Horse1",
                    ml_probability=0.8,
                    ml_rank=1,
                    factor_rank=1,
                    actual_rank=1,
                ),
                PredictionResult(
                    horse_number=2,
                    horse_name="Horse2",
                    ml_probability=0.6,
                    ml_rank=2,
                    factor_rank=2,
                    actual_rank=2,
                ),
            ]

            result = engine._predict_race("202401010101")

            assert isinstance(result, RaceBacktestResult)
            assert result.race_id == "202401010101"
            assert result.race_date == "2024-01-01"
            assert len(result.predictions) == 2


class TestLightGBMDependency:
    """LightGBM依存のテスト"""

    def test_ml_prediction_none_when_lightgbm_unavailable(self):
        """LightGBM未インストール時はML予測がNone"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # LightGBMのインポートエラーをシミュレート
        with patch.dict("sys.modules", {"lightgbm": None}), patch.object(
            engine, "_get_race_data"
        ) as mock_get_race, patch.object(
            engine, "_is_lightgbm_available", return_value=False
        ):
            mock_get_race.return_value = {
                "race_id": "202401010101",
                "race_date": "2024-01-01",
                "race_name": "Test Race",
                "venue": "Tokyo",
                "horses": [
                    {"horse_number": 1, "horse_name": "Horse1", "actual_rank": 1},
                ],
            }

            # 内部でLightGBMが使えない場合、予測確率はNoneになるべき
            # この動作は実装後に具体的に確認


class TestIntegration:
    """統合テスト（モック使用）"""

    def test_full_backtest_flow(self):
        """バックテスト全体フローのテスト"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # 2週間分のレースをシミュレート
        mock_races = [
            {"race_id": "race1", "race_date": "2024-01-06"},  # 週1
            {"race_id": "race2", "race_date": "2024-01-07"},  # 週1
            {"race_id": "race3", "race_date": "2024-01-13"},  # 週2 - 再学習
            {"race_id": "race4", "race_date": "2024-01-14"},  # 週2
        ]

        train_calls = []

        with patch.object(engine, "_get_races_in_period") as mock_get_races, patch.object(
            engine, "_train_model"
        ) as mock_train, patch.object(
            engine, "_predict_race"
        ) as mock_predict:
            mock_get_races.return_value = mock_races

            def track_train(cutoff_date):
                train_calls.append(cutoff_date)
                engine._last_train_date = cutoff_date

            mock_train.side_effect = track_train

            mock_predict.side_effect = [
                RaceBacktestResult(
                    race_id=r["race_id"],
                    race_date=r["race_date"],
                    race_name=f"Race {r['race_id']}",
                    venue="Tokyo",
                    predictions=[],
                )
                for r in mock_races
            ]

            results = list(engine.run())

            # 4レース分の結果
            assert len(results) == 4

            # 週1の最初と週2の最初で再学習が発生
            # (正確なタイミングは実装による)
            assert len(train_calls) >= 2, "Should retrain at least twice for 2 weeks"


class TestHelperFunctions:
    """ヘルパー関数のテスト"""

    def test_parse_date(self):
        """_parse_date は日付文字列をdateオブジェクトに変換"""
        from keiba.backtest.backtester import _parse_date

        result = _parse_date("2024-01-15")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_get_iso_week(self):
        """_get_iso_week はISO週番号を返す"""
        from datetime import date

        from keiba.backtest.backtester import _get_iso_week

        # 2024年1月1日は2024年第1週
        result = _get_iso_week(date(2024, 1, 1))
        assert result == (2024, 1)

        # 2024年1月8日は2024年第2週
        result = _get_iso_week(date(2024, 1, 8))
        assert result == (2024, 2)


class TestPredictRaceEmptyData:
    """_predict_race の空データ処理テスト"""

    def test_predict_race_returns_empty_result_for_missing_race(self):
        """存在しないレースIDの場合は空の結果を返す"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        with patch.object(engine, "_get_race_data") as mock_get_race:
            mock_get_race.return_value = {}

            result = engine._predict_race("nonexistent")

            assert result.race_id == "nonexistent"
            assert result.race_date == ""
            assert result.predictions == []


class TestTrainModelWithoutLightGBM:
    """LightGBMなしでの_train_modelテスト"""

    def test_train_model_sets_model_to_none_when_lightgbm_unavailable(self):
        """LightGBM未インストール時はモデルがNone"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        with patch.object(engine, "_is_lightgbm_available", return_value=False):
            engine._train_model("2024-01-15")
            assert engine._model is None


class TestCalculatePastStats:
    """_calculate_past_stats のテスト"""

    def test_calculate_past_stats_empty_results(self):
        """空の過去成績に対するテスト"""
        from datetime import date

        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        result = engine._calculate_past_stats([], date(2024, 1, 15))

        assert result["win_rate"] is None
        assert result["top3_rate"] is None
        assert result["avg_finish_position"] is None
        assert result["days_since_last_race"] is None

    def test_calculate_past_stats_with_results(self):
        """過去成績がある場合のテスト"""
        from datetime import date

        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        past_results = [
            {"finish_position": 1, "race_date": date(2024, 1, 10)},
            {"finish_position": 2, "race_date": date(2024, 1, 5)},
            {"finish_position": 5, "race_date": date(2024, 1, 1)},
        ]

        result = engine._calculate_past_stats(past_results, date(2024, 1, 15))

        assert result["win_rate"] == 1 / 3  # 1勝/3戦
        assert result["top3_rate"] == 2 / 3  # 2回3着以内/3戦
        assert result["avg_finish_position"] == (1 + 2 + 5) / 3
        assert result["days_since_last_race"] == 5  # 1/10から1/15


class TestYearCrossing:
    """年をまたぐケースのテスト"""

    def test_should_retrain_year_crossing_weekly(self):
        """年をまたぐ週次再学習"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2023-12-25",
            end_date="2024-01-07",
            retrain_interval="weekly",
        )
        engine._last_train_date = "2023-12-31"
        # 年をまたいだ翌週は再学習必要
        assert engine._should_retrain("2024-01-08") is True

    def test_should_retrain_year_crossing_monthly(self):
        """年をまたぐ月次再学習"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2023-12-01",
            end_date="2024-01-31",
            retrain_interval="monthly",
        )
        engine._last_train_date = "2023-12-15"
        # 年をまたいだ翌月は再学習必要
        assert engine._should_retrain("2024-01-01") is True


class TestIsLightGBMAvailable:
    """_is_lightgbm_available メソッドのテスト"""

    def test_lightgbm_available_caching(self):
        """LightGBM利用可能状態がキャッシュされる"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # 初回は None
        assert engine._lightgbm_available is None

        # 呼び出し後は True or False がキャッシュされる
        result = engine._is_lightgbm_available()
        assert engine._lightgbm_available is not None
        assert isinstance(result, bool)

        # 2回目の呼び出しでも同じ値
        result2 = engine._is_lightgbm_available()
        assert result == result2


class TestShouldRetrainEdgeCases:
    """_should_retrain の境界ケーステスト"""

    def test_should_retrain_with_invalid_interval(self):
        """不明な再学習間隔では常に再学習"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",  # type: ignore
        )
        # 手動でretrain_intervalを無効な値に設定
        engine.retrain_interval = "unknown"  # type: ignore
        engine._last_train_date = "2024-01-01"

        # 不明な間隔は常に再学習
        assert engine._should_retrain("2024-01-02") is True


class TestGetTrainingRaces:
    """_get_training_races メソッドのテスト"""

    def test_get_training_races_with_db(self, tmp_path):
        """データベースからトレーニングデータを取得"""
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Race

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        # テストデータを挿入
        with get_session(engine_db) as session:
            race1 = Race(
                id="2024010101",
                name="Test Race 1",
                date=dt_date(2024, 1, 1),
                course="Tokyo",
                surface="芝",
                distance=2000,
                race_number=1,
            )
            race2 = Race(
                id="2024011501",
                name="Test Race 2",
                date=dt_date(2024, 1, 15),
                course="Nakayama",
                surface="ダート",
                distance=1800,
                race_number=1,
            )
            session.add_all([race1, race2])

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # カットオフ日より前のレースのみ取得
        result = engine._get_training_races("2024-01-10")

        assert len(result) == 1
        assert result[0]["race_id"] == "2024010101"


class TestGetRacesInPeriod:
    """_get_races_in_period メソッドのテスト"""

    def test_get_races_in_period_returns_sorted_races(self, tmp_path):
        """期間内のレースを時系列順で取得"""
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Race

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
            races = [
                Race(
                    id="2024011501",
                    name="Test Race 3",
                    date=dt_date(2024, 1, 15),
                    course="Tokyo",
                    surface="芝",
                    distance=2000,
                    race_number=1,
                ),
                Race(
                    id="2024010101",
                    name="Test Race 1",
                    date=dt_date(2024, 1, 1),
                    course="Nakayama",
                    surface="ダート",
                    distance=1800,
                    race_number=1,
                ),
                Race(
                    id="2024010801",
                    name="Test Race 2",
                    date=dt_date(2024, 1, 8),
                    course="Kyoto",
                    surface="芝",
                    distance=1600,
                    race_number=1,
                ),
            ]
            session.add_all(races)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        result = engine._get_races_in_period()

        # 日付順にソートされていることを確認
        assert len(result) == 3
        assert result[0]["race_id"] == "2024010101"
        assert result[1]["race_id"] == "2024010801"
        assert result[2]["race_id"] == "2024011501"


class TestGetRaceData:
    """_get_race_data メソッドのテスト"""

    def test_get_race_data_returns_empty_for_missing_race(self, tmp_path):
        """存在しないレースIDの場合は空の辞書を返す"""
        from keiba.db import get_engine, init_db

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        result = engine._get_race_data("nonexistent")

        assert result == {}

    def test_get_race_data_returns_race_info(self, tmp_path):
        """レースデータと結果を取得"""
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Race, RaceResult, Horse, Jockey, Trainer

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
            # 必要なエンティティを追加
            horse = Horse(
                id="horse001",
                name="Test Horse",
                sex="牡",
                birth_year=2020,
            )
            jockey = Jockey(id="jockey001", name="Test Jockey")
            trainer = Trainer(id="trainer001", name="Test Trainer")
            session.add_all([horse, jockey, trainer])

            race = Race(
                id="2024010101",
                name="Test Race",
                date=dt_date(2024, 1, 1),
                course="Tokyo",
                surface="芝",
                distance=2000,
                race_number=1,
            )
            session.add(race)

            result = RaceResult(
                race_id="2024010101",
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

        race_data = engine._get_race_data("2024010101")

        assert race_data["race_id"] == "2024010101"
        assert race_data["race_name"] == "Test Race"
        assert race_data["venue"] == "Tokyo"
        assert len(race_data["horses"]) == 1
        assert race_data["horses"][0]["horse_name"] == "Test Horse"


class TestBuildTrainingData:
    """_build_training_data メソッドのテスト"""

    def test_build_training_data_returns_empty_for_no_past_races(self, tmp_path):
        """過去レースがない場合は空のリストを返す"""
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        with get_session(engine_db) as session:
            features, labels = engine._build_training_data(session, dt_date(2024, 1, 1))

        assert features == []
        assert labels == []


class TestGetHorsePastResults:
    """_get_horse_past_results メソッドのテスト"""

    def test_get_horse_past_results_returns_list(self, tmp_path):
        """馬の過去成績をリストで取得"""
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Race, RaceResult, Horse, Jockey, Trainer

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
            horse = Horse(
                id="horse001",
                name="Test Horse",
                sex="牡",
                birth_year=2020,
            )
            jockey = Jockey(id="jockey001", name="Test Jockey")
            trainer = Trainer(id="trainer001", name="Test Trainer")
            session.add_all([horse, jockey, trainer])

            race = Race(
                id="2024010101",
                name="Test Race",
                date=dt_date(2024, 1, 1),
                course="Tokyo",
                surface="芝",
                distance=2000,
                race_number=1,
            )
            session.add(race)

            result = RaceResult(
                race_id="2024010101",
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
                last_3f=33.5,
            )
            session.add(result)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        with get_session(engine_db) as session:
            past_results = engine._get_horse_past_results(session, "horse001")

        assert len(past_results) == 1
        assert past_results[0]["horse_id"] == "horse001"
        assert past_results[0]["finish_position"] == 1
        assert past_results[0]["surface"] == "芝"
        assert past_results[0]["distance"] == 2000


class TestTrainModelEmptyData:
    """_train_model の空データテスト"""

    def test_train_model_with_no_training_data(self, tmp_path):
        """トレーニングデータがない場合はモデルがNone"""
        from keiba.db import get_engine, init_db

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        with patch.object(engine, "_is_lightgbm_available", return_value=True):
            engine._train_model("2024-01-15")

        assert engine._model is None


class TestCalculatePredictions:
    """_calculate_predictions メソッドのテスト"""

    def test_calculate_predictions_without_model(self, tmp_path):
        """モデルなしで予測を実行"""
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Race, RaceResult, Horse, Jockey, Trainer

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

            race = Race(
                id="2024010101",
                name="Test Race",
                date=dt_date(2024, 1, 1),
                course="Tokyo",
                surface="芝",
                distance=2000,
                race_number=1,
            )
            session.add(race)

            result = RaceResult(
                race_id="2024010101",
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

        race_data = {
            "race_id": "2024010101",
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

        predictions = engine._calculate_predictions(race_data)

        assert len(predictions) == 1
        assert predictions[0].horse_number == 1
        assert predictions[0].horse_name == "Test Horse"
        # モデルがないのでML予測はNone
        assert predictions[0].ml_probability is None
        assert predictions[0].ml_rank is None
        # ファクターランクは設定される
        assert predictions[0].factor_rank == 1


class TestRunWithRealDatabase:
    """実際のデータベースを使ったrunメソッドのテスト"""

    def test_run_returns_results(self, tmp_path):
        """runメソッドが結果を返す"""
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Race, RaceResult, Horse, Jockey, Trainer

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

            race = Race(
                id="2024010101",
                name="Test Race",
                date=dt_date(2024, 1, 1),
                course="Tokyo",
                surface="芝",
                distance=2000,
                race_number=1,
            )
            session.add(race)

            result = RaceResult(
                race_id="2024010101",
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

        results = list(engine.run())

        assert len(results) == 1
        assert results[0].race_id == "2024010101"
        assert len(results[0].predictions) == 1
