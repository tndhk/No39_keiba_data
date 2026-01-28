"""Tests for backtest CLI commands"""

import pytest
from click.testing import CliRunner
from keiba.backtest.sanrenpuku_simulator import SanrenpukuRaceResult
from keiba.cli.commands.backtest import backtest_all


class TestSanrenpukuRaceResultFields:
    """SanrenpukuRaceResultのフィールド名テスト（Phase 1-4）"""

    def test_result_has_predicted_trio_field(self):
        """SanrenpukuRaceResultがpredicted_trioフィールドを持つこと"""
        # Arrange & Act
        result = SanrenpukuRaceResult(
            race_id="202501010101",
            race_name="テストステークス",
            venue="東京",
            race_date="2025-01-01",
            predicted_trio=(1, 2, 3),
            actual_trio=(1, 2, 3),
            hit=True,
            payout=5000,
            investment=100,
        )

        # Assert
        assert hasattr(result, "predicted_trio"), (
            "SanrenpukuRaceResultにpredicted_trioフィールドが存在しない"
        )
        assert result.predicted_trio == (1, 2, 3)

    def test_result_has_actual_trio_field(self):
        """SanrenpukuRaceResultがactual_trioフィールドを持つこと"""
        # Arrange & Act
        result = SanrenpukuRaceResult(
            race_id="202501010101",
            race_name="テストステークス",
            venue="東京",
            race_date="2025-01-01",
            predicted_trio=(1, 2, 3),
            actual_trio=(4, 5, 6),
            hit=False,
            payout=0,
            investment=100,
        )

        # Assert
        assert hasattr(result, "actual_trio"), (
            "SanrenpukuRaceResultにactual_trioフィールドが存在しない"
        )
        assert result.actual_trio == (4, 5, 6)

    def test_result_does_not_have_bet_combination_field(self):
        """SanrenpukuRaceResultがbet_combinationフィールドを持たないこと"""
        # Arrange & Act
        result = SanrenpukuRaceResult(
            race_id="202501010101",
            race_name="テストステークス",
            venue="東京",
            race_date="2025-01-01",
            predicted_trio=(1, 2, 3),
            actual_trio=(1, 2, 3),
            hit=True,
            payout=5000,
            investment=100,
        )

        # Assert
        # bet_combinationフィールドは存在しないはず
        assert not hasattr(result, "bet_combination"), (
            "SanrenpukuRaceResultにbet_combinationフィールドが存在する（削除されたはず）"
        )


class TestBacktestAllModelOption:
    """backtest-allコマンドの--modelオプションテスト（Task 2-2）"""

    def test_backtest_all_accepts_model_option(self, tmp_path):
        """backtest-allコマンドが--modelオプションを受け取れることを検証"""
        # RED: --modelオプションがまだ存在しないため、エラーが発生するはず
        runner = CliRunner()

        # 一時的なDBファイルを作成
        db_path = str(tmp_path / "test.db")
        with open(db_path, "w") as f:
            f.write("")  # 空ファイル

        # テスト用モデルファイルを作成
        model_path = str(tmp_path / "test_model.joblib")
        with open(model_path, "w") as f:
            f.write("")  # 空ファイル

        # --modelオプション付きで実行
        result = runner.invoke(
            backtest_all,
            [
                "--from", "2025-01-01",
                "--to", "2025-01-31",
                "--db", db_path,
                "--model", model_path,
            ]
        )

        # デバッグ出力
        if result.exit_code != 0:
            print(f"Exit code: {result.exit_code}")
            print(f"Output: {result.output}")
            if result.exception:
                print(f"Exception: {result.exception}")
                import traceback
                traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)

        # --modelオプションが受け取れることを確認
        # エラーが発生した場合でも、"no such option"エラーでなければOK
        # (実際の実行エラーは別問題)
        assert "no such option" not in result.output.lower(), (
            f"--modelオプションが認識されていない: {result.output}"
        )
