"""Integration tests for predict-day and review-day commands.

This module contains integration tests that verify:
1. predict-day and review-day work together correctly
2. RaceDetailScraper.fetch_payouts parses payouts correctly
3. End-to-end scenarios with mocked data
"""

import re
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from keiba.cli import (
    _append_review_to_markdown,
    _calculate_fukusho_simulation,
    _parse_predictions_markdown,
    _save_predictions_markdown,
    main,
)
from keiba.scrapers.race_detail import RaceDetailScraper


class TestPredictDayReviewDayIntegration:
    """predict-dayとreview-dayの連携テスト"""

    def test_predict_generates_markdown_that_review_can_parse(self, tmp_path):
        """predict-dayで生成したMarkdownをreview-dayがパースできる"""
        predictions_data = [
            {
                "race_number": 1,
                "race_name": "未勝利",
                "surface": "芝",
                "distance": 2000,
                "predictions": [
                    {
                        "rank": 1,
                        "horse_number": 5,
                        "horse_name": "テストホース1",
                        "ml_probability": 0.65,
                        "total_score": 75.5,
                    },
                    {
                        "rank": 2,
                        "horse_number": 3,
                        "horse_name": "テストホース2",
                        "ml_probability": 0.45,
                        "total_score": 65.0,
                    },
                    {
                        "rank": 3,
                        "horse_number": 8,
                        "horse_name": "テストホース3",
                        "ml_probability": 0.30,
                        "total_score": 55.0,
                    },
                ],
            },
            {
                "race_number": 2,
                "race_name": "1勝クラス",
                "surface": "ダート",
                "distance": 1200,
                "predictions": [
                    {
                        "rank": 1,
                        "horse_number": 2,
                        "horse_name": "ダートホース1",
                        "ml_probability": 0.55,
                        "total_score": 70.0,
                    },
                    {
                        "rank": 2,
                        "horse_number": 7,
                        "horse_name": "ダートホース2",
                        "ml_probability": 0.40,
                        "total_score": 60.0,
                    },
                    {
                        "rank": 3,
                        "horse_number": 1,
                        "horse_name": "ダートホース3",
                        "ml_probability": 0.25,
                        "total_score": 50.0,
                    },
                ],
            },
        ]

        output_dir = tmp_path / "predictions"
        output_dir.mkdir(parents=True)

        # predict-dayでMarkdownを生成
        filepath = _save_predictions_markdown(
            predictions_data,
            date_str="2026-01-24",
            venue="中山",
            output_dir=str(output_dir),
        )

        # review-dayでパース
        parsed = _parse_predictions_markdown(filepath)

        assert len(parsed["races"]) == 2
        assert parsed["races"][0]["race_number"] == 1
        assert parsed["races"][0]["predictions"][0]["horse_number"] == 5
        assert parsed["races"][1]["race_number"] == 2
        assert parsed["races"][1]["predictions"][0]["horse_number"] == 2

    def test_review_appends_to_prediction_file(self, tmp_path):
        """review-dayが予測ファイルに検証結果を追記する"""
        # 予測ファイルを作成
        predictions_data = [
            {
                "race_number": 1,
                "race_name": "テストレース",
                "surface": "芝",
                "distance": 2000,
                "predictions": [
                    {
                        "rank": 1,
                        "horse_number": 5,
                        "horse_name": "テストホース",
                        "ml_probability": 0.65,
                        "total_score": 75.5,
                    }
                ],
            }
        ]

        output_dir = tmp_path / "predictions"
        output_dir.mkdir(parents=True)

        filepath = _save_predictions_markdown(
            predictions_data,
            date_str="2026-01-24",
            venue="中山",
            output_dir=str(output_dir),
        )

        # 検証結果を追記
        review_data = {
            "top1": {
                "hits": 1,
                "total_races": 1,
                "hit_rate": 1.0,
                "payout": 150,
                "investment": 100,
                "return_rate": 1.5,
            },
            "top3": {
                "hits": 1,
                "total_bets": 1,
                "hit_rate": 1.0,
                "payout": 150,
                "investment": 100,
                "return_rate": 1.5,
            },
            "race_results": [
                {
                    "race_number": 1,
                    "actual_top3": [5, 3, 1],
                    "predicted_top3": [5],
                    "top1_hit": True,
                    "top3_hits": 1,
                }
            ],
        }

        _append_review_to_markdown(filepath, review_data)

        # ファイル内容を確認
        content = Path(filepath).read_text(encoding="utf-8")

        # 検証結果セクションが追記されている
        assert "## 検証結果" in content
        assert "検証日時:" in content
        assert "的中率: 100.0%" in content
        assert "回収率: 150.0%" in content
        assert "### レース別結果" in content

    def test_full_workflow_with_multiple_races(self, tmp_path):
        """複数レースでの完全なワークフローテスト"""
        # 5レース分の予測データ
        predictions_data = [
            {
                "race_number": i,
                "race_name": f"レース{i}",
                "surface": "芝" if i % 2 == 0 else "ダート",
                "distance": 1600 + (i * 200),
                "predictions": [
                    {
                        "rank": j,
                        "horse_number": j * i + 1,
                        "horse_name": f"馬{j}_{i}",
                        "ml_probability": 0.5 - (j * 0.1),
                        "total_score": 80 - (j * 10),
                    }
                    for j in range(1, 4)
                ],
            }
            for i in range(1, 6)
        ]

        output_dir = tmp_path / "predictions"
        output_dir.mkdir(parents=True)

        # predict-dayでMarkdownを生成
        filepath = _save_predictions_markdown(
            predictions_data,
            date_str="2026-01-24",
            venue="中山",
            output_dir=str(output_dir),
        )

        # パース
        parsed = _parse_predictions_markdown(filepath)
        assert len(parsed["races"]) == 5

        # 実際の結果（一部的中）
        actual_results = {
            1: [2, 3, 4],  # 1位的中
            2: [7, 8, 9],  # 外れ
            3: [4, 8, 12],  # 1位的中
            4: [13, 14, 15],  # 外れ
            5: [6, 12, 18],  # 1位的中
        }
        payouts = {
            1: {2: 150, 3: 200, 4: 300},
            2: {7: 120, 8: 180, 9: 250},
            3: {4: 140, 8: 220, 12: 280},
            4: {13: 130, 14: 190, 15: 260},
            5: {6: 160, 12: 210, 18: 290},
        }

        # シミュレーション計算
        review_data = _calculate_fukusho_simulation(parsed, actual_results, payouts)

        # 5レース中3レース的中
        assert review_data["top1"]["total_races"] == 5
        assert review_data["top1"]["hits"] == 3
        assert review_data["top1"]["hit_rate"] == 0.6  # 60%

        # 払戻金の確認（的中したレースの1位馬の払戻金合計）
        # 1R: 馬番2=150, 3R: 馬番4=140, 5R: 馬番6=160
        assert review_data["top1"]["payout"] == 150 + 140 + 160


