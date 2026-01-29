"""TanshoSimulatorのテスト

単勝馬券のバックテストシミュレータをテストする
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from keiba.backtest.tansho_simulator import (
    TanshoRaceResult,
    TanshoSimulator,
    TanshoSummary,
)
from keiba.models.entry import ShutubaData


# === テストデータ生成ヘルパー ===


def make_tansho_race_result(
    race_id: str = "202501050101",
    race_name: str = "テストレース",
    venue: str = "中山",
    race_date: str = "2025-01-01",
    top_n_predictions: tuple[int, ...] = (1, 2, 3),
    winning_horse: int | None = 1,
    hit: bool = True,
    payout: int = 350,
    investment: int = 300,
) -> TanshoRaceResult:
    """テスト用TanshoRaceResultを生成"""
    return TanshoRaceResult(
        race_id=race_id,
        race_name=race_name,
        venue=venue,
        race_date=race_date,
        top_n_predictions=top_n_predictions,
        winning_horse=winning_horse,
        hit=hit,
        payout=payout,
        investment=investment,
    )


def make_tansho_summary(
    period_from: str = "2025-01-01",
    period_to: str = "2025-01-31",
    total_races: int = 10,
    total_bets: int = 30,
    total_hits: int = 3,
    hit_rate: float = 0.1,
    total_investment: int = 3000,
    total_payout: int = 2400,
    return_rate: float = 0.8,
    race_results: tuple[TanshoRaceResult, ...] | None = None,
) -> TanshoSummary:
    """テスト用TanshoSummaryを生成"""
    if race_results is None:
        race_results = ()
    return TanshoSummary(
        period_from=period_from,
        period_to=period_to,
        total_races=total_races,
        total_bets=total_bets,
        total_hits=total_hits,
        hit_rate=hit_rate,
        total_investment=total_investment,
        total_payout=total_payout,
        return_rate=return_rate,
        race_results=race_results,
    )


# === TanshoRaceResult データクラスのテスト ===


class TestTanshoRaceResult:
    """TanshoRaceResultデータクラスのテスト"""

    def test_create_instance(self):
        """TanshoRaceResultインスタンスを作成できる"""
        result = TanshoRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            top_n_predictions=(1, 2, 3),
            winning_horse=1,
            hit=True,
            payout=350,
            investment=300,
        )
        assert result.race_id == "202501050101"
        assert result.race_name == "1R 3歳未勝利"
        assert result.venue == "中山"
        assert result.race_date == "2025-01-05"
        assert result.top_n_predictions == (1, 2, 3)
        assert result.winning_horse == 1
        assert result.hit is True
        assert result.payout == 350
        assert result.investment == 300

    def test_immutability(self):
        """frozen=Trueで変更不可であることを確認"""
        result = make_tansho_race_result()

        with pytest.raises(AttributeError):
            result.race_id = "changed"  # type: ignore

        with pytest.raises(AttributeError):
            result.investment = 500  # type: ignore

    def test_hit_case(self):
        """的中ケース: 予測馬が1着"""
        # 予測: 1, 2, 3番 / 1着: 2番
        result = TanshoRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            top_n_predictions=(1, 2, 3),
            winning_horse=2,
            hit=True,
            payout=500,
            investment=300,
        )
        assert result.hit is True
        assert result.payout == 500
        assert result.investment == 300
        # 回収率 500/300 = 約1.67
        assert result.payout > result.investment

    def test_no_hit_case(self):
        """外れケース: 予測馬が1着ではない"""
        # 予測: 1, 2, 3番 / 1着: 5番
        result = TanshoRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            top_n_predictions=(1, 2, 3),
            winning_horse=5,
            hit=False,
            payout=0,
            investment=300,
        )
        assert result.hit is False
        assert result.payout == 0
        assert result.investment == 300

    def test_no_winning_horse_data(self):
        """勝ち馬データがない場合"""
        result = TanshoRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            top_n_predictions=(1, 2, 3),
            winning_horse=None,
            hit=False,
            payout=0,
            investment=300,
        )
        assert result.winning_horse is None
        assert result.hit is False
        assert result.payout == 0


# === TanshoSummary データクラスのテスト ===


class TestTanshoSummary:
    """TanshoSummaryデータクラスのテスト"""

    def test_create_instance(self):
        """TanshoSummaryインスタンスを作成できる"""
        summary = TanshoSummary(
            period_from="2025-01-01",
            period_to="2025-01-31",
            total_races=10,
            total_bets=30,
            total_hits=3,
            hit_rate=0.1,
            total_investment=3000,
            total_payout=2400,
            return_rate=0.8,
            race_results=(),
        )
        assert summary.period_from == "2025-01-01"
        assert summary.period_to == "2025-01-31"
        assert summary.total_races == 10
        assert summary.total_bets == 30
        assert summary.total_hits == 3
        assert summary.hit_rate == 0.1
        assert summary.total_investment == 3000
        assert summary.total_payout == 2400
        assert summary.return_rate == 0.8
        assert summary.race_results == ()

    def test_immutability(self):
        """frozen=Trueで変更不可であることを確認"""
        summary = make_tansho_summary()

        with pytest.raises(AttributeError):
            summary.total_races = 20  # type: ignore

        with pytest.raises(AttributeError):
            summary.return_rate = 1.5  # type: ignore

    def test_calculate_return_rate(self):
        """回収率計算の正確性を確認"""
        # 投資3000円、払戻2400円 -> 回収率80%
        summary = make_tansho_summary(
            total_investment=3000,
            total_payout=2400,
            return_rate=0.8,
        )
        expected_return_rate = 2400 / 3000
        assert abs(summary.return_rate - expected_return_rate) < 0.001

        # 投資3000円、払戻4500円 -> 回収率150%
        summary2 = make_tansho_summary(
            total_investment=3000,
            total_payout=4500,
            return_rate=1.5,
        )
        expected_return_rate2 = 4500 / 3000
        assert abs(summary2.return_rate - expected_return_rate2) < 0.001

    def test_calculate_hit_rate(self):
        """的中率計算の正確性を確認"""
        # 10レース中3的中 -> 的中率30%
        summary = make_tansho_summary(
            total_races=10,
            total_hits=3,
            hit_rate=0.3,
        )
        expected_hit_rate = 3 / 10
        assert abs(summary.hit_rate - expected_hit_rate) < 0.001

        # 10レース中8的中 -> 的中率80%
        summary2 = make_tansho_summary(
            total_races=10,
            total_hits=8,
            hit_rate=0.8,
        )
        expected_hit_rate2 = 8 / 10
        assert abs(summary2.hit_rate - expected_hit_rate2) < 0.001

    def test_with_race_results(self):
        """race_resultsを含むサマリーを作成できる"""
        race1 = make_tansho_race_result(
            race_id="202501050101",
            hit=True,
            payout=500,
        )
        race2 = make_tansho_race_result(
            race_id="202501050102",
            hit=False,
            payout=0,
        )
        summary = make_tansho_summary(
            total_races=2,
            race_results=(race1, race2),
        )
        assert len(summary.race_results) == 2
        assert summary.race_results[0].race_id == "202501050101"
        assert summary.race_results[1].race_id == "202501050102"


# === TanshoSimulator クラスのテスト ===


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


class TestTanshoSimulator:
    """TanshoSimulatorクラスのテスト"""

    @pytest.fixture
    def simulator(self, tmp_path):
        """テスト用シミュレータを作成"""
        db_path = str(tmp_path / "test.db")
        # BaseSimulatorの__init__でRaceDetailScraperが作成されるため、
        # 事前にモック化する
        with patch("keiba.backtest.base_simulator.RaceDetailScraper") as mock_scraper_cls:
            mock_scraper = MagicMock()
            mock_scraper_cls.return_value = mock_scraper
            simulator = TanshoSimulator(db_path)
            # テスト内でモックスクレイパーを上書きできるように保持
            simulator._scraper = mock_scraper
        return simulator

    def test_init_with_db_path(self, tmp_path):
        """DBパスを指定してシミュレータを初期化できる"""
        db_path = str(tmp_path / "test.db")
        simulator = TanshoSimulator(db_path)
        assert simulator is not None

    def test_simulate_race_hit(self, simulator):
        """予測馬が1着になった場合（的中）"""
        mock_race = _make_mock_race(race_id="202501050101")
        mock_race.race_number = 1
        mock_race.distance = 1200
        mock_race.surface = "芝"
        mock_results = [
            _make_mock_race_result(horse_number=1, popularity=1),
            _make_mock_race_result(horse_number=2, popularity=2),
            _make_mock_race_result(horse_number=3, popularity=3),
        ]
        # 単勝払戻: 馬番1が1着、払戻350円
        mock_tansho_payout = {"horse_number": 1, "payout": 350}

        with patch.object(simulator, "_get_session") as mock_session_factory:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.get.return_value = mock_race
            mock_session.execute.return_value.scalars.return_value.all.return_value = (
                mock_results
            )
            mock_session_factory.return_value = mock_session

            simulator._scraper.fetch_tansho_payout.return_value = mock_tansho_payout
            result = simulator.simulate_race("202501050101", top_n=3)

        assert isinstance(result, TanshoRaceResult)
        assert result.race_id == "202501050101"
        assert result.winning_horse == 1
        assert result.hit is True
        assert result.payout == 350
        assert result.investment == 300  # top_n=3 * 100円

    def test_simulate_race_no_hit(self, simulator):
        """予測馬が1着ではない場合（外れ）"""
        mock_race = _make_mock_race(race_id="202501050102")
        mock_race.race_number = 2
        mock_race.distance = 1600
        mock_race.surface = "ダート"
        mock_results = [
            _make_mock_race_result(horse_number=1, popularity=1),
            _make_mock_race_result(horse_number=2, popularity=2),
            _make_mock_race_result(horse_number=3, popularity=3),
        ]
        # 単勝払戻: 馬番5が1着（予測馬ではない）
        mock_tansho_payout = {"horse_number": 5, "payout": 800}

        with patch.object(simulator, "_get_session") as mock_session_factory:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.get.return_value = mock_race
            mock_session.execute.return_value.scalars.return_value.all.return_value = (
                mock_results
            )
            mock_session_factory.return_value = mock_session

            simulator._scraper.fetch_tansho_payout.return_value = mock_tansho_payout
            result = simulator.simulate_race("202501050102", top_n=3)

        assert isinstance(result, TanshoRaceResult)
        assert result.winning_horse == 5
        assert result.hit is False
        assert result.payout == 0
        assert result.investment == 300

    def test_simulate_race_no_tansho_data(self, simulator):
        """単勝払戻データがない場合"""
        mock_race = _make_mock_race(race_id="202501050103")
        mock_race.race_number = 3
        mock_race.distance = 1800
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

            simulator._scraper.fetch_tansho_payout.return_value = None
            result = simulator.simulate_race("202501050103", top_n=3)

        assert isinstance(result, TanshoRaceResult)
        assert result.winning_horse is None
        assert result.hit is False
        assert result.payout == 0
        assert result.investment == 300

    def test_simulate_race_with_different_top_n(self, simulator):
        """top_n=5で5頭に賭けるケース"""
        mock_race = _make_mock_race(race_id="202501050101")
        mock_race.race_number = 1
        mock_race.distance = 1200
        mock_race.surface = "芝"
        mock_results = [
            _make_mock_race_result(horse_number=i, popularity=i) for i in range(1, 6)
        ]
        mock_tansho_payout = {"horse_number": 3, "payout": 500}

        with patch.object(simulator, "_get_session") as mock_session_factory:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.get.return_value = mock_race
            mock_session.execute.return_value.scalars.return_value.all.return_value = (
                mock_results
            )
            mock_session_factory.return_value = mock_session

            simulator._scraper.fetch_tansho_payout.return_value = mock_tansho_payout
            result = simulator.simulate_race("202501050101", top_n=5)

        assert isinstance(result, TanshoRaceResult)
        assert len(result.top_n_predictions) == 5
        assert result.investment == 500  # top_n=5 * 100円
        assert result.hit is True  # 馬番3は予測Top5に含まれる
        assert result.payout == 500

    def test_simulate_race_not_found(self, simulator):
        """レースが見つからない場合"""
        with patch.object(simulator, "_get_session") as mock_session_factory:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.get.return_value = None
            mock_session_factory.return_value = mock_session

            with pytest.raises(ValueError, match="Race not found"):
                simulator.simulate_race("nonexistent", top_n=3)

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
        # レース1: 馬番1が1着（的中）
        # レース2: 馬番5が1着（外れ）
        mock_tansho_payouts = [
            {"horse_number": 1, "payout": 350},
            {"horse_number": 5, "payout": 800},
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

            simulator._scraper.fetch_tansho_payout.side_effect = mock_tansho_payouts
            summary = simulator.simulate_period(
                from_date="2025-01-01",
                to_date="2025-01-31",
                venues=None,
                top_n=3,
            )

        assert isinstance(summary, TanshoSummary)
        assert summary.period_from == "2025-01-01"
        assert summary.period_to == "2025-01-31"
        assert summary.total_races == 2
        assert summary.total_bets == 6  # 2 races * 3 bets
        assert summary.total_hits == 1  # 1レースのみ的中
        assert summary.total_investment == 600  # 300 * 2
        assert summary.total_payout == 350  # 1レース的中分

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
        mock_tansho_payout = {"horse_number": 1, "payout": 350}

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

            simulator._scraper.fetch_tansho_payout.return_value = mock_tansho_payout
            summary = simulator.simulate_period(
                from_date="2025-01-01",
                to_date="2025-01-31",
                venues=["中山", "京都"],
                top_n=3,
            )

        assert isinstance(summary, TanshoSummary)
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
                top_n=3,
            )

        assert isinstance(summary, TanshoSummary)
        assert summary.total_races == 0
        assert summary.total_bets == 0
        assert summary.total_hits == 0
        assert summary.hit_rate == 0.0
        assert summary.return_rate == 0.0


# === エッジケースのテスト ===


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_tansho_race_result_with_empty_predictions(self):
        """空の予測を持つTanshoRaceResult"""
        result = TanshoRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            top_n_predictions=(),
            winning_horse=1,
            hit=False,
            payout=0,
            investment=0,
        )
        assert result.top_n_predictions == ()
        assert result.investment == 0

    def test_tansho_summary_with_zero_values(self):
        """ゼロ値を持つTanshoSummary"""
        summary = TanshoSummary(
            period_from="2025-01-01",
            period_to="2025-01-31",
            total_races=0,
            total_bets=0,
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

    def test_tansho_race_result_high_payout(self):
        """高額払戻のケース"""
        # 大穴的中: 15,000円以上の払戻
        result = TanshoRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            top_n_predictions=(12,),
            winning_horse=12,
            hit=True,
            payout=15890,
            investment=100,
        )
        assert result.payout == 15890
        assert result.payout / result.investment == 158.9  # 回収率15890%


# === PredictionService統合テスト ===


class TestSimulateRaceWithPredictionService:
    """simulate_raceがPredictionServiceを使用するテスト

    simulate_raceは人気順ではなく、PredictionServiceの7ファクタースコア順で
    Top-N馬を選択することを確認する。
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
            simulator = TanshoSimulator(db_path)
            # テスト内でモックスクレイパーを上書きできるように保持
            simulator._scraper = mock_scraper
        return simulator

    def test_simulate_race_uses_prediction_service(self, simulator):
        """PredictionServiceが呼び出され、予測順でTop-Nが選択されることを確認

        予測順序が人気順と異なる場合、top_n_predictionsは予測順に基づく。
        モック予測: 馬番5（rank=1）, 馬番3（rank=2）, 馬番1（rank=3）
        人気順: 馬番1（人気1）, 馬番2（人気2）, 馬番3（人気3）
        期待: top_n_predictions = (5, 3, 1) （予測順）
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

        # 単勝対象: 馬番5が1着
        mock_tansho_payout = {"horse_number": 5, "payout": 1500}

        with patch.object(simulator, "_get_session") as mock_session_factory:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.get.return_value = mock_race
            mock_session.execute.return_value.scalars.return_value.all.return_value = (
                mock_results
            )
            mock_session_factory.return_value = mock_session

            simulator._scraper.fetch_tansho_payout.return_value = mock_tansho_payout

            with patch(
                "keiba.backtest.tansho_simulator.PredictionService"
            ) as mock_prediction_service_cls:
                mock_prediction_service = MagicMock()
                mock_prediction_service.predict_from_shutuba.return_value = (
                    mock_predictions
                )
                mock_prediction_service_cls.return_value = mock_prediction_service

                result = simulator.simulate_race("202501050101", top_n=3)

        # 予測順（馬番5, 3, 1）になっていることを確認
        assert result.top_n_predictions == (5, 3, 1), (
            f"Expected prediction order (5, 3, 1), got {result.top_n_predictions}. "
            "simulate_race should use PredictionService, not popularity order."
        )

        # 人気順（馬番1, 2, 3）ではないことを確認
        assert result.top_n_predictions != (1, 2, 3), (
            "top_n_predictions should NOT be in popularity order."
        )

        # 馬番5が1着で的中
        assert result.winning_horse == 5
        assert result.hit is True
        assert result.payout == 1500

    def test_simulate_race_prediction_order_affects_result(self, simulator):
        """予測順序が異なると結果も異なることを確認

        同じレースでも予測順序が変われば、top_n_predictionsと的中結果が変わる。
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

        # 単勝: 馬番1が1着
        # 予測Top3（4, 5, 2）には馬番1が含まれないため外れ
        mock_tansho_payout = {"horse_number": 1, "payout": 130}

        with patch.object(simulator, "_get_session") as mock_session_factory:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.get.return_value = mock_race
            mock_session.execute.return_value.scalars.return_value.all.return_value = (
                mock_results
            )
            mock_session_factory.return_value = mock_session

            simulator._scraper.fetch_tansho_payout.return_value = mock_tansho_payout

            with patch(
                "keiba.backtest.tansho_simulator.PredictionService"
            ) as mock_prediction_service_cls:
                mock_prediction_service = MagicMock()
                mock_prediction_service.predict_from_shutuba.return_value = (
                    mock_predictions
                )
                mock_prediction_service_cls.return_value = mock_prediction_service

                result = simulator.simulate_race("202501050102", top_n=3)

        # 予測順（馬番4, 5, 2）になっていることを確認
        assert result.top_n_predictions == (4, 5, 2), (
            f"Expected (4, 5, 2), got {result.top_n_predictions}"
        )

        # 馬番1が1着だが、予測Top3には含まれないため外れ
        assert result.winning_horse == 1
        assert result.hit is False
        assert result.payout == 0

        # 人気順（1, 2, 3）だった場合は的中していたはず
        # これは予測順が結果に影響することを示す
