"""PastResultsFactor - 過去成績Factor"""

from keiba.analyzers.factors.base import BaseFactor


class PastResultsFactor(BaseFactor):
    """過去成績に基づくスコア計算

    直近5走の相対着順スコアの加重平均を計算する。
    相対着順スコア = (出走頭数 - 着順 + 1) / 出走頭数 × 100
    """

    name = "past_results"

    def _calculate_relative_score(
        self, finish_position: int, total_runners: int
    ) -> float:
        """相対着順スコアを計算する

        Args:
            finish_position: 着順
            total_runners: 出走頭数

        Returns:
            0-100の範囲のスコア
        """
        return (total_runners - finish_position + 1) / total_runners * 100

    def calculate(
        self, horse_id: str, race_results: list, presorted: bool = False, **kwargs
    ) -> float | None:
        """過去成績スコアを計算する

        Args:
            horse_id: 馬ID
            race_results: レース結果のリスト（horse_id, finish_position, total_runners, race_dateを含む）
            presorted: Trueの場合、race_resultsは既に日付降順でソート済みとみなし、
                       ソート処理をスキップする（デフォルト: False）

        Returns:
            0-100の範囲のスコア、データ不足の場合はNone
        """
        # 対象馬のレースを抽出
        horse_races = [
            r
            for r in race_results
            if r.get("horse_id") == horse_id
            and r.get("finish_position") is not None
            and r.get("finish_position") > 0
        ]

        if not horse_races:
            return None

        # presorted=Falseの場合のみ、日付でソート（新しい順）
        if not presorted:
            horse_races.sort(key=lambda x: x.get("race_date", ""), reverse=True)

        # 直近5走を取得
        recent_races = horse_races[:5]

        # 重み付け（最新の方を重視）
        weights = [0.35, 0.25, 0.20, 0.12, 0.08]
        total_score = 0.0
        total_weight = 0.0

        for i, race in enumerate(recent_races):
            score = self._calculate_relative_score(
                race["finish_position"], race.get("total_runners", 10)
            )
            weight = weights[i] if i < len(weights) else weights[-1]
            total_score += score * weight
            total_weight += weight

        # 正規化
        if total_weight > 0:
            return total_score / total_weight

        return None
