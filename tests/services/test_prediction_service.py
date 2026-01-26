"""Tests for PredictionService"""

import pytest
from unittest.mock import Mock, MagicMock
from keiba.models.entry import RaceEntry, ShutubaData
from keiba.services.prediction_service import (
    PredictionService,
    PredictionResult,
    RaceResultRepository,
)


def create_test_entry(
    horse_id: str,
    horse_name: str,
    horse_number: int,
    bracket_number: int = 1,
    jockey_id: str = "jockey_001",
    jockey_name: str = "Test Jockey",
    impost: float = 55.0,
    sex: str = "male",
    age: int = 3,
) -> RaceEntry:
    """テスト用のRaceEntryを作成するヘルパー"""
    return RaceEntry(
        horse_id=horse_id,
        horse_name=horse_name,
        horse_number=horse_number,
        bracket_number=bracket_number,
        jockey_id=jockey_id,
        jockey_name=jockey_name,
        impost=impost,
        sex=sex,
        age=age,
    )


def create_test_shutuba(entries: tuple[RaceEntry, ...]) -> ShutubaData:
    """テスト用のShutubaDataを作成するヘルパー"""
    return ShutubaData(
        race_id="202501010101",
        race_name="Test Race",
        race_number=1,
        course="Tokyo",
        distance=1600,
        surface="turf",
        date="2025-01-01",
        entries=entries,
    )


def create_mock_past_result(
    horse_id: str,
    finish_position: int,
    total_runners: int = 10,
    race_date: str = "2024-12-01",
    course: str = "Tokyo",
    distance: int = 1600,
    surface: str = "turf",
) -> dict:
    """テスト用の過去成績データを作成するヘルパー"""
    return {
        "horse_id": horse_id,
        "finish_position": finish_position,
        "total_runners": total_runners,
        "race_date": race_date,
        "course": course,
        "distance": distance,
        "surface": surface,
        "time_index": 100.0,
        "last_3f": 34.0,
        "odds": 5.0,
        "popularity": 3,
    }


