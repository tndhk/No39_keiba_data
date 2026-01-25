"""Tests for train command in keiba.cli module."""

import os
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from keiba.cli import main


# LightGBMが使用可能か確認
try:
    import lightgbm  # noqa: F401

    LIGHTGBM_AVAILABLE = True
except (ImportError, OSError):
    LIGHTGBM_AVAILABLE = False

skip_without_lightgbm = pytest.mark.skipif(
    not LIGHTGBM_AVAILABLE,
    reason="LightGBM is not available (missing libomp or other dependency)",
)


class TestTrainCommand:
    """train コマンドのテスト"""

    @pytest.fixture
    def runner(self):
        """CliRunner fixture"""
        return CliRunner()

    @pytest.fixture
    def temp_db(self, tmp_path):
        """一時的なSQLiteデータベースを作成"""
        from keiba.db import get_engine, init_db
        from keiba.models import Horse, Race, RaceResult

        db_path = tmp_path / "test.db"
        engine = get_engine(str(db_path))
        init_db(engine)

        # テスト用のデータを作成
        from sqlalchemy.orm import Session

        with Session(engine) as session:
            # 複数のレースと結果を作成（最低100サンプル以上必要）
            for i in range(20):
                race = Race(
                    id=f"20240101010{i:02d}",
                    name=f"テストレース{i}",
                    date=date(2024, 1, 1),
                    course="中山",
                    race_number=i + 1,
                    distance=1600,
                    surface="芝",
                )
                session.add(race)

                # 各レースに10頭の馬を追加
                for j in range(10):
                    horse = Horse(
                        id=f"horse{i:02d}{j:02d}",
                        name=f"テスト馬{i}-{j}",
                        sex="牡",
                        birth_year=2020,
                    )
                    session.add(horse)

                    result = RaceResult(
                        race_id=race.id,
                        horse_id=horse.id,
                        jockey_id="jockey001",
                        trainer_id="trainer001",
                        finish_position=j + 1,
                        bracket_number=1,
                        horse_number=j + 1,
                        odds=5.0,
                        popularity=j + 1,
                        weight=480,
                        weight_diff=0,
                        time="1:35.0",
                        margin="0",
                    )
                    session.add(result)

            session.commit()

        return str(db_path)

    @skip_without_lightgbm
    def test_train_command_creates_model(self, runner, temp_db, tmp_path):
        """trainコマンドがモデルファイルを作成する"""
        output_path = tmp_path / "model.joblib"

        result = runner.invoke(
            main, ["train", "--db", temp_db, "--output", str(output_path)]
        )

        # コマンドが成功することを確認
        assert result.exit_code == 0, f"Command failed: {result.output}"
        # モデルファイルが作成されていることを確認
        assert output_path.exists(), "Model file was not created"
        # 出力メッセージを確認
        assert "学習完了" in result.output or "モデルを保存しました" in result.output

    @skip_without_lightgbm
    def test_train_command_with_cutoff_date(self, runner, temp_db, tmp_path):
        """カットオフ日付を指定してtrainコマンドが動作する"""
        output_path = tmp_path / "model_cutoff.joblib"

        result = runner.invoke(
            main,
            [
                "train",
                "--db",
                temp_db,
                "--output",
                str(output_path),
                "--cutoff-date",
                "2024-01-02",
            ],
        )

        # コマンドが成功することを確認
        assert result.exit_code == 0, f"Command failed: {result.output}"
        # モデルファイルが作成されていることを確認
        assert output_path.exists(), "Model file was not created"

    def test_train_command_requires_db_option(self, runner, tmp_path):
        """--db オプションは必須"""
        output_path = tmp_path / "model.joblib"

        result = runner.invoke(main, ["train", "--output", str(output_path)])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "--db" in result.output

    def test_train_command_requires_output_option(self, runner, temp_db):
        """--output オプションは必須"""
        result = runner.invoke(main, ["train", "--db", temp_db])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "--output" in result.output

    @skip_without_lightgbm
    def test_train_command_shows_training_progress(self, runner, temp_db, tmp_path):
        """trainコマンドが学習の進捗を表示する"""
        output_path = tmp_path / "model.joblib"

        result = runner.invoke(
            main, ["train", "--db", temp_db, "--output", str(output_path)]
        )

        # 学習に関するメッセージが表示されることを確認
        assert result.exit_code == 0
        assert "学習" in result.output

    @skip_without_lightgbm
    def test_train_command_handles_invalid_cutoff_date(self, runner, temp_db, tmp_path):
        """不正なカットオフ日付形式でエラーを返す"""
        output_path = tmp_path / "model.joblib"

        result = runner.invoke(
            main,
            [
                "train",
                "--db",
                temp_db,
                "--output",
                str(output_path),
                "--cutoff-date",
                "invalid-date",
            ],
        )

        # エラーメッセージが表示されることを確認
        assert result.exit_code != 0 or "日付形式" in result.output

    @skip_without_lightgbm
    def test_train_command_creates_output_directory(self, runner, temp_db, tmp_path):
        """出力ディレクトリが存在しない場合に作成する"""
        output_path = tmp_path / "nested" / "dir" / "model.joblib"

        result = runner.invoke(
            main, ["train", "--db", temp_db, "--output", str(output_path)]
        )

        # コマンドが成功することを確認
        assert result.exit_code == 0, f"Command failed: {result.output}"
        # モデルファイルが作成されていることを確認
        assert output_path.exists(), "Model file was not created in nested directory"
