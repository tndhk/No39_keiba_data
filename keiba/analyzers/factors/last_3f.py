"""Last3FFactor - 上がり3F Factor"""

from keiba.analyzers.factors.base import BaseFactor


class Last3FFactor(BaseFactor):
    """上がり3Fに基づくスコア計算

    直近の上がり3Fタイムからスコアを算出する。
    速いほど高スコア。
    """

    name = "last_3f"

    def calculate(self, horse_id: str, race_results: list, **kwargs) -> float | None:
        """上がり3Fスコアを計算する

        Args:
            horse_id: 馬ID
            race_results: レース結果のリスト

        Returns:
            0-100の範囲のスコア、データ不足の場合はNone
        """
        # 対象馬の上がり3Fデータを抽出
        horse_last_3f = [
            r.get("last_3f")
            for r in race_results
            if r.get("horse_id") == horse_id and r.get("last_3f") is not None
        ]

        if not horse_last_3f:
            return None

        # 直近3走の平均（あれば）
        recent_last_3f = horse_last_3f[:3]
        avg_last_3f = sum(recent_last_3f) / len(recent_last_3f)

        # スコア計算
        # 基準: 33秒を100点、38秒を0点とする線形スケール
        # スコア = (38 - タイム) / (38 - 33) * 100
        score = (38 - avg_last_3f) / 5 * 100

        # 0-100に正規化
        return max(0, min(100, round(score, 1)))
