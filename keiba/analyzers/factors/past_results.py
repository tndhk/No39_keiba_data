"""PastResultsFactor - 過去成績Factor"""

from keiba.analyzers.factors.base import BaseFactor
from keiba.utils.grade_extractor import extract_grade


class PastResultsFactor(BaseFactor):
    """過去成績に基づくスコア計算

    直近5走の相対着順スコアの加重平均を計算する。
    相対着順スコア = (出走頭数 - 着順 + 1) / 出走頭数 × 100
    レースクラス別の補正係数を適用する。
    """

    name = "past_results"

    # レースクラス別補正係数
    GRADE_MULTIPLIERS = {
        "G1": 1.5,
        "G2": 1.3,
        "G3": 1.2,
        "Jpn1": 1.4,
        "Jpn2": 1.2,
        "Jpn3": 1.1,
        "L": 1.1,
        "OP": 1.1,
        "3WIN": 1.0,
        "2WIN": 0.95,
        "1WIN": 0.9,
        "MAIDEN": 0.8,
        "DEBUT": 0.7,
    }

    def _calculate_relative_score(
        self, finish_position: int, total_runners: int, race_name: str | None = None
    ) -> float:
        """相対着順スコアを計算する

        Args:
            finish_position: 着順
            total_runners: 出走頭数
            race_name: レース名（グレード判定用）

        Returns:
            0-100の範囲のスコア（クラス補正適用後、上限100）
        """
        # 基本スコア
        base_score = (total_runners - finish_position + 1) / total_runners * 100

        # レースクラス補正
        if race_name:
            grade = extract_grade(race_name)
            multiplier = self.GRADE_MULTIPLIERS.get(grade, 1.0)
            score = base_score * multiplier
            # 上限100点
            return min(score, 100.0)

        return base_score

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
                race["finish_position"],
                race.get("total_runners", 10),
                race.get("race_name"),
            )
            weight = weights[i] if i < len(weights) else weights[-1]
            total_score += score * weight
            total_weight += weight

        # 正規化
        if total_weight > 0:
            return total_score / total_weight

        return None
