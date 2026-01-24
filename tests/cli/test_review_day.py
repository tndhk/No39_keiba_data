"""Tests for review-day command in keiba.cli module.

TDDアプローチで review-day コマンドのテストを実装。
"""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from keiba.cli import main


class TestParsePredictionsMarkdown:
    """_parse_predictions_markdown関数のテスト"""

    def test_parses_basic_prediction_file(self, tmp_path):
        """基本的な予測ファイルをパースできる"""
        from keiba.cli import _parse_predictions_markdown

        content = """# 2026-01-24 中山 予測結果

生成日時: 2026-01-24 18:55:31

## 1R テストレース
芝2000m

| 順位 | 馬番 | 馬名 | ML確率 | 総合 |
|:---:|:---:|:---|:---:|:---:|
| 1 | 5 | テストホース1 | 65.0% | 75.5 |
| 2 | 3 | テストホース2 | 45.0% | 65.0 |
| 3 | 8 | テストホース3 | 30.0% | 55.0 |

## 2R 別のレース
ダート1200m

| 順位 | 馬番 | 馬名 | ML確率 | 総合 |
|:---:|:---:|:---|:---:|:---:|
| 1 | 2 | ダートホース1 | 55.0% | 70.0 |
| 2 | 7 | ダートホース2 | 40.0% | 60.0 |
| 3 | 1 | ダートホース3 | 25.0% | 50.0 |

"""
        filepath = tmp_path / "2026-01-24-nakayama.md"
        filepath.write_text(content, encoding="utf-8")

        result = _parse_predictions_markdown(str(filepath))

        assert "races" in result
        assert len(result["races"]) == 2
        assert result["races"][0]["race_number"] == 1
        assert result["races"][0]["predictions"][0]["horse_number"] == 5
        assert result["races"][0]["predictions"][0]["horse_name"] == "テストホース1"

    def test_parses_race_number_from_header(self, tmp_path):
        """レース番号をヘッダーから正しく抽出する"""
        from keiba.cli import _parse_predictions_markdown

        content = """# 2026-01-24 中山 予測結果

## 12R 第65回京成杯(G3)
芝2000m

| 順位 | 馬番 | 馬名 | ML確率 | 総合 |
|:---:|:---:|:---|:---:|:---:|
| 1 | 5 | テストホース | 65.0% | 75.5 |

"""
        filepath = tmp_path / "test.md"
        filepath.write_text(content, encoding="utf-8")

        result = _parse_predictions_markdown(str(filepath))

        assert result["races"][0]["race_number"] == 12
        assert result["races"][0]["race_name"] == "第65回京成杯(G3)"

    def test_returns_empty_for_nonexistent_file(self, tmp_path):
        """存在しないファイルは空の結果を返す"""
        from keiba.cli import _parse_predictions_markdown

        result = _parse_predictions_markdown(str(tmp_path / "nonexistent.md"))

        assert result == {"races": []}

    def test_parses_prediction_without_ml_probability(self, tmp_path):
        """ML確率が'-'の予測もパースできる"""
        from keiba.cli import _parse_predictions_markdown

        content = """# 2026-01-24 中山 予測結果

## 1R テストレース
芝2000m

| 順位 | 馬番 | 馬名 | ML確率 | 総合 |
|:---:|:---:|:---|:---:|:---:|
| 1 | 5 | テストホース | - | 75.5 |

"""
        filepath = tmp_path / "test.md"
        filepath.write_text(content, encoding="utf-8")

        result = _parse_predictions_markdown(str(filepath))

        assert result["races"][0]["predictions"][0]["ml_probability"] == 0.0


