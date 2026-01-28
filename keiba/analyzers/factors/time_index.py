"""TimeIndexFactor - タイム指数Factor"""

import re

from keiba.analyzers.factors.base import BaseFactor


class TimeIndexFactor(BaseFactor):
    """タイム指数に基づくスコア計算

    同条件平均タイムとの比較でスコアを算出する。
    """

    name = "time_index"

    def _parse_time(self, time_str: str) -> float | None:
        """タイム文字列を秒に変換する

        Args:
            time_str: タイム文字列（例: "1:33.5", "59.8"）

        Returns:
            秒数
        """
        if not time_str:
            return None

        # "分:秒.小数" 形式
        match = re.match(r"(\d+):(\d+(?:\.\d+)?)", time_str)
        if match:
            minutes = int(match.group(1))
            seconds = float(match.group(2))
            return minutes * 60 + seconds

        # "秒.小数" 形式
        try:
            return float(time_str)
        except ValueError:
            return None

    def calculate(
        self,
        horse_id: str,
        race_results: list,
        target_surface: str | None = None,
        target_distance: int | None = None,
        track_condition: str | None = None,
        **kwargs,
    ) -> float | None:
        """タイム指数スコアを計算する

        Args:
            horse_id: 馬ID
            race_results: レース結果のリスト
            target_surface: 対象馬場
            target_distance: 対象距離
            track_condition: 馬場状態（良、稍重、重、不良など）

        Returns:
            0-100の範囲のスコア、データ不足の場合はNone
        """
        if target_surface is None or target_distance is None:
            return None

        # 距離帯（±200m）で同条件のレースを抽出
        matching_races = [
            r
            for r in race_results
            if r.get("surface") == target_surface
            and abs(r.get("distance", 0) - target_distance) <= 200
            and r.get("time")
            and (track_condition is None or r.get("track_condition") == track_condition)
        ]

        if len(matching_races) < 3:
            return None

        # タイムを秒に変換
        times = []
        horse_times = []
        for r in matching_races:
            time_sec = self._parse_time(r["time"])
            if time_sec:
                times.append(time_sec)
                if r.get("horse_id") == horse_id:
                    horse_times.append(time_sec)

        if not horse_times:
            return None

        # 平均タイムとの比較
        avg_time = sum(times) / len(times)
        horse_avg_time = sum(horse_times) / len(horse_times)

        # スコア計算: 平均より速いほど高スコア
        # 1秒速いと+10点、1秒遅いと-10点
        diff = avg_time - horse_avg_time
        score = 50 + diff * 10

        # 0-100に正規化
        return max(0, min(100, round(score, 1)))
