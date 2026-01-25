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
        from keiba.cli.formatters.markdown import parse_predictions_markdown as _parse_predictions_markdown

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
        from keiba.cli.formatters.markdown import parse_predictions_markdown as _parse_predictions_markdown

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
        from keiba.cli.formatters.markdown import parse_predictions_markdown as _parse_predictions_markdown

        result = _parse_predictions_markdown(str(tmp_path / "nonexistent.md"))

        assert result == {"races": []}

    def test_parses_prediction_without_ml_probability(self, tmp_path):
        """ML確率が'-'の予測もパースできる"""
        from keiba.cli.formatters.markdown import parse_predictions_markdown as _parse_predictions_markdown

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
        from keiba.cli.formatters.simulation import calculate_fukusho_simulation as _calculate_fukusho_simulation

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
        from keiba.cli.formatters.simulation import calculate_fukusho_simulation as _calculate_fukusho_simulation

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
        from keiba.cli.formatters.simulation import calculate_fukusho_simulation as _calculate_fukusho_simulation

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
        from keiba.cli.formatters.simulation import calculate_fukusho_simulation as _calculate_fukusho_simulation

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
        from keiba.cli.formatters.simulation import calculate_fukusho_simulation as _calculate_fukusho_simulation

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
        from keiba.cli.formatters.simulation import calculate_fukusho_simulation as _calculate_fukusho_simulation

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
        from keiba.cli.formatters.markdown import append_review_to_markdown as _append_review_to_markdown

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
        from keiba.cli.formatters.markdown import append_review_to_markdown as _append_review_to_markdown

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

    @patch("keiba.cli.commands.review.append_review_to_markdown")
    @patch("keiba.cli.commands.review.calculate_fukusho_simulation")
    @patch("keiba.cli.commands.review.parse_predictions_markdown")
    @patch("keiba.cli.commands.review.RaceDetailScraper")
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

    @patch("keiba.cli.commands.review.append_review_to_markdown")
    @patch("keiba.cli.commands.review.calculate_fukusho_simulation")
    @patch("keiba.cli.commands.review.parse_predictions_markdown")
    @patch("keiba.cli.commands.review.RaceDetailScraper")
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

    @patch("keiba.cli.commands.review.append_review_to_markdown")
    @patch("keiba.cli.commands.review.calculate_fukusho_simulation")
    @patch("keiba.cli.commands.review.parse_predictions_markdown")
    @patch("keiba.cli.commands.review.RaceDetailScraper")
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

    @patch("keiba.cli.commands.review.append_review_to_markdown")
    @patch("keiba.cli.commands.review.calculate_fukusho_simulation")
    @patch("keiba.cli.commands.review.parse_predictions_markdown")
    @patch("keiba.cli.commands.review.RaceDetailScraper")
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

    @patch("keiba.cli.commands.review.parse_predictions_markdown")
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