class TestPredictFromShutuba:
    """predict_from_shutubaメソッドのテスト"""

    def test_predict_from_shutuba_returns_predictions_for_all_entries(self):
        """全出走馬の予測が返ること"""
        # Arrange
        entries = (
            create_test_entry("horse_001", "Horse A", 1),
            create_test_entry("horse_002", "Horse B", 2),
            create_test_entry("horse_003", "Horse C", 3),
        )
        shutuba = create_test_shutuba(entries)

        mock_repo = Mock(spec=RaceResultRepository)
        mock_repo.get_past_results.return_value = [
            create_mock_past_result("horse_001", 1),
            create_mock_past_result("horse_001", 2),
        ]

        service = PredictionService(repository=mock_repo)

        # Act
        results = service.predict_from_shutuba(shutuba)

        # Assert
        assert len(results) == 3
        horse_numbers = {r.horse_number for r in results}
        assert horse_numbers == {1, 2, 3}

    def test_prediction_contains_required_fields(self):
        """予測結果に必要なフィールドが含まれること"""
        # Arrange
        entries = (create_test_entry("horse_001", "Horse A", 1),)
        shutuba = create_test_shutuba(entries)

        mock_repo = Mock(spec=RaceResultRepository)
        mock_repo.get_past_results.return_value = [
            create_mock_past_result("horse_001", 1),
        ]

        service = PredictionService(repository=mock_repo)

        # Act
        results = service.predict_from_shutuba(shutuba)

        # Assert
        assert len(results) == 1
        result = results[0]

        # 必須フィールドの存在確認
        assert hasattr(result, "horse_number")
        assert hasattr(result, "horse_name")
        assert hasattr(result, "horse_id")
        assert hasattr(result, "ml_probability")
        assert hasattr(result, "factor_scores")
        assert hasattr(result, "total_score")
        assert hasattr(result, "combined_score")
        assert hasattr(result, "rank")

        # 値の確認
        assert result.horse_number == 1
        assert result.horse_name == "Horse A"
        assert result.horse_id == "horse_001"
        assert isinstance(result.ml_probability, float)
        assert isinstance(result.factor_scores, dict)
        assert isinstance(result.rank, int)

    def test_ml_probability_in_valid_range(self):
        """ML確率が0-1の範囲内であること"""
        # Arrange
        entries = (
            create_test_entry("horse_001", "Horse A", 1),
            create_test_entry("horse_002", "Horse B", 2),
        )
        shutuba = create_test_shutuba(entries)

        mock_repo = Mock(spec=RaceResultRepository)
        mock_repo.get_past_results.return_value = [
            create_mock_past_result("horse_001", 1),
        ]

        service = PredictionService(repository=mock_repo)

        # Act
        results = service.predict_from_shutuba(shutuba)

        # Assert
        for result in results:
            assert 0.0 <= result.ml_probability <= 1.0, (
                f"ML probability {result.ml_probability} is out of range [0, 1]"
            )

    def test_factor_scores_calculated(self):
        """7因子スコアが計算されること"""
        # Arrange
        entries = (create_test_entry("horse_001", "Horse A", 1),)
        shutuba = create_test_shutuba(entries)

        mock_repo = Mock(spec=RaceResultRepository)
        mock_repo.get_past_results.return_value = [
            create_mock_past_result("horse_001", 1),
            create_mock_past_result("horse_001", 2, race_date="2024-11-01"),
            create_mock_past_result("horse_001", 3, race_date="2024-10-01"),
        ]

        service = PredictionService(repository=mock_repo)

        # Act
        results = service.predict_from_shutuba(shutuba)

        # Assert
        result = results[0]
        expected_factors = [
            "past_results",
            "course_fit",
            "time_index",
            "last_3f",
            "popularity",
            "pedigree",
            "running_style",
        ]

        # 7因子全てがfactor_scoresに含まれること
        for factor in expected_factors:
            assert factor in result.factor_scores, f"Factor '{factor}' not found"

    def test_predictions_sorted_by_probability(self):
        """予測結果が確率降順でソートされていること"""
        # Arrange
        entries = (
            create_test_entry("horse_001", "Horse A", 1),
            create_test_entry("horse_002", "Horse B", 2),
            create_test_entry("horse_003", "Horse C", 3),
        )
        shutuba = create_test_shutuba(entries)

        mock_repo = Mock(spec=RaceResultRepository)

        # 各馬に異なる過去成績を設定して異なるスコアになるようにする
        def get_past_results_side_effect(horse_id, before_date, limit=20):
            if horse_id == "horse_001":
                return [create_mock_past_result("horse_001", 5)]  # 弱い成績
            elif horse_id == "horse_002":
                return [create_mock_past_result("horse_002", 1)]  # 最高成績
            else:
                return [create_mock_past_result("horse_003", 3)]  # 中間成績

        mock_repo.get_past_results.side_effect = get_past_results_side_effect

        service = PredictionService(repository=mock_repo)

        # Act
        results = service.predict_from_shutuba(shutuba)

        # Assert
        probabilities = [r.ml_probability for r in results]
        assert probabilities == sorted(probabilities, reverse=True), (
            "Results should be sorted by probability in descending order"
        )

        # ランキングが正しく付与されていること
        for i, result in enumerate(results):
            assert result.rank == i + 1, f"Rank should be {i + 1}, got {result.rank}"

    def test_works_without_past_results(self):
        """過去成績がなくても動作すること（新馬戦対応）"""
        # Arrange
        entries = (
            create_test_entry("horse_001", "Horse A", 1),
            create_test_entry("horse_002", "Horse B", 2),
        )
        shutuba = create_test_shutuba(entries)

        mock_repo = Mock(spec=RaceResultRepository)
        mock_repo.get_past_results.return_value = []  # 過去成績なし

        service = PredictionService(repository=mock_repo)

        # Act
        results = service.predict_from_shutuba(shutuba)

        # Assert
        assert len(results) == 2

        for result in results:
            # ML確率は0.0（モデルなしまたは特徴量不足）
            assert result.ml_probability == 0.0
            # factor_scoresは存在するが、値はNone
            assert result.factor_scores is not None
            for factor_name, score in result.factor_scores.items():
                assert score is None, (
                    f"Factor '{factor_name}' should be None for new horse"
                )
            # total_scoreもNone
            assert result.total_score is None

    def test_data_leakage_prevention(self):
        """未来のデータが使用されないこと（データリーク防止）"""
        # Arrange
        entries = (create_test_entry("horse_001", "Horse A", 1),)
        shutuba = create_test_shutuba(entries)  # date="2025-01-01"

        mock_repo = Mock(spec=RaceResultRepository)
        mock_repo.get_past_results.return_value = [
            create_mock_past_result("horse_001", 1, race_date="2024-12-01"),
        ]

        service = PredictionService(repository=mock_repo)

        # Act
        service.predict_from_shutuba(shutuba)

        # Assert
        # get_past_resultsがbefore_dateパラメータで呼び出されていること
        mock_repo.get_past_results.assert_called()

        # 呼び出し引数を確認
        call_args = mock_repo.get_past_results.call_args
        # 位置引数またはキーワード引数でbefore_dateが渡されていることを確認
        if len(call_args.args) >= 2:
            before_date = call_args.args[1]
        else:
            before_date = call_args.kwargs.get("before_date")

        assert before_date == "2025-01-01", (
            f"before_date should be race date '2025-01-01', got '{before_date}'"
        )

    def test_predictions_sorted_by_combined_score(self):
        """combined_score降順でソートされること"""
        # Arrange
        entries = (
            create_test_entry("horse_001", "Horse A", 1),
            create_test_entry("horse_002", "Horse B", 2),
            create_test_entry("horse_003", "Horse C", 3),
        )
        shutuba = create_test_shutuba(entries)

        mock_repo = Mock(spec=RaceResultRepository)

        # 各馬に異なる過去成績を設定
        def get_past_results_side_effect(horse_id, before_date, limit=20):
            if horse_id == "horse_001":
                # ML確率低め、total_score高め -> combined中程度
                return [create_mock_past_result("horse_001", 2)]
            elif horse_id == "horse_002":
                # ML確率高め、total_score中程度 -> combined高め
                return [create_mock_past_result("horse_002", 1)]
            else:
                # ML確率中程度、total_score低め -> combined低め
                return [create_mock_past_result("horse_003", 5)]

        mock_repo.get_past_results.side_effect = get_past_results_side_effect

        service = PredictionService(repository=mock_repo)

        # Act
        results = service.predict_from_shutuba(shutuba)

        # Assert
        # combined_scoreフィールドが存在すること
        for result in results:
            assert hasattr(result, 'combined_score'), (
                f"Result should have 'combined_score' field"
            )

        # combined_scoreがNoneでない結果は降順でソートされていること
        combined_scores = [r.combined_score for r in results if r.combined_score is not None]
        assert combined_scores == sorted(combined_scores, reverse=True), (
            "Results should be sorted by combined_score in descending order"
        )