class TestFetchPayoutsIntegration:
    """RaceDetailScraper.fetch_payouts の統合テスト"""

    def test_parses_multiple_fukusho_payouts_correctly(self):
        """複数馬の払戻金が正しくパースされる"""
        html = """
        <html>
        <dl class="pay_block">
        <table class="pay_table_01">
        <tr>
        <th class="fuku">複勝</th>
        <td>5<br />3<br />8</td>
        <td class="txt_r">150<br />280<br />320</td>
        </tr>
        </table>
        </dl>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, "fetch", return_value=html):
            result = scraper.fetch_payouts("202401010101")

        assert len(result) == 3
        assert result[0] == {"horse_number": 5, "payout": 150}
        assert result[1] == {"horse_number": 3, "payout": 280}
        assert result[2] == {"horse_number": 8, "payout": 320}

    def test_handles_empty_payout_table(self):
        """空の払戻金テーブルを正しく処理する"""
        html = """
        <html>
        <body>
        <div>No payout data</div>
        </body>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, "fetch", return_value=html):
            result = scraper.fetch_payouts("202401010101")

        assert result == []

    def test_horse_number_payout_pairs_are_correct(self):
        """馬番と払戻金のペアが正しく抽出される"""
        html = """
        <html>
        <dl class="pay_block">
        <table class="pay_table_01">
        <tr>
        <th class="fuku">複勝</th>
        <td>11<br />2<br />14</td>
        <td class="txt_r">180<br />2,450<br />530</td>
        </tr>
        </table>
        </dl>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, "fetch", return_value=html):
            result = scraper.fetch_payouts("202401010101")

        # 順序を確認
        assert result[0]["horse_number"] == 11
        assert result[0]["payout"] == 180

        assert result[1]["horse_number"] == 2
        assert result[1]["payout"] == 2450  # カンマが除去されている

        assert result[2]["horse_number"] == 14
        assert result[2]["payout"] == 530

    def test_handles_high_value_payouts(self):
        """高額払戻金（カンマ区切り）を正しく処理する"""
        html = """
        <html>
        <dl class="pay_block">
        <table class="pay_table_01">
        <tr>
        <th class="fuku">複勝</th>
        <td>16</td>
        <td class="txt_r">12,345</td>
        </tr>
        </table>
        </dl>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, "fetch", return_value=html):
            result = scraper.fetch_payouts("202401010101")

        assert result[0]["payout"] == 12345

    def test_handles_single_horse_fukusho(self):
        """単一馬の複勝払戻金を正しく処理する"""
        html = """
        <html>
        <dl class="pay_block">
        <table class="pay_table_01">
        <tr>
        <th class="fuku">複勝</th>
        <td>7</td>
        <td class="txt_r">210</td>
        </tr>
        </table>
        </dl>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, "fetch", return_value=html):
            result = scraper.fetch_payouts("202401010101")

        assert len(result) == 1
        assert result[0] == {"horse_number": 7, "payout": 210}


class TestEndToEndScenario:
    """エンドツーエンドのシナリオテスト"""

    @patch("keiba.cli._save_predictions_markdown")
    @patch("keiba.services.prediction_service.PredictionService")
    @patch("keiba.scrapers.shutuba.ShutubaScraper")
    @patch("keiba.cli.RaceListScraper")
    @patch("keiba.cli.get_session")
    @patch("keiba.cli.get_engine")
    def test_predict_day_to_review_day_flow(
        self,
        mock_get_engine,
        mock_get_session,
        mock_race_list_scraper,
        mock_shutuba_scraper,
        mock_prediction_service,
        mock_save_markdown,
        tmp_path,
    ):
        """predict-dayからreview-dayまでの流れを確認する"""
        # Setup predict-day mocks
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_list_scraper = MagicMock()
        mock_list_scraper.fetch_race_urls.return_value = [
            "https://db.netkeiba.com/race/202606010801/",
            "https://db.netkeiba.com/race/202606010802/",
        ]
        mock_race_list_scraper.return_value = mock_list_scraper

        mock_shutuba = MagicMock()
        mock_shutuba.fetch_shutuba.side_effect = [
            MagicMock(
                race_id="202606010801",
                race_name="1R テスト",
                race_number=1,
                course="中山",
                distance=2000,
                surface="芝",
                date="2026年1月24日",
                entries=(),
            ),
            MagicMock(
                race_id="202606010802",
                race_name="2R テスト",
                race_number=2,
                course="中山",
                distance=1600,
                surface="ダート",
                date="2026年1月24日",
                entries=(),
            ),
        ]
        mock_shutuba_scraper.return_value = mock_shutuba

        mock_service = MagicMock()
        mock_prediction1 = MagicMock()
        mock_prediction1.rank = 1
        mock_prediction1.horse_number = 5
        mock_prediction1.horse_name = "テストホース1"
        mock_prediction1.ml_probability = 0.65
        mock_prediction1.total_score = 75.5

        mock_prediction2 = MagicMock()
        mock_prediction2.rank = 1
        mock_prediction2.horse_number = 2
        mock_prediction2.horse_name = "テストホース2"
        mock_prediction2.ml_probability = 0.55
        mock_prediction2.total_score = 70.0

        mock_service.predict_from_shutuba.side_effect = [
            [mock_prediction1],
            [mock_prediction2],
        ]
        mock_prediction_service.return_value = mock_service

        # Run predict-day
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "predict-day",
                    "--date",
                    "2026-01-24",
                    "--venue",
                    "中山",
                    "--db",
                    "test.db",
                ],
            )

        # Verify predict-day succeeded
        assert mock_save_markdown.called
        call_kwargs = mock_save_markdown.call_args.kwargs
        assert call_kwargs["date_str"] == "2026-01-24"
        assert call_kwargs["venue"] == "中山"

    @patch("keiba.cli._append_review_to_markdown")
    @patch("keiba.cli._calculate_fukusho_simulation")
    @patch("keiba.cli._parse_predictions_markdown")
    @patch("keiba.cli.RaceDetailScraper")
    def test_review_day_with_real_results(
        self,
        mock_scraper_class,
        mock_parse,
        mock_calculate,
        mock_append,
        tmp_path,
    ):
        """review-dayが実際の結果を取得して検証する"""
        # 予測データを設定
        mock_parse.return_value = {
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

        # 検証結果を設定
        mock_calculate.return_value = {
            "top1": {
                "hits": 1,
                "total_races": 2,
                "hit_rate": 0.5,
                "payout": 150,
                "investment": 200,
                "return_rate": 0.75,
            },
            "top3": {
                "hits": 4,
                "total_bets": 6,
                "hit_rate": 0.667,
                "payout": 580,
                "investment": 600,
                "return_rate": 0.967,
            },
            "race_results": [
                {
                    "race_number": 1,
                    "actual_top3": [5, 3, 1],
                    "predicted_top3": [5, 3, 8],
                    "top1_hit": True,
                    "top3_hits": 2,
                },
                {
                    "race_number": 2,
                    "actual_top3": [7, 8, 9],
                    "predicted_top3": [2, 7, 1],
                    "top1_hit": False,
                    "top3_hits": 1,
                },
            ],
        }

        mock_scraper = MagicMock()
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
            (predictions_dir / "2026-01-24-nakayama.md").write_text(
                "# Test", encoding="utf-8"
            )

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

        # 検証関数が呼ばれたことを確認
        mock_append.assert_called_once()
        assert "的中率" in result.output or "回収率" in result.output


class TestMarkdownFormatValidation:
    """Markdownフォーマットの検証テスト"""

    def test_prediction_markdown_format_is_valid(self, tmp_path):
        """予測Markdownのフォーマットが正しい"""
        predictions_data = [
            {
                "race_number": 1,
                "race_name": "テストレース",
                "surface": "芝",
                "distance": 2000,
                "predictions": [
                    {
                        "rank": 1,
                        "horse_number": 5,
                        "horse_name": "テストホース",
                        "ml_probability": 0.65,
                        "total_score": 75.5,
                    }
                ],
            }
        ]

        output_dir = tmp_path / "predictions"
        output_dir.mkdir(parents=True)

        filepath = _save_predictions_markdown(
            predictions_data,
            date_str="2026-01-24",
            venue="中山",
            output_dir=str(output_dir),
        )

        content = Path(filepath).read_text(encoding="utf-8")

        # 必須要素を確認
        assert "# 2026-01-24 中山 予測結果" in content
        assert "生成日時:" in content
        assert "## 1R テストレース" in content
        assert "芝2000m" in content
        assert "| 順位 | 馬番 | 馬名 | ML確率 | 総合 |" in content
        assert "| 1 | 5 | テストホース | 65.0% | 75.5 |" in content

    def test_review_markdown_format_is_valid(self, tmp_path):
        """検証結果のMarkdownフォーマットが正しい"""
        original_content = "# 2026-01-24 中山 予測結果\n\n"
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
                {
                    "race_number": 2,
                    "actual_top3": [7, 8, 9],
                    "predicted_top3": [2, 7, 1],
                    "top1_hit": False,
                    "top3_hits": 1,
                },
            ],
        }

        _append_review_to_markdown(str(filepath), review_data)

        content = filepath.read_text(encoding="utf-8")

        # 検証結果セクションの必須要素
        assert "---" in content
        assert "## 検証結果" in content
        assert "### 複勝シミュレーション" in content
        assert "#### 予測1位のみに賭けた場合" in content
        assert "#### 予測1-3位に各100円賭けた場合" in content
        assert "### レース別結果" in content
        assert "| R | 実際の3着以内 | 予測Top3 | Top1的中 | Top3的中数 |" in content

    def test_markdown_table_rows_are_correct(self, tmp_path):
        """Markdownテーブルの行が正しい形式"""
        original_content = "# Test\n"
        filepath = tmp_path / "test.md"
        filepath.write_text(original_content, encoding="utf-8")

        review_data = {
            "top1": {
                "hits": 1,
                "total_races": 2,
                "hit_rate": 0.5,
                "payout": 150,
                "investment": 200,
                "return_rate": 0.75,
            },
            "top3": {
                "hits": 3,
                "total_bets": 6,
                "hit_rate": 0.5,
                "payout": 450,
                "investment": 600,
                "return_rate": 0.75,
            },
            "race_results": [
                {
                    "race_number": 1,
                    "actual_top3": [5, 3, 1],
                    "predicted_top3": [5, 8, 3],
                    "top1_hit": True,
                    "top3_hits": 2,
                },
                {
                    "race_number": 2,
                    "actual_top3": [7, 8, 9],
                    "predicted_top3": [2, 7, 1],
                    "top1_hit": False,
                    "top3_hits": 1,
                },
            ],
        }

        _append_review_to_markdown(str(filepath), review_data)

        content = filepath.read_text(encoding="utf-8")

        # レース結果テーブルの行を確認
        assert "| 1 | 5, 3, 1 | 5, 8, 3 | O | 2 |" in content
        assert "| 2 | 7, 8, 9 | 2, 7, 1 | X | 1 |" in content


class TestSimulationCalculation:
    """シミュレーション計算の検証テスト"""

    def test_investment_calculation_is_correct(self):
        """投資額の計算が正しい"""
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
        actual_results = {
            1: [5, 3, 1],
            2: [2, 7, 9],
        }
        payouts = {
            1: {5: 150, 3: 280, 1: 320},
            2: {2: 200, 7: 350, 9: 400},
        }

        result = _calculate_fukusho_simulation(predictions, actual_results, payouts)

        # Top1: 2レース x 100円 = 200円
        assert result["top1"]["investment"] == 200

        # Top3: 2レース x 3頭 x 100円 = 600円
        assert result["top3"]["investment"] == 600

    def test_payout_calculation_is_correct(self):
        """払戻額の計算が正しい"""
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
            1: [5, 3, 1],  # 5と3が的中、8は外れ
        }
        payouts = {
            1: {5: 150, 3: 280, 1: 320},
        }

        result = _calculate_fukusho_simulation(predictions, actual_results, payouts)

        # Top1: 5番が的中 = 150円
        assert result["top1"]["payout"] == 150

        # Top3: 5番(150) + 3番(280) + 8番(0) = 430円
        assert result["top3"]["payout"] == 430

    def test_handles_no_hits_correctly(self):
        """全て外れた場合の処理が正しい"""
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
            1: [10, 11, 12],  # 全て外れ
        }
        payouts = {
            1: {10: 150, 11: 280, 12: 320},
        }

        result = _calculate_fukusho_simulation(predictions, actual_results, payouts)

        assert result["top1"]["hits"] == 0
        assert result["top1"]["payout"] == 0
        assert result["top1"]["return_rate"] == 0.0

        assert result["top3"]["hits"] == 0
        assert result["top3"]["payout"] == 0
        assert result["top3"]["return_rate"] == 0.0

    def test_handles_all_hits_correctly(self):
        """全て的中した場合の処理が正しい"""
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
            1: [5, 3, 8],  # 全て的中
        }
        payouts = {
            1: {5: 150, 3: 280, 8: 320},
        }

        result = _calculate_fukusho_simulation(predictions, actual_results, payouts)

        assert result["top1"]["hits"] == 1
        assert result["top3"]["hits"] == 3
        assert result["top3"]["payout"] == 150 + 280 + 320
