"""FukushoSimulatorのテスト

複勝馬券のバックテストシミュレータをテストする
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from keiba.backtest.fukusho_simulator import (
    FukushoRaceResult,
    FukushoSimulator,
    FukushoSummary,
)
from keiba.models.entry import ShutubaData


# === テストデータ生成ヘルパー ===


def make_fukusho_race_result(
    race_id: str = "202501050101",
    race_name: str = "テストレース",
    venue: str = "中山",
    race_date: str = "2025-01-01",
    top_n_predictions: tuple[int, ...] = (1, 2, 3),
    fukusho_horses: tuple[int, ...] = (1, 5, 8),
    hits: tuple[int, ...] = (1,),
    payouts: tuple[int, ...] = (150,),
    investment: int = 300,
    payout_total: int = 150,
) -> FukushoRaceResult:
    """テスト用FukushoRaceResultを生成"""
    return FukushoRaceResult(
        race_id=race_id,
        race_name=race_name,
        venue=venue,
        race_date=race_date,
        top_n_predictions=top_n_predictions,
        fukusho_horses=fukusho_horses,
        hits=hits,
        payouts=payouts,
        investment=investment,
        payout_total=payout_total,
    )


def make_fukusho_summary(
    period_from: str = "2025-01-01",
    period_to: str = "2025-01-31",
    total_races: int = 10,
    total_bets: int = 30,
    total_hits: int = 15,
    hit_rate: float = 0.5,
    total_investment: int = 3000,
    total_payout: int = 2400,
    return_rate: float = 0.8,
    race_results: tuple[FukushoRaceResult, ...] | None = None,
) -> FukushoSummary:
    """テスト用FukushoSummaryを生成"""
    if race_results is None:
        race_results = ()
    return FukushoSummary(
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


# === FukushoRaceResult データクラスのテスト ===


class TestFukushoRaceResult:
    """FukushoRaceResultデータクラスのテスト"""

    def test_create_instance(self):
        """FukushoRaceResultインスタンスを作成できる"""
        result = FukushoRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            top_n_predictions=(1, 2, 3),
            fukusho_horses=(1, 5, 8),
            hits=(1,),
            payouts=(150,),
            investment=300,
            payout_total=150,
        )
        assert result.race_id == "202501050101"
        assert result.race_name == "1R 3歳未勝利"
        assert result.venue == "中山"
        assert result.race_date == "2025-01-05"
        assert result.top_n_predictions == (1, 2, 3)
        assert result.fukusho_horses == (1, 5, 8)
        assert result.hits == (1,)
        assert result.payouts == (150,)
        assert result.investment == 300
        assert result.payout_total == 150

    def test_immutability(self):
        """frozen=Trueで変更不可であることを確認"""
        result = make_fukusho_race_result()

        with pytest.raises(AttributeError):
            result.race_id = "changed"  # type: ignore

        with pytest.raises(AttributeError):
            result.investment = 500  # type: ignore

    def test_all_hit(self):
        """全的中ケース: 予測Top3が全て複勝対象"""
        # 予測: 1, 2, 3番 / 複勝対象: 1, 2, 3番（3着以内）
        result = FukushoRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            top_n_predictions=(1, 2, 3),
            fukusho_horses=(1, 2, 3),
            hits=(1, 2, 3),
            payouts=(150, 200, 180),
            investment=300,
            payout_total=530,
        )
        assert result.hits == (1, 2, 3)
        assert result.payouts == (150, 200, 180)
        assert result.investment == 300
        assert result.payout_total == 530
        # 回収率 530/300 = 約1.77
        assert result.payout_total > result.investment

    def test_partial_hit(self):
        """部分的中ケース: 予測Top3のうち1頭のみ的中"""
        # 予測: 1, 2, 3番 / 複勝対象: 1, 5, 8番
        result = FukushoRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            top_n_predictions=(1, 2, 3),
            fukusho_horses=(1, 5, 8),
            hits=(1,),
            payouts=(150,),
            investment=300,
            payout_total=150,
        )
        assert result.hits == (1,)
        assert len(result.hits) == 1
        assert result.payout_total == 150
        assert result.payout_total < result.investment

    def test_no_hit(self):
        """全外れケース: 予測Top3が全て外れ"""
        # 予測: 1, 2, 3番 / 複勝対象: 5, 8, 10番
        result = FukushoRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            top_n_predictions=(1, 2, 3),
            fukusho_horses=(5, 8, 10),
            hits=(),
            payouts=(),
            investment=300,
            payout_total=0,
        )
        assert result.hits == ()
        assert result.payouts == ()
        assert result.payout_total == 0


# === FukushoSummary データクラスのテスト ===


class TestFukushoSummary:
    """FukushoSummaryデータクラスのテスト"""

    def test_create_instance(self):
        """FukushoSummaryインスタンスを作成できる"""
        summary = FukushoSummary(
            period_from="2025-01-01",
            period_to="2025-01-31",
            total_races=10,
            total_bets=30,
            total_hits=15,
            hit_rate=0.5,
            total_investment=3000,
            total_payout=2400,
            return_rate=0.8,
            race_results=(),
        )
        assert summary.period_from == "2025-01-01"
        assert summary.period_to == "2025-01-31"
        assert summary.total_races == 10
        assert summary.total_bets == 30
        assert summary.total_hits == 15
        assert summary.hit_rate == 0.5
        assert summary.total_investment == 3000
        assert summary.total_payout == 2400
        assert summary.return_rate == 0.8
        assert summary.race_results == ()

    def test_immutability(self):
        """frozen=Trueで変更不可であることを確認"""
        summary = make_fukusho_summary()

        with pytest.raises(AttributeError):
            summary.total_races = 20  # type: ignore

        with pytest.raises(AttributeError):
            summary.return_rate = 1.5  # type: ignore

    def test_calculate_return_rate(self):
        """回収率計算の正確性を確認"""
        # 投資3000円、払戻2400円 -> 回収率80%
        summary = make_fukusho_summary(
            total_investment=3000,
            total_payout=2400,
            return_rate=0.8,
        )
        expected_return_rate = 2400 / 3000
        assert abs(summary.return_rate - expected_return_rate) < 0.001

        # 投資3000円、払戻4500円 -> 回収率150%
        summary2 = make_fukusho_summary(
            total_investment=3000,
            total_payout=4500,
            return_rate=1.5,
        )
        expected_return_rate2 = 4500 / 3000
        assert abs(summary2.return_rate - expected_return_rate2) < 0.001

    def test_calculate_hit_rate(self):
        """的中率計算の正確性を確認"""
        # 30ベット中15的中 -> 的中率50%
        summary = make_fukusho_summary(
            total_bets=30,
            total_hits=15,
            hit_rate=0.5,
        )
        expected_hit_rate = 15 / 30
        assert abs(summary.hit_rate - expected_hit_rate) < 0.001

        # 30ベット中24的中 -> 的中率80%
        summary2 = make_fukusho_summary(
            total_bets=30,
            total_hits=24,
            hit_rate=0.8,
        )
        expected_hit_rate2 = 24 / 30
        assert abs(summary2.hit_rate - expected_hit_rate2) < 0.001

    def test_with_race_results(self):
        """race_resultsを含むサマリーを作成できる"""
        race1 = make_fukusho_race_result(
            race_id="202501050101",
            hits=(1, 2),
            payouts=(150, 200),
            payout_total=350,
        )
        race2 = make_fukusho_race_result(
            race_id="202501050102",
            hits=(),
            payouts=(),
            payout_total=0,
        )
        summary = make_fukusho_summary(
            total_races=2,
            race_results=(race1, race2),
        )
        assert len(summary.race_results) == 2
        assert summary.race_results[0].race_id == "202501050101"
        assert summary.race_results[1].race_id == "202501050102"


# === FukushoSimulator クラスのテスト ===


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


class TestFukushoSimulator:
    """FukushoSimulatorクラスのテスト"""

    @pytest.fixture
    def simulator(self, tmp_path):
        """テスト用シミュレータを作成"""
        db_path = str(tmp_path / "test.db")
        return FukushoSimulator(db_path)

    def test_init_with_db_path(self, tmp_path):
        """DBパスを指定してシミュレータを初期化できる"""
        db_path = str(tmp_path / "test.db")
        simulator = FukushoSimulator(db_path)
        assert simulator is not None

    def test_simulate_race_all_hit(self, simulator):
        """予測Top3全て的中のケース"""
        # モック設定: 人気1,2,3番が馬番1,2,3で、複勝対象も1,2,3
        mock_race = _make_mock_race(race_id="202501050101")
        mock_results = [
            _make_mock_race_result(horse_number=1, popularity=1),
            _make_mock_race_result(horse_number=2, popularity=2),
            _make_mock_race_result(horse_number=3, popularity=3),
        ]
        mock_payouts = [
            {"horse_number": 1, "payout": 150},
            {"horse_number": 2, "payout": 200},
            {"horse_number": 3, "payout": 180},
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

            with patch(
                "keiba.backtest.fukusho_simulator.RaceDetailScraper"
            ) as mock_scraper_cls:
                mock_scraper = MagicMock()
                mock_scraper.fetch_payouts.return_value = mock_payouts
                mock_scraper_cls.return_value = mock_scraper

                result = simulator.simulate_race("202501050101", top_n=3)

        assert isinstance(result, FukushoRaceResult)
        assert result.race_id == "202501050101"
        assert len(result.hits) == 3
        assert result.investment == 300
        assert result.payout_total == 530  # 150+200+180

    def test_simulate_race_partial_hit(self, simulator):
        """予測Top3の一部的中のケース"""
        mock_race = _make_mock_race(race_id="202501050102")
        mock_results = [
            _make_mock_race_result(horse_number=1, popularity=1),
            _make_mock_race_result(horse_number=2, popularity=2),
            _make_mock_race_result(horse_number=3, popularity=3),
        ]
        # 複勝対象は1,5,8なので、予測1のみ的中
        mock_payouts = [
            {"horse_number": 1, "payout": 150},
            {"horse_number": 5, "payout": 300},
            {"horse_number": 8, "payout": 450},
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

            with patch(
                "keiba.backtest.fukusho_simulator.RaceDetailScraper"
            ) as mock_scraper_cls:
                mock_scraper = MagicMock()
                mock_scraper.fetch_payouts.return_value = mock_payouts
                mock_scraper_cls.return_value = mock_scraper

                result = simulator.simulate_race("202501050102", top_n=3)

        assert isinstance(result, FukushoRaceResult)
        assert result.investment == 300
        assert len(result.hits) == 1
        assert result.hits == (1,)
        assert result.payout_total == 150

    def test_simulate_race_no_hit(self, simulator):
        """予測Top3全て外れのケース"""
        mock_race = _make_mock_race(race_id="202501050103")
        mock_results = [
            _make_mock_race_result(horse_number=1, popularity=1),
            _make_mock_race_result(horse_number=2, popularity=2),
            _make_mock_race_result(horse_number=3, popularity=3),
        ]
        # 複勝対象は5,8,10なので、全て外れ
        mock_payouts = [
            {"horse_number": 5, "payout": 300},
            {"horse_number": 8, "payout": 450},
            {"horse_number": 10, "payout": 600},
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

            with patch(
                "keiba.backtest.fukusho_simulator.RaceDetailScraper"
            ) as mock_scraper_cls:
                mock_scraper = MagicMock()
                mock_scraper.fetch_payouts.return_value = mock_payouts
                mock_scraper_cls.return_value = mock_scraper

                result = simulator.simulate_race("202501050103", top_n=3)

        assert isinstance(result, FukushoRaceResult)
        assert result.hits == ()
        assert result.payouts == ()
        assert result.payout_total == 0
        assert result.investment == 300

    def test_simulate_race_with_different_top_n(self, simulator):
        """top_n=5で5頭に賭けるケース"""
        mock_race = _make_mock_race(race_id="202501050101")
        mock_results = [
            _make_mock_race_result(horse_number=i, popularity=i) for i in range(1, 6)
        ]
        mock_payouts = [
            {"horse_number": 1, "payout": 150},
            {"horse_number": 2, "payout": 200},
            {"horse_number": 3, "payout": 180},
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

            with patch(
                "keiba.backtest.fukusho_simulator.RaceDetailScraper"
            ) as mock_scraper_cls:
                mock_scraper = MagicMock()
                mock_scraper.fetch_payouts.return_value = mock_payouts
                mock_scraper_cls.return_value = mock_scraper

                result = simulator.simulate_race("202501050101", top_n=5)

        assert isinstance(result, FukushoRaceResult)
        assert len(result.top_n_predictions) == 5
        assert result.investment == 500

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
        mock_results = [
            _make_mock_race_result(horse_number=1, popularity=1),
            _make_mock_race_result(horse_number=2, popularity=2),
            _make_mock_race_result(horse_number=3, popularity=3),
        ]
        mock_payouts = [
            {"horse_number": 1, "payout": 150},
            {"horse_number": 2, "payout": 200},
            {"horse_number": 3, "payout": 180},
        ]

        with patch.object(simulator, "_get_session") as mock_session_factory:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            # 最初の呼び出しは期間内レース取得
            mock_session.execute.return_value.scalars.return_value.all.side_effect = [
                mock_races,  # _get_races_in_period
                mock_results,  # simulate_race for race 1
                mock_results,  # simulate_race for race 2
            ]
            mock_session.get.side_effect = [mock_races[0], mock_races[1]]
            mock_session_factory.return_value = mock_session

            with patch(
                "keiba.backtest.fukusho_simulator.RaceDetailScraper"
            ) as mock_scraper_cls:
                mock_scraper = MagicMock()
                mock_scraper.fetch_payouts.return_value = mock_payouts
                mock_scraper_cls.return_value = mock_scraper

                summary = simulator.simulate_period(
                    from_date="2025-01-01",
                    to_date="2025-01-31",
                    venues=None,
                    top_n=3,
                )

        assert isinstance(summary, FukushoSummary)
        assert summary.period_from == "2025-01-01"
        assert summary.period_to == "2025-01-31"
        assert summary.total_races == 2
        assert summary.total_bets == 6  # 2 races * 3 bets
        assert 0.0 <= summary.hit_rate <= 1.0
        assert summary.return_rate >= 0.0

    def test_simulate_period_with_venue_filter(self, simulator):
        """特定会場でフィルタリングした期間シミュレーション"""
        mock_races = [_make_mock_race(race_id="202501050101", course="中山")]
        mock_results = [
            _make_mock_race_result(horse_number=1, popularity=1),
            _make_mock_race_result(horse_number=2, popularity=2),
            _make_mock_race_result(horse_number=3, popularity=3),
        ]
        mock_payouts = [
            {"horse_number": 1, "payout": 150},
            {"horse_number": 2, "payout": 200},
            {"horse_number": 3, "payout": 180},
        ]

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

            with patch(
                "keiba.backtest.fukusho_simulator.RaceDetailScraper"
            ) as mock_scraper_cls:
                mock_scraper = MagicMock()
                mock_scraper.fetch_payouts.return_value = mock_payouts
                mock_scraper_cls.return_value = mock_scraper

                summary = simulator.simulate_period(
                    from_date="2025-01-01",
                    to_date="2025-01-31",
                    venues=["中山", "京都"],
                    top_n=3,
                )

        assert isinstance(summary, FukushoSummary)
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

        assert isinstance(summary, FukushoSummary)
        assert summary.total_races == 0
        assert summary.total_bets == 0
        assert summary.total_hits == 0
        assert summary.hit_rate == 0.0
        assert summary.return_rate == 0.0


# === エッジケースのテスト ===


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_fukusho_race_result_with_empty_tuples(self):
        """空のタプルを持つFukushoRaceResult"""
        result = FukushoRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            top_n_predictions=(),
            fukusho_horses=(),
            hits=(),
            payouts=(),
            investment=0,
            payout_total=0,
        )
        assert result.top_n_predictions == ()
        assert result.fukusho_horses == ()
        assert result.hits == ()
        assert result.payouts == ()

    def test_fukusho_summary_with_zero_values(self):
        """ゼロ値を持つFukushoSummary"""
        summary = FukushoSummary(
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

    def test_fukusho_race_result_high_payout(self):
        """高額払戻のケース"""
        # 大穴的中: 1頭で1000円以上の払戻
        result = FukushoRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            top_n_predictions=(12,),
            fukusho_horses=(12, 5, 8),
            hits=(12,),
            payouts=(1500,),
            investment=100,
            payout_total=1500,
        )
        assert result.payout_total == 1500
        assert result.payout_total / result.investment == 15.0  # 回収率1500%


# === _build_shutuba_from_race_results メソッドのテスト ===


class TestBuildShutubaFromRaceResults:
    """_build_shutuba_from_race_results メソッドのテスト

    RaceResultのリストからShutubaDataを構築するメソッドをテストする。
    """

    @pytest.fixture
    def simulator(self, tmp_path):
        """テスト用シミュレータを作成"""
        db_path = str(tmp_path / "test.db")
        return FukushoSimulator(db_path)

    def test_build_shutuba_from_race_results_success(self, simulator):
        """正常系: RaceResultからShutubaDataを正しく構築できる"""
        # モックRaceオブジェクトを作成
        mock_race = _make_mock_race(
            race_id="202501050101",
            name="1R 3歳未勝利",
            course="中山",
            race_date=date(2025, 1, 5),
        )
        mock_race.race_number = 1
        mock_race.distance = 1200
        mock_race.surface = "芝"

        # モックRaceResultオブジェクトを作成（3頭分）
        mock_results = [
            _make_mock_race_result(
                horse_number=1,
                popularity=2,
                horse_id="horse_001",
                horse_name="テスト馬A",
                jockey_id="jockey_001",
                jockey_name="騎手A",
                bracket_number=1,
                impost=55.0,
                sex="牡",
                age=3,
            ),
            _make_mock_race_result(
                horse_number=2,
                popularity=1,
                horse_id="horse_002",
                horse_name="テスト馬B",
                jockey_id="jockey_002",
                jockey_name="騎手B",
                bracket_number=1,
                impost=54.0,
                sex="牝",
                age=4,
            ),
            _make_mock_race_result(
                horse_number=3,
                popularity=3,
                horse_id="horse_003",
                horse_name="テスト馬C",
                jockey_id="jockey_003",
                jockey_name="騎手C",
                bracket_number=2,
                impost=57.0,
                sex="セ",
                age=5,
            ),
        ]

        # _build_shutuba_from_race_resultsを呼び出す
        shutuba = simulator._build_shutuba_from_race_results(mock_race, mock_results)

        # ShutubaDataの検証
        assert isinstance(shutuba, ShutubaData)
        assert shutuba.race_id == "202501050101"
        assert shutuba.race_name == "1R 3歳未勝利"
        assert shutuba.race_number == 1
        assert shutuba.course == "中山"
        assert shutuba.distance == 1200
        assert shutuba.surface == "芝"
        assert shutuba.date == "2025-01-05"

        # エントリーの検証
        assert len(shutuba.entries) == 3

        # 1頭目の検証
        entry1 = shutuba.entries[0]
        assert entry1.horse_id == "horse_001"
        assert entry1.horse_name == "テスト馬A"
        assert entry1.horse_number == 1
        assert entry1.bracket_number == 1
        assert entry1.jockey_id == "jockey_001"
        assert entry1.jockey_name == "騎手A"
        assert entry1.impost == 55.0
        assert entry1.sex == "牡"
        assert entry1.age == 3

        # 2頭目の検証
        entry2 = shutuba.entries[1]
        assert entry2.horse_id == "horse_002"
        assert entry2.horse_name == "テスト馬B"
        assert entry2.horse_number == 2
        assert entry2.bracket_number == 1
        assert entry2.jockey_id == "jockey_002"
        assert entry2.jockey_name == "騎手B"
        assert entry2.impost == 54.0
        assert entry2.sex == "牝"
        assert entry2.age == 4

        # 3頭目の検証
        entry3 = shutuba.entries[2]
        assert entry3.horse_id == "horse_003"
        assert entry3.horse_name == "テスト馬C"
        assert entry3.horse_number == 3
        assert entry3.bracket_number == 2
        assert entry3.jockey_id == "jockey_003"
        assert entry3.jockey_name == "騎手C"
        assert entry3.impost == 57.0
        assert entry3.sex == "セ"
        assert entry3.age == 5

    def test_build_shutuba_from_race_results_no_results(self, simulator):
        """異常系: RaceResultがない場合"""
        # モックRaceオブジェクトを作成
        mock_race = _make_mock_race(
            race_id="202501050102",
            name="2R 3歳未勝利",
            course="京都",
            race_date=date(2025, 1, 5),
        )
        mock_race.race_number = 2
        mock_race.distance = 1400
        mock_race.surface = "ダート"

        # 空のRaceResultリスト
        mock_results = []

        # _build_shutuba_from_race_resultsを呼び出す
        shutuba = simulator._build_shutuba_from_race_results(mock_race, mock_results)

        # ShutubaDataの検証（レース情報は設定されるが、entriesは空）
        assert isinstance(shutuba, ShutubaData)
        assert shutuba.race_id == "202501050102"
        assert shutuba.race_name == "2R 3歳未勝利"
        assert shutuba.race_number == 2
        assert shutuba.course == "京都"
        assert shutuba.distance == 1400
        assert shutuba.surface == "ダート"
        assert shutuba.date == "2025-01-05"
        assert shutuba.entries == ()


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
        return FukushoSimulator(db_path)

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
                rank=5,
            ),
        ]

        # 複勝対象: 馬番5, 3, 1が3着以内
        mock_payouts = [
            {"horse_number": 5, "payout": 450},
            {"horse_number": 3, "payout": 200},
            {"horse_number": 1, "payout": 130},
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

            with patch(
                "keiba.backtest.fukusho_simulator.RaceDetailScraper"
            ) as mock_scraper_cls:
                mock_scraper = MagicMock()
                mock_scraper.fetch_payouts.return_value = mock_payouts
                mock_scraper_cls.return_value = mock_scraper

                with patch(
                    "keiba.backtest.fukusho_simulator.PredictionService"
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

        # 全3頭的中
        assert result.hits == (5, 3, 1)
        assert result.payouts == (450, 200, 130)
        assert result.payout_total == 780

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
                rank=1,
            ),
            PredictionResult(
                horse_number=5,
                horse_name="テスト馬5",
                horse_id="horse_005",
                ml_probability=0.0,
                factor_scores={"past_results": 80.0},
                total_score=80.0,
                rank=2,
            ),
            PredictionResult(
                horse_number=2,
                horse_name="テスト馬2",
                horse_id="horse_002",
                ml_probability=0.0,
                factor_scores={"past_results": 75.0},
                total_score=75.0,
                rank=3,
            ),
            PredictionResult(
                horse_number=1,
                horse_name="テスト馬1",
                horse_id="horse_001",
                ml_probability=0.0,
                factor_scores={"past_results": 70.0},
                total_score=70.0,
                rank=4,
            ),
            PredictionResult(
                horse_number=3,
                horse_name="テスト馬3",
                horse_id="horse_003",
                ml_probability=0.0,
                factor_scores={"past_results": 65.0},
                total_score=65.0,
                rank=5,
            ),
        ]

        # 複勝対象: 馬番1, 3, 5が3着以内
        # 予測Top3（4, 5, 2）のうち、馬番5のみが複勝対象
        mock_payouts = [
            {"horse_number": 1, "payout": 130},
            {"horse_number": 3, "payout": 180},
            {"horse_number": 5, "payout": 350},
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

            with patch(
                "keiba.backtest.fukusho_simulator.RaceDetailScraper"
            ) as mock_scraper_cls:
                mock_scraper = MagicMock()
                mock_scraper.fetch_payouts.return_value = mock_payouts
                mock_scraper_cls.return_value = mock_scraper

                with patch(
                    "keiba.backtest.fukusho_simulator.PredictionService"
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

        # 馬番5のみが複勝対象なので、1頭だけ的中
        assert result.hits == (5,)
        assert result.payouts == (350,)
        assert result.payout_total == 350

        # 人気順（1, 2, 3）だった場合と比較
        # 人気順なら馬番1, 3が複勝対象で2頭的中だったはず
        # これは予測順が結果に影響することを示す