class TestCalculateFukushoSimulation:
    """_calculate_fukusho_simulation関数のテスト"""

    def test_calculates_hit_on_predicted_first(self):
        """予測1位が3着以内で的中と判定する"""
        from keiba.cli import _calculate_fukusho_simulation

        predictions = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [
                        {"horse_number": 5, "rank": 1},
                        {"horse_number": 3, "rank": 2},
                        {"horse_number": 8, "rank": 3},
                    ],
                }
            ]
        }
        actual_results = {
            1: [5, 3, 1],  # race_number: [1着, 2着, 3着]
        }
        payouts = {
            1: {5: 150, 3: 280, 1: 320},  # race_number: {horse_number: payout}
        }

        result = _calculate_fukusho_simulation(predictions, actual_results, payouts)

        assert result["top1"]["hits"] == 1
        assert result["top1"]["total_races"] == 1
        assert result["top1"]["payout"] == 150

    def test_calculates_miss_when_predicted_first_not_in_top3(self):
        """予測1位が3着以内でない場合はミスと判定する"""
        from keiba.cli import _calculate_fukusho_simulation

        predictions = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [
                        {"horse_number": 5, "rank": 1},
                        {"horse_number": 3, "rank": 2},
                        {"horse_number": 8, "rank": 3},
                    ],
                }
            ]
        }
        actual_results = {
            1: [2, 7, 9],  # 予測馬は入っていない
        }
        payouts = {
            1: {2: 150, 7: 280, 9: 320},
        }

        result = _calculate_fukusho_simulation(predictions, actual_results, payouts)

        assert result["top1"]["hits"] == 0
        assert result["top1"]["total_races"] == 1
        assert result["top1"]["payout"] == 0

    def test_calculates_top3_simulation(self):
        """予測1-3位に各100円賭けたシミュレーションを計算する"""
        from keiba.cli import _calculate_fukusho_simulation

        predictions = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [
                        {"horse_number": 5, "rank": 1},
                        {"horse_number": 3, "rank": 2},
                        {"horse_number": 8, "rank": 3},
                    ],
                }
            ]
        }
        actual_results = {
            1: [5, 3, 1],  # 5, 3が的中、8は外れ
        }
        payouts = {
            1: {5: 150, 3: 280, 1: 320},
        }

        result = _calculate_fukusho_simulation(predictions, actual_results, payouts)

        assert result["top3"]["hits"] == 2  # 5, 3が的中
        assert result["top3"]["total_bets"] == 3  # 3頭に賭けた
        assert result["top3"]["payout"] == 150 + 280  # 430円

    def test_calculates_hit_rate(self):
        """的中率を計算する"""
        from keiba.cli import _calculate_fukusho_simulation

        predictions = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [
                        {"horse_number": 5, "rank": 1},
                    ],
                },
                {
                    "race_number": 2,
                    "predictions": [
                        {"horse_number": 2, "rank": 1},
                    ],
                },
            ]
        }
        actual_results = {
            1: [5, 3, 1],  # 1Rは的中
            2: [7, 8, 9],  # 2Rは外れ
        }
        payouts = {
            1: {5: 150, 3: 280, 1: 320},
            2: {7: 200, 8: 300, 9: 400},
        }

        result = _calculate_fukusho_simulation(predictions, actual_results, payouts)

        assert result["top1"]["hits"] == 1
        assert result["top1"]["total_races"] == 2
        assert result["top1"]["hit_rate"] == 0.5  # 50%

    def test_calculates_return_rate(self):
        """回収率を計算する"""
        from keiba.cli import _calculate_fukusho_simulation

        predictions = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [
                        {"horse_number": 5, "rank": 1},
                    ],
                },
            ]
        }
        actual_results = {
            1: [5, 3, 1],
        }
        payouts = {
            1: {5: 150, 3: 280, 1: 320},
        }

        result = _calculate_fukusho_simulation(predictions, actual_results, payouts)

        # 100円賭けて150円返ってきた = 回収率150%
        assert result["top1"]["return_rate"] == 1.5

    def test_handles_empty_predictions(self):
        """予測データがない場合は空の結果を返す"""
        from keiba.cli import _calculate_fukusho_simulation

        predictions = {"races": []}
        actual_results = {}
        payouts = {}

        result = _calculate_fukusho_simulation(predictions, actual_results, payouts)

        assert result["top1"]["total_races"] == 0
        assert result["top1"]["hits"] == 0
        assert result["top3"]["total_bets"] == 0


