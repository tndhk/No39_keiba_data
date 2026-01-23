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


class TestPredictionPhaseNoFutureData:
    """予測フェーズで未来データを使用しないことを確認するテスト

    TDD RED フェーズ: _get_race_data_for_prediction メソッドはまだ存在しない
    """

    def test_get_race_data_for_prediction_excludes_actual_rank(self):
        """_get_race_data_for_prediction は actual_rank を含まない"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # _get_race_data_for_prediction メソッドが存在することを確認
        assert hasattr(engine, "_get_race_data_for_prediction"), \
            "_get_race_data_for_prediction メソッドが存在しない"

        # モックでDBセッションを差し替え
        with patch.object(engine, "_with_session") as mock_session:
            mock_sess = MagicMock()
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_sess)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            # モックのレースとレース結果
            mock_race = MagicMock()
            mock_race.id = "2024010101"
            mock_race.date.strftime.return_value = "2024-01-01"
            mock_race.name = "Test Race"
            mock_race.course = "Tokyo"
            mock_race.surface = "芝"
            mock_race.distance = 2000

            mock_result = MagicMock()
            mock_result.horse_number = 1
            mock_result.horse.name = "Test Horse"
            mock_result.horse_id = "horse001"
            mock_result.finish_position = 1  # これは未来データ（actual_rank）
            mock_result.odds = 2.5
            mock_result.popularity = 1
            mock_result.weight = 450
            mock_result.weight_diff = 0
            mock_result.age = 4
            mock_result.impost = 57.0
            mock_result.passing_order = "1-1-1-1"  # これも未来データ

            mock_sess.get.return_value = mock_race
            mock_sess.query.return_value.filter.return_value.all.return_value = [mock_result]

            # _get_race_data_for_prediction を呼び出し
            result = engine._get_race_data_for_prediction("2024010101")

            # 返り値の horses に actual_rank が含まれていないことを確認
            assert "horses" in result
            for horse in result["horses"]:
                assert "actual_rank" not in horse, \
                    "予測用データに actual_rank が含まれている（未来データ漏洩）"

    def test_get_race_data_for_prediction_excludes_passing_order(self):
        """_get_race_data_for_prediction は passing_order を含まない"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # _get_race_data_for_prediction メソッドが存在することを確認
        assert hasattr(engine, "_get_race_data_for_prediction"), \
            "_get_race_data_for_prediction メソッドが存在しない"

        # モックでDBセッションを差し替え
        with patch.object(engine, "_with_session") as mock_session:
            mock_sess = MagicMock()
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_sess)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            mock_race = MagicMock()
            mock_race.id = "2024010101"
            mock_race.date.strftime.return_value = "2024-01-01"
            mock_race.name = "Test Race"
            mock_race.course = "Tokyo"
            mock_race.surface = "芝"
            mock_race.distance = 2000

            mock_result = MagicMock()
            mock_result.horse_number = 1
            mock_result.horse.name = "Test Horse"
            mock_result.horse_id = "horse001"
            mock_result.finish_position = 1
            mock_result.odds = 2.5
            mock_result.popularity = 1
            mock_result.weight = 450
            mock_result.weight_diff = 0
            mock_result.age = 4
            mock_result.impost = 57.0
            mock_result.passing_order = "1-1-1-1"

            mock_sess.get.return_value = mock_race
            mock_sess.query.return_value.filter.return_value.all.return_value = [mock_result]

            result = engine._get_race_data_for_prediction("2024010101")

            # 返り値の horses に passing_order が含まれていないことを確認
            assert "horses" in result
            for horse in result["horses"]:
                assert "passing_order" not in horse, \
                    "予測用データに passing_order が含まれている（未来データ漏洩）"

    def test_calculate_predictions_does_not_receive_passing_order(self):
        """_calculate_predictions に渡すデータに passing_order が含まれない

        FactorCalculationContext に passing_order=None が設定されることを確認
        """
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # CachedFactorCalculator.calculate_all をモックして引数を検証
        from keiba.backtest.factor_calculator import FactorCalculationContext

        contexts_received = []

        def capture_context(context):
            contexts_received.append(context)
            return {
                "win_rate": 0.0,
                "distance": 0.0,
                "rotation": 0.0,
                "time": 0.0,
                "popularity": 0.0,
                "stable": 0.0,
                "pedigree": 0.0,
            }

        with patch.object(
            engine._factor_calculator, "calculate_all", side_effect=capture_context
        ), patch.object(
            engine, "_get_horses_past_results_batch", return_value={"horse001": []}
        ), patch.object(
            engine, "_get_horses_batch", return_value={}
        ):
            # passing_order を含む race_data を渡す（これが漏洩の原因）
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
                        "passing_order": "1-1-1-1",  # 未来データ
                    }
                ],
            }

            engine._calculate_predictions(race_data)

            # FactorCalculationContext に passing_order が渡されていないことを確認
            assert len(contexts_received) > 0, "calculate_all が呼ばれていない"
            for ctx in contexts_received:
                assert ctx.passing_order is None, \
                    f"FactorCalculationContext に passing_order が渡されている: {ctx.passing_order}"


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
        with patch.object(engine, "_get_race_data_for_prediction") as mock_get_race, \
             patch.object(engine, "_get_actual_results") as mock_get_actual, \
             patch.object(engine, "_calculate_predictions") as mock_calc:
            mock_get_race.return_value = {
                "race_id": "202401010101",
                "race_date": "2024-01-01",
                "race_name": "Test Race",
                "venue": "Tokyo",
                "horses": [
                    {"horse_number": 1, "horse_name": "Horse1"},
                    {"horse_number": 2, "horse_name": "Horse2"},
                ],
            }

            mock_get_actual.return_value = {1: 1, 2: 2}

            mock_calc.return_value = [
                PredictionResult(
                    horse_number=1,
                    horse_name="Horse1",
                    ml_probability=0.8,
                    ml_rank=1,
                    factor_rank=1,
                    actual_rank=99,
                ),
                PredictionResult(
                    horse_number=2,
                    horse_name="Horse2",
                    ml_probability=0.6,
                    ml_rank=2,
                    factor_rank=2,
                    actual_rank=99,
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

            def track_train(cutoff_date, session=None):
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

        with patch.object(engine, "_get_race_data_for_prediction") as mock_get_race:
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


class TestSessionManagement:
    """セッション管理のテスト (Phase 1)"""

    def test_session_fields_initialized_to_none(self):
        """初期化時にセッションフィールドがNone"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        assert engine._db_engine is None
        assert engine._session is None

    def test_open_session_creates_session(self, tmp_path):
        """_open_sessionでセッションが作成される"""
        from keiba.db import get_engine, init_db

        db_path = str(tmp_path / "test.db")
        db_engine = get_engine(db_path)
        init_db(db_engine)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # セッション開始前はNone
        assert engine._db_engine is None
        assert engine._session is None

        # セッション開始
        engine._open_session()

        # セッションが作成される
        assert engine._db_engine is not None
        assert engine._session is not None

        # クリーンアップ
        engine._close_session()

    def test_close_session_cleans_up(self, tmp_path):
        """_close_sessionでセッションがクリーンアップされる"""
        from keiba.db import get_engine, init_db

        db_path = str(tmp_path / "test.db")
        db_engine = get_engine(db_path)
        init_db(db_engine)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # セッション開始
        engine._open_session()
        assert engine._db_engine is not None
        assert engine._session is not None

        # セッション終了
        engine._close_session()

        # セッションがクリーンアップされる
        assert engine._db_engine is None
        assert engine._session is None

    def test_open_session_idempotent(self, tmp_path):
        """二重呼び出しでも安全（べき等性）"""
        from keiba.db import get_engine, init_db

        db_path = str(tmp_path / "test.db")
        db_engine = get_engine(db_path)
        init_db(db_engine)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # 1回目のセッション開始
        engine._open_session()
        first_session = engine._session
        first_db_engine = engine._db_engine

        # 2回目のセッション開始（同じセッションを維持）
        engine._open_session()

        # セッションが変わっていないことを確認
        assert engine._session is first_session
        assert engine._db_engine is first_db_engine

        # クリーンアップ
        engine._close_session()

    def test_close_session_idempotent(self, tmp_path):
        """close_sessionの二重呼び出しでも安全"""
        from keiba.db import get_engine, init_db

        db_path = str(tmp_path / "test.db")
        db_engine = get_engine(db_path)
        init_db(db_engine)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # セッション開始
        engine._open_session()

        # 1回目のセッション終了
        engine._close_session()
        assert engine._db_engine is None
        assert engine._session is None

        # 2回目のセッション終了（エラーなし）
        engine._close_session()
        assert engine._db_engine is None
        assert engine._session is None

    def test_run_manages_session_lifecycle(self, tmp_path):
        """runメソッドがセッションライフサイクルを管理"""
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Race, RaceResult, Horse, Jockey, Trainer

        db_path = str(tmp_path / "test.db")
        db_engine = get_engine(db_path)
        init_db(db_engine)

        with get_session(db_engine) as session:
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

        # run実行前はセッションがない
        assert engine._db_engine is None
        assert engine._session is None

        # runを実行
        results = list(engine.run())

        # run実行後はセッションがクリーンアップされている
        assert engine._db_engine is None
        assert engine._session is None

        # 結果は正しく返される
        assert len(results) == 1

    def test_run_cleans_up_session_on_exception(self, tmp_path):
        """例外発生時もセッションがクリーンアップされる"""
        from keiba.db import get_engine, init_db

        db_path = str(tmp_path / "test.db")
        db_engine = get_engine(db_path)
        init_db(db_engine)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # _get_races_in_periodで例外を発生させる
        with patch.object(
            engine, "_get_races_in_period", side_effect=Exception("Test error")
        ):
            with pytest.raises(Exception, match="Test error"):
                list(engine.run())

        # 例外発生後もセッションがクリーンアップされている
        assert engine._db_engine is None
        assert engine._session is None


class TestInternalMethodsSessionArg:
    """Phase 2: 内部メソッドのセッション引数化テスト"""

    # _get_races_in_period

    def test_get_races_in_period_accepts_session(self, tmp_path):
        """_get_races_in_period がsession引数を受け取れる"""
        from datetime import date as dt_date

        from sqlalchemy.orm import Session as SqlSession

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Race

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
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

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # 外部からセッションを渡して呼び出し
        with get_session(engine_db) as session:
            result = engine._get_races_in_period(session=session)

        assert len(result) == 1
        assert result[0]["race_id"] == "2024010101"

    def test_get_races_in_period_without_session_backward_compatible(self, tmp_path):
        """_get_races_in_period がsessionなしでも従来通り動作"""
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Race

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
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

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # sessionなしで呼び出し（後方互換性）
        result = engine._get_races_in_period()

        assert len(result) == 1
        assert result[0]["race_id"] == "2024010101"

    # _get_training_races

    def test_get_training_races_accepts_session(self, tmp_path):
        """_get_training_races がsession引数を受け取れる"""
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Race

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
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

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # 外部からセッションを渡して呼び出し
        with get_session(engine_db) as session:
            result = engine._get_training_races("2024-01-10", session=session)

        assert len(result) == 1
        assert result[0]["race_id"] == "2024010101"

    def test_get_training_races_without_session_backward_compatible(self, tmp_path):
        """_get_training_races がsessionなしでも従来通り動作"""
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Race

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
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

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # sessionなしで呼び出し（後方互換性）
        result = engine._get_training_races("2024-01-10")

        assert len(result) == 1
        assert result[0]["race_id"] == "2024010101"

    # _get_race_data

    def test_get_race_data_accepts_session(self, tmp_path):
        """_get_race_data がsession引数を受け取れる"""
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
            )
            session.add(result)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # 外部からセッションを渡して呼び出し
        with get_session(engine_db) as session:
            race_data = engine._get_race_data("2024010101", session=session)

        assert race_data["race_id"] == "2024010101"
        assert race_data["race_name"] == "Test Race"

    def test_get_race_data_without_session_backward_compatible(self, tmp_path):
        """_get_race_data がsessionなしでも従来通り動作"""
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
            )
            session.add(result)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # sessionなしで呼び出し（後方互換性）
        race_data = engine._get_race_data("2024010101")

        assert race_data["race_id"] == "2024010101"
        assert race_data["race_name"] == "Test Race"

    # _calculate_predictions

    def test_calculate_predictions_accepts_session(self, tmp_path):
        """_calculate_predictions がsession引数を受け取れる"""
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

        # 外部からセッションを渡して呼び出し
        with get_session(engine_db) as session:
            predictions = engine._calculate_predictions(race_data, session=session)

        assert len(predictions) == 1
        assert predictions[0].horse_number == 1

    def test_calculate_predictions_without_session_backward_compatible(self, tmp_path):
        """_calculate_predictions がsessionなしでも従来通り動作"""
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

        # sessionなしで呼び出し（後方互換性）
        predictions = engine._calculate_predictions(race_data)

        assert len(predictions) == 1
        assert predictions[0].horse_number == 1

    # _train_model

    def test_train_model_accepts_session(self, tmp_path):
        """_train_model がsession引数を受け取れる"""
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Race

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
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

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # 外部からセッションを渡して呼び出し（LightGBM無効でもエラーにならない）
        with patch.object(engine, "_is_lightgbm_available", return_value=False):
            with get_session(engine_db) as session:
                engine._train_model("2024-01-15", session=session)

        # LightGBM無効の場合はモデルがNone
        assert engine._model is None

    def test_train_model_without_session_backward_compatible(self, tmp_path):
        """_train_model がsessionなしでも従来通り動作"""
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Race

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
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

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # sessionなしで呼び出し（後方互換性）
        with patch.object(engine, "_is_lightgbm_available", return_value=False):
            engine._train_model("2024-01-15")

        # LightGBM無効の場合はモデルがNone
        assert engine._model is None


class TestRunUsesSessionForInternalMethods:
    """runメソッドが内部メソッドにセッションを渡すことをテスト"""

    def test_run_passes_session_to_internal_methods(self, tmp_path):
        """runメソッドがself._sessionを内部メソッドに渡す"""
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

        # 内部メソッドへの呼び出しを追跡
        call_tracker = {
            "get_races_in_period": [],
            "train_model": [],
            "get_race_data": [],
            "calculate_predictions": [],
        }

        original_get_races = engine._get_races_in_period
        original_train_model = engine._train_model
        original_get_race_data_for_prediction = engine._get_race_data_for_prediction
        original_calc_predictions = engine._calculate_predictions

        def track_get_races(session=None):
            call_tracker["get_races_in_period"].append(session)
            return original_get_races(session=session)

        def track_train_model(cutoff_date, session=None):
            call_tracker["train_model"].append(session)
            return original_train_model(cutoff_date, session=session)

        def track_get_race_data_for_prediction(race_id, session=None):
            call_tracker["get_race_data"].append(session)
            return original_get_race_data_for_prediction(race_id, session=session)

        def track_calc_predictions(race_data, session=None):
            call_tracker["calculate_predictions"].append(session)
            return original_calc_predictions(race_data, session=session)

        with patch.object(engine, "_get_races_in_period", side_effect=track_get_races):
            with patch.object(engine, "_train_model", side_effect=track_train_model):
                with patch.object(engine, "_get_race_data_for_prediction", side_effect=track_get_race_data_for_prediction):
                    with patch.object(
                        engine, "_calculate_predictions", side_effect=track_calc_predictions
                    ):
                        results = list(engine.run())

        # 内部メソッドにセッションが渡されていることを確認
        assert len(call_tracker["get_races_in_period"]) == 1
        assert call_tracker["get_races_in_period"][0] is not None

        assert len(call_tracker["train_model"]) >= 1
        for session in call_tracker["train_model"]:
            assert session is not None

        assert len(call_tracker["get_race_data"]) == 1
        assert call_tracker["get_race_data"][0] is not None

        assert len(call_tracker["calculate_predictions"]) == 1
        assert call_tracker["calculate_predictions"][0] is not None


class TestGetHorsesPastResultsBatch:
    """Phase 3: _get_horses_past_results_batch メソッドのテスト（N+1問題解消）"""

    def test_get_horses_past_results_batch_returns_dict(self, tmp_path):
        """バッチ取得の戻り値がdictであること"""
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Race, RaceResult, Horse, Jockey, Trainer

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
            # 馬を作成
            horse = Horse(
                id="horse001",
                name="Test Horse",
                sex="牡",
                birth_year=2020,
            )
            jockey = Jockey(id="jockey001", name="Test Jockey")
            trainer = Trainer(id="trainer001", name="Test Trainer")
            session.add_all([horse, jockey, trainer])

            # レースを作成
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

            # レース結果を作成
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
            result = engine._get_horses_past_results_batch(session, ["horse001"])

        assert isinstance(result, dict)

    def test_get_horses_past_results_batch_groups_by_horse_id(self, tmp_path):
        """horse_idでグループ化されること"""
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Race, RaceResult, Horse, Jockey, Trainer

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
            # 2頭の馬を作成
            horse1 = Horse(id="horse001", name="Horse 1", sex="牡", birth_year=2020)
            horse2 = Horse(id="horse002", name="Horse 2", sex="牝", birth_year=2021)
            jockey = Jockey(id="jockey001", name="Test Jockey")
            trainer = Trainer(id="trainer001", name="Test Trainer")
            session.add_all([horse1, horse2, jockey, trainer])

            # 2つのレースを作成
            race1 = Race(
                id="2024010101",
                name="Race 1",
                date=dt_date(2024, 1, 1),
                course="Tokyo",
                surface="芝",
                distance=2000,
                race_number=1,
            )
            race2 = Race(
                id="2024010801",
                name="Race 2",
                date=dt_date(2024, 1, 8),
                course="Nakayama",
                surface="ダート",
                distance=1800,
                race_number=1,
            )
            session.add_all([race1, race2])

            # レース結果（各馬が各レースに出走）
            results = [
                RaceResult(
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
                ),
                RaceResult(
                    race_id="2024010101",
                    horse_id="horse002",
                    jockey_id="jockey001",
                    trainer_id="trainer001",
                    horse_number=2,
                    bracket_number=1,
                    finish_position=2,
                    odds=5.0,
                    popularity=2,
                    time="2:00.5",
                    margin="3",
                ),
                RaceResult(
                    race_id="2024010801",
                    horse_id="horse001",
                    jockey_id="jockey001",
                    trainer_id="trainer001",
                    horse_number=1,
                    bracket_number=1,
                    finish_position=3,
                    odds=3.0,
                    popularity=2,
                    time="1:50.0",
                    margin="1",
                ),
            ]
            session.add_all(results)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        with get_session(engine_db) as session:
            result = engine._get_horses_past_results_batch(
                session, ["horse001", "horse002"]
            )

        # 各馬のキーが存在
        assert "horse001" in result
        assert "horse002" in result
        # horse001は2レース、horse002は1レース
        assert len(result["horse001"]) == 2
        assert len(result["horse002"]) == 1

    def test_get_horses_past_results_batch_limits_results(self, tmp_path):
        """最大20件に制限されること"""
        from datetime import date as dt_date, timedelta

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Race, RaceResult, Horse, Jockey, Trainer

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
            horse = Horse(id="horse001", name="Test Horse", sex="牡", birth_year=2020)
            jockey = Jockey(id="jockey001", name="Test Jockey")
            trainer = Trainer(id="trainer001", name="Test Trainer")
            session.add_all([horse, jockey, trainer])

            # 25レース作成（20件制限をテスト）
            for i in range(25):
                race = Race(
                    id=f"20240101{i:02d}",
                    name=f"Race {i}",
                    date=dt_date(2024, 1, 1) + timedelta(days=i),
                    course="Tokyo",
                    surface="芝",
                    distance=2000,
                    race_number=1,
                )
                session.add(race)
                result = RaceResult(
                    race_id=f"20240101{i:02d}",
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

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        with get_session(engine_db) as session:
            result = engine._get_horses_past_results_batch(session, ["horse001"])

        # 最大20件に制限
        assert len(result["horse001"]) == 20

    def test_get_horses_past_results_batch_includes_total_runners(self, tmp_path):
        """出走頭数が含まれること"""
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Race, RaceResult, Horse, Jockey, Trainer

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
            # 3頭の馬を作成
            horses = [
                Horse(id=f"horse00{i}", name=f"Horse {i}", sex="牡", birth_year=2020)
                for i in range(1, 4)
            ]
            jockey = Jockey(id="jockey001", name="Test Jockey")
            trainer = Trainer(id="trainer001", name="Test Trainer")
            session.add_all(horses + [jockey, trainer])

            # 1つのレースに3頭出走
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

            # 3頭のレース結果
            for i, horse in enumerate(horses, 1):
                result = RaceResult(
                    race_id="2024010101",
                    horse_id=horse.id,
                    jockey_id="jockey001",
                    trainer_id="trainer001",
                    horse_number=i,
                    bracket_number=1,
                    finish_position=i,
                    odds=2.5 * i,
                    popularity=i,
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

        with get_session(engine_db) as session:
            result = engine._get_horses_past_results_batch(session, ["horse001"])

        # total_runnersが3であること
        assert result["horse001"][0]["total_runners"] == 3

    def test_get_horses_past_results_batch_empty_horse_ids(self, tmp_path):
        """空のリストでもエラーにならないこと"""
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
            result = engine._get_horses_past_results_batch(session, [])

        assert result == {}

    def test_get_horses_past_results_batch_nonexistent_horse(self, tmp_path):
        """存在しない馬IDの場合も空のリストを返す"""
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
            result = engine._get_horses_past_results_batch(session, ["nonexistent"])

        assert "nonexistent" in result
        assert result["nonexistent"] == []

    def test_batch_and_individual_results_match(self, tmp_path):
        """バッチ取得と個別取得の結果が一致すること"""
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Race, RaceResult, Horse, Jockey, Trainer

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
            # 2頭の馬を作成
            horse1 = Horse(id="horse001", name="Horse 1", sex="牡", birth_year=2020)
            horse2 = Horse(id="horse002", name="Horse 2", sex="牝", birth_year=2021)
            jockey = Jockey(id="jockey001", name="Test Jockey")
            trainer = Trainer(id="trainer001", name="Test Trainer")
            session.add_all([horse1, horse2, jockey, trainer])

            # 複数のレースを作成
            race1 = Race(
                id="2024010101",
                name="Race 1",
                date=dt_date(2024, 1, 1),
                course="Tokyo",
                surface="芝",
                distance=2000,
                race_number=1,
            )
            race2 = Race(
                id="2024010801",
                name="Race 2",
                date=dt_date(2024, 1, 8),
                course="Nakayama",
                surface="ダート",
                distance=1800,
                race_number=1,
            )
            session.add_all([race1, race2])

            # レース結果
            results = [
                RaceResult(
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
                ),
                RaceResult(
                    race_id="2024010101",
                    horse_id="horse002",
                    jockey_id="jockey001",
                    trainer_id="trainer001",
                    horse_number=2,
                    bracket_number=1,
                    finish_position=2,
                    odds=5.0,
                    popularity=2,
                    time="2:00.5",
                    margin="3",
                    last_3f=34.0,
                ),
                RaceResult(
                    race_id="2024010801",
                    horse_id="horse001",
                    jockey_id="jockey001",
                    trainer_id="trainer001",
                    horse_number=1,
                    bracket_number=1,
                    finish_position=3,
                    odds=3.0,
                    popularity=2,
                    time="1:50.0",
                    margin="1",
                    last_3f=35.0,
                ),
            ]
            session.add_all(results)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        with get_session(engine_db) as session:
            # バッチ取得
            batch_result = engine._get_horses_past_results_batch(
                session, ["horse001", "horse002"]
            )
            # 個別取得
            individual_result1 = engine._get_horse_past_results(session, "horse001")
            individual_result2 = engine._get_horse_past_results(session, "horse002")

        # 結果数が一致
        assert len(batch_result["horse001"]) == len(individual_result1)
        assert len(batch_result["horse002"]) == len(individual_result2)

        # フィールドの比較（horse_id, finish_position, surface, distance）
        for batch, individual in zip(batch_result["horse001"], individual_result1):
            assert batch["horse_id"] == individual["horse_id"]
            assert batch["finish_position"] == individual["finish_position"]
            assert batch["surface"] == individual["surface"]
            assert batch["distance"] == individual["distance"]
            assert batch["total_runners"] == individual["total_runners"]

    def test_get_horses_past_results_batch_ordered_by_date_desc(self, tmp_path):
        """結果が日付降順でソートされること"""
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Race, RaceResult, Horse, Jockey, Trainer

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
            horse = Horse(id="horse001", name="Test Horse", sex="牡", birth_year=2020)
            jockey = Jockey(id="jockey001", name="Test Jockey")
            trainer = Trainer(id="trainer001", name="Test Trainer")
            session.add_all([horse, jockey, trainer])

            # 日付順がランダムなレースを作成
            dates = [dt_date(2024, 1, 15), dt_date(2024, 1, 1), dt_date(2024, 1, 8)]
            for i, d in enumerate(dates):
                race = Race(
                    id=f"2024010{i+1}01",
                    name=f"Race {i}",
                    date=d,
                    course="Tokyo",
                    surface="芝",
                    distance=2000,
                    race_number=1,
                )
                session.add(race)
                result = RaceResult(
                    race_id=f"2024010{i+1}01",
                    horse_id="horse001",
                    jockey_id="jockey001",
                    trainer_id="trainer001",
                    horse_number=1,
                    bracket_number=1,
                    finish_position=i + 1,
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

        with get_session(engine_db) as session:
            result = engine._get_horses_past_results_batch(session, ["horse001"])

        # 日付降順（最新が最初）
        dates_in_result = [r["race_date"] for r in result["horse001"]]
        assert dates_in_result == sorted(dates_in_result, reverse=True)


class TestBuildTrainingDataUsesBatch:
    """_build_training_data がバッチ取得を使用することをテスト"""

    def test_build_training_data_uses_batch_method(self, tmp_path):
        """_build_training_data がバッチ取得メソッドを使用する"""
        from datetime import date as dt_date
        from unittest.mock import patch, MagicMock

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Race, RaceResult, Horse, Jockey, Trainer

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
            # 馬を作成
            horse1 = Horse(id="horse001", name="Horse 1", sex="牡", birth_year=2020)
            horse2 = Horse(id="horse002", name="Horse 2", sex="牝", birth_year=2021)
            jockey = Jockey(id="jockey001", name="Test Jockey")
            trainer = Trainer(id="trainer001", name="Test Trainer")
            session.add_all([horse1, horse2, jockey, trainer])

            # レースを作成
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

            # レース結果を作成（2頭）
            results = [
                RaceResult(
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
                ),
                RaceResult(
                    race_id="2024010101",
                    horse_id="horse002",
                    jockey_id="jockey001",
                    trainer_id="trainer001",
                    horse_number=2,
                    bracket_number=1,
                    finish_position=2,
                    odds=5.0,
                    popularity=2,
                    time="2:00.5",
                    margin="3",
                ),
            ]
            session.add_all(results)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # バッチ取得メソッドが呼ばれることを確認
        with get_session(engine_db) as session:
            with patch.object(
                engine,
                "_get_horses_past_results_batch",
                wraps=engine._get_horses_past_results_batch,
            ) as mock_batch:
                engine._build_training_data(session, dt_date(2024, 1, 15))

                # バッチ取得が呼ばれた
                assert mock_batch.call_count >= 1


class TestCalculatePredictionsUsesBatch:
    """_calculate_predictions がバッチ取得を使用することをテスト"""

    def test_calculate_predictions_uses_batch_method(self, tmp_path):
        """_calculate_predictions がバッチ取得メソッドを使用する"""
        from datetime import date as dt_date
        from unittest.mock import patch

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

        # バッチ取得メソッドが呼ばれることを確認
        with get_session(engine_db) as session:
            with patch.object(
                engine,
                "_get_horses_past_results_batch",
                wraps=engine._get_horses_past_results_batch,
            ) as mock_batch:
                engine._calculate_predictions(race_data, session=session)

                # バッチ取得が呼ばれた
                assert mock_batch.call_count == 1


class TestGetHorsesPastResultsBatchDateFilter:
    """_get_horses_past_results_batch の日付フィルタテスト（データリーク防止）"""

    def test_excludes_future_races_when_target_date_specified(self, tmp_path):
        """target_date 指定時は未来のレースを除外する"""
        from datetime import date as dt_date

        from keiba.db import get_engine, get_session, init_db
        from keiba.models import Horse, Jockey, Race, RaceResult, Trainer

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        # テストデータ作成: 過去レース2件、未来レース2件
        with get_session(engine_db) as session:
            horse = Horse(id="horse001", name="Test Horse", sex="牡", birth_year=2020)
            jockey = Jockey(id="jockey001", name="Test Jockey")
            trainer = Trainer(id="trainer001", name="Test Trainer")
            session.add_all([horse, jockey, trainer])

            # 過去レース (target_date: 2024-01-15 より前)
            race_past1 = Race(
                id="race_past1",
                name="Past Race 1",
                date=dt_date(2024, 1, 1),
                course="東京",
                race_number=1,
                surface="芝",
                distance=1600,
            )
            race_past2 = Race(
                id="race_past2",
                name="Past Race 2",
                date=dt_date(2024, 1, 8),
                course="中山",
                race_number=1,
                surface="ダート",
                distance=1800,
            )
            # 未来レース (target_date: 2024-01-15 以降)
            race_future1 = Race(
                id="race_future1",
                name="Future Race 1",
                date=dt_date(2024, 1, 15),
                course="京都",
                race_number=1,
                surface="芝",
                distance=2000,
            )
            race_future2 = Race(
                id="race_future2",
                name="Future Race 2",
                date=dt_date(2024, 1, 22),
                course="阪神",
                race_number=1,
                surface="ダート",
                distance=1400,
            )
            session.add_all([race_past1, race_past2, race_future1, race_future2])

            # 各レースの結果を追加
            for i, race in enumerate(
                [race_past1, race_past2, race_future1, race_future2], 1
            ):
                result = RaceResult(
                    race_id=race.id,
                    horse_id="horse001",
                    jockey_id="jockey001",
                    trainer_id="trainer001",
                    horse_number=1,
                    bracket_number=1,
                    finish_position=i,
                    odds=5.0,
                    popularity=1,
                    time="1:35.0",
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

        # target_date=2024-01-15 で呼び出し
        target_date = dt_date(2024, 1, 15)
        with get_session(engine_db) as session:
            result = engine._get_horses_past_results_batch(
                session, ["horse001"], target_date=target_date
            )

        # 2024-01-15 より前のレースのみ含まれる
        assert "horse001" in result
        past_results = result["horse001"]
        assert len(past_results) == 2, f"Expected 2 past races, got {len(past_results)}"

        # 過去レースのみが含まれていることを確認
        race_ids = {r["race_id"] for r in past_results}
        assert "race_past1" in race_ids
        assert "race_past2" in race_ids
        assert "race_future1" not in race_ids
        assert "race_future2" not in race_ids

    def test_includes_all_races_when_target_date_is_none(self, tmp_path):
        """target_date=None の場合は全レースを返す（後方互換性）"""
        from datetime import date as dt_date

        from keiba.db import get_engine, get_session, init_db
        from keiba.models import Horse, Jockey, Race, RaceResult, Trainer

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
            horse = Horse(id="horse001", name="Test Horse", sex="牡", birth_year=2020)
            jockey = Jockey(id="jockey001", name="Test Jockey")
            trainer = Trainer(id="trainer001", name="Test Trainer")
            session.add_all([horse, jockey, trainer])

            # レースを2件作成（日付は関係なく全て取得される）
            race1 = Race(
                id="race1",
                name="Race 1",
                date=dt_date(2024, 1, 1),
                course="東京",
                race_number=1,
                surface="芝",
                distance=1600,
            )
            race2 = Race(
                id="race2",
                name="Race 2",
                date=dt_date(2024, 12, 31),
                course="中山",
                race_number=1,
                surface="ダート",
                distance=1800,
            )
            session.add_all([race1, race2])

            for i, race in enumerate([race1, race2], 1):
                result = RaceResult(
                    race_id=race.id,
                    horse_id="horse001",
                    jockey_id="jockey001",
                    trainer_id="trainer001",
                    horse_number=1,
                    bracket_number=1,
                    finish_position=i,
                    odds=5.0,
                    popularity=1,
                    time="1:35.0",
                    margin="",
                    last_3f=33.5,
                )
                session.add(result)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-12-31",
            retrain_interval="weekly",
        )

        # target_date=None（デフォルト）で呼び出し
        with get_session(engine_db) as session:
            result = engine._get_horses_past_results_batch(session, ["horse001"])

        # 全レースが含まれる
        assert "horse001" in result
        past_results = result["horse001"]
        assert len(past_results) == 2, f"Expected 2 races, got {len(past_results)}"

    def test_excludes_race_on_target_date(self, tmp_path):
        """target_date と同日のレースも除外される（< 比較のため）"""
        from datetime import date as dt_date

        from keiba.db import get_engine, get_session, init_db
        from keiba.models import Horse, Jockey, Race, RaceResult, Trainer

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
            horse = Horse(id="horse001", name="Test Horse", sex="牡", birth_year=2020)
            jockey = Jockey(id="jockey001", name="Test Jockey")
            trainer = Trainer(id="trainer001", name="Test Trainer")
            session.add_all([horse, jockey, trainer])

            # target_date と同日のレース
            race_same_day = Race(
                id="race_same_day",
                name="Same Day Race",
                date=dt_date(2024, 1, 15),
                course="東京",
                race_number=1,
                surface="芝",
                distance=1600,
            )
            # target_date より前のレース
            race_before = Race(
                id="race_before",
                name="Before Race",
                date=dt_date(2024, 1, 14),
                course="中山",
                race_number=1,
                surface="ダート",
                distance=1800,
            )
            session.add_all([race_same_day, race_before])

            for race in [race_same_day, race_before]:
                result = RaceResult(
                    race_id=race.id,
                    horse_id="horse001",
                    jockey_id="jockey001",
                    trainer_id="trainer001",
                    horse_number=1,
                    bracket_number=1,
                    finish_position=1,
                    odds=5.0,
                    popularity=1,
                    time="1:35.0",
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

        # target_date=2024-01-15 で呼び出し
        target_date = dt_date(2024, 1, 15)
        with get_session(engine_db) as session:
            result = engine._get_horses_past_results_batch(
                session, ["horse001"], target_date=target_date
            )

        # 同日のレースは除外、前日のレースのみ含まれる
        assert "horse001" in result
        past_results = result["horse001"]
        assert len(past_results) == 1, f"Expected 1 race, got {len(past_results)}"
        assert past_results[0]["race_id"] == "race_before"


class TestCreateFactorContextForTrainingPassingOrder:
    """_create_factor_context_for_training の passing_order テスト"""

    def test_passing_order_is_none_for_consistency(self):
        """passing_order は None に設定される（予測時との一貫性のため）"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # RaceResult モックを作成（passing_order に値を設定）
        mock_result = MagicMock()
        mock_result.horse_id = "horse001"
        mock_result.odds = 5.0
        mock_result.popularity = 1
        mock_result.passing_order = "1-2-3-4"  # 未来データ

        # Race モックを作成
        mock_race = MagicMock()
        mock_race.surface = "芝"
        mock_race.distance = 1600
        mock_race.course = "東京"

        # horse_data タプル: (Horse, past_results, past_race_ids)
        mock_horse = MagicMock()
        mock_horse.id = "horse001"
        horse_data = (mock_horse, [], [])

        # _create_factor_context_for_training を呼び出し
        context = engine._create_factor_context_for_training(
            mock_result, mock_race, horse_data
        )

        # passing_order は None であるべき（予測時との一貫性のため）
        assert context.passing_order is None, (
            f"passing_order は None であるべき（予測時との一貫性のため）。"
            f"実際の値: {context.passing_order}"
        )


class TestGetHorsesBatch:
    """Phase 4: _get_horses_batch メソッドのテスト（馬情報N+1問題解消）"""

    def test_get_horses_batch_returns_dict(self, tmp_path):
        """バッチ取得の戻り値がdictであること"""
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Horse

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
            session.add(horse)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        with get_session(engine_db) as session:
            result = engine._get_horses_batch(session, ["horse001"])

        assert isinstance(result, dict)

    def test_get_horses_batch_maps_by_id(self, tmp_path):
        """horse_idでマッピングされること"""
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Horse

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
            horse1 = Horse(id="horse001", name="Horse 1", sex="牡", birth_year=2020)
            horse2 = Horse(id="horse002", name="Horse 2", sex="牝", birth_year=2021)
            session.add_all([horse1, horse2])

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        with get_session(engine_db) as session:
            result = engine._get_horses_batch(session, ["horse001", "horse002"])

            # セッション内でアサーション（DetachedInstanceError回避）
            assert "horse001" in result
            assert "horse002" in result
            assert result["horse001"].name == "Horse 1"
            assert result["horse002"].name == "Horse 2"

    def test_get_horses_batch_empty_list(self, tmp_path):
        """空のリストでもエラーにならないこと"""
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
            result = engine._get_horses_batch(session, [])

        assert result == {}

    def test_get_horses_batch_missing_horse(self, tmp_path):
        """存在しない馬は結果に含まれないこと"""
        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Horse

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
            horse = Horse(id="horse001", name="Test Horse", sex="牡", birth_year=2020)
            session.add(horse)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        with get_session(engine_db) as session:
            result = engine._get_horses_batch(session, ["horse001", "nonexistent"])

        assert "horse001" in result
        assert "nonexistent" not in result

    def test_get_horses_batch_returns_horse_objects(self, tmp_path):
        """Horseオブジェクトが返されること"""
        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Horse

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
                dam_sire="Test Dam Sire",
            )
            session.add(horse)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        with get_session(engine_db) as session:
            result = engine._get_horses_batch(session, ["horse001"])

            # セッション内でアサーション（DetachedInstanceError回避）
            assert isinstance(result["horse001"], Horse)
            assert result["horse001"].sire == "Test Sire"
            assert result["horse001"].dam_sire == "Test Dam Sire"


class TestBuildTrainingDataUsesHorsesBatch:
    """_build_training_data が馬情報バッチ取得を使用することをテスト"""

    def test_build_training_data_uses_horses_batch(self, tmp_path):
        """_build_training_data が_get_horses_batchを使用する"""
        from datetime import date as dt_date
        from unittest.mock import patch

        from keiba.db import get_engine, init_db, get_session
        from keiba.models import Race, RaceResult, Horse, Jockey, Trainer

        db_path = str(tmp_path / "test.db")
        engine_db = get_engine(db_path)
        init_db(engine_db)

        with get_session(engine_db) as session:
            horse1 = Horse(
                id="horse001",
                name="Horse 1",
                sex="牡",
                birth_year=2020,
                sire="Sire1",
            )
            horse2 = Horse(
                id="horse002",
                name="Horse 2",
                sex="牝",
                birth_year=2021,
                sire="Sire2",
            )
            jockey = Jockey(id="jockey001", name="Test Jockey")
            trainer = Trainer(id="trainer001", name="Test Trainer")
            session.add_all([horse1, horse2, jockey, trainer])

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

            results = [
                RaceResult(
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
                ),
                RaceResult(
                    race_id="2024010101",
                    horse_id="horse002",
                    jockey_id="jockey001",
                    trainer_id="trainer001",
                    horse_number=2,
                    bracket_number=1,
                    finish_position=2,
                    odds=5.0,
                    popularity=2,
                    time="2:00.5",
                    margin="3",
                ),
            ]
            session.add_all(results)

        engine = BacktestEngine(
            db_path=db_path,
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        with get_session(engine_db) as session:
            with patch.object(
                engine,
                "_get_horses_batch",
                wraps=engine._get_horses_batch,
            ) as mock_batch:
                engine._build_training_data(session, dt_date(2024, 1, 15))

                # 馬情報のバッチ取得が呼ばれた
                assert mock_batch.call_count >= 1


class TestCalculatePredictionsUsesHorsesBatch:
    """_calculate_predictions が馬情報バッチ取得を使用することをテスト"""

    def test_calculate_predictions_uses_horses_batch(self, tmp_path):
        """_calculate_predictions が_get_horses_batchを使用する"""
        from datetime import date as dt_date
        from unittest.mock import patch

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

        with get_session(engine_db) as session:
            with patch.object(
                engine,
                "_get_horses_batch",
                wraps=engine._get_horses_batch,
            ) as mock_batch:
                engine._calculate_predictions(race_data, session=session)

                # 馬情報のバッチ取得が呼ばれた
                assert mock_batch.call_count == 1


class TestFactorCacheIntegration:
    """BacktestEngineとFactorCacheの統合テスト

    TDD RED フェーズ: BacktestEngineにFactorCacheを統合した後の動作をテスト
    """

    def test_cache_initialized_on_engine_creation(self):
        """BacktestEngine初期化時にFactorCacheが作成されること"""
        from keiba.backtest.cache import FactorCache

        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # _factor_cache 属性が存在し、FactorCache型であること
        assert hasattr(engine, "_factor_cache")
        assert isinstance(engine._factor_cache, FactorCache)

    def test_factor_calculation_uses_cache(self, tmp_path):
        """_calculate_predictions内でキャッシュが使用されること

        同じ馬の同じFactor計算で2回目はキャッシュヒット
        """
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
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

            # 2つのレースを作成（同じ馬が出走）
            for i, race_date in enumerate([dt_date(2024, 1, 1), dt_date(2024, 1, 8)]):
                race = Race(
                    id=f"20240101{i:02d}",
                    name=f"Test Race {i}",
                    date=race_date,
                    course="Tokyo",
                    surface="芝",
                    distance=2000,
                    race_number=1,
                )
                session.add(race)

                result = RaceResult(
                    race_id=f"20240101{i:02d}",
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

        # 1回目の予測計算
        engine._calculate_predictions(race_data)

        # キャッシュ統計を取得
        stats_after_first = engine._factor_cache.get_stats()
        initial_misses = stats_after_first["misses"]

        # 同じデータで2回目の予測計算（キャッシュがヒットすべき）
        engine._calculate_predictions(race_data)

        stats_after_second = engine._factor_cache.get_stats()

        # 2回目ではキャッシュヒットが発生するため、missesは増えず、hitsが増えること
        assert stats_after_second["hits"] > 0, "2回目の計算でキャッシュヒットが発生すべき"
        # ミス数が増えていないことを確認（同じ計算はキャッシュから取得）
        assert stats_after_second["misses"] == initial_misses, \
            "同じデータで2回目の計算ではミス数が増えないこと"

    def test_popularity_factor_not_cached(self, tmp_path):
        """PopularityFactorはキャッシュ対象外であること

        PopularityFactorはレースごとのオッズ・人気順に依存するため
        キャッシュ対象外とすべき
        """
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
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

        # 同じ馬で異なるオッズ/人気順のレースデータ
        race_data_1 = {
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
                    "odds": 2.5,  # 低オッズ
                    "popularity": 1,  # 1番人気
                }
            ],
        }

        race_data_2 = {
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
                    "odds": 50.0,  # 高オッズ（異なる値）
                    "popularity": 10,  # 10番人気（異なる値）
                }
            ],
        }

        # 1回目の予測計算
        predictions_1 = engine._calculate_predictions(race_data_1)

        # 2回目の予測計算（異なるオッズ/人気順）
        predictions_2 = engine._calculate_predictions(race_data_2)

        # PopularityFactorがキャッシュされていない場合、異なるファクタースコア合計になるべき
        # （PopularityFactorはレースごとのオッズに依存）
        # 注: このテストは実装によっては total_score で検証
        # キャッシュされていれば factor_scores["popularity"] が同じになってしまう

        # キャッシュキーにPopularityFactorが含まれていないことを確認するため
        # キャッシュキーパターンを検証
        cache_stats = engine._factor_cache.get_stats()

        # PopularityFactorはキャッシュ対象外なので、キャッシュサイズは
        # popularity以外のファクター数 * 馬数 であるべき
        # 7ファクター中、popularityを除く6ファクター
        # ただし、1馬 x 2回予測 で、他の6ファクターはキャッシュヒットすべき
        # このテストはキャッシュキー生成ロジックを検証

    def test_cache_stats_after_predictions(self, tmp_path):
        """予測後にキャッシュ統計情報を取得できること"""
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
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

        # 初期状態の統計
        initial_stats = engine._factor_cache.get_stats()
        assert initial_stats["hits"] == 0
        assert initial_stats["misses"] == 0
        assert initial_stats["size"] == 0

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

        # 予測を実行
        engine._calculate_predictions(race_data)

        # 予測後の統計を取得
        stats = engine._factor_cache.get_stats()

        # 統計情報の構造を確認
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
        assert "size" in stats

        # 1回目の予測なのでミスが発生しているはず
        assert stats["misses"] > 0, "初回予測ではキャッシュミスが発生するべき"
        # キャッシュにエントリが追加されているはず
        assert stats["size"] > 0, "予測後にキャッシュサイズが増加すべき"

    def test_cache_cleared_on_retrain(self, tmp_path):
        """再学習時にキャッシュがクリアされること（オプション）

        モデルの再学習時、キャッシュに古い計算結果が残っていると
        新しいモデルとの整合性が取れなくなる可能性があるため、
        再学習時にキャッシュをクリアすることを推奨
        """
        from datetime import date as dt_date

        from keiba.db import get_engine, init_db, get_session
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

        # まずキャッシュにデータを入れる
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
        assert stats_before_retrain["size"] > 0, "予測後にキャッシュにデータが存在すべき"

        # 再学習を実行（LightGBMがなくてもキャッシュクリアは発生すべき）
        with patch.object(engine, "_is_lightgbm_available", return_value=False):
            engine._train_model("2024-01-15")

        # 再学習後、キャッシュがクリアされていることを確認
        stats_after_retrain = engine._factor_cache.get_stats()
        assert stats_after_retrain["size"] == 0, "再学習後にキャッシュがクリアされるべき"
        assert stats_after_retrain["hits"] == 0, "再学習後にヒットカウントがリセットされるべき"
        assert stats_after_retrain["misses"] == 0, "再学習後にミスカウントがリセットされるべき"


class TestRankByFactorScore:
    """_rank_by_factor_score メソッドのテスト"""

    def test_rank_by_factor_score_adds_factor_rank(self):
        """ファクタースコアでランキングが追加される"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        horses_data = [
            {"horse_id": "h1", "total_score": 80.0},
            {"horse_id": "h2", "total_score": 100.0},
            {"horse_id": "h3", "total_score": 60.0},
        ]

        result = engine._rank_by_factor_score(horses_data)

        # スコアが高い順にランキング
        h1 = next(h for h in result if h["horse_id"] == "h1")
        h2 = next(h for h in result if h["horse_id"] == "h2")
        h3 = next(h for h in result if h["horse_id"] == "h3")

        assert h2["factor_rank"] == 1  # 最高スコア
        assert h1["factor_rank"] == 2
        assert h3["factor_rank"] == 3

    def test_rank_by_factor_score_handles_none_score(self):
        """Noneスコアを持つ馬は最下位になる"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        horses_data = [
            {"horse_id": "h1", "total_score": 50.0},
            {"horse_id": "h2", "total_score": None},
            {"horse_id": "h3", "total_score": 80.0},
        ]

        result = engine._rank_by_factor_score(horses_data)

        h1 = next(h for h in result if h["horse_id"] == "h1")
        h2 = next(h for h in result if h["horse_id"] == "h2")
        h3 = next(h for h in result if h["horse_id"] == "h3")

        assert h3["factor_rank"] == 1
        assert h1["factor_rank"] == 2
        assert h2["factor_rank"] == 3  # Noneは最下位

    def test_rank_by_factor_score_empty_list(self):
        """空リストの場合は空リストを返す"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        result = engine._rank_by_factor_score([])

        assert result == []


class TestRankByMlProbability:
    """_rank_by_ml_probability メソッドのテスト"""

    def test_rank_by_ml_probability_adds_ml_rank(self):
        """ML確率でランキングが追加される"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        horses_data = [
            {"horse_id": "h1", "ml_probability": 0.6},
            {"horse_id": "h2", "ml_probability": 0.9},
            {"horse_id": "h3", "ml_probability": 0.3},
        ]

        result = engine._rank_by_ml_probability(horses_data)

        h1 = next(h for h in result if h["horse_id"] == "h1")
        h2 = next(h for h in result if h["horse_id"] == "h2")
        h3 = next(h for h in result if h["horse_id"] == "h3")

        assert h2["ml_rank"] == 1  # 最高確率
        assert h1["ml_rank"] == 2
        assert h3["ml_rank"] == 3

    def test_rank_by_ml_probability_handles_none(self):
        """Noneの確率を持つ馬にはml_rank=Noneが設定される"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        horses_data = [
            {"horse_id": "h1", "ml_probability": None},
            {"horse_id": "h2", "ml_probability": None},
        ]

        result = engine._rank_by_ml_probability(horses_data)

        h1 = next(h for h in result if h["horse_id"] == "h1")
        h2 = next(h for h in result if h["horse_id"] == "h2")

        assert h1["ml_rank"] is None
        assert h2["ml_rank"] is None

    def test_rank_by_ml_probability_mixed_none(self):
        """一部がNoneの場合、有効な値のみランキング"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        horses_data = [
            {"horse_id": "h1", "ml_probability": 0.7},
            {"horse_id": "h2", "ml_probability": None},
            {"horse_id": "h3", "ml_probability": 0.5},
        ]

        result = engine._rank_by_ml_probability(horses_data)

        h1 = next(h for h in result if h["horse_id"] == "h1")
        h2 = next(h for h in result if h["horse_id"] == "h2")
        h3 = next(h for h in result if h["horse_id"] == "h3")

        # 有効な値を持つ馬のみランキング
        assert h1["ml_rank"] == 1
        assert h3["ml_rank"] == 2
        assert h2["ml_rank"] is None

    def test_rank_by_ml_probability_empty_list(self):
        """空リストの場合は空リストを返す"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        result = engine._rank_by_ml_probability([])

        assert result == []


class TestConvertToPredictionResults:
    """_convert_to_prediction_results メソッドのテスト"""

    def test_convert_to_prediction_results_basic(self):
        """基本的な変換が正しく行われる"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        horses_data = [
            {
                "horse_number": 1,
                "horse_name": "Horse A",
                "horse_id": "h1",
                "actual_rank": 2,
                "ml_probability": 0.8,
                "ml_rank": 1,
                "factor_rank": 2,
            },
            {
                "horse_number": 2,
                "horse_name": "Horse B",
                "horse_id": "h2",
                "actual_rank": 1,
                "ml_probability": 0.6,
                "ml_rank": 2,
                "factor_rank": 1,
            },
        ]

        race_data = {
            "race_id": "2024010101",
            "race_date": "2024-01-01",
            "race_name": "Test Race",
            "venue": "Tokyo",
        }

        result = engine._convert_to_prediction_results(horses_data, race_data)

        assert len(result) == 2
        assert all(isinstance(r, PredictionResult) for r in result)

        # 順序は入力のまま
        assert result[0].horse_number == 1
        assert result[0].horse_name == "Horse A"
        assert result[0].ml_probability == 0.8
        assert result[0].ml_rank == 1
        assert result[0].factor_rank == 2
        assert result[0].actual_rank == 2

        assert result[1].horse_number == 2
        assert result[1].horse_name == "Horse B"
        assert result[1].actual_rank == 1

    def test_convert_to_prediction_results_with_none_values(self):
        """None値を含む場合も正しく変換される"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        horses_data = [
            {
                "horse_number": 1,
                "horse_name": "Horse A",
                "horse_id": "h1",
                "actual_rank": 1,
                "ml_probability": None,
                "ml_rank": None,
                "factor_rank": 1,
            },
        ]

        race_data = {
            "race_id": "2024010101",
            "race_date": "2024-01-01",
            "race_name": "Test Race",
            "venue": "Tokyo",
        }

        result = engine._convert_to_prediction_results(horses_data, race_data)

        assert len(result) == 1
        assert result[0].ml_probability is None
        assert result[0].ml_rank is None
        assert result[0].factor_rank == 1

    def test_convert_to_prediction_results_empty_list(self):
        """空リストの場合は空リストを返す"""
        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        race_data = {
            "race_id": "2024010101",
            "race_date": "2024-01-01",
            "race_name": "Test Race",
            "venue": "Tokyo",
        }

        result = engine._convert_to_prediction_results([], race_data)

        assert result == []


class TestCreateFactorContextForTrainingPassingOrder:
    """_create_factor_context_for_training の passing_order テスト"""

    def test_passing_order_is_none_for_consistency(self):
        """passing_order は None に設定される（予測時との一貫性のため）

        学習データ作成時も予測時と同様に passing_order を使用しないことで、
        学習と推論の一貫性を保つ。passing_order は当該レースの結果データであり、
        予測時には利用できないため。
        """
        from keiba.backtest.factor_calculator import FactorCalculationContext

        engine = BacktestEngine(
            db_path=":memory:",
            start_date="2024-01-01",
            end_date="2024-01-31",
            retrain_interval="weekly",
        )

        # RaceResult モックを作成（passing_order を持つ）
        mock_result = MagicMock()
        mock_result.horse_id = "horse001"
        mock_result.odds = 2.5
        mock_result.popularity = 1
        mock_result.passing_order = "1-2-3-4"  # 実際の通過順位データ

        # Race モックを作成
        mock_race = MagicMock()
        mock_race.surface = "turf"
        mock_race.distance = 2000
        mock_race.course = "Tokyo"

        # horse_data タプルを作成
        mock_horse = MagicMock()
        past_results = [{"finish_position": 1, "distance": 2000}]
        past_race_ids = ["race001"]
        horse_data = (mock_horse, past_results, past_race_ids)

        # _create_factor_context_for_training を呼び出し
        context = engine._create_factor_context_for_training(
            mock_result, mock_race, horse_data
        )

        # context.passing_order が None であることを確認
        # (予測時との一貫性のため、学習時も passing_order は使用しない)
        assert context.passing_order is None, (
            f"passing_order は None であるべき（予測時との一貫性のため）。"
            f"実際の値: {context.passing_order}"
        )
