"""RunningStyleFactor - 脚質分析Factor"""

from collections import Counter

from keiba.analyzers.factors.base import BaseFactor


DEFAULT_COURSE_STATS = {
    "escape": 0.15,
    "front": 0.35,
    "stalker": 0.35,
    "closer": 0.15,
}


class RunningStyleFactor(BaseFactor):
    """脚質に基づくスコア計算

    馬の脚質（逃げ/先行/差し/追込）を過去のレース結果から判定し、
    コース別の有利脚質とのマッチ度をスコア化する。
    """

    name = "running_style"

    def _classify_running_style(
        self, passing_order: str | None, total_horses: int
    ) -> str | None:
        """通過順位から脚質を判定する

        Args:
            passing_order: 通過順位（例："1-1-1-1"、"5-5-4-3"）
            total_horses: 出走頭数

        Returns:
            脚質（"escape", "front", "stalker", "closer"）、判定不可の場合はNone
        """
        if not passing_order or total_horses == 0:
            return None

        try:
            first_corner = int(passing_order.split("-")[0])
        except (ValueError, IndexError):
            return None

        position_ratio = first_corner / total_horses

        if position_ratio <= 0.15:
            return "escape"
        elif position_ratio <= 0.40:
            return "front"
        elif position_ratio <= 0.70:
            return "stalker"
        else:
            return "closer"

    def _get_horse_tendency(
        self, horse_id: str, race_results: list
    ) -> str | None:
        """馬の脚質傾向を判定する

        過去5走の脚質から最も頻出する脚質を傾向として返す。

        Args:
            horse_id: 馬ID
            race_results: レース結果のリスト

        Returns:
            脚質傾向、判定不可の場合はNone
        """
        horse_races = [
            r for r in race_results
            if r.get("horse_id") == horse_id
            and r.get("passing_order")
            and r.get("total_runners")
        ]

        if not horse_races:
            return None

        recent_races = horse_races[:5]

        styles = []
        for race in recent_races:
            style = self._classify_running_style(
                race.get("passing_order"),
                race.get("total_runners", 18),
            )
            if style:
                styles.append(style)

        if not styles:
            return None

        counter = Counter(styles)
        return counter.most_common(1)[0][0]

    def calculate(
        self, horse_id: str, race_results: list, **kwargs
    ) -> float | None:
        """脚質適性スコアを計算する

        馬の脚質傾向とコース統計から、その脚質がコースで有利かどうかを
        スコア化して返す。

        Args:
            horse_id: 馬ID
            race_results: レース結果のリスト
            **kwargs: 追加パラメータ
                - course_stats: コース別脚質勝率統計（オプション）

        Returns:
            0-100の範囲のスコア、データ不足の場合はNone
        """
        tendency = self._get_horse_tendency(horse_id, race_results)
        if tendency is None:
            return None

        course_stats = kwargs.get("course_stats", DEFAULT_COURSE_STATS)

        win_rate = course_stats.get(tendency, 0.25)

        # スコアを0-100に正規化
        # 勝率5%を0点、40%を100点として線形変換
        score = min(100, max(0, (win_rate - 0.05) / 0.35 * 100))

        return round(score, 1)