class TestAppendReviewToMarkdown:
    """_append_review_to_markdown関数のテスト"""

    def test_appends_review_section_to_file(self, tmp_path):
        """検証結果セクションをファイルに追記する"""
        from keiba.cli import _append_review_to_markdown

        original_content = """# 2026-01-24 中山 予測結果

生成日時: 2026-01-24 18:55:31

## 1R テストレース
芝2000m

| 順位 | 馬番 | 馬名 | ML確率 | 総合 |
|:---:|:---:|:---|:---:|:---:|
| 1 | 5 | テストホース | 65.0% | 75.5 |

"""
        filepath = tmp_path / "test.md"
        filepath.write_text(original_content, encoding="utf-8")

        review_data = {
            "top1": {
                "hits": 5,
                "total_races": 10,
                "hit_rate": 0.5,
                "payout": 750,
                "investment": 1000,
                "return_rate": 0.75,
            },
            "top3": {
                "hits": 15,
                "total_bets": 30,
                "hit_rate": 0.5,
                "payout": 2500,
                "investment": 3000,
                "return_rate": 0.833,
            },
            "race_results": [
                {
                    "race_number": 1,
                    "actual_top3": [5, 3, 1],
                    "predicted_top3": [5, 8, 3],
                    "top1_hit": True,
                    "top3_hits": 2,
                },
            ],
        }

        _append_review_to_markdown(str(filepath), review_data)

        content = filepath.read_text(encoding="utf-8")
        assert "## 検証結果" in content
        assert "50.0%" in content  # 的中率
        assert "75.0%" in content  # 回収率

    def test_creates_review_datetime(self, tmp_path):
        """検証日時がセクションに含まれる"""
        from keiba.cli import _append_review_to_markdown

        original_content = "# Test\n"
        filepath = tmp_path / "test.md"
        filepath.write_text(original_content, encoding="utf-8")

        review_data = {
            "top1": {"hits": 0, "total_races": 0, "hit_rate": 0, "payout": 0, "investment": 0, "return_rate": 0},
            "top3": {"hits": 0, "total_bets": 0, "hit_rate": 0, "payout": 0, "investment": 0, "return_rate": 0},
            "race_results": [],
        }

        _append_review_to_markdown(str(filepath), review_data)

        content = filepath.read_text(encoding="utf-8")
        assert "検証日時:" in content


class TestReviewDayCommand:
    """review-dayコマンドのテスト"""

    def test_review_day_command_registered(self):
        """review-dayコマンドが登録されている"""
        assert "review-day" in main.commands

    def test_review_day_help(self):
        """review-day --helpが正常に動作する"""
        runner = CliRunner()
        result = runner.invoke(main, ["review-day", "--help"])
        assert result.exit_code == 0
        assert "--date" in result.output
        assert "--venue" in result.output
        assert "--db" in result.output

    def test_review_day_requires_db(self):
        """review-dayは--dbオプションを必須とする"""
        runner = CliRunner()
        result = runner.invoke(
            main, ["review-day", "--date", "2026-01-24", "--venue", "中山"]
        )
        assert result.exit_code != 0
        assert "db" in result.output.lower() or "missing" in result.output.lower()

    def test_review_day_requires_venue(self):
        """review-dayは--venueオプションを必須とする"""
        runner = CliRunner()
        result = runner.invoke(
            main, ["review-day", "--date", "2026-01-24", "--db", "test.db"]
        )
        assert result.exit_code != 0
        assert "venue" in result.output.lower() or "missing" in result.output.lower()

    def test_review_day_date_defaults_to_today(self):
        """--dateを省略すると今日の日付が使用される"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # DBファイルを作成
            Path("test.db").touch()
            result = runner.invoke(
                main, ["review-day", "--venue", "中山", "--db", "test.db"]
            )
            # 日付形式エラーではないことを確認
            assert "日付形式が不正" not in result.output

    def test_review_day_invalid_date_format(self):
        """無効な日付形式はエラーになる"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("test.db").touch()
            result = runner.invoke(
                main,
                [
                    "review-day",
                    "--date",
                    "2026/01/24",  # Invalid format
                    "--venue",
                    "中山",
                    "--db",
                    "test.db",
                ],
            )
            assert result.exit_code != 0
            assert "日付形式" in result.output