class TestCalculateUmarenSimulation:
    """_calculate_umaren_simulation関数のテスト"""

    def test_generates_three_combinations_from_top3(self):
        """予測上位3頭から3組の馬連を生成する: (1,2), (1,3), (2,3)"""
        from keiba.cli.formatters.simulation import calculate_umaren_simulation as _calculate_umaren_simulation

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
        # 馬連は (5,3), (5,8), (3,8) の3組
        # horse_numbers [5, 3] が的中
        umaren_payouts = {
            1: {"horse_numbers": [5, 3], "payout": 2470},
        }

        result = _calculate_umaren_simulation(predictions, umaren_payouts)

        # 3点買いなので投資額は300円
        assert result["investment"] == 300
        assert result["total_races"] == 1

    def test_hit_when_combination_matches(self):
        """馬連ペアがset()として一致すれば的中"""
        from keiba.cli.formatters.simulation import calculate_umaren_simulation as _calculate_umaren_simulation

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
        # (5, 3) が的中（順序関係なく）
        umaren_payouts = {
            1: {"horse_numbers": [3, 5], "payout": 2470},  # 順序が逆でも的中
        }

        result = _calculate_umaren_simulation(predictions, umaren_payouts)

        assert result["hits"] == 1
        assert result["payout"] == 2470

    def test_miss_when_combination_not_in_predictions(self):
        """馬連ペアが予測3組に含まれない場合は外れ"""
        from keiba.cli.formatters.simulation import calculate_umaren_simulation as _calculate_umaren_simulation

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
        # 7-9 は予測外
        umaren_payouts = {
            1: {"horse_numbers": [7, 9], "payout": 5000},
        }

        result = _calculate_umaren_simulation(predictions, umaren_payouts)

        assert result["hits"] == 0
        assert result["payout"] == 0

    def test_payout_added_once_per_hit(self):
        """的中時は払戻金を1回だけ加算（3点のうち1点のみ的中）"""
        from keiba.cli.formatters.simulation import calculate_umaren_simulation as _calculate_umaren_simulation

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
        umaren_payouts = {
            1: {"horse_numbers": [5, 3], "payout": 2470},
        }

        result = _calculate_umaren_simulation(predictions, umaren_payouts)

        # 払戻金は2470円のみ（複数回加算されない）
        assert result["payout"] == 2470

    def test_calculates_hit_rate(self):
        """的中率を計算する"""
        from keiba.cli.formatters.simulation import calculate_umaren_simulation as _calculate_umaren_simulation

        predictions = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [
                        {"horse_number": 5, "rank": 1},
                        {"horse_number": 3, "rank": 2},
                        {"horse_number": 8, "rank": 3},
                    ],
                },
                {
                    "race_number": 2,
                    "predictions": [
                        {"horse_number": 2, "rank": 1},
                        {"horse_number": 7, "rank": 2},
                        {"horse_number": 1, "rank": 3},
                    ],
                },
            ]
        }
        umaren_payouts = {
            1: {"horse_numbers": [5, 3], "payout": 2470},  # 的中
            2: {"horse_numbers": [9, 10], "payout": 3000},  # 外れ
        }

        result = _calculate_umaren_simulation(predictions, umaren_payouts)

        assert result["hits"] == 1
        assert result["total_races"] == 2
        assert result["hit_rate"] == 0.5

    def test_calculates_return_rate(self):
        """回収率を計算する"""
        from keiba.cli.formatters.simulation import calculate_umaren_simulation as _calculate_umaren_simulation

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
        umaren_payouts = {
            1: {"horse_numbers": [5, 3], "payout": 2470},
        }

        result = _calculate_umaren_simulation(predictions, umaren_payouts)

        # 投資額300円、払戻2470円 = 回収率823.3%
        assert result["investment"] == 300
        assert result["payout"] == 2470
        assert result["return_rate"] == pytest.approx(2470 / 300)

    def test_handles_empty_predictions(self):
        """予測データがない場合は空の結果を返す"""
        from keiba.cli.formatters.simulation import calculate_umaren_simulation as _calculate_umaren_simulation

        predictions = {"races": []}
        umaren_payouts = {}

        result = _calculate_umaren_simulation(predictions, umaren_payouts)

        assert result["total_races"] == 0
        assert result["hits"] == 0
        assert result["investment"] == 0
        assert result["payout"] == 0
        assert result["hit_rate"] == 0.0
        assert result["return_rate"] == 0.0

    def test_skips_race_without_umaren_payout(self):
        """umaren_payoutsにないレースはスキップ"""
        from keiba.cli.formatters.simulation import calculate_umaren_simulation as _calculate_umaren_simulation

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
        umaren_payouts = {}  # 払戻情報なし

        result = _calculate_umaren_simulation(predictions, umaren_payouts)

        assert result["total_races"] == 0

    def test_skips_race_with_less_than_3_predictions(self):
        """予測が3頭未満のレースはスキップ"""
        from keiba.cli.formatters.simulation import calculate_umaren_simulation as _calculate_umaren_simulation

        predictions = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [
                        {"horse_number": 5, "rank": 1},
                        {"horse_number": 3, "rank": 2},
                        # 3頭目がない
                    ],
                }
            ]
        }
        umaren_payouts = {
            1: {"horse_numbers": [5, 3], "payout": 2470},
        }

        result = _calculate_umaren_simulation(predictions, umaren_payouts)

        assert result["total_races"] == 0

    def test_multiple_races_accumulation(self):
        """複数レースの累計を正しく計算する"""
        from keiba.cli.formatters.simulation import calculate_umaren_simulation as _calculate_umaren_simulation

        predictions = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [
                        {"horse_number": 5, "rank": 1},
                        {"horse_number": 3, "rank": 2},
                        {"horse_number": 8, "rank": 3},
                    ],
                },
                {
                    "race_number": 2,
                    "predictions": [
                        {"horse_number": 2, "rank": 1},
                        {"horse_number": 7, "rank": 2},
                        {"horse_number": 1, "rank": 3},
                    ],
                },
                {
                    "race_number": 3,
                    "predictions": [
                        {"horse_number": 4, "rank": 1},
                        {"horse_number": 6, "rank": 2},
                        {"horse_number": 9, "rank": 3},
                    ],
                },
            ]
        }
        umaren_payouts = {
            1: {"horse_numbers": [5, 3], "payout": 2470},  # 的中
            2: {"horse_numbers": [2, 1], "payout": 1500},  # 的中 (2-1)
            3: {"horse_numbers": [10, 11], "payout": 8000},  # 外れ
        }

        result = _calculate_umaren_simulation(predictions, umaren_payouts)

        assert result["total_races"] == 3
        assert result["hits"] == 2
        assert result["investment"] == 900  # 3レース x 3点 x 100円
        assert result["payout"] == 2470 + 1500