class TestCombinedScoreCalculation:
    """複合スコア計算のテスト（加重平均方式）"""

    def test_combined_score_uses_weighted_average(self):
        """加重平均で複合スコアを計算する

        alpha = 0.6 の場合:
        正規化ML = (0.5 / 1.0) * 100 = 50
        複合 = 0.6 * 50 + 0.4 * 80 = 30 + 32 = 62
        """
        mock_repo = Mock(spec=RaceResultRepository)
        mock_repo.get_past_results.return_value = []
        service = PredictionService(repository=mock_repo)

        result = service._calculate_combined_score(
            ml_probability=0.5,
            max_ml_probability=1.0,
            total_score=80.0,
        )
        assert result == 62.0

    def test_combined_score_with_low_ml_probability(self):
        """ML確率が低くても総合スコアが高ければ適度な評価

        alpha = 0.6 の場合:
        正規化ML = (0.1 / 1.0) * 100 = 10
        複合 = 0.6 * 10 + 0.4 * 90 = 6 + 36 = 42
        """
        mock_repo = Mock(spec=RaceResultRepository)
        mock_repo.get_past_results.return_value = []
        service = PredictionService(repository=mock_repo)

        result = service._calculate_combined_score(
            ml_probability=0.1,
            max_ml_probability=1.0,
            total_score=90.0,
        )
        assert result == 42.0

    def test_combined_score_with_max_ml_probability(self):
        """ML確率が最大の場合の計算

        alpha = 0.6 の場合:
        正規化ML = (0.02 / 0.02) * 100 = 100
        複合 = 0.6 * 100 + 0.4 * 80 = 60 + 32 = 92
        """
        mock_repo = Mock(spec=RaceResultRepository)
        mock_repo.get_past_results.return_value = []
        service = PredictionService(repository=mock_repo)

        score = service._calculate_combined_score(
            ml_probability=0.02,
            max_ml_probability=0.02,
            total_score=80.0
        )
        assert score == 92.0

    def test_combined_score_partial_ml(self):
        """ML確率が最大より低い場合の計算

        alpha = 0.6 の場合:
        正規化ML = (0.01 / 0.02) * 100 = 50
        複合 = 0.6 * 50 + 0.4 * 80 = 30 + 32 = 62
        """
        mock_repo = Mock(spec=RaceResultRepository)
        mock_repo.get_past_results.return_value = []
        service = PredictionService(repository=mock_repo)

        score = service._calculate_combined_score(
            ml_probability=0.01,
            max_ml_probability=0.02,
            total_score=80.0
        )
        assert score == 62.0

    def test_combined_score_none_when_no_total_score(self):
        """total_scoreがNoneの場合はNone"""
        mock_repo = Mock(spec=RaceResultRepository)
        mock_repo.get_past_results.return_value = []
        service = PredictionService(repository=mock_repo)

        score = service._calculate_combined_score(
            ml_probability=0.02,
            max_ml_probability=0.02,
            total_score=None
        )
        assert score is None

    def test_combined_score_none_when_max_ml_is_zero(self):
        """max_ml_probabilityが0の場合はNone"""
        mock_repo = Mock(spec=RaceResultRepository)
        mock_repo.get_past_results.return_value = []
        service = PredictionService(repository=mock_repo)

        score = service._calculate_combined_score(
            ml_probability=0.0,
            max_ml_probability=0.0,
            total_score=80.0
        )
        assert score is None