class TestReviewDayExecution:
    """review-dayコマンドの実行テスト"""

    @patch("keiba.cli._append_review_to_markdown")
    @patch("keiba.cli._calculate_fukusho_simulation")
    @patch("keiba.cli._parse_predictions_markdown")
    @patch("keiba.cli.RaceDetailScraper")
    def test_review_day_reads_prediction_file(
        self,
        mock_scraper_class,
        mock_parse,
        mock_calculate,
        mock_append,
    ):
        """review-dayは予測ファイルを読み込む"""
        # Setup mocks
        mock_parse.return_value = {"races": []}
        mock_calculate.return_value = {
            "top1": {"hits": 0, "total_races": 0, "hit_rate": 0, "payout": 0, "investment": 0, "return_rate": 0},
            "top3": {"hits": 0, "total_bets": 0, "hit_rate": 0, "payout": 0, "investment": 0, "return_rate": 0},
            "race_results": [],
        }

        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("test.db").touch()
            # 予測ファイルを作成
            predictions_dir = Path("docs/predictions")
            predictions_dir.mkdir(parents=True)
            (predictions_dir / "2026-01-24-nakayama.md").write_text("# Test", encoding="utf-8")

            result = runner.invoke(
                main,
                [
                    "review-day",
                    "--date",
                    "2026-01-24",
                    "--venue",
                    "中山",
                    "--db",
                    "test.db",
                ],
            )

        # パース関数が呼ばれたことを確認
        mock_parse.assert_called_once()
        call_args = mock_parse.call_args[0][0]
        assert "2026-01-24-nakayama.md" in call_args

    @patch("keiba.cli._append_review_to_markdown")
    @patch("keiba.cli._calculate_fukusho_simulation")
    @patch("keiba.cli._parse_predictions_markdown")
    @patch("keiba.cli.RaceDetailScraper")
    def test_review_day_fetches_race_results(
        self,
        mock_scraper_class,
        mock_parse,
        mock_calculate,
        mock_append,
    ):
        """review-dayはRaceDetailScraperで結果を取得する"""
        # Setup mocks
        mock_parse.return_value = {
            "races": [
                {
                    "race_number": 1,
                    "race_id": "202606010801",
                    "predictions": [{"horse_number": 5, "rank": 1}],
                }
            ]
        }
        mock_calculate.return_value = {
            "top1": {"hits": 0, "total_races": 0, "hit_rate": 0, "payout": 0, "investment": 0, "return_rate": 0},
            "top3": {"hits": 0, "total_bets": 0, "hit_rate": 0, "payout": 0, "investment": 0, "return_rate": 0},
            "race_results": [],
        }

        mock_scraper = MagicMock()
        mock_scraper.fetch_race_detail.return_value = {
            "race": {"id": "202606010801"},
            "results": [
                {"finish_position": 1, "horse_number": 5},
                {"finish_position": 2, "horse_number": 3},
                {"finish_position": 3, "horse_number": 1},
            ],
        }
        mock_scraper.fetch_payouts.return_value = [
            {"horse_number": 5, "payout": 150},
            {"horse_number": 3, "payout": 280},
            {"horse_number": 1, "payout": 320},
        ]
        mock_scraper_class.return_value = mock_scraper

        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("test.db").touch()
            predictions_dir = Path("docs/predictions")
            predictions_dir.mkdir(parents=True)
            (predictions_dir / "2026-01-24-nakayama.md").write_text("# Test", encoding="utf-8")

            result = runner.invoke(
                main,
                [
                    "review-day",
                    "--date",
                    "2026-01-24",
                    "--venue",
                    "中山",
                    "--db",
                    "test.db",
                ],
            )

        # スクレイパーが呼ばれたことを確認
        mock_scraper.fetch_payouts.assert_called()

    @patch("keiba.cli._append_review_to_markdown")
    @patch("keiba.cli._calculate_fukusho_simulation")
    @patch("keiba.cli._parse_predictions_markdown")
    @patch("keiba.cli.RaceDetailScraper")
    def test_review_day_appends_review_to_markdown(
        self,
        mock_scraper_class,
        mock_parse,
        mock_calculate,
        mock_append,
    ):
        """review-dayは検証結果をMarkdownに追記する"""
        # Setup mocks - 予測データがあるケースを設定
        mock_parse.return_value = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [{"horse_number": 5, "rank": 1}],
                }
            ]
        }
        mock_calculate.return_value = {
            "top1": {"hits": 5, "total_races": 10, "hit_rate": 0.5, "payout": 750, "investment": 1000, "return_rate": 0.75},
            "top3": {"hits": 15, "total_bets": 30, "hit_rate": 0.5, "payout": 2500, "investment": 3000, "return_rate": 0.833},
            "race_results": [],
        }

        mock_scraper = MagicMock()
        mock_scraper.fetch_payouts.return_value = []
        mock_scraper_class.return_value = mock_scraper

        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("test.db").touch()
            predictions_dir = Path("docs/predictions")
            predictions_dir.mkdir(parents=True)
            (predictions_dir / "2026-01-24-nakayama.md").write_text("# Test", encoding="utf-8")

            result = runner.invoke(
                main,
                [
                    "review-day",
                    "--date",
                    "2026-01-24",
                    "--venue",
                    "中山",
                    "--db",
                    "test.db",
                ],
            )

        # 追記関数が呼ばれたことを確認
        mock_append.assert_called_once()

    @patch("keiba.cli._append_review_to_markdown")
    @patch("keiba.cli._calculate_fukusho_simulation")
    @patch("keiba.cli._parse_predictions_markdown")
    @patch("keiba.cli.RaceDetailScraper")
    def test_review_day_shows_summary(
        self,
        mock_scraper_class,
        mock_parse,
        mock_calculate,
        mock_append,
    ):
        """review-dayはコンソールにサマリーを表示する"""
        # Setup mocks - 予測データがあるケースを設定
        mock_parse.return_value = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [{"horse_number": 5, "rank": 1}],
                }
            ]
        }
        mock_calculate.return_value = {
            "top1": {"hits": 5, "total_races": 10, "hit_rate": 0.5, "payout": 750, "investment": 1000, "return_rate": 0.75},
            "top3": {"hits": 15, "total_bets": 30, "hit_rate": 0.5, "payout": 2500, "investment": 3000, "return_rate": 0.833},
            "race_results": [],
        }

        mock_scraper = MagicMock()
        mock_scraper.fetch_payouts.return_value = []
        mock_scraper_class.return_value = mock_scraper

        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("test.db").touch()
            predictions_dir = Path("docs/predictions")
            predictions_dir.mkdir(parents=True)
            (predictions_dir / "2026-01-24-nakayama.md").write_text("# Test", encoding="utf-8")

            result = runner.invoke(
                main,
                [
                    "review-day",
                    "--date",
                    "2026-01-24",
                    "--venue",
                    "中山",
                    "--db",
                    "test.db",
                ],
            )

        # サマリーがコンソールに出力されることを確認
        assert "的中率" in result.output or "回収率" in result.output


class TestReviewDayPredictionFileNotFound:
    """予測ファイルが見つからない場合のテスト"""

    @patch("keiba.cli._parse_predictions_markdown")
    def test_shows_error_when_prediction_file_not_found(self, mock_parse):
        """予測ファイルがない場合はエラーメッセージを表示する"""
        # パース結果を空に設定（ファイルが見つからなかった場合と同様）
        mock_parse.return_value = {"races": []}

        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("test.db").touch()
            # 予測ファイルは作成しない（存在チェックはパスするがデータがない）
            predictions_dir = Path("docs/predictions")
            predictions_dir.mkdir(parents=True)
            (predictions_dir / "2026-01-24-nakayama.md").write_text("# 空のファイル", encoding="utf-8")

            result = runner.invoke(
                main,
                [
                    "review-day",
                    "--date",
                    "2026-01-24",
                    "--venue",
                    "中山",
                    "--db",
                    "test.db",
                ],
            )

        assert result.exit_code != 0
        # 予測データがないエラーメッセージを確認
        assert "予測データがありません" in result.output or "予測ファイル" in result.output