class TestCalculateSanrenpukuSimulation:
    """_calculate_sanrenpuku_simulation関数のテスト"""

    def test_generates_one_combination_from_top3(self):
        """予測上位3頭から1組の3連複を生成する: {1,2,3}"""
        from keiba.cli.formatters.simulation import calculate_sanrenpuku_simulation as _calculate_sanrenpuku_simulation

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
        # 3連複は {5, 3, 8} の1組
        sanrenpuku_payouts = {
            1: {"horse_numbers": [5, 3, 8], "payout": 11060},
        }

        result = _calculate_sanrenpuku_simulation(predictions, sanrenpuku_payouts)

        # 1点買いなので投資額は100円
        assert result["investment"] == 100
        assert result["total_races"] == 1

    def test_hit_when_combination_matches(self):
        """3連複トリオがset()として一致すれば的中"""
        from keiba.cli.formatters.simulation import calculate_sanrenpuku_simulation as _calculate_sanrenpuku_simulation

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
        # (8, 3, 5) が的中（順序関係なく）
        sanrenpuku_payouts = {
            1: {"horse_numbers": [8, 3, 5], "payout": 11060},  # 順序が違っても的中
        }

        result = _calculate_sanrenpuku_simulation(predictions, sanrenpuku_payouts)

        assert result["hits"] == 1
        assert result["payout"] == 11060

    def test_miss_when_combination_not_in_predictions(self):
        """3連複トリオが予測と一致しない場合は外れ"""
        from keiba.cli.formatters.simulation import calculate_sanrenpuku_simulation as _calculate_sanrenpuku_simulation

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
        # 7-9-10 は予測外
        sanrenpuku_payouts = {
            1: {"horse_numbers": [7, 9, 10], "payout": 5000},
        }

        result = _calculate_sanrenpuku_simulation(predictions, sanrenpuku_payouts)

        assert result["hits"] == 0
        assert result["payout"] == 0

    def test_miss_when_only_two_horses_match(self):
        """3頭中2頭だけ一致しても外れ"""
        from keiba.cli.formatters.simulation import calculate_sanrenpuku_simulation as _calculate_sanrenpuku_simulation

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
        # 5, 3 は予測内だが、7 は予測外
        sanrenpuku_payouts = {
            1: {"horse_numbers": [5, 3, 7], "payout": 8000},
        }

        result = _calculate_sanrenpuku_simulation(predictions, sanrenpuku_payouts)

        assert result["hits"] == 0
        assert result["payout"] == 0

    def test_calculates_hit_rate(self):
        """的中率を計算する"""
        from keiba.cli.formatters.simulation import calculate_sanrenpuku_simulation as _calculate_sanrenpuku_simulation

        predictions = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [
                        {"horse_number": 5, "rank": 1},
                        {"horse_number": 3, "rank": 2},
                        {"horse_number": 8, "rank": 3},
                    ],
                },
                {
                    "race_number": 2,
                    "predictions": [
                        {"horse_number": 2, "rank": 1},
                        {"horse_number": 7, "rank": 2},
                        {"horse_number": 1, "rank": 3},
                    ],
                },
            ]
        }
        sanrenpuku_payouts = {
            1: {"horse_numbers": [5, 3, 8], "payout": 11060},  # 的中
            2: {"horse_numbers": [9, 10, 11], "payout": 3000},  # 外れ
        }

        result = _calculate_sanrenpuku_simulation(predictions, sanrenpuku_payouts)

        assert result["hits"] == 1
        assert result["total_races"] == 2
        assert result["hit_rate"] == 0.5

    def test_calculates_return_rate(self):
        """回収率を計算する"""
        from keiba.cli.formatters.simulation import calculate_sanrenpuku_simulation as _calculate_sanrenpuku_simulation

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
        sanrenpuku_payouts = {
            1: {"horse_numbers": [5, 3, 8], "payout": 11060},
        }

        result = _calculate_sanrenpuku_simulation(predictions, sanrenpuku_payouts)

        # 投資額100円、払戻11060円 = 回収率11060%
        assert result["investment"] == 100
        assert result["payout"] == 11060
        assert result["return_rate"] == pytest.approx(11060 / 100)

    def test_handles_empty_predictions(self):
        """予測データがない場合は空の結果を返す"""
        from keiba.cli.formatters.simulation import calculate_sanrenpuku_simulation as _calculate_sanrenpuku_simulation

        predictions = {"races": []}
        sanrenpuku_payouts = {}

        result = _calculate_sanrenpuku_simulation(predictions, sanrenpuku_payouts)

        assert result["total_races"] == 0
        assert result["hits"] == 0
        assert result["investment"] == 0
        assert result["payout"] == 0
        assert result["hit_rate"] == 0.0
        assert result["return_rate"] == 0.0

    def test_skips_race_without_sanrenpuku_payout(self):
        """sanrenpuku_payoutsにないレースはスキップ"""
        from keiba.cli.formatters.simulation import calculate_sanrenpuku_simulation as _calculate_sanrenpuku_simulation

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
        sanrenpuku_payouts = {}  # 払戻情報なし

        result = _calculate_sanrenpuku_simulation(predictions, sanrenpuku_payouts)

        assert result["total_races"] == 0

    def test_skips_race_with_less_than_3_predictions(self):
        """予測が3頭未満のレースはスキップ"""
        from keiba.cli.formatters.simulation import calculate_sanrenpuku_simulation as _calculate_sanrenpuku_simulation

        predictions = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [
                        {"horse_number": 5, "rank": 1},
                        {"horse_number": 3, "rank": 2},
                        # 3頭目がない
                    ],
                }
            ]
        }
        sanrenpuku_payouts = {
            1: {"horse_numbers": [5, 3, 8], "payout": 11060},
        }

        result = _calculate_sanrenpuku_simulation(predictions, sanrenpuku_payouts)

        assert result["total_races"] == 0

    def test_multiple_races_accumulation(self):
        """複数レースの累計を正しく計算する"""
        from keiba.cli.formatters.simulation import calculate_sanrenpuku_simulation as _calculate_sanrenpuku_simulation

        predictions = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [
                        {"horse_number": 5, "rank": 1},
                        {"horse_number": 3, "rank": 2},
                        {"horse_number": 8, "rank": 3},
                    ],
                },
                {
                    "race_number": 2,
                    "predictions": [
                        {"horse_number": 2, "rank": 1},
                        {"horse_number": 7, "rank": 2},
                        {"horse_number": 1, "rank": 3},
                    ],
                },
                {
                    "race_number": 3,
                    "predictions": [
                        {"horse_number": 4, "rank": 1},
                        {"horse_number": 6, "rank": 2},
                        {"horse_number": 9, "rank": 3},
                    ],
                },
            ]
        }
        sanrenpuku_payouts = {
            1: {"horse_numbers": [5, 3, 8], "payout": 11060},  # 的中
            2: {"horse_numbers": [2, 7, 1], "payout": 5500},  # 的中
            3: {"horse_numbers": [10, 11, 12], "payout": 8000},  # 外れ
        }

        result = _calculate_sanrenpuku_simulation(predictions, sanrenpuku_payouts)

        assert result["total_races"] == 3
        assert result["hits"] == 2
        assert result["investment"] == 300  # 3レース x 1点 x 100円
        assert result["payout"] == 11060 + 5500


