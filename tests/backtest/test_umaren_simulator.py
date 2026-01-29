"""UmarenSimulatorのテスト

馬連馬券のバックテストシミュレータをテストする
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from keiba.backtest.umaren_simulator import (
    UmarenRaceResult,
    UmarenSimulator,
    UmarenSummary,
)
from keiba.models.entry import ShutubaData


# === テストデータ生成ヘルパー ===


def make_umaren_race_result(
    race_id: str = "202501050101",
    race_name: str = "テストレース",
    venue: str = "中山",
    race_date: str = "2025-01-01",
    bet_combinations: tuple[tuple[int, int], ...] = ((1, 2), (1, 3), (2, 3)),
    actual_pair: tuple[int, int] | None = (1, 2),
    hit: bool = True,
    payout: int = 1500,
    investment: int = 300,
) -> UmarenRaceResult:
    """テスト用UmarenRaceResultを生成"""
    return UmarenRaceResult(
        race_id=race_id,
        race_name=race_name,
        venue=venue,
        race_date=race_date,
        bet_combinations=bet_combinations,
        actual_pair=actual_pair,
        hit=hit,
        payout=payout,
        investment=investment,
    )


def make_umaren_summary(
    period_from: str = "2025-01-01",
    period_to: str = "2025-01-31",
    total_races: int = 10,
    total_hits: int = 3,
    hit_rate: float = 0.3,
    total_investment: int = 3000,
    total_payout: int = 4500,
    return_rate: float = 1.5,
    race_results: tuple[UmarenRaceResult, ...] | None = None,
) -> UmarenSummary:
    """テスト用UmarenSummaryを生成"""
    if race_results is None:
        race_results = ()
    return UmarenSummary(
        period_from=period_from,
        period_to=period_to,
        total_races=total_races,
        total_hits=total_hits,
        hit_rate=hit_rate,
        total_investment=total_investment,
        total_payout=total_payout,
        return_rate=return_rate,
        race_results=race_results,
    )


# === UmarenRaceResult データクラスのテスト ===


class TestUmarenRaceResult:
    """UmarenRaceResultデータクラスのテスト"""

    def test_create_instance(self):
        """UmarenRaceResultインスタンスを作成できる"""
        result = UmarenRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            bet_combinations=((1, 2), (1, 3), (2, 3)),
            actual_pair=(1, 2),
            hit=True,
            payout=1500,
            investment=300,
        )
        assert result.race_id == "202501050101"
        assert result.race_name == "1R 3歳未勝利"
        assert result.venue == "中山"
        assert result.race_date == "2025-01-05"
        assert result.bet_combinations == ((1, 2), (1, 3), (2, 3))
        assert result.actual_pair == (1, 2)
        assert result.hit is True
        assert result.payout == 1500
        assert result.investment == 300

    def test_immutability(self):
        """frozen=Trueで変更不可であることを確認"""
        result = make_umaren_race_result()

        with pytest.raises(AttributeError):
            result.race_id = "changed"  # type: ignore

        with pytest.raises(AttributeError):
            result.investment = 500  # type: ignore

    def test_hit_case_first_combination(self):
        """的中ケース: 1-2の組み合わせが的中"""
        # 予測Top3: 1, 2, 3 -> 馬連組み合わせ: (1,2), (1,3), (2,3)
        # 実際の1-2着: 1-2
        result = UmarenRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            bet_combinations=((1, 2), (1, 3), (2, 3)),
            actual_pair=(1, 2),
            hit=True,
            payout=1500,
            investment=300,
        )
        assert result.hit is True
        assert result.payout == 1500
        # 回収率 1500/300 = 5.0
        assert result.payout > result.investment

    def test_hit_case_second_combination(self):
        """的中ケース: 1-3の組み合わせが的中"""
        # 予測Top3: 1, 2, 3 -> 馬連組み合わせ: (1,2), (1,3), (2,3)
        # 実際の1-2着: 1-3
        result = UmarenRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            bet_combinations=((1, 2), (1, 3), (2, 3)),
            actual_pair=(1, 3),
            hit=True,
            payout=2000,
            investment=300,
        )
        assert result.hit is True
        assert result.actual_pair == (1, 3)

    def test_hit_case_third_combination(self):
        """的中ケース: 2-3の組み合わせが的中"""
        # 予測Top3: 1, 2, 3 -> 馬連組み合わせ: (1,2), (1,3), (2,3)
        # 実際の1-2着: 2-3
        result = UmarenRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            bet_combinations=((1, 2), (1, 3), (2, 3)),
            actual_pair=(2, 3),
            hit=True,
            payout=2500,
            investment=300,
        )
        assert result.hit is True
        assert result.actual_pair == (2, 3)

    def test_no_hit_case(self):
        """外れケース: 予測組み合わせに的中がない"""
        # 予測Top3: 1, 2, 3 -> 馬連組み合わせ: (1,2), (1,3), (2,3)
        # 実際の1-2着: 5-8（予測外）
        result = UmarenRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            bet_combinations=((1, 2), (1, 3), (2, 3)),
            actual_pair=(5, 8),
            hit=False,
            payout=0,
            investment=300,
        )
        assert result.hit is False
        assert result.payout == 0
        assert result.investment == 300

    def test_no_umaren_data(self):
        """馬連データがない場合"""
        result = UmarenRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            bet_combinations=((1, 2), (1, 3), (2, 3)),
            actual_pair=None,
            hit=False,
            payout=0,
            investment=300,
        )
        assert result.actual_pair is None
        assert result.hit is False
        assert result.payout == 0


# === UmarenSummary データクラスのテスト ===


class TestUmarenSummary:
    """UmarenSummaryデータクラスのテスト"""

    def test_create_instance(self):
        """UmarenSummaryインスタンスを作成できる"""
        summary = UmarenSummary(
            period_from="2025-01-01",
            period_to="2025-01-31",
            total_races=10,
            total_hits=3,
            hit_rate=0.3,
            total_investment=3000,
            total_payout=4500,
            return_rate=1.5,
            race_results=(),
        )
        assert summary.period_from == "2025-01-01"
        assert summary.period_to == "2025-01-31"
        assert summary.total_races == 10
        assert summary.total_hits == 3
        assert summary.hit_rate == 0.3
        assert summary.total_investment == 3000
        assert summary.total_payout == 4500
        assert summary.return_rate == 1.5
        assert summary.race_results == ()

    def test_immutability(self):
        """frozen=Trueで変更不可であることを確認"""
        summary = make_umaren_summary()

        with pytest.raises(AttributeError):
            summary.total_races = 20  # type: ignore

        with pytest.raises(AttributeError):
            summary.return_rate = 2.0  # type: ignore

    def test_calculate_return_rate(self):
        """回収率計算の正確性を確認"""
        # 投資3000円、払戻4500円 -> 回収率150%
        summary = make_umaren_summary(
            total_investment=3000,
            total_payout=4500,
            return_rate=1.5,
        )
        expected_return_rate = 4500 / 3000
        assert abs(summary.return_rate - expected_return_rate) < 0.001

        # 投資3000円、払戻1500円 -> 回収率50%
        summary2 = make_umaren_summary(
            total_investment=3000,
            total_payout=1500,
            return_rate=0.5,
        )
        expected_return_rate2 = 1500 / 3000
        assert abs(summary2.return_rate - expected_return_rate2) < 0.001

    def test_calculate_hit_rate(self):
        """的中率計算の正確性を確認"""
        # 10レース中3的中 -> 的中率30%
        summary = make_umaren_summary(
            total_races=10,
            total_hits=3,
            hit_rate=0.3,
        )
        expected_hit_rate = 3 / 10
        assert abs(summary.hit_rate - expected_hit_rate) < 0.001

        # 10レース中5的中 -> 的中率50%
        summary2 = make_umaren_summary(
            total_races=10,
            total_hits=5,
            hit_rate=0.5,
        )
        expected_hit_rate2 = 5 / 10
        assert abs(summary2.hit_rate - expected_hit_rate2) < 0.001

    def test_with_race_results(self):
        """race_resultsを含むサマリーを作成できる"""
        race1 = make_umaren_race_result(
            race_id="202501050101",
            hit=True,
            payout=1500,
        )
        race2 = make_umaren_race_result(
            race_id="202501050102",
            hit=False,
            payout=0,
        )
        summary = make_umaren_summary(
            total_races=2,
            race_results=(race1, race2),
        )
        assert len(summary.race_results) == 2
        assert summary.race_results[0].race_id == "202501050101"
        assert summary.race_results[1].race_id == "202501050102"


# === UmarenSimulator クラスのテスト ===


def _make_mock_race(
    race_id: str = "202501050101",
    name: str = "テストレース",
    course: str = "中山",
    race_date: date | None = None,
) -> MagicMock:
    """モックRaceオブジェクトを作成"""
    mock_race = MagicMock()
    mock_race.id = race_id
    mock_race.name = name
    mock_race.course = course
    mock_race.date = race_date if race_date else date(2025, 1, 5)
    return mock_race


def _make_mock_race_result(
    horse_number: int,
    popularity: int,
    horse_id: str | None = None,
    horse_name: str | None = None,
    jockey_id: str | None = None,
    jockey_name: str | None = None,
    bracket_number: int | None = None,
    impost: float | None = None,
    sex: str | None = None,
    age: int | None = None,
) -> MagicMock:
    """モックRaceResultオブジェクトを作成"""
    mock_result = MagicMock()
    mock_result.horse_number = horse_number
    mock_result.popularity = popularity
    mock_result.horse_id = horse_id if horse_id else f"horse_{horse_number:03d}"
    mock_result.jockey_id = jockey_id if jockey_id else f"jockey_{horse_number:03d}"
    mock_result.bracket_number = bracket_number if bracket_number else (horse_number - 1) // 2 + 1
    mock_result.impost = impost if impost else 55.0
    mock_result.sex = sex if sex else "牡"
    mock_result.age = age if age else 3

    # リレーションシップのモック（horse, jockeyオブジェクト）
    mock_horse = MagicMock()
    mock_horse.name = horse_name if horse_name else f"テスト馬{horse_number}"
    mock_result.horse = mock_horse

    mock_jockey = MagicMock()
    mock_jockey.name = jockey_name if jockey_name else f"テスト騎手{horse_number}"
    mock_result.jockey = mock_jockey

    return mock_result


class TestUmarenSimulator:
    """UmarenSimulatorクラスのテスト"""

    @pytest.fixture
    def simulator(self, tmp_path):
        """テスト用シミュレータを作成"""
        db_path = str(tmp_path / "test.db")
        # BaseSimulatorの__init__でRaceDetailScraperが作成されるため、
        # 事前にモック化する
        with patch("keiba.backtest.base_simulator.RaceDetailScraper") as mock_scraper_cls:
            mock_scraper = MagicMock()
            mock_scraper_cls.return_value = mock_scraper
            simulator = UmarenSimulator(db_path)
            # テスト内でモックスクレイパーを上書きできるように保持
            simulator._scraper = mock_scraper
        return simulator

    def test_init_with_db_path(self, tmp_path):
        """DBパスを指定してシミュレータを初期化できる"""
        db_path = str(tmp_path / "test.db")
        simulator = UmarenSimulator(db_path)
        assert simulator is not None

    def test_simulate_race_hit_first_combination(self, simulator):
        """馬連的中ケース: 1-2組み合わせが的中"""
        mock_race = _make_mock_race(race_id="202501050101")
        mock_race.race_number = 1
        mock_race.distance = 1200
        mock_race.surface = "芝"
        mock_results = [
            _make_mock_race_result(horse_number=1, popularity=1),
            _make_mock_race_result(horse_number=2, popularity=2),
            _make_mock_race_result(horse_number=3, popularity=3),
        ]
        # 馬連払戻: 1-2が1-2着、払戻1500円
        mock_umaren_payout = {"horse_numbers": [1, 2], "payout": 1500}

        with patch.object(simulator, "_get_session") as mock_session_factory:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.get.return_value = mock_race
            mock_session.execute.return_value.scalars.return_value.all.return_value = (
                mock_results
            )
            mock_session_factory.return_value = mock_session

            simulator._scraper.fetch_umaren_payout.return_value = mock_umaren_payout
            result = simulator.simulate_race("202501050101")

        assert isinstance(result, UmarenRaceResult)
        assert result.race_id == "202501050101"
        assert result.bet_combinations == ((1, 2), (1, 3), (2, 3))
        assert result.actual_pair == (1, 2)
        assert result.hit is True
        assert result.payout == 1500
        assert result.investment == 300  # 3点 x 100円

    def test_simulate_race_hit_second_combination(self, simulator):
        """馬連的中ケース: 1-3組み合わせが的中"""
        mock_race = _make_mock_race(race_id="202501050102")
        mock_race.race_number = 2
        mock_race.distance = 1600
        mock_race.surface = "ダート"
        mock_results = [
            _make_mock_race_result(horse_number=1, popularity=1),
            _make_mock_race_result(horse_number=2, popularity=2),
            _make_mock_race_result(horse_number=3, popularity=3),
        ]
        # 馬連払戻: 1-3が1-2着（順序は小さい方が先）
        mock_umaren_payout = {"horse_numbers": [1, 3], "payout": 2000}

        with patch.object(simulator, "_get_session") as mock_session_factory:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.get.return_value = mock_race
            mock_session.execute.return_value.scalars.return_value.all.return_value = (
                mock_results
            )
            mock_session_factory.return_value = mock_session

            simulator._scraper.fetch_umaren_payout.return_value = mock_umaren_payout
            result = simulator.simulate_race("202501050102")

        assert isinstance(result, UmarenRaceResult)
        assert result.actual_pair == (1, 3)
        assert result.hit is True
        assert result.payout == 2000

    def test_simulate_race_no_hit(self, simulator):
        """馬連外れケース: 予測組み合わせに的中がない"""
        mock_race = _make_mock_race(race_id="202501050103")
        mock_race.race_number = 3
        mock_race.distance = 1800
        mock_race.surface = "芝"
        mock_results = [
            _make_mock_race_result(horse_number=1, popularity=1),
            _make_mock_race_result(horse_number=2, popularity=2),
            _make_mock_race_result(horse_number=3, popularity=3),
        ]
        # 馬連払戻: 5-8が1-2着（予測外）
        mock_umaren_payout = {"horse_numbers": [5, 8], "payout": 5000}

        with patch.object(simulator, "_get_session") as mock_session_factory:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.get.return_value = mock_race
            mock_session.execute.return_value.scalars.return_value.all.return_value = (
                mock_results
            )
            mock_session_factory.return_value = mock_session

            simulator._scraper.fetch_umaren_payout.return_value = mock_umaren_payout
            result = simulator.simulate_race("202501050103")

        assert isinstance(result, UmarenRaceResult)
        assert result.actual_pair == (5, 8)
        assert result.hit is False
        assert result.payout == 0
        assert result.investment == 300

    def test_simulate_race_no_umaren_data(self, simulator):
        """馬連払戻データがない場合"""
        mock_race = _make_mock_race(race_id="202501050104")
        mock_race.race_number = 4
        mock_race.distance = 2000
        mock_race.surface = "芝"
        mock_results = [
            _make_mock_race_result(horse_number=1, popularity=1),
            _make_mock_race_result(horse_number=2, popularity=2),
            _make_mock_race_result(horse_number=3, popularity=3),
        ]

        with patch.object(simulator, "_get_session") as mock_session_factory:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.get.return_value = mock_race
            mock_session.execute.return_value.scalars.return_value.all.return_value = (
                mock_results
            )
            mock_session_factory.return_value = mock_session

            simulator._scraper.fetch_umaren_payout.return_value = None
            result = simulator.simulate_race("202501050104")

        assert isinstance(result, UmarenRaceResult)
        assert result.actual_pair is None
        assert result.hit is False
        assert result.payout == 0
        assert result.investment == 300

    def test_simulate_race_not_found(self, simulator):
        """レースが見つからない場合"""
        with patch.object(simulator, "_get_session") as mock_session_factory:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.get.return_value = None
            mock_session_factory.return_value = mock_session

            with pytest.raises(ValueError, match="Race not found"):
                simulator.simulate_race("nonexistent")

    def test_simulate_period(self, simulator):
        """期間シミュレーション"""
        mock_races = [
            _make_mock_race(race_id="202501050101", course="中山"),
            _make_mock_race(race_id="202501050102", course="京都"),
        ]
        for race in mock_races:
            race.race_number = 1
            race.distance = 1200
            race.surface = "芝"

        mock_results = [
            _make_mock_race_result(horse_number=1, popularity=1),
            _make_mock_race_result(horse_number=2, popularity=2),
            _make_mock_race_result(horse_number=3, popularity=3),
        ]
        # レース1: 1-2が的中
        # レース2: 5-8で外れ
        mock_umaren_payouts = [
            {"horse_numbers": [1, 2], "payout": 1500},
            {"horse_numbers": [5, 8], "payout": 5000},
        ]

        with patch.object(simulator, "_get_session") as mock_session_factory:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.execute.return_value.scalars.return_value.all.side_effect = [
                mock_races,  # _get_races_in_period
                mock_results,  # simulate_race for race 1
                mock_results,  # simulate_race for race 2
            ]
            mock_session.get.side_effect = [mock_races[0], mock_races[1]]
            mock_session_factory.return_value = mock_session

            simulator._scraper.fetch_umaren_payout.side_effect = mock_umaren_payouts
            summary = simulator.simulate_period(
                from_date="2025-01-01",
                to_date="2025-01-31",
                venues=None,
            )

        assert isinstance(summary, UmarenSummary)
        assert summary.period_from == "2025-01-01"
        assert summary.period_to == "2025-01-31"
        assert summary.total_races == 2
        assert summary.total_hits == 1  # 1レースのみ的中
        assert summary.total_investment == 600  # 300 * 2
        assert summary.total_payout == 1500  # 1レース的中分

    def test_simulate_period_with_venue_filter(self, simulator):
        """特定会場でフィルタリングした期間シミュレーション"""
        mock_races = [_make_mock_race(race_id="202501050101", course="中山")]
        mock_races[0].race_number = 1
        mock_races[0].distance = 1200
        mock_races[0].surface = "芝"

        mock_results = [
            _make_mock_race_result(horse_number=1, popularity=1),
            _make_mock_race_result(horse_number=2, popularity=2),
            _make_mock_race_result(horse_number=3, popularity=3),
        ]
        mock_umaren_payout = {"horse_numbers": [1, 2], "payout": 1500}

        with patch.object(simulator, "_get_session") as mock_session_factory:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.execute.return_value.scalars.return_value.all.side_effect = [
                mock_races,
                mock_results,
            ]
            mock_session.get.return_value = mock_races[0]
            mock_session_factory.return_value = mock_session

            simulator._scraper.fetch_umaren_payout.return_value = mock_umaren_payout
            summary = simulator.simulate_period(
                from_date="2025-01-01",
                to_date="2025-01-31",
                venues=["中山", "京都"],
            )

        assert isinstance(summary, UmarenSummary)
        for race_result in summary.race_results:
            assert race_result.venue in ["中山", "京都"]

    def test_simulate_period_empty_result(self, simulator):
        """対象レースがない期間のシミュレーション"""
        with patch.object(simulator, "_get_session") as mock_session_factory:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.execute.return_value.scalars.return_value.all.return_value = []
            mock_session_factory.return_value = mock_session

            summary = simulator.simulate_period(
                from_date="1900-01-01",
                to_date="1900-01-31",
                venues=None,
            )

        assert isinstance(summary, UmarenSummary)
        assert summary.total_races == 0
        assert summary.total_hits == 0
        assert summary.hit_rate == 0.0
        assert summary.return_rate == 0.0


# === エッジケースのテスト ===


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_umaren_race_result_with_empty_combinations(self):
        """空の組み合わせを持つUmarenRaceResult"""
        result = UmarenRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            bet_combinations=(),
            actual_pair=None,
            hit=False,
            payout=0,
            investment=0,
        )
        assert result.bet_combinations == ()
        assert result.investment == 0

    def test_umaren_summary_with_zero_values(self):
        """ゼロ値を持つUmarenSummary"""
        summary = UmarenSummary(
            period_from="2025-01-01",
            period_to="2025-01-31",
            total_races=0,
            total_hits=0,
            hit_rate=0.0,
            total_investment=0,
            total_payout=0,
            return_rate=0.0,
            race_results=(),
        )
        assert summary.total_races == 0
        assert summary.hit_rate == 0.0
        assert summary.return_rate == 0.0

    def test_umaren_race_result_high_payout(self):
        """高額払戻のケース"""
        # 大穴的中: 50,000円以上の払戻
        result = UmarenRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            bet_combinations=((10, 12), (10, 15), (12, 15)),
            actual_pair=(10, 12),
            hit=True,
            payout=58900,
            investment=300,
        )
        assert result.payout == 58900
        # 回収率 58900/300 = 約196.3
        assert result.payout / result.investment > 190

    def test_bet_combinations_order(self):
        """馬連組み合わせの順序確認

        予測Top3が(5, 3, 1)の場合、組み合わせは
        (3, 5), (1, 5), (1, 3) となる（小さい番号が先）
        """
        # このテストは実装が正しい順序で組み合わせを生成することを確認
        result = UmarenRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            bet_combinations=((3, 5), (1, 5), (1, 3)),
            actual_pair=(3, 5),
            hit=True,
            payout=1500,
            investment=300,
        )
        # 各組み合わせで小さい番号が先になっているか確認
        for combo in result.bet_combinations:
            assert combo[0] < combo[1], f"Combination {combo} should have smaller number first"


# === PredictionService統合テスト ===


class TestSimulateRaceWithPredictionService:
    """simulate_raceがPredictionServiceを使用するテスト

    simulate_raceは人気順ではなく、PredictionServiceの7ファクタースコア順で
    Top-N馬を選択し、そこから馬連組み合わせを生成することを確認する。
    """

    @pytest.fixture
    def simulator(self, tmp_path):
        """テスト用シミュレータを作成"""
        db_path = str(tmp_path / "test.db")
        # BaseSimulatorの__init__でRaceDetailScraperが作成されるため、
        # 事前にモック化する
        with patch("keiba.backtest.base_simulator.RaceDetailScraper") as mock_scraper_cls:
            mock_scraper = MagicMock()
            mock_scraper_cls.return_value = mock_scraper
            simulator = UmarenSimulator(db_path)
            # テスト内でモックスクレイパーを上書きできるように保持
            simulator._scraper = mock_scraper
        return simulator

    def test_simulate_race_uses_prediction_service(self, simulator):
        """PredictionServiceが呼び出され、予測順でTop-3から馬連組み合わせが生成されることを確認

        予測順序が人気順と異なる場合、bet_combinationsは予測順に基づく。
        モック予測: 馬番5（rank=1）, 馬番3（rank=2）, 馬番1（rank=3）
        人気順: 馬番1（人気1）, 馬番2（人気2）, 馬番3（人気3）
        期待: bet_combinations = ((3, 5), (1, 5), (1, 3))
        """
        from keiba.services.prediction_service import PredictionResult

        mock_race = _make_mock_race(race_id="202501050101")
        mock_race.race_number = 1
        mock_race.distance = 1200
        mock_race.surface = "芝"

        # 人気順: 馬番1(人気1), 馬番2(人気2), 馬番3(人気3), 馬番4(人気4), 馬番5(人気5)
        mock_results = [
            _make_mock_race_result(horse_number=1, popularity=1, horse_name="人気1番馬"),
            _make_mock_race_result(horse_number=2, popularity=2, horse_name="人気2番馬"),
            _make_mock_race_result(horse_number=3, popularity=3, horse_name="人気3番馬"),
            _make_mock_race_result(horse_number=4, popularity=4, horse_name="人気4番馬"),
            _make_mock_race_result(horse_number=5, popularity=5, horse_name="人気5番馬"),
        ]

        # PredictionServiceの予測結果: 馬番5, 3, 1の順（人気順とは異なる）
        mock_predictions = [
            PredictionResult(
                horse_number=5,
                horse_name="人気5番馬",
                horse_id="horse_005",
                ml_probability=0.0,
                factor_scores={
                    "past_results": 80.0,
                    "course_fit": 75.0,
                    "time_index": 70.0,
                    "last_3f": 72.0,
                    "popularity": 60.0,
                    "pedigree": 68.0,
                    "running_style": 65.0,
                },
                total_score=75.0,
                combined_score=None,
                rank=1,
            ),
            PredictionResult(
                horse_number=3,
                horse_name="人気3番馬",
                horse_id="horse_003",
                ml_probability=0.0,
                factor_scores={
                    "past_results": 70.0,
                    "course_fit": 65.0,
                    "time_index": 60.0,
                    "last_3f": 62.0,
                    "popularity": 70.0,
                    "pedigree": 58.0,
                    "running_style": 55.0,
                },
                total_score=65.0,
                combined_score=None,
                rank=2,
            ),
            PredictionResult(
                horse_number=1,
                horse_name="人気1番馬",
                horse_id="horse_001",
                ml_probability=0.0,
                factor_scores={
                    "past_results": 60.0,
                    "course_fit": 55.0,
                    "time_index": 50.0,
                    "last_3f": 52.0,
                    "popularity": 90.0,
                    "pedigree": 48.0,
                    "running_style": 45.0,
                },
                total_score=55.0,
                combined_score=None,
                rank=3,
            ),
            PredictionResult(
                horse_number=2,
                horse_name="人気2番馬",
                horse_id="horse_002",
                ml_probability=0.0,
                factor_scores={
                    "past_results": 50.0,
                    "course_fit": 45.0,
                    "time_index": 40.0,
                    "last_3f": 42.0,
                    "popularity": 85.0,
                    "pedigree": 38.0,
                    "running_style": 35.0,
                },
                total_score=45.0,
                combined_score=None,
                rank=4,
            ),
            PredictionResult(
                horse_number=4,
                horse_name="人気4番馬",
                horse_id="horse_004",
                ml_probability=0.0,
                factor_scores={
                    "past_results": 40.0,
                    "course_fit": 35.0,
                    "time_index": 30.0,
                    "last_3f": 32.0,
                    "popularity": 65.0,
                    "pedigree": 28.0,
                    "running_style": 25.0,
                },
                total_score=35.0,
                combined_score=None,
                rank=5,
            ),
        ]

        # 馬連対象: 馬番3-5が1-2着
        mock_umaren_payout = {"horse_numbers": [3, 5], "payout": 2500}

        with patch.object(simulator, "_get_session") as mock_session_factory:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.get.return_value = mock_race
            mock_session.execute.return_value.scalars.return_value.all.return_value = (
                mock_results
            )
            mock_session_factory.return_value = mock_session

            simulator._scraper.fetch_umaren_payout.return_value = mock_umaren_payout

            with patch(
                "keiba.backtest.umaren_simulator.PredictionService"
            ) as mock_prediction_service_cls:
                mock_prediction_service = MagicMock()
                mock_prediction_service.predict_from_shutuba.return_value = (
                    mock_predictions
                )
                mock_prediction_service_cls.return_value = mock_prediction_service

                result = simulator.simulate_race("202501050101")

        # 予測順（馬番5, 3, 1）から生成された組み合わせを確認
        # 組み合わせ: (3,5), (1,5), (1,3) （小さい番号が先）
        expected_combinations = ((3, 5), (1, 5), (1, 3))
        assert result.bet_combinations == expected_combinations, (
            f"Expected bet_combinations {expected_combinations}, got {result.bet_combinations}. "
            "simulate_race should use PredictionService, not popularity order."
        )

        # 人気順（馬番1, 2, 3）からの組み合わせではないことを確認
        popularity_based_combinations = ((1, 2), (1, 3), (2, 3))
        assert result.bet_combinations != popularity_based_combinations, (
            "bet_combinations should NOT be based on popularity order."
        )

        # 馬番3-5が1-2着なので、(3,5)が的中
        assert result.actual_pair == (3, 5)
        assert result.hit is True
        assert result.payout == 2500

    def test_simulate_race_prediction_order_affects_result(self, simulator):
        """予測順序が異なると結果も異なることを確認

        同じレースでも予測順序が変われば、bet_combinationsと的中結果が変わる。
        """
        from keiba.services.prediction_service import PredictionResult

        mock_race = _make_mock_race(race_id="202501050102")
        mock_race.race_number = 2
        mock_race.distance = 1600
        mock_race.surface = "ダート"

        # 人気順: 馬番1(人気1), 馬番2(人気2), 馬番3(人気3)
        mock_results = [
            _make_mock_race_result(horse_number=1, popularity=1),
            _make_mock_race_result(horse_number=2, popularity=2),
            _make_mock_race_result(horse_number=3, popularity=3),
            _make_mock_race_result(horse_number=4, popularity=4),
            _make_mock_race_result(horse_number=5, popularity=5),
        ]

        # 予測順: 馬番4, 5, 2の順（人気4番, 5番, 2番の馬）
        mock_predictions = [
            PredictionResult(
                horse_number=4,
                horse_name="テスト馬4",
                horse_id="horse_004",
                ml_probability=0.0,
                factor_scores={"past_results": 85.0},
                total_score=85.0,
                combined_score=None,
                rank=1,
            ),
            PredictionResult(
                horse_number=5,
                horse_name="テスト馬5",
                horse_id="horse_005",
                ml_probability=0.0,
                factor_scores={"past_results": 80.0},
                total_score=80.0,
                combined_score=None,
                rank=2,
            ),
            PredictionResult(
                horse_number=2,
                horse_name="テスト馬2",
                horse_id="horse_002",
                ml_probability=0.0,
                factor_scores={"past_results": 75.0},
                total_score=75.0,
                combined_score=None,
                rank=3,
            ),
            PredictionResult(
                horse_number=1,
                horse_name="テスト馬1",
                horse_id="horse_001",
                ml_probability=0.0,
                factor_scores={"past_results": 70.0},
                total_score=70.0,
                combined_score=None,
                rank=4,
            ),
            PredictionResult(
                horse_number=3,
                horse_name="テスト馬3",
                horse_id="horse_003",
                ml_probability=0.0,
                factor_scores={"past_results": 65.0},
                total_score=65.0,
                combined_score=None,
                rank=5,
            ),
        ]

        # 馬連: 馬番1-2が1-2着
        # 予測Top3（4, 5, 2）の組み合わせ: (4,5), (2,4), (2,5)
        # 馬番1-2は予測組み合わせに含まれないため外れ
        mock_umaren_payout = {"horse_numbers": [1, 2], "payout": 1500}

        with patch.object(simulator, "_get_session") as mock_session_factory:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.get.return_value = mock_race
            mock_session.execute.return_value.scalars.return_value.all.return_value = (
                mock_results
            )
            mock_session_factory.return_value = mock_session

            simulator._scraper.fetch_umaren_payout.return_value = mock_umaren_payout

            with patch(
                "keiba.backtest.umaren_simulator.PredictionService"
            ) as mock_prediction_service_cls:
                mock_prediction_service = MagicMock()
                mock_prediction_service.predict_from_shutuba.return_value = (
                    mock_predictions
                )
                mock_prediction_service_cls.return_value = mock_prediction_service

                result = simulator.simulate_race("202501050102")

        # 予測順（馬番4, 5, 2）から生成された組み合わせを確認
        expected_combinations = ((4, 5), (2, 4), (2, 5))
        assert result.bet_combinations == expected_combinations, (
            f"Expected {expected_combinations}, got {result.bet_combinations}"
        )

        # 馬番1-2が1-2着だが、予測組み合わせには含まれないため外れ
        assert result.actual_pair == (1, 2)
        assert result.hit is False
        assert result.payout == 0

        # 人気順（1, 2, 3）の組み合わせ（1,2), (1,3), (2,3）だった場合は的中していたはず
        # これは予測順が結果に影響することを示す
