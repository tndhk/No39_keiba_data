"""BacktestReporterのテスト

TDD: RED -> GREEN -> REFACTOR
"""

import pytest

from keiba.backtest.metrics import PredictionResult, RaceBacktestResult
from keiba.backtest.reporter import BacktestReporter


class TestBacktestReporter:
    """BacktestReporterのテスト"""

    @pytest.fixture
    def reporter(self) -> BacktestReporter:
        """テスト用レポーターを作成"""
        return BacktestReporter(
            start_date="2024-10-01",
            end_date="2024-12-31",
            retrain_interval="weekly",
        )

    @pytest.fixture
    def sample_results(self) -> list[RaceBacktestResult]:
        """テスト用のバックテスト結果を作成"""
        return [
            RaceBacktestResult(
                race_id="202406050811",
                race_date="2024-12-15",
                race_name="有馬記念",
                venue="中山",
                predictions=[
                    PredictionResult(
                        horse_number=7,
                        horse_name="ドウデュース",
                        ml_probability=0.423,
                        ml_rank=1,
                        factor_rank=2,
                        actual_rank=1,
                    ),
                    PredictionResult(
                        horse_number=3,
                        horse_name="スターズオンアース",
                        ml_probability=0.381,
                        ml_rank=2,
                        factor_rank=1,
                        actual_rank=3,
                    ),
                    PredictionResult(
                        horse_number=12,
                        horse_name="ジャスティンパレス",
                        ml_probability=0.315,
                        ml_rank=3,
                        factor_rank=5,
                        actual_rank=2,
                    ),
                ],
            ),
            RaceBacktestResult(
                race_id="202406050810",
                race_date="2024-12-15",
                race_name="中山10R",
                venue="中山",
                predictions=[
                    PredictionResult(
                        horse_number=1,
                        horse_name="テスト馬A",
                        ml_probability=0.350,
                        ml_rank=1,
                        factor_rank=1,
                        actual_rank=2,
                    ),
                    PredictionResult(
                        horse_number=5,
                        horse_name="テスト馬B",
                        ml_probability=0.280,
                        ml_rank=2,
                        factor_rank=3,
                        actual_rank=1,
                    ),
                ],
            ),
        ]

    @pytest.fixture
    def sample_metrics(self) -> dict:
        """テスト用のメトリクスを作成"""
        return {
            "ml": {
                "precision_at_1": 0.325,
                "precision_at_3": 0.582,
                "hit_rate_rank_1": 0.352,
                "hit_rate_rank_2": 0.318,
                "hit_rate_rank_3": 0.284,
            },
            "factor": {
                "precision_at_1": 0.281,
                "precision_at_3": 0.527,
                "hit_rate_rank_1": 0.305,
                "hit_rate_rank_2": 0.273,
                "hit_rate_rank_3": 0.251,
            },
        }