class TestPredictionResultDataclass:
    """PredictionResultデータクラスのテスト"""

    def test_prediction_result_is_immutable(self):
        """PredictionResultがイミュータブルであること"""
        result = PredictionResult(
            horse_number=1,
            horse_name="Horse A",
            horse_id="horse_001",
            ml_probability=0.5,
            factor_scores={"past_results": 80.0},
            total_score=80.0,
            combined_score=80.0,
            rank=1,
        )

        # frozen=Trueなので変更しようとすると例外
        with pytest.raises(Exception):  # FrozenInstanceError
            result.horse_number = 2

    def test_prediction_result_has_combined_score_field(self):
        """PredictionResultにcombined_scoreフィールドが存在すること"""
        result = PredictionResult(
            horse_number=1,
            horse_name="Horse A",
            horse_id="horse_001",
            ml_probability=0.5,
            factor_scores={"past_results": 80.0},
            total_score=80.0,
            combined_score=63.2,
            rank=1,
        )
        assert result.combined_score == 63.2

    def test_combined_score_can_be_none(self):
        """新馬戦対応: combined_scoreがNoneを許容"""
        result = PredictionResult(
            horse_number=1,
            horse_name="Horse A",
            horse_id="horse_001",
            ml_probability=0.0,
            factor_scores={},
            total_score=None,
            combined_score=None,
            rank=1,
        )
        assert result.combined_score is None


class TestIsDebutRace:
    """新馬戦判定メソッドのテスト"""

    def test_is_debut_race_returns_true_for_shinba(self):
        """新馬戦のレース名に対してTrueを返す"""
        assert PredictionService.is_debut_race("2歳新馬") is True

    def test_is_debut_race_returns_false_for_regular_race(self):
        """通常レースに対してFalseを返す"""
        assert PredictionService.is_debut_race("皐月賞(G1)") is False
        assert PredictionService.is_debut_race("3勝クラス") is False


class TestPredictFromShutubaDebutRaceSkip:
    """新馬戦スキップのテスト"""

    def test_predict_from_shutuba_returns_empty_list_for_debut_race(self):
        """新馬戦の場合は空リストを返す"""
        # Arrange: 新馬戦の出馬表データ
        entries = (
            create_test_entry("horse_001", "テスト馬", 1),
            create_test_entry("horse_002", "テスト馬2", 2),
        )
        shutuba = ShutubaData(
            race_id="202401010101",
            race_name="2歳新馬",
            race_number=1,
            date="2024-01-01",
            course="中山",
            surface="芝",
            distance=1600,
            entries=entries,
        )

        mock_repo = Mock(spec=RaceResultRepository)
        mock_repo.get_past_results.return_value = []

        service = PredictionService(repository=mock_repo)

        # Act
        result = service.predict_from_shutuba(shutuba)

        # Assert: 新馬戦なので空リストを返す
        assert result == []

        # リポジトリは呼び出されないこと（早期リターンのため）
        mock_repo.get_past_results.assert_not_called()

    def test_predict_from_shutuba_returns_predictions_for_regular_race(self):
        """通常レースの場合は予測結果を返す"""
        # Arrange: 通常レースの出馬表データ
        entries = (
            create_test_entry("horse_001", "テスト馬", 1),
        )
        shutuba = ShutubaData(
            race_id="202401010101",
            race_name="皐月賞(G1)",
            race_number=1,
            date="2024-01-01",
            course="中山",
            surface="芝",
            distance=2000,
            entries=entries,
        )

        mock_repo = Mock(spec=RaceResultRepository)
        mock_repo.get_past_results.return_value = [
            create_mock_past_result("horse_001", 1),
        ]

        service = PredictionService(repository=mock_repo)

        # Act
        result = service.predict_from_shutuba(shutuba)

        # Assert: 通常レースなので予測結果を返す
        assert len(result) == 1
        assert result[0].horse_name == "テスト馬"
