"""CourseFitFactor - コース適性Factor"""

from keiba.analyzers.factors.base import BaseFactor


class CourseFitFactor(BaseFactor):
    """コース適性に基づくスコア計算

    同条件（芝/ダート × 距離帯）での3着内率を計算する。
    """

    name = "course_fit"

    def _get_distance_band(self, distance: int) -> str:
        """距離帯を判定する

        Args:
            distance: 距離（メートル）

        Returns:
            距離帯（short/mile/middle/long）
        """
        if distance <= 1400:
            return "short"
        elif distance <= 1800:
            return "mile"
        elif distance <= 2200:
            return "middle"
        else:
            return "long"

    def calculate(
        self,
        horse_id: str,
        race_results: list,
        target_surface: str | None = None,
        target_distance: int | None = None,
        **kwargs,
    ) -> float | None:
        """コース適性スコアを計算する

        Args:
            horse_id: 馬ID
            race_results: レース結果のリスト
            target_surface: 対象馬場（芝/ダート）
            target_distance: 対象距離

        Returns:
            0-100の範囲のスコア（3着内率×100）、データ不足の場合はNone
        """
        if target_surface is None or target_distance is None:
            return None

        target_band = self._get_distance_band(target_distance)

        # 同条件のレースを抽出
        matching_races = [
            r
            for r in race_results
            if r.get("horse_id") == horse_id
            and r.get("surface") == target_surface
            and self._get_distance_band(r.get("distance", 0)) == target_band
            and r.get("finish_position") is not None
            and r.get("finish_position") > 0
        ]

        if not matching_races:
            return None

        # 3着内率を計算
        top3_count = sum(1 for r in matching_races if r["finish_position"] <= 3)
        top3_rate = top3_count / len(matching_races) * 100

        return round(top3_rate, 1)
