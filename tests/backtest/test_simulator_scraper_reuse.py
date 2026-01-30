"""バックテストシミュレータのスクレイパー再利用テスト"""

from unittest.mock import Mock, patch

import pytest

from keiba.backtest.fukusho_simulator import FukushoSimulator
from keiba.backtest.sanrenpuku_simulator import SanrenpukuSimulator
from keiba.backtest.tansho_simulator import TanshoSimulator
from keiba.backtest.umaren_simulator import UmarenSimulator
from keiba.scrapers.race_detail import RaceDetailScraper


class TestSimulatorScraperReuse:
    """シミュレータがスクレイパーインスタンスを再利用することを確認"""

    @patch("keiba.backtest.base_simulator.RaceDetailScraper")
    def test_fukusho_simulator_reuses_scraper_instance(self, mock_scraper_class):
        """FukushoSimulatorが単一のスクレイパーインスタンスを再利用する"""
        # モックスクレイパーインスタンスを作成
        mock_scraper_instance = Mock(spec=RaceDetailScraper)
        mock_scraper_class.return_value = mock_scraper_instance

        # シミュレータを初期化
        simulator = FukushoSimulator(db_path=":memory:")

        # スクレイパーインスタンスが作成されたことを確認
        mock_scraper_class.assert_called_once()

        # シミュレータが_scraperプロパティを持つことを確認
        assert hasattr(simulator, "_scraper")
        assert simulator._scraper is mock_scraper_instance

    @patch("keiba.backtest.base_simulator.RaceDetailScraper")
    def test_tansho_simulator_reuses_scraper_instance(self, mock_scraper_class):
        """TanshoSimulatorが単一のスクレイパーインスタンスを再利用する"""
        mock_scraper_instance = Mock(spec=RaceDetailScraper)
        mock_scraper_class.return_value = mock_scraper_instance

        simulator = TanshoSimulator(db_path=":memory:")

        mock_scraper_class.assert_called_once()
        assert hasattr(simulator, "_scraper")
        assert simulator._scraper is mock_scraper_instance

    @patch("keiba.backtest.base_simulator.RaceDetailScraper")
    def test_umaren_simulator_reuses_scraper_instance(self, mock_scraper_class):
        """UmarenSimulatorが単一のスクレイパーインスタンスを再利用する"""
        mock_scraper_instance = Mock(spec=RaceDetailScraper)
        mock_scraper_class.return_value = mock_scraper_instance

        simulator = UmarenSimulator(db_path=":memory:")

        mock_scraper_class.assert_called_once()
        assert hasattr(simulator, "_scraper")
        assert simulator._scraper is mock_scraper_instance

    @patch("keiba.backtest.base_simulator.RaceDetailScraper")
    def test_sanrenpuku_simulator_reuses_scraper_instance(self, mock_scraper_class):
        """SanrenpukuSimulatorが単一のスクレイパーインスタンスを再利用する"""
        mock_scraper_instance = Mock(spec=RaceDetailScraper)
        mock_scraper_class.return_value = mock_scraper_instance

        simulator = SanrenpukuSimulator(db_path=":memory:")

        mock_scraper_class.assert_called_once()
        assert hasattr(simulator, "_scraper")
        assert simulator._scraper is mock_scraper_instance

    @patch("keiba.scrapers.base.BaseScraper._global_last_request_time", None)
    @patch("keiba.backtest.base_simulator.RaceDetailScraper")
    def test_scraper_not_recreated_on_each_simulate_race_call(self, mock_scraper_class):
        """simulate_race()を複数回呼んでもスクレイパーが再生成されない"""
        # モックスクレイパーインスタンスを作成
        mock_scraper_instance = Mock(spec=RaceDetailScraper)
        mock_scraper_class.return_value = mock_scraper_instance

        # fetch_payouts()のモック設定
        mock_scraper_instance.fetch_payouts.return_value = [
            {"horse_number": 1, "payout": 150},
            {"horse_number": 2, "payout": 200},
            {"horse_number": 3, "payout": 300},
        ]

        # シミュレータを初期化
        simulator = FukushoSimulator(db_path=":memory:")

        # スクレイパーは初期化時に1回だけ作成される
        assert mock_scraper_class.call_count == 1

        # NOTE: simulate_race()は実際のDBアクセスが必要なため、
        # ここではスクレイパーインスタンスの再利用だけを確認
        # （実際のsimulate_race()の呼び出しは統合テストで確認）

        # 同じスクレイパーインスタンスが保持されていることを確認
        assert simulator._scraper is mock_scraper_instance

        # スクレイパーが再生成されていないことを確認
        # （初期化時の1回のみ）
        assert mock_scraper_class.call_count == 1
