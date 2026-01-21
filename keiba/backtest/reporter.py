"""バックテスト結果レポーターモジュール

ML予測と7ファクター予測のバックテスト結果を整形して出力する
"""

from keiba.backtest.metrics import RaceBacktestResult


class BacktestReporter:
    """バックテスト結果のレポート出力"""

    def __init__(
        self,
        start_date: str,
        end_date: str,
        retrain_interval: str = "weekly",
    ):
        """初期化

        Args:
            start_date: バックテスト開始日
            end_date: バックテスト終了日
            retrain_interval: 再学習間隔
        """
        self.start_date = start_date
        self.end_date = end_date
        self.retrain_interval = retrain_interval

    def print_summary(
        self,
        results: list[RaceBacktestResult],
        metrics: dict,
    ) -> str:
        """サマリーを生成して返す

        Args:
            results: バックテスト結果
            metrics: MetricsCalculator.calculate()の結果

        Returns:
            フォーマットされたサマリー文字列
        """
        # 統計情報を計算
        race_count = len(results)
        horse_count = sum(len(r.predictions) for r in results)

        # メトリクス値を取得
        ml = metrics["ml"]
        factor = metrics["factor"]

        # ヘッダー
        lines = [
            "=" * 80,
            f"バックテスト結果: {self.start_date} ~ {self.end_date}",
            "=" * 80,
            f"対象レース数: {race_count:,}",
            f"対象出走馬数: {horse_count:,}",
            f"再学習間隔: {self.retrain_interval}",
            "",
            "-" * 80,
            f"{'':21}|{'ML予測':^12}|{'7ファクター':^12}|{'差分':^8}",
            "-" * 80,
        ]

        # Precision@k
        lines.append(
            f"{'Precision@1':21}|"
            f"{ml['precision_at_1'] * 100:>10.1f}% |"
            f"{factor['precision_at_1'] * 100:>10.1f}% |"
            f"{self._format_diff(ml['precision_at_1'], factor['precision_at_1']):>8}"
        )
        lines.append(
            f"{'Precision@3':21}|"
            f"{ml['precision_at_3'] * 100:>10.1f}% |"
            f"{factor['precision_at_3'] * 100:>10.1f}% |"
            f"{self._format_diff(ml['precision_at_3'], factor['precision_at_3']):>8}"
        )

        lines.append("-" * 80)

        # 的中率
        lines.append(
            f"{'1位指名 的中率':21}|"
            f"{ml['hit_rate_rank_1'] * 100:>10.1f}% |"
            f"{factor['hit_rate_rank_1'] * 100:>10.1f}% |"
            f"{self._format_diff(ml['hit_rate_rank_1'], factor['hit_rate_rank_1']):>8}"
        )
        lines.append(
            f"{'2位指名 的中率':21}|"
            f"{ml['hit_rate_rank_2'] * 100:>10.1f}% |"
            f"{factor['hit_rate_rank_2'] * 100:>10.1f}% |"
            f"{self._format_diff(ml['hit_rate_rank_2'], factor['hit_rate_rank_2']):>8}"
        )
        lines.append(
            f"{'3位指名 的中率':21}|"
            f"{ml['hit_rate_rank_3'] * 100:>10.1f}% |"
            f"{factor['hit_rate_rank_3'] * 100:>10.1f}% |"
            f"{self._format_diff(ml['hit_rate_rank_3'], factor['hit_rate_rank_3']):>8}"
        )

        lines.append("-" * 80)

        return "\n".join(lines)

    def print_race_detail(
        self,
        result: RaceBacktestResult,
        top_k: int = 3,
    ) -> str:
        """1レースの詳細を生成して返す

        Args:
            result: 1レースのバックテスト結果
            top_k: 上位何頭まで表示するか

        Returns:
            フォーマットされた詳細文字列
        """
        lines = []

        # レース情報ヘッダー
        lines.append(f"{result.race_date} {result.venue} {result.race_name}")

        # テーブルヘッダー
        lines.append(
            f"{'馬番':>4} | {'馬名':^16} | {'ML確率':>6} | "
            f"{'ML順':>4} | {'FS順':>4} | {'着順':>4} | {'結果':^4}"
        )
        lines.append("-" * 70)

        # ML順でソートして上位k頭を取得
        sorted_predictions = sorted(
            [p for p in result.predictions if p.ml_rank is not None],
            key=lambda p: p.ml_rank,
        )
        top_predictions = sorted_predictions[:top_k]

        # 各馬の情報を出力
        for pred in top_predictions:
            hit_marker = "HIT" if pred.actual_rank <= 3 else ""
            prob_str = (
                f"{pred.ml_probability * 100:.1f}%"
                if pred.ml_probability is not None
                else "-"
            )

            lines.append(
                f"{pred.horse_number:>4} | {pred.horse_name:^16} | {prob_str:>6} | "
                f"{pred.ml_rank:>4} | {pred.factor_rank:>4} | "
                f"{pred.actual_rank:>4} | {hit_marker:^4}"
            )

        return "\n".join(lines)

    @staticmethod
    def _format_diff(ml_value: float, factor_value: float) -> str:
        """差分を+/-付きでフォーマット

        Args:
            ml_value: ML予測の値
            factor_value: 7ファクターの値

        Returns:
            "+X.X%" または "-X.X%" 形式の文字列
        """
        diff = (ml_value - factor_value) * 100
        sign = "+" if diff >= 0 else ""
        return f"{sign}{diff:.1f}%"
