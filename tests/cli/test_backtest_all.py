"""backtest-all コマンドのテスト

TDDアプローチ: このテストを先に書いてから実装する
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from keiba.cli import main


class TestResolveDateRange:
    """_resolve_date_range ヘルパー関数のテスト"""

    def test_last_week_flag_returns_last_week(self):
        """--last-week フラグが先週の月曜〜日曜を返す"""
        from keiba.cli.commands.backtest import _resolve_date_range

        # テスト実行時の日付から先週を計算
        today = date.today()
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        expected_from = (this_monday - timedelta(days=7)).strftime("%Y-%m-%d")
        expected_to = (this_monday - timedelta(days=1)).strftime("%Y-%m-%d")

        from_date, to_date = _resolve_date_range(None, None, last_week=True)

        assert from_date == expected_from
        assert to_date == expected_to

    def test_no_args_returns_last_week(self):
        """引数なしの場合も先週を返す"""
        from keiba.cli.commands.backtest import _resolve_date_range

        today = date.today()
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        expected_from = (this_monday - timedelta(days=7)).strftime("%Y-%m-%d")
        expected_to = (this_monday - timedelta(days=1)).strftime("%Y-%m-%d")

        from_date, to_date = _resolve_date_range(None, None, last_week=False)

        assert from_date == expected_from
        assert to_date == expected_to

    def test_explicit_dates_returned_as_is(self):
        """--from と --to を両方指定すると、その日付がそのまま返る"""
        from keiba.cli.commands.backtest import _resolve_date_range

        from_date, to_date = _resolve_date_range(
            "2026-01-01", "2026-01-31", last_week=False
        )

        assert from_date == "2026-01-01"
        assert to_date == "2026-01-31"

    def test_only_from_date_raises_system_exit(self):
        """--from のみ指定するとエラー"""
        from keiba.cli.commands.backtest import _resolve_date_range

        with pytest.raises(SystemExit):
            _resolve_date_range("2026-01-01", None, last_week=False)

    def test_only_to_date_raises_system_exit(self):
        """--to のみ指定するとエラー"""
        from keiba.cli.commands.backtest import _resolve_date_range

        with pytest.raises(SystemExit):
            _resolve_date_range(None, "2026-01-31", last_week=False)

    def test_invalid_date_format_raises_system_exit(self):
        """不正な日付形式はエラー"""
        from keiba.cli.commands.backtest import _resolve_date_range

        with pytest.raises(SystemExit):
            _resolve_date_range("01-01-2026", "2026-01-31", last_week=False)

    def test_invalid_to_date_format_raises_system_exit(self):
        """不正なto日付形式はエラー"""
        from keiba.cli.commands.backtest import _resolve_date_range

        with pytest.raises(SystemExit):
            _resolve_date_range("2026-01-01", "invalid", last_week=False)


class TestBacktestAllCommand:
    """backtest-all コマンドのテスト"""

    @pytest.fixture
    def runner(self):
        """Click テストランナー"""
        return CliRunner()

    @pytest.fixture
    def mock_simulators(self):
        """全シミュレータをモック"""
        with patch(
            "keiba.cli.commands.backtest.FukushoSimulator"
        ) as mock_fukusho, patch(
            "keiba.cli.commands.backtest.TanshoSimulator"
        ) as mock_tansho, patch(
            "keiba.cli.commands.backtest.UmarenSimulator"
        ) as mock_umaren, patch(
            "keiba.cli.commands.backtest.SanrenpukuSimulator"
        ) as mock_sanrenpuku:
            # Fukushoのモック
            fukusho_summary = MagicMock()
            fukusho_summary.total_races = 48
            fukusho_summary.total_bets = 144
            fukusho_summary.total_hits = 25
            fukusho_summary.hit_rate = 0.174
            fukusho_summary.total_investment = 14400
            fukusho_summary.total_payout = 18500
            fukusho_summary.return_rate = 1.285
            mock_fukusho.return_value.simulate_period.return_value = fukusho_summary

            # Tanshoのモック
            tansho_summary = MagicMock()
            tansho_summary.total_races = 48
            tansho_summary.total_bets = 144
            tansho_summary.total_hits = 12
            tansho_summary.hit_rate = 0.083
            tansho_summary.total_investment = 14400
            tansho_summary.total_payout = 15340
            tansho_summary.return_rate = 1.065
            mock_tansho.return_value.simulate_period.return_value = tansho_summary

            # Umarenのモック
            umaren_summary = MagicMock()
            umaren_summary.total_races = 48
            umaren_summary.total_hits = 8
            umaren_summary.hit_rate = 0.167
            umaren_summary.total_investment = 14400
            umaren_summary.total_payout = 18200
            umaren_summary.return_rate = 1.264
            mock_umaren.return_value.simulate_period.return_value = umaren_summary

            # Sanrenpukuのモック
            sanrenpuku_summary = MagicMock()
            sanrenpuku_summary.total_races = 48
            sanrenpuku_summary.total_hits = 2
            sanrenpuku_summary.hit_rate = 0.042
            sanrenpuku_summary.total_investment = 4800
            sanrenpuku_summary.total_payout = 22400
            sanrenpuku_summary.return_rate = 4.667
            mock_sanrenpuku.return_value.simulate_period.return_value = sanrenpuku_summary

            yield {
                "fukusho": mock_fukusho,
                "tansho": mock_tansho,
                "umaren": mock_umaren,
                "sanrenpuku": mock_sanrenpuku,
            }

    def test_command_exists(self, runner):
        """backtest-all コマンドが登録されている"""
        result = runner.invoke(main, ["backtest-all", "--help"])
        assert result.exit_code == 0
        assert "全券種" in result.output or "backtest" in result.output.lower()

    def test_db_option_required(self, runner):
        """--db オプションが必須"""
        result = runner.invoke(main, ["backtest-all"])
        assert result.exit_code != 0
        assert "db" in result.output.lower() or "required" in result.output.lower()

    def test_calls_all_simulators(self, runner, mock_simulators, tmp_path):
        """全シミュレータが呼び出される"""
        # ダミーDBファイル作成
        db_path = tmp_path / "test.db"
        db_path.touch()

        result = runner.invoke(
            main,
            [
                "backtest-all",
                "--db",
                str(db_path),
                "--from",
                "2026-01-20",
                "--to",
                "2026-01-26",
            ],
        )

        # 全シミュレータが呼び出されたことを確認
        mock_simulators["fukusho"].return_value.simulate_period.assert_called_once()
        mock_simulators["tansho"].return_value.simulate_period.assert_called_once()
        mock_simulators["umaren"].return_value.simulate_period.assert_called_once()
        mock_simulators["sanrenpuku"].return_value.simulate_period.assert_called_once()

    def test_passes_correct_parameters_to_simulators(
        self, runner, mock_simulators, tmp_path
    ):
        """正しいパラメータがシミュレータに渡される"""
        db_path = tmp_path / "test.db"
        db_path.touch()

        result = runner.invoke(
            main,
            [
                "backtest-all",
                "--db",
                str(db_path),
                "--from",
                "2026-01-20",
                "--to",
                "2026-01-26",
                "--top-n",
                "5",
                "--venue",
                "中山",
                "--venue",
                "京都",
            ],
        )

        # Fukusho/Tanshoはtop_nを受け取る
        fukusho_call = mock_simulators[
            "fukusho"
        ].return_value.simulate_period.call_args
        assert fukusho_call.kwargs["from_date"] == "2026-01-20"
        assert fukusho_call.kwargs["to_date"] == "2026-01-26"
        assert fukusho_call.kwargs["top_n"] == 5
        assert fukusho_call.kwargs["venues"] == ["中山", "京都"]

        tansho_call = mock_simulators["tansho"].return_value.simulate_period.call_args
        assert tansho_call.kwargs["top_n"] == 5

        # Umaren/Sanrenpukuはtop_nを受け取らない
        umaren_call = mock_simulators["umaren"].return_value.simulate_period.call_args
        assert "top_n" not in umaren_call.kwargs or umaren_call.kwargs.get("top_n") is None

    def test_output_contains_header(self, runner, mock_simulators, tmp_path):
        """出力にヘッダーが含まれる"""
        db_path = tmp_path / "test.db"
        db_path.touch()

        result = runner.invoke(
            main,
            [
                "backtest-all",
                "--db",
                str(db_path),
                "--from",
                "2026-01-20",
                "--to",
                "2026-01-26",
            ],
        )

        assert result.exit_code == 0
        assert "2026-01-20" in result.output
        assert "2026-01-26" in result.output

    def test_output_contains_all_bet_types(self, runner, mock_simulators, tmp_path):
        """出力に全券種が含まれる"""
        db_path = tmp_path / "test.db"
        db_path.touch()

        result = runner.invoke(
            main,
            [
                "backtest-all",
                "--db",
                str(db_path),
                "--from",
                "2026-01-20",
                "--to",
                "2026-01-26",
            ],
        )

        assert result.exit_code == 0
        assert "複勝" in result.output
        assert "単勝" in result.output
        assert "馬連" in result.output
        assert "三連複" in result.output

    def test_output_contains_summary_totals(self, runner, mock_simulators, tmp_path):
        """出力に総計が含まれる"""
        db_path = tmp_path / "test.db"
        db_path.touch()

        result = runner.invoke(
            main,
            [
                "backtest-all",
                "--db",
                str(db_path),
                "--from",
                "2026-01-20",
                "--to",
                "2026-01-26",
            ],
        )

        assert result.exit_code == 0
        # 総投資額・総払戻額・総回収率が表示される
        assert "総投資額" in result.output or "投資" in result.output
        assert "総払戻額" in result.output or "払戻" in result.output
        assert "総回収率" in result.output or "回収率" in result.output

    def test_last_week_default(self, runner, mock_simulators, tmp_path):
        """--from/--to なしで先週がデフォルト"""
        db_path = tmp_path / "test.db"
        db_path.touch()

        result = runner.invoke(
            main,
            ["backtest-all", "--db", str(db_path)],
        )

        # エラーなく実行され、シミュレータが呼ばれる
        assert result.exit_code == 0
        mock_simulators["fukusho"].return_value.simulate_period.assert_called_once()

    def test_verbose_option(self, runner, mock_simulators, tmp_path):
        """-v オプションでverbose出力"""
        db_path = tmp_path / "test.db"
        db_path.touch()

        # verboseモード用に各券種のrace_resultsを設定
        # 複勝のモック結果
        fukusho_result = MagicMock()
        fukusho_result.race_date = "2026-01-18"
        fukusho_result.venue = "中山"
        fukusho_result.race_name = "1R"
        fukusho_result.top_n_predictions = (1, 3, 5)
        fukusho_result.hits = (1, 3)
        fukusho_result.payout_total = 380
        mock_simulators["fukusho"].return_value.simulate_period.return_value.race_results = [
            fukusho_result
        ]

        # 単勝のモック結果
        tansho_result = MagicMock()
        tansho_result.race_date = "2026-01-18"
        tansho_result.venue = "中山"
        tansho_result.race_name = "1R"
        tansho_result.top_n_predictions = (1, 3, 5)
        tansho_result.winning_horse = 1
        tansho_result.hit = True
        tansho_result.payout = 250
        mock_simulators["tansho"].return_value.simulate_period.return_value.race_results = [
            tansho_result
        ]

        # 馬連のモック結果
        umaren_result = MagicMock()
        umaren_result.race_date = "2026-01-18"
        umaren_result.venue = "中山"
        umaren_result.race_name = "1R"
        umaren_result.bet_combinations = ((1, 3), (1, 5), (3, 5))
        umaren_result.actual_pair = (1, 3)
        umaren_result.hit = True
        umaren_result.payout = 1520
        mock_simulators["umaren"].return_value.simulate_period.return_value.race_results = [
            umaren_result
        ]

        # 三連複のモック結果
        sanrenpuku_result = MagicMock()
        sanrenpuku_result.race_date = "2026-01-18"
        sanrenpuku_result.venue = "中山"
        sanrenpuku_result.race_name = "1R"
        sanrenpuku_result.predicted_trio = (1, 3, 5)
        sanrenpuku_result.actual_trio = (1, 3, 7)
        sanrenpuku_result.hit = False
        sanrenpuku_result.payout = 0
        mock_simulators["sanrenpuku"].return_value.simulate_period.return_value.race_results = [
            sanrenpuku_result
        ]

        result = runner.invoke(
            main,
            ["backtest-all", "--db", str(db_path), "-v"],
        )

        # エラーなく実行される
        assert result.exit_code == 0
        # verbose時に各券種の詳細ヘッダが表示される
        assert "複勝" in result.output and "レース別詳細" in result.output
        assert "単勝" in result.output
        assert "馬連" in result.output
        assert "三連複" in result.output
        # レース結果の詳細が表示される
        assert "2026-01-18" in result.output
        assert "中山" in result.output


class TestFormatResultsTable:
    """_format_results_table ヘルパー関数のテスト"""

    def test_generates_table_with_correct_structure(self):
        """正しいテーブル構造が生成される"""
        from keiba.cli.commands.backtest import _format_results_table

        # モックサマリを作成
        fukusho = MagicMock()
        fukusho.total_hits = 25
        fukusho.hit_rate = 0.174
        fukusho.total_investment = 14400
        fukusho.total_payout = 18500
        fukusho.return_rate = 1.285

        tansho = MagicMock()
        tansho.total_hits = 12
        tansho.hit_rate = 0.083
        tansho.total_investment = 14400
        tansho.total_payout = 15340
        tansho.return_rate = 1.065

        umaren = MagicMock()
        umaren.total_hits = 8
        umaren.hit_rate = 0.167
        umaren.total_investment = 14400
        umaren.total_payout = 18200
        umaren.return_rate = 1.264

        sanrenpuku = MagicMock()
        sanrenpuku.total_hits = 2
        sanrenpuku.hit_rate = 0.042
        sanrenpuku.total_investment = 4800
        sanrenpuku.total_payout = 22400
        sanrenpuku.return_rate = 4.667

        table = _format_results_table(fukusho, tansho, umaren, sanrenpuku)

        # テーブルに全券種が含まれる
        assert "複勝" in table
        assert "単勝" in table
        assert "馬連" in table
        assert "三連複" in table
        # テーブル罫線が含まれる
        assert "+" in table
        assert "|" in table
        # ヘッダが含まれる
        assert "券種" in table
        assert "的中数" in table
        assert "的中率" in table
        assert "投資額" in table
        assert "払戻額" in table
        assert "回収率" in table

    def test_handles_large_numbers(self):
        """大きな数値でも正しくフォーマットされる"""
        from keiba.cli.commands.backtest import _format_results_table

        # 大きな数値のモックサマリ
        fukusho = MagicMock()
        fukusho.total_hits = 1000
        fukusho.hit_rate = 0.50
        fukusho.total_investment = 1000000
        fukusho.total_payout = 1500000
        fukusho.return_rate = 1.5

        tansho = MagicMock()
        tansho.total_hits = 500
        tansho.hit_rate = 0.25
        tansho.total_investment = 1000000
        tansho.total_payout = 800000
        tansho.return_rate = 0.8

        umaren = MagicMock()
        umaren.total_hits = 100
        umaren.hit_rate = 0.10
        umaren.total_investment = 1000000
        umaren.total_payout = 2000000
        umaren.return_rate = 2.0

        sanrenpuku = MagicMock()
        sanrenpuku.total_hits = 10
        sanrenpuku.hit_rate = 0.01
        sanrenpuku.total_investment = 100000
        sanrenpuku.total_payout = 5000000
        sanrenpuku.return_rate = 50.0

        table = _format_results_table(fukusho, tansho, umaren, sanrenpuku)

        # 大きな数値が表示される
        assert "1,000,000" in table or "1000000" in table
        # テーブルが崩れていない（各行の+の数が同じ）
        lines = table.strip().split("\n")
        border_lines = [line for line in lines if line.startswith("+")]
        first_border_len = len(border_lines[0])
        for border_line in border_lines:
            assert len(border_line) == first_border_len, "テーブル幅が揃っていない"


class TestBacktestAllIntegration:
    """backtest-all コマンドの統合テスト（シミュレータの呼び出し検証）"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_invalid_from_only(self, runner, tmp_path):
        """--from のみ指定するとエラー"""
        db_path = tmp_path / "test.db"
        db_path.touch()

        result = runner.invoke(
            main,
            ["backtest-all", "--db", str(db_path), "--from", "2026-01-20"],
        )

        assert result.exit_code != 0
        assert "--from" in result.output and "--to" in result.output

    def test_invalid_to_only(self, runner, tmp_path):
        """--to のみ指定するとエラー"""
        db_path = tmp_path / "test.db"
        db_path.touch()

        result = runner.invoke(
            main,
            ["backtest-all", "--db", str(db_path), "--to", "2026-01-26"],
        )

        assert result.exit_code != 0

    def test_invalid_date_format(self, runner, tmp_path):
        """不正な日付形式はエラー"""
        db_path = tmp_path / "test.db"
        db_path.touch()

        result = runner.invoke(
            main,
            [
                "backtest-all",
                "--db",
                str(db_path),
                "--from",
                "invalid",
                "--to",
                "2026-01-26",
            ],
        )

        assert result.exit_code != 0
        assert "日付形式" in result.output