class TestCalculateTanshoSimulation:
    """_calculate_tansho_simulation関数のテスト

    単勝シミュレーション:
    - top1: 予測1位のみに100円賭けた場合
    - top3: 予測1-3位に各100円（計300円）賭けた場合
    """

    def test_top1_hit_when_predicted_first_wins(self):
        """top1: 予測1位が1着で的中と判定する"""
        from keiba.cli.formatters.simulation import calculate_tansho_simulation as _calculate_tansho_simulation

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
        tansho_payouts = {
            1: {"horse_number": 5, "payout": 350},  # 馬番5が1着
        }

        result = _calculate_tansho_simulation(predictions, tansho_payouts)

        assert result["top1"]["hits"] == 1
        assert result["top1"]["total_races"] == 1
        assert result["top1"]["payout"] == 350

    def test_top1_miss_when_predicted_first_not_win(self):
        """top1: 予測1位が1着でない場合はミスと判定する"""
        from keiba.cli.formatters.simulation import calculate_tansho_simulation as _calculate_tansho_simulation

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
        tansho_payouts = {
            1: {"horse_number": 7, "payout": 800},  # 馬番7が1着（予測外）
        }

        result = _calculate_tansho_simulation(predictions, tansho_payouts)

        assert result["top1"]["hits"] == 0
        assert result["top1"]["total_races"] == 1
        assert result["top1"]["payout"] == 0

    def test_top1_investment_calculation(self):
        """top1: 投資額はレース数 x 100円"""
        from keiba.cli.formatters.simulation import calculate_tansho_simulation as _calculate_tansho_simulation

        predictions = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [{"horse_number": 5, "rank": 1}],
                },
                {
                    "race_number": 2,
                    "predictions": [{"horse_number": 3, "rank": 1}],
                },
                {
                    "race_number": 3,
                    "predictions": [{"horse_number": 8, "rank": 1}],
                },
            ]
        }
        tansho_payouts = {
            1: {"horse_number": 5, "payout": 350},
            2: {"horse_number": 7, "payout": 500},
            3: {"horse_number": 8, "payout": 200},
        }

        result = _calculate_tansho_simulation(predictions, tansho_payouts)

        assert result["top1"]["total_races"] == 3
        assert result["top1"]["investment"] == 300  # 3レース x 100円

    def test_top3_hit_when_any_predicted_horse_wins(self):
        """top3: 予測1-3位のいずれかが1着で的中と判定する"""
        from keiba.cli.formatters.simulation import calculate_tansho_simulation as _calculate_tansho_simulation

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
        # 予測2位の馬番3が1着
        tansho_payouts = {
            1: {"horse_number": 3, "payout": 650},
        }

        result = _calculate_tansho_simulation(predictions, tansho_payouts)

        assert result["top3"]["hits"] == 1
        assert result["top3"]["payout"] == 650

    def test_top3_miss_when_no_predicted_horse_wins(self):
        """top3: 予測1-3位のいずれも1着でない場合はミス"""
        from keiba.cli.formatters.simulation import calculate_tansho_simulation as _calculate_tansho_simulation

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
        tansho_payouts = {
            1: {"horse_number": 12, "payout": 1500},  # 予測外の馬が1着
        }

        result = _calculate_tansho_simulation(predictions, tansho_payouts)

        assert result["top3"]["hits"] == 0
        assert result["top3"]["payout"] == 0

    def test_top3_investment_calculation(self):
        """top3: 投資額はレース数 x 300円（3頭に各100円）"""
        from keiba.cli.formatters.simulation import calculate_tansho_simulation as _calculate_tansho_simulation

        predictions = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [
                        {"horse_number": 5, "rank": 1},
                        {"horse_number": 3, "rank": 2},
                        {"horse_number": 8, "rank": 3},
                    ],
                },
                {
                    "race_number": 2,
                    "predictions": [
                        {"horse_number": 2, "rank": 1},
                        {"horse_number": 7, "rank": 2},
                        {"horse_number": 1, "rank": 3},
                    ],
                },
            ]
        }
        tansho_payouts = {
            1: {"horse_number": 5, "payout": 350},
            2: {"horse_number": 9, "payout": 800},
        }

        result = _calculate_tansho_simulation(predictions, tansho_payouts)

        assert result["top3"]["total_races"] == 2
        assert result["top3"]["total_bets"] == 6  # 2レース x 3頭
        assert result["top3"]["investment"] == 600  # 2レース x 300円

    def test_top3_payout_added_once_per_hit(self):
        """top3: 的中時は払戻金を1回だけ加算（予測1位と2位の両方が的中しても1回）"""
        from keiba.cli.formatters.simulation import calculate_tansho_simulation as _calculate_tansho_simulation

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
        # 予測1位の馬番5が1着（単勝は1着のみなので1回のみ的中）
        tansho_payouts = {
            1: {"horse_number": 5, "payout": 350},
        }

        result = _calculate_tansho_simulation(predictions, tansho_payouts)

        # 払戻金は350円のみ（複数回加算されない）
        assert result["top3"]["hits"] == 1
        assert result["top3"]["payout"] == 350

    def test_calculates_hit_rate_for_top1(self):
        """top1: 的中率を計算する"""
        from keiba.cli.formatters.simulation import calculate_tansho_simulation as _calculate_tansho_simulation

        predictions = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [{"horse_number": 5, "rank": 1}],
                },
                {
                    "race_number": 2,
                    "predictions": [{"horse_number": 2, "rank": 1}],
                },
            ]
        }
        tansho_payouts = {
            1: {"horse_number": 5, "payout": 350},  # 1Rは的中
            2: {"horse_number": 7, "payout": 800},  # 2Rは外れ
        }

        result = _calculate_tansho_simulation(predictions, tansho_payouts)

        assert result["top1"]["hits"] == 1
        assert result["top1"]["total_races"] == 2
        assert result["top1"]["hit_rate"] == 0.5  # 50%

    def test_calculates_hit_rate_for_top3(self):
        """top3: 的中率を計算する"""
        from keiba.cli.formatters.simulation import calculate_tansho_simulation as _calculate_tansho_simulation

        predictions = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [
                        {"horse_number": 5, "rank": 1},
                        {"horse_number": 3, "rank": 2},
                        {"horse_number": 8, "rank": 3},
                    ],
                },
                {
                    "race_number": 2,
                    "predictions": [
                        {"horse_number": 2, "rank": 1},
                        {"horse_number": 7, "rank": 2},
                        {"horse_number": 1, "rank": 3},
                    ],
                },
            ]
        }
        tansho_payouts = {
            1: {"horse_number": 3, "payout": 650},  # 1Rは予測2位が1着で的中
            2: {"horse_number": 9, "payout": 800},  # 2Rは外れ
        }

        result = _calculate_tansho_simulation(predictions, tansho_payouts)

        assert result["top3"]["hits"] == 1
        assert result["top3"]["total_races"] == 2
        assert result["top3"]["hit_rate"] == 0.5  # 50%

    def test_calculates_return_rate_for_top1(self):
        """top1: 回収率を計算する"""
        from keiba.cli.formatters.simulation import calculate_tansho_simulation as _calculate_tansho_simulation

        predictions = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [{"horse_number": 5, "rank": 1}],
                },
            ]
        }
        tansho_payouts = {
            1: {"horse_number": 5, "payout": 350},
        }

        result = _calculate_tansho_simulation(predictions, tansho_payouts)

        # 100円賭けて350円返ってきた = 回収率350%
        assert result["top1"]["investment"] == 100
        assert result["top1"]["payout"] == 350
        assert result["top1"]["return_rate"] == 3.5

    def test_calculates_return_rate_for_top3(self):
        """top3: 回収率を計算する"""
        from keiba.cli.formatters.simulation import calculate_tansho_simulation as _calculate_tansho_simulation

        predictions = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [
                        {"horse_number": 5, "rank": 1},
                        {"horse_number": 3, "rank": 2},
                        {"horse_number": 8, "rank": 3},
                    ],
                },
            ]
        }
        tansho_payouts = {
            1: {"horse_number": 5, "payout": 350},
        }

        result = _calculate_tansho_simulation(predictions, tansho_payouts)

        # 300円賭けて350円返ってきた = 回収率116.7%
        assert result["top3"]["investment"] == 300
        assert result["top3"]["payout"] == 350
        assert result["top3"]["return_rate"] == pytest.approx(350 / 300)

    def test_handles_empty_predictions(self):
        """予測データがない場合は空の結果を返す"""
        from keiba.cli.formatters.simulation import calculate_tansho_simulation as _calculate_tansho_simulation

        predictions = {"races": []}
        tansho_payouts = {}

        result = _calculate_tansho_simulation(predictions, tansho_payouts)

        assert result["top1"]["total_races"] == 0
        assert result["top1"]["hits"] == 0
        assert result["top1"]["investment"] == 0
        assert result["top1"]["payout"] == 0
        assert result["top1"]["hit_rate"] == 0.0
        assert result["top1"]["return_rate"] == 0.0
        assert result["top3"]["total_races"] == 0
        assert result["top3"]["total_bets"] == 0
        assert result["top3"]["hits"] == 0
        assert result["top3"]["investment"] == 0
        assert result["top3"]["payout"] == 0
        assert result["top3"]["hit_rate"] == 0.0
        assert result["top3"]["return_rate"] == 0.0

    def test_skips_race_without_tansho_payout(self):
        """tansho_payoutsにないレースはスキップ"""
        from keiba.cli.formatters.simulation import calculate_tansho_simulation as _calculate_tansho_simulation

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
        tansho_payouts = {}  # 払戻情報なし

        result = _calculate_tansho_simulation(predictions, tansho_payouts)

        assert result["top1"]["total_races"] == 0
        assert result["top3"]["total_races"] == 0

    def test_skips_race_with_no_predictions(self):
        """予測がないレースはスキップ"""
        from keiba.cli.formatters.simulation import calculate_tansho_simulation as _calculate_tansho_simulation

        predictions = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [],
                }
            ]
        }
        tansho_payouts = {
            1: {"horse_number": 5, "payout": 350},
        }

        result = _calculate_tansho_simulation(predictions, tansho_payouts)

        assert result["top1"]["total_races"] == 0
        assert result["top3"]["total_races"] == 0

    def test_top3_with_less_than_3_predictions(self):
        """予測が3頭未満のレースはtop3の賭け数がその頭数になる"""
        from keiba.cli.formatters.simulation import calculate_tansho_simulation as _calculate_tansho_simulation

        predictions = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [
                        {"horse_number": 5, "rank": 1},
                        {"horse_number": 3, "rank": 2},
                        # 3頭目がない
                    ],
                }
            ]
        }
        tansho_payouts = {
            1: {"horse_number": 3, "payout": 650},
        }

        result = _calculate_tansho_simulation(predictions, tansho_payouts)

        # top1は通常通り
        assert result["top1"]["total_races"] == 1
        assert result["top1"]["investment"] == 100
        # top3は2頭分（200円）
        assert result["top3"]["total_races"] == 1
        assert result["top3"]["total_bets"] == 2
        assert result["top3"]["investment"] == 200
        assert result["top3"]["hits"] == 1  # 馬番3が的中
        assert result["top3"]["payout"] == 650

    def test_multiple_races_accumulation(self):
        """複数レースの累計を正しく計算する"""
        from keiba.cli.formatters.simulation import calculate_tansho_simulation as _calculate_tansho_simulation

        predictions = {
            "races": [
                {
                    "race_number": 1,
                    "predictions": [
                        {"horse_number": 5, "rank": 1},
                        {"horse_number": 3, "rank": 2},
                        {"horse_number": 8, "rank": 3},
                    ],
                },
                {
                    "race_number": 2,
                    "predictions": [
                        {"horse_number": 2, "rank": 1},
                        {"horse_number": 7, "rank": 2},
                        {"horse_number": 1, "rank": 3},
                    ],
                },
                {
                    "race_number": 3,
                    "predictions": [
                        {"horse_number": 4, "rank": 1},
                        {"horse_number": 6, "rank": 2},
                        {"horse_number": 9, "rank": 3},
                    ],
                },
            ]
        }
        tansho_payouts = {
            1: {"horse_number": 5, "payout": 350},  # top1的中、top3的中
            2: {"horse_number": 7, "payout": 650},  # top1外れ、top3的中（予測2位）
            3: {"horse_number": 10, "payout": 1500},  # top1外れ、top3外れ
        }

        result = _calculate_tansho_simulation(predictions, tansho_payouts)

        # top1
        assert result["top1"]["total_races"] == 3
        assert result["top1"]["hits"] == 1  # 1Rのみ的中
        assert result["top1"]["investment"] == 300
        assert result["top1"]["payout"] == 350
        assert result["top1"]["hit_rate"] == pytest.approx(1 / 3)
        assert result["top1"]["return_rate"] == pytest.approx(350 / 300)

        # top3
        assert result["top3"]["total_races"] == 3
        assert result["top3"]["total_bets"] == 9  # 3レース x 3頭
        assert result["top3"]["hits"] == 2  # 1R, 2Rが的中
        assert result["top3"]["investment"] == 900
        assert result["top3"]["payout"] == 350 + 650
        assert result["top3"]["hit_rate"] == pytest.approx(2 / 3)
        assert result["top3"]["return_rate"] == pytest.approx(1000 / 900)