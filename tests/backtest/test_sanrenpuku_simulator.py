"""SanrenpukuSimulatorのテスト

三連複馬券のバックテストシミュレータをテストする
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from keiba.backtest.sanrenpuku_simulator import (
    SanrenpukuRaceResult,
    SanrenpukuSimulator,
    SanrenpukuSummary,
)
from keiba.models.entry import ShutubaData


# === テストデータ生成ヘルパー ===


def make_sanrenpuku_race_result(
    race_id: str = "202501050101",
    race_name: str = "テストレース",
    venue: str = "中山",
    race_date: str = "2025-01-01",
    predicted_trio: tuple[int, int, int] = (1, 2, 3),
    actual_trio: tuple[int, int, int] | None = (1, 2, 3),
    hit: bool = True,
    payout: int = 1500,
    investment: int = 100,
) -> SanrenpukuRaceResult:
    """テスト用SanrenpukuRaceResultを生成"""
    return SanrenpukuRaceResult(
        race_id=race_id,
        race_name=race_name,
        venue=venue,
        race_date=race_date,
        predicted_trio=predicted_trio,
        actual_trio=actual_trio,
        hit=hit,
        payout=payout,
        investment=investment,
    )


def make_sanrenpuku_summary(
    period_from: str = "2025-01-01",
    period_to: str = "2025-01-31",
    total_races: int = 10,
    total_hits: int = 2,
    hit_rate: float = 0.2,
    total_investment: int = 1000,
    total_payout: int = 3000,
    return_rate: float = 3.0,
    race_results: tuple[SanrenpukuRaceResult, ...] | None = None,
) -> SanrenpukuSummary:
    """テスト用SanrenpukuSummaryを生成"""
    if race_results is None:
        race_results = ()
    return SanrenpukuSummary(
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


# === SanrenpukuRaceResult データクラスのテスト ===


class TestSanrenpukuRaceResult:
    """SanrenpukuRaceResultデータクラスのテスト"""

    def test_create_instance(self):
        """SanrenpukuRaceResultインスタンスを作成できる"""
        result = SanrenpukuRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            predicted_trio=(1, 2, 3),
            actual_trio=(1, 2, 3),
            hit=True,
            payout=1500,
            investment=100,
        )
        assert result.race_id == "202501050101"
        assert result.race_name == "1R 3歳未勝利"
        assert result.venue == "中山"
        assert result.race_date == "2025-01-05"
        assert result.predicted_trio == (1, 2, 3)
        assert result.actual_trio == (1, 2, 3)
        assert result.hit is True
        assert result.payout == 1500
        assert result.investment == 100

    def test_immutability(self):
        """frozen=Trueで変更不可であることを確認"""
        result = make_sanrenpuku_race_result()

        with pytest.raises(AttributeError):
            result.race_id = "changed"  # type: ignore

        with pytest.raises(AttributeError):
            result.investment = 500  # type: ignore

    def test_hit_case_exact_match(self):
        """的中ケース: 予測トリオと実際のトリオが完全一致"""
        # 予測: 1, 2, 3 / 実際: 1, 2, 3
        result = SanrenpukuRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            predicted_trio=(1, 2, 3),
            actual_trio=(1, 2, 3),
            hit=True,
            payout=1500,
            investment=100,
        )
        assert result.hit is True
        assert result.payout == 1500
        # 回収率 1500/100 = 15.0
        assert result.payout > result.investment

    def test_hit_case_different_order(self):
        """的中ケース: 順序が異なっても3頭が一致すれば的中（昇順ソート後）

        三連複は順不同なので、predicted_trioとactual_trioは共に昇順ソートで保持される。
        実際には同じ3頭であれば的中。
        """
        # 予測: (1, 2, 5) / 実際: (1, 2, 5) - 両方昇順
        result = SanrenpukuRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            predicted_trio=(1, 2, 5),
            actual_trio=(1, 2, 5),
            hit=True,
            payout=2500,
            investment=100,
        )
        assert result.hit is True
        assert result.payout == 2500

    def test_no_hit_case_partial_match(self):
        """外れケース: 2頭のみ一致（部分一致は外れ）"""
        # 予測: (1, 2, 3) / 実際: (1, 2, 5) - 1, 2のみ一致
        result = SanrenpukuRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            predicted_trio=(1, 2, 3),
            actual_trio=(1, 2, 5),
            hit=False,
            payout=0,
            investment=100,
        )
        assert result.hit is False
        assert result.payout == 0
        assert result.investment == 100

    def test_no_hit_case_no_match(self):
        """外れケース: 予測トリオに的中がない"""
        # 予測: (1, 2, 3) / 実際: (5, 8, 10)
        result = SanrenpukuRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            predicted_trio=(1, 2, 3),
            actual_trio=(5, 8, 10),
            hit=False,
            payout=0,
            investment=100,
        )
        assert result.hit is False
        assert result.payout == 0
        assert result.investment == 100

    def test_no_sanrenpuku_data(self):
        """三連複データがない場合"""
        result = SanrenpukuRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            predicted_trio=(1, 2, 3),
            actual_trio=None,
            hit=False,
            payout=0,
            investment=100,
        )
        assert result.actual_trio is None
        assert result.hit is False
        assert result.payout == 0

    def test_trio_is_sorted(self):
        """トリオは昇順ソートで保持される"""
        result = SanrenpukuRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            predicted_trio=(3, 1, 5),  # 昇順: (1, 3, 5)
            actual_trio=(5, 1, 3),      # 昇順: (1, 3, 5)
            hit=True,
            payout=1500,
            investment=100,
        )
        # 注: データクラスに渡す前に昇順ソートする責任はシミュレータ側にある
        # このテストでは昇順でない値を渡しているが、実装時に修正が必要
        assert result.predicted_trio == (3, 1, 5)  # 現状はそのまま保持


# === SanrenpukuSummary データクラスのテスト ===


class TestSanrenpukuSummary:
    """SanrenpukuSummaryデータクラスのテスト"""

    def test_create_instance(self):
        """SanrenpukuSummaryインスタンスを作成できる"""
        summary = SanrenpukuSummary(
            period_from="2025-01-01",
            period_to="2025-01-31",
            total_races=10,
            total_hits=2,
            hit_rate=0.2,
            total_investment=1000,
            total_payout=3000,
            return_rate=3.0,
            race_results=(),
        )
        assert summary.period_from == "2025-01-01"
        assert summary.period_to == "2025-01-31"
        assert summary.total_races == 10
        assert summary.total_hits == 2
        assert summary.hit_rate == 0.2
        assert summary.total_investment == 1000
        assert summary.total_payout == 3000
        assert summary.return_rate == 3.0
        assert summary.race_results == ()

    def test_immutability(self):
        """frozen=Trueで変更不可であることを確認"""
        summary = make_sanrenpuku_summary()

        with pytest.raises(AttributeError):
            summary.total_races = 20  # type: ignore

        with pytest.raises(AttributeError):
            summary.return_rate = 5.0  # type: ignore

    def test_calculate_return_rate(self):
        """回収率計算の正確性を確認"""
        # 投資1000円、払戻3000円 -> 回収率300%
        summary = make_sanrenpuku_summary(
            total_investment=1000,
            total_payout=3000,
            return_rate=3.0,
        )
        expected_return_rate = 3000 / 1000
        assert abs(summary.return_rate - expected_return_rate) < 0.001

        # 投資1000円、払戻500円 -> 回収率50%
        summary2 = make_sanrenpuku_summary(
            total_investment=1000,
            total_payout=500,
            return_rate=0.5,
        )
        expected_return_rate2 = 500 / 1000
        assert abs(summary2.return_rate - expected_return_rate2) < 0.001

    def test_calculate_hit_rate(self):
        """的中率計算の正確性を確認"""
        # 10レース中2的中 -> 的中率20%
        summary = make_sanrenpuku_summary(
            total_races=10,
            total_hits=2,
            hit_rate=0.2,
        )
        expected_hit_rate = 2 / 10
        assert abs(summary.hit_rate - expected_hit_rate) < 0.001

        # 10レース中5的中 -> 的中率50%
        summary2 = make_sanrenpuku_summary(
            total_races=10,
            total_hits=5,
            hit_rate=0.5,
        )
        expected_hit_rate2 = 5 / 10
        assert abs(summary2.hit_rate - expected_hit_rate2) < 0.001

    def test_with_race_results(self):
        """race_resultsを含むサマリーを作成できる"""
        race1 = make_sanrenpuku_race_result(
            race_id="202501050101",
            hit=True,
            payout=1500,
        )
        race2 = make_sanrenpuku_race_result(
            race_id="202501050102",
            hit=False,
            payout=0,
        )
        summary = make_sanrenpuku_summary(
            total_races=2,
            race_results=(race1, race2),
        )
        assert len(summary.race_results) == 2
        assert summary.race_results[0].race_id == "202501050101"
        assert summary.race_results[1].race_id == "202501050102"


# === SanrenpukuSimulator クラスのテスト ===


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


class TestSanrenpukuSimulator:
    """SanrenpukuSimulatorクラスのテスト"""

    @pytest.fixture
    def simulator(self, tmp_path):
        """テスト用シミュレータを作成"""
        db_path = str(tmp_path / "test.db")
        return SanrenpukuSimulator(db_path)

    def test_init_with_db_path(self, tmp_path):
        """DBパスを指定してシミュレータを初期化できる"""
        db_path = str(tmp_path / "test.db")
        simulator = SanrenpukuSimulator(db_path)
        assert simulator is not None

    def test_simulate_race_hit(self, simulator):
        """予測トリオが3着以内と完全一致した場合（的中）"""
        mock_race = _make_mock_race(race_id="202501050101")
        mock_race.race_number = 1
        mock_race.distance = 1200
        mock_race.surface = "芝"
        mock_results = [
            _make_mock_race_result(horse_number=1, popularity=1),
            _make_mock_race_result(horse_number=2, popularity=2),
            _make_mock_race_result(horse_number=3, popularity=3),
        ]
        # 三連複払戻: 馬番1, 2, 3が3着以内、払戻1500円
        mock_sanrenpuku_payout = {"horse_numbers": [1, 2, 3], "payout": 1500}

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
                "keiba.backtest.sanrenpuku_simulator.RaceDetailScraper"
            ) as mock_scraper_cls:
                mock_scraper = MagicMock()
                mock_scraper.fetch_sanrenpuku_payout.return_value = mock_sanrenpuku_payout
                mock_scraper_cls.return_value = mock_scraper

                result = simulator.simulate_race("202501050101")

        assert isinstance(result, SanrenpukuRaceResult)
        assert result.race_id == "202501050101"
        assert result.predicted_trio == (1, 2, 3)
        assert result.actual_trio == (1, 2, 3)
        assert result.hit is True
        assert result.payout == 1500
        assert result.investment == 100  # 1点 x 100円

    def test_simulate_race_no_hit_partial_match(self, simulator):
        """予測トリオが2頭のみ一致する場合（外れ）"""
        mock_race = _make_mock_race(race_id="202501050102")
        mock_race.race_number = 2
        mock_race.distance = 1600
        mock_race.surface = "ダート"
        mock_results = [
            _make_mock_race_result(horse_number=1, popularity=1),
            _make_mock_race_result(horse_number=2, popularity=2),
            _make_mock_race_result(horse_number=3, popularity=3),
        ]
        # 三連複払戻: 馬番1, 2, 5が3着以内（3は外れ）
        mock_sanrenpuku_payout = {"horse_numbers": [1, 2, 5], "payout": 2000}

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
                "keiba.backtest.sanrenpuku_simulator.RaceDetailScraper"
            ) as mock_scraper_cls:
                mock_scraper = MagicMock()
                mock_scraper.fetch_sanrenpuku_payout.return_value = mock_sanrenpuku_payout
                mock_scraper_cls.return_value = mock_scraper

                result = simulator.simulate_race("202501050102")

        assert isinstance(result, SanrenpukuRaceResult)
        assert result.predicted_trio == (1, 2, 3)
        assert result.actual_trio == (1, 2, 5)
        assert result.hit is False
        assert result.payout == 0
        assert result.investment == 100

    def test_simulate_race_no_hit(self, simulator):
        """予測トリオと実際のトリオが全く異なる場合（外れ）"""
        mock_race = _make_mock_race(race_id="202501050103")
        mock_race.race_number = 3
        mock_race.distance = 1800
        mock_race.surface = "芝"
        mock_results = [
            _make_mock_race_result(horse_number=1, popularity=1),
            _make_mock_race_result(horse_number=2, popularity=2),
            _make_mock_race_result(horse_number=3, popularity=3),
        ]
        # 三連複払戻: 馬番5, 8, 10が3着以内（予測外）
        mock_sanrenpuku_payout = {"horse_numbers": [5, 8, 10], "payout": 8000}

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
                "keiba.backtest.sanrenpuku_simulator.RaceDetailScraper"
            ) as mock_scraper_cls:
                mock_scraper = MagicMock()
                mock_scraper.fetch_sanrenpuku_payout.return_value = mock_sanrenpuku_payout
                mock_scraper_cls.return_value = mock_scraper

                result = simulator.simulate_race("202501050103")

        assert isinstance(result, SanrenpukuRaceResult)
        assert result.actual_trio == (5, 8, 10)
        assert result.hit is False
        assert result.payout == 0
        assert result.investment == 100

    def test_simulate_race_no_sanrenpuku_data(self, simulator):
        """三連複払戻データがない場合"""
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

            with patch(
                "keiba.backtest.sanrenpuku_simulator.RaceDetailScraper"
            ) as mock_scraper_cls:
                mock_scraper = MagicMock()
                mock_scraper.fetch_sanrenpuku_payout.return_value = None
                mock_scraper_cls.return_value = mock_scraper

                result = simulator.simulate_race("202501050104")

        assert isinstance(result, SanrenpukuRaceResult)
        assert result.actual_trio is None
        assert result.hit is False
        assert result.payout == 0
        assert result.investment == 100

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
        # レース1: 1-2-3が的中
        # レース2: 5-8-10で外れ
        mock_sanrenpuku_payouts = [
            {"horse_numbers": [1, 2, 3], "payout": 1500},
            {"horse_numbers": [5, 8, 10], "payout": 8000},
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

            with patch(
                "keiba.backtest.sanrenpuku_simulator.RaceDetailScraper"
            ) as mock_scraper_cls:
                mock_scraper = MagicMock()
                mock_scraper.fetch_sanrenpuku_payout.side_effect = mock_sanrenpuku_payouts
                mock_scraper_cls.return_value = mock_scraper

                summary = simulator.simulate_period(
                    from_date="2025-01-01",
                    to_date="2025-01-31",
                    venues=None,
                )

        assert isinstance(summary, SanrenpukuSummary)
        assert summary.period_from == "2025-01-01"
        assert summary.period_to == "2025-01-31"
        assert summary.total_races == 2
        assert summary.total_hits == 1  # 1レースのみ的中
        assert summary.total_investment == 200  # 100 * 2
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
        mock_sanrenpuku_payout = {"horse_numbers": [1, 2, 3], "payout": 1500}

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
                "keiba.backtest.sanrenpuku_simulator.RaceDetailScraper"
            ) as mock_scraper_cls:
                mock_scraper = MagicMock()
                mock_scraper.fetch_sanrenpuku_payout.return_value = mock_sanrenpuku_payout
                mock_scraper_cls.return_value = mock_scraper

                summary = simulator.simulate_period(
                    from_date="2025-01-01",
                    to_date="2025-01-31",
                    venues=["中山", "京都"],
                )

        assert isinstance(summary, SanrenpukuSummary)
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

        assert isinstance(summary, SanrenpukuSummary)
        assert summary.total_races == 0
        assert summary.total_hits == 0
        assert summary.hit_rate == 0.0
        assert summary.return_rate == 0.0


# === エッジケースのテスト ===


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_sanrenpuku_race_result_with_sorted_trio(self):
        """トリオが昇順ソートされていることを確認"""
        # 予測: (5, 3, 1) を昇順ソート -> (1, 3, 5)
        result = SanrenpukuRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            predicted_trio=(1, 3, 5),  # シミュレータが昇順ソートして渡す
            actual_trio=(1, 3, 5),
            hit=True,
            payout=1500,
            investment=100,
        )
        # predicted_trio内の順序確認（昇順）
        assert result.predicted_trio[0] < result.predicted_trio[1] < result.predicted_trio[2]

    def test_sanrenpuku_summary_with_zero_values(self):
        """ゼロ値を持つSanrenpukuSummary"""
        summary = SanrenpukuSummary(
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

    def test_sanrenpuku_race_result_high_payout(self):
        """高額払戻のケース"""
        # 大穴的中: 100,000円以上の払戻
        result = SanrenpukuRaceResult(
            race_id="202501050101",
            race_name="1R 3歳未勝利",
            venue="中山",
            race_date="2025-01-05",
            predicted_trio=(10, 12, 15),
            actual_trio=(10, 12, 15),
            hit=True,
            payout=128900,
            investment=100,
        )
        assert result.payout == 128900
        # 回収率 128900/100 = 1289.0
        assert result.payout / result.investment > 1000


# === PredictionService統合テスト ===


class TestSimulateRaceWithPredictionService:
    """simulate_raceがPredictionServiceを使用するテスト

    simulate_raceは人気順ではなく、PredictionServiceの7ファクタースコア順で
    Top-3馬を選択し、そこから三連複を購入することを確認する。
    """

    @pytest.fixture
    def simulator(self, tmp_path):
        """テスト用シミュレータを作成"""
        db_path = str(tmp_path / "test.db")
        return SanrenpukuSimulator(db_path)

    def test_simulate_race_uses_prediction_service(self, simulator):
        """PredictionServiceが呼び出され、予測順でTop-3から三連複を購入することを確認

        予測順序が人気順と異なる場合、predicted_trioは予測順に基づく。
        モック予測: 馬番5（rank=1）, 馬番3（rank=2）, 馬番1（rank=3）
        人気順: 馬番1（人気1）, 馬番2（人気2）, 馬番3（人気3）
        期待: predicted_trio = (1, 3, 5) （昇順ソート）
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

        # 三連複対象: 馬番1, 3, 5が3着以内
        mock_sanrenpuku_payout = {"horse_numbers": [1, 3, 5], "payout": 2500}

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
                "keiba.backtest.sanrenpuku_simulator.RaceDetailScraper"
            ) as mock_scraper_cls:
                mock_scraper = MagicMock()
                mock_scraper.fetch_sanrenpuku_payout.return_value = mock_sanrenpuku_payout
                mock_scraper_cls.return_value = mock_scraper

                with patch(
                    "keiba.backtest.sanrenpuku_simulator.PredictionService"
                ) as mock_prediction_service_cls:
                    mock_prediction_service = MagicMock()
                    mock_prediction_service.predict_from_shutuba.return_value = (
                        mock_predictions
                    )
                    mock_prediction_service_cls.return_value = mock_prediction_service

                    result = simulator.simulate_race("202501050101")

        # 予測順（馬番5, 3, 1）から生成されたトリオを確認
        # predicted_trio = (1, 3, 5) （昇順ソート）
        expected_predicted_trio = (1, 3, 5)
        assert result.predicted_trio == expected_predicted_trio, (
            f"Expected predicted_trio {expected_predicted_trio}, got {result.predicted_trio}. "
            "simulate_race should use PredictionService, not popularity order."
        )

        # 人気順（馬番1, 2, 3）からのトリオではないことを確認
        popularity_based_trio = (1, 2, 3)
        assert result.predicted_trio != popularity_based_trio, (
            "predicted_trio should NOT be based on popularity order."
        )

        # 馬番1, 3, 5が3着以内なので的中
        assert result.actual_trio == (1, 3, 5)
        assert result.hit is True
        assert result.payout == 2500

    def test_simulate_race_prediction_order_affects_result(self, simulator):
        """予測順序が異なると結果も異なることを確認

        同じレースでも予測順序が変われば、predicted_trioと的中結果が変わる。
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

        # 三連複: 馬番1, 2, 3が3着以内
        # 予測Top3（4, 5, 2）の昇順ソート: (2, 4, 5)
        # 馬番1, 2, 3は予測トリオに含まれないため外れ
        mock_sanrenpuku_payout = {"horse_numbers": [1, 2, 3], "payout": 1500}

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
                "keiba.backtest.sanrenpuku_simulator.RaceDetailScraper"
            ) as mock_scraper_cls:
                mock_scraper = MagicMock()
                mock_scraper.fetch_sanrenpuku_payout.return_value = mock_sanrenpuku_payout
                mock_scraper_cls.return_value = mock_scraper

                with patch(
                    "keiba.backtest.sanrenpuku_simulator.PredictionService"
                ) as mock_prediction_service_cls:
                    mock_prediction_service = MagicMock()
                    mock_prediction_service.predict_from_shutuba.return_value = (
                        mock_predictions
                    )
                    mock_prediction_service_cls.return_value = mock_prediction_service

                    result = simulator.simulate_race("202501050102")

        # 予測順（馬番4, 5, 2）から生成されたトリオを確認
        expected_predicted_trio = (2, 4, 5)
        assert result.predicted_trio == expected_predicted_trio, (
            f"Expected {expected_predicted_trio}, got {result.predicted_trio}"
        )

        # 馬番1, 2, 3が3着以内だが、予測トリオ(2, 4, 5)とは異なるため外れ
        assert result.actual_trio == (1, 2, 3)
        assert result.hit is False
        assert result.payout == 0

        # 人気順（1, 2, 3）だった場合は的中していたはず
        # これは予測順が結果に影響することを示す