class TestPrintSummary(TestBacktestReporter):
    """print_summaryメソッドのテスト"""

    def test_summary_contains_header(
        self, reporter: BacktestReporter, sample_results: list, sample_metrics: dict
    ):
        """サマリーにヘッダーが含まれる"""
        result = reporter.print_summary(sample_results, sample_metrics)

        assert "バックテスト結果" in result
        assert "2024-10-01" in result
        assert "2024-12-31" in result

    def test_summary_contains_race_count(
        self, reporter: BacktestReporter, sample_results: list, sample_metrics: dict
    ):
        """サマリーに対象レース数が含まれる"""
        result = reporter.print_summary(sample_results, sample_metrics)

        assert "対象レース数" in result
        # sample_resultsには2レース含まれている
        assert "2" in result

    def test_summary_contains_horse_count(
        self, reporter: BacktestReporter, sample_results: list, sample_metrics: dict
    ):
        """サマリーに対象出走馬数が含まれる"""
        result = reporter.print_summary(sample_results, sample_metrics)

        assert "対象出走馬数" in result
        # sample_resultsには合計5頭含まれている
        assert "5" in result

    def test_summary_contains_retrain_interval(
        self, reporter: BacktestReporter, sample_results: list, sample_metrics: dict
    ):
        """サマリーに再学習間隔が含まれる"""
        result = reporter.print_summary(sample_results, sample_metrics)

        assert "再学習間隔" in result
        assert "weekly" in result

    def test_summary_contains_precision_at_1(
        self, reporter: BacktestReporter, sample_results: list, sample_metrics: dict
    ):
        """サマリーにPrecision@1が含まれる"""
        result = reporter.print_summary(sample_results, sample_metrics)

        assert "Precision@1" in result
        # ML: 32.5%, Factor: 28.1%
        assert "32.5%" in result
        assert "28.1%" in result

    def test_summary_contains_precision_at_3(
        self, reporter: BacktestReporter, sample_results: list, sample_metrics: dict
    ):
        """サマリーにPrecision@3が含まれる"""
        result = reporter.print_summary(sample_results, sample_metrics)

        assert "Precision@3" in result
        # ML: 58.2%, Factor: 52.7%
        assert "58.2%" in result
        assert "52.7%" in result

    def test_summary_contains_hit_rate_rank_1(
        self, reporter: BacktestReporter, sample_results: list, sample_metrics: dict
    ):
        """サマリーに1位指名的中率が含まれる"""
        result = reporter.print_summary(sample_results, sample_metrics)

        assert "1位指名" in result
        # ML: 35.2%, Factor: 30.5%
        assert "35.2%" in result
        assert "30.5%" in result

    def test_summary_contains_hit_rate_rank_2(
        self, reporter: BacktestReporter, sample_results: list, sample_metrics: dict
    ):
        """サマリーに2位指名的中率が含まれる"""
        result = reporter.print_summary(sample_results, sample_metrics)

        assert "2位指名" in result
        # ML: 31.8%, Factor: 27.3%
        assert "31.8%" in result
        assert "27.3%" in result

    def test_summary_contains_hit_rate_rank_3(
        self, reporter: BacktestReporter, sample_results: list, sample_metrics: dict
    ):
        """サマリーに3位指名的中率が含まれる"""
        result = reporter.print_summary(sample_results, sample_metrics)

        assert "3位指名" in result
        # ML: 28.4%, Factor: 25.1%
        assert "28.4%" in result
        assert "25.1%" in result

    def test_summary_contains_column_headers(
        self, reporter: BacktestReporter, sample_results: list, sample_metrics: dict
    ):
        """サマリーに列ヘッダーが含まれる"""
        result = reporter.print_summary(sample_results, sample_metrics)

        assert "ML" in result
        assert "ファクター" in result
        assert "差分" in result


class TestPrintRaceDetail(TestBacktestReporter):
    """print_race_detailメソッドのテスト"""

    def test_detail_contains_race_info(
        self, reporter: BacktestReporter, sample_results: list
    ):
        """詳細にレース情報が含まれる"""
        result = reporter.print_race_detail(sample_results[0])

        assert "2024-12-15" in result
        assert "中山" in result
        assert "有馬記念" in result

    def test_detail_contains_column_headers(
        self, reporter: BacktestReporter, sample_results: list
    ):
        """詳細に列ヘッダーが含まれる"""
        result = reporter.print_race_detail(sample_results[0])

        assert "馬番" in result
        assert "馬名" in result
        assert "ML確率" in result or "確率" in result
        assert "着順" in result

    def test_detail_contains_horse_number(
        self, reporter: BacktestReporter, sample_results: list
    ):
        """詳細に馬番が含まれる"""
        result = reporter.print_race_detail(sample_results[0])

        # 上位3頭の馬番: 7, 3, 12
        assert "7" in result
        assert "3" in result
        assert "12" in result

    def test_detail_contains_horse_name(
        self, reporter: BacktestReporter, sample_results: list
    ):
        """詳細に馬名が含まれる"""
        result = reporter.print_race_detail(sample_results[0])

        assert "ドウデュース" in result
        assert "スターズオンアース" in result
        assert "ジャスティンパレス" in result

    def test_detail_contains_ml_probability(
        self, reporter: BacktestReporter, sample_results: list
    ):
        """詳細にML確率が含まれる"""
        result = reporter.print_race_detail(sample_results[0])

        # 42.3%, 38.1%, 31.5%
        assert "42.3%" in result
        assert "38.1%" in result
        assert "31.5%" in result

    def test_detail_contains_actual_rank(
        self, reporter: BacktestReporter, sample_results: list
    ):
        """詳細に着順が含まれる"""
        result = reporter.print_race_detail(sample_results[0])

        # 着順が表示されている（1, 2, 3を含む）
        # これはテーブル形式で出力されるため、着順列の値として存在することを確認
        lines = result.split("\n")
        # ドウデュース（着順1）、スターズオンアース（着順3）、ジャスティンパレス（着順2）
        # が各行に含まれていることを間接的に確認
        assert any("ドウデュース" in line and "1" in line for line in lines)

    def test_detail_contains_hit_marker(
        self, reporter: BacktestReporter, sample_results: list
    ):
        """詳細にHITマーカーが含まれる（3着以内の場合）"""
        result = reporter.print_race_detail(sample_results[0])

        # 3頭とも3着以内なのでHITが3回表示される
        assert result.count("HIT") == 3

    def test_detail_respects_top_k(
        self, reporter: BacktestReporter, sample_results: list
    ):
        """詳細はtop_k件のみ表示"""
        # top_k=2を指定
        result = reporter.print_race_detail(sample_results[0], top_k=2)

        # 上位2頭のみ表示される
        assert "ドウデュース" in result
        assert "スターズオンアース" in result
        # 3位のジャスティンパレスは表示されない
        assert "ジャスティンパレス" not in result


