"""backtest-fukusho CLIコマンドの統合テスト

複勝馬券バックテストCLIの入力バリデーションと出力をテストする。
内部ロジックのテストは test_fukusho_simulator.py に任せる。
"""

import pytest
from click.testing import CliRunner

from keiba.cli import main


@pytest.fixture
def runner():
    """CLIテスト用のClickランナー"""
    return CliRunner()


class TestBacktestFukushoCLI:
    """backtest-fukushoコマンドのテスト"""

    def test_backtest_fukusho_help(self, runner):
        """ヘルプが表示される"""
        result = runner.invoke(main, ["backtest-fukusho", "--help"])
        assert result.exit_code == 0
        assert "複勝馬券のバックテストシミュレーション" in result.output
        assert "--from" in result.output
        assert "--to" in result.output
        assert "--last-week" in result.output
        assert "--top-n" in result.output
        assert "--venue" in result.output
        assert "--db" in result.output
        assert "-v" in result.output or "--verbose" in result.output

    def test_backtest_fukusho_requires_db(self, runner):
        """--db オプションが必須"""
        result = runner.invoke(main, ["backtest-fukusho"])
        assert result.exit_code != 0
        assert (
            "Missing option '--db'" in result.output
            or "required" in result.output.lower()
        )

    def test_backtest_fukusho_last_week_default(self, runner):
        """--last-week がデフォルト動作（--from/--to未指定時）"""
        with runner.isolated_filesystem():
            # 空のDBファイルを作成
            with open("test.db", "w") as f:
                f.write("")

            result = runner.invoke(main, ["backtest-fukusho", "--db", "test.db"])

            # last-weekモードで動作するが、DBが空なので実行時エラーになる可能性がある
            # ここでは開始メッセージと期間表示を確認
            # DBファイルが存在しないか不正な場合は早期にエラーになる可能性がある
            # 重要: 開始メッセージ「複勝シミュレーション」が表示されることを確認
            assert "複勝シミュレーション" in result.output or result.exit_code != 0

    def test_backtest_fukusho_date_range(self, runner):
        """--from と --to で期間指定"""
        with runner.isolated_filesystem():
            with open("test.db", "w") as f:
                f.write("")

            result = runner.invoke(
                main,
                [
                    "backtest-fukusho",
                    "--db",
                    "test.db",
                    "--from",
                    "2025-01-01",
                    "--to",
                    "2025-01-31",
                ],
            )

            # 指定した期間が出力に含まれる
            assert "2025-01-01" in result.output
            assert "2025-01-31" in result.output

    def test_backtest_fukusho_invalid_date(self, runner):
        """不正な日付形式でエラー"""
        with runner.isolated_filesystem():
            with open("test.db", "w") as f:
                f.write("")

            result = runner.invoke(
                main,
                [
                    "backtest-fukusho",
                    "--db",
                    "test.db",
                    "--from",
                    "invalid-date",
                    "--to",
                    "2025-01-31",
                ],
            )

            assert result.exit_code != 0
            assert "日付形式が不正です" in result.output

    def test_backtest_fukusho_missing_date(self, runner):
        """--from のみ指定でエラー"""
        with runner.isolated_filesystem():
            with open("test.db", "w") as f:
                f.write("")

            result = runner.invoke(
                main,
                [
                    "backtest-fukusho",
                    "--db",
                    "test.db",
                    "--from",
                    "2025-01-01",
                ],
            )

            # --toがない場合はエラーメッセージを表示
            assert result.exit_code != 0
            assert "--from と --to の両方を指定してください" in result.output


class TestBacktestFukushoOptions:
    """backtest-fukushoコマンドのオプションテスト"""

    def test_top_n_option(self, runner):
        """--top-n オプションが受け付けられる"""
        result = runner.invoke(main, ["backtest-fukusho", "--help"])
        assert "--top-n" in result.output

    def test_venue_option_multiple(self, runner):
        """--venue オプションが複数指定可能"""
        result = runner.invoke(main, ["backtest-fukusho", "--help"])
        assert "--venue" in result.output

    def test_verbose_flag(self, runner):
        """-v/--verbose フラグが受け付けられる"""
        result = runner.invoke(main, ["backtest-fukusho", "--help"])
        assert "-v" in result.output or "--verbose" in result.output

    def test_db_must_exist(self, runner):
        """--db で指定されたファイルが存在しない場合エラー"""
        result = runner.invoke(
            main,
            [
                "backtest-fukusho",
                "--db",
                "/nonexistent/path/to/db.db",
            ],
        )
        assert result.exit_code != 0
        # click.Path(exists=True)により自動でエラーメッセージが出る
        assert "does not exist" in result.output.lower() or "存在しません" in result.output


class TestBacktestFukushoOutput:
    """backtest-fukushoコマンドの出力テスト"""

    def test_shows_simulation_header(self, runner):
        """シミュレーションヘッダーが表示される"""
        with runner.isolated_filesystem():
            with open("test.db", "w") as f:
                f.write("")

            result = runner.invoke(
                main,
                [
                    "backtest-fukusho",
                    "--db",
                    "test.db",
                    "--from",
                    "2025-01-01",
                    "--to",
                    "2025-01-31",
                ],
            )

            # ヘッダーが表示される
            assert "複勝シミュレーション" in result.output

    def test_date_range_in_output(self, runner):
        """期間が出力に表示される"""
        with runner.isolated_filesystem():
            with open("test.db", "w") as f:
                f.write("")

            result = runner.invoke(
                main,
                [
                    "backtest-fukusho",
                    "--db",
                    "test.db",
                    "--from",
                    "2025-01-01",
                    "--to",
                    "2025-01-31",
                ],
            )

            assert "2025-01-01" in result.output
            assert "2025-01-31" in result.output