class TestFormatDiff(TestBacktestReporter):
    """_format_diffメソッドのテスト"""

    def test_diff_positive(self, reporter: BacktestReporter):
        """正の差分は+付きでフォーマット"""
        # ML: 0.325, Factor: 0.281 -> diff = 0.044 = +4.4%
        result = BacktestReporter._format_diff(0.325, 0.281)

        assert result.startswith("+")
        assert "4.4%" in result

    def test_diff_negative(self, reporter: BacktestReporter):
        """負の差分は-付きでフォーマット"""
        # ML: 0.250, Factor: 0.300 -> diff = -0.050 = -5.0%
        result = BacktestReporter._format_diff(0.250, 0.300)

        assert result.startswith("-")
        assert "5.0%" in result

    def test_diff_zero(self, reporter: BacktestReporter):
        """差分が0の場合"""
        result = BacktestReporter._format_diff(0.300, 0.300)

        # 0.0%または+0.0%のどちらかで表示
        assert "0.0%" in result

    def test_diff_large_positive(self, reporter: BacktestReporter):
        """大きな正の差分"""
        # ML: 0.500, Factor: 0.300 -> diff = 0.200 = +20.0%
        result = BacktestReporter._format_diff(0.500, 0.300)

        assert result.startswith("+")
        assert "20.0%" in result

    def test_diff_small_positive(self, reporter: BacktestReporter):
        """小さな正の差分"""
        # ML: 0.301, Factor: 0.300 -> diff = 0.001 = +0.1%
        result = BacktestReporter._format_diff(0.301, 0.300)

        assert result.startswith("+")
        assert "0.1%" in result


class TestSummaryFormat(TestBacktestReporter):
    """サマリーのフォーマットテスト"""

    def test_summary_uses_separator_lines(
        self, reporter: BacktestReporter, sample_results: list, sample_metrics: dict
    ):
        """サマリーに区切り線が含まれる"""
        result = reporter.print_summary(sample_results, sample_metrics)

        # 区切り線として===または---が使われている
        assert "=" * 10 in result or "-" * 10 in result

    def test_summary_formats_large_numbers_with_comma(
        self, reporter: BacktestReporter, sample_metrics: dict
    ):
        """大きな数値はカンマ区切りでフォーマット"""
        # 多くのレースを含む結果を作成
        large_results = []
        for i in range(1234):
            large_results.append(
                RaceBacktestResult(
                    race_id=f"race_{i}",
                    race_date="2024-12-15",
                    race_name=f"レース{i}",
                    venue="東京",
                    predictions=[
                        PredictionResult(
                            horse_number=1,
                            horse_name="馬A",
                            ml_probability=0.5,
                            ml_rank=1,
                            factor_rank=1,
                            actual_rank=1,
                        )
                    ],
                )
            )

        result = reporter.print_summary(large_results, sample_metrics)

        # 1234は1,234と表示される
        assert "1,234" in result
