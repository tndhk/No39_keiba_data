"""PedigreeFactor - 血統分析Factor"""

from keiba.analyzers.factors.base import BaseFactor
from keiba.config.pedigree_master import get_line_aptitude, get_sire_line


class PedigreeFactor(BaseFactor):
    """血統に基づくスコア計算

    父と母父の系統から、レース条件（距離・馬場）への適性を計算する。
    父:母父 = 7:3 の重み付けで合算。
    """

    name = "pedigree"

    def _get_distance_band(self, distance: int) -> str:
        """距離から距離帯を判定する"""
        if distance <= 1400:
            return "sprint"
        elif distance <= 1800:
            return "mile"
        elif distance <= 2200:
            return "middle"
        else:
            return "long"

    def _get_track_type(self, track_condition: str | None) -> str:
        """馬場状態をタイプに変換する"""
        if track_condition is None:
            return "good"
        if track_condition in ("重", "不良"):
            return "heavy"
        return "good"

    def calculate(
        self, horse_id: str, race_results: list, **kwargs
    ) -> float | None:
        """血統適性スコアを計算する"""
        sire = kwargs.get("sire")
        dam_sire = kwargs.get("dam_sire")
        distance = kwargs.get("distance")
        track_condition = kwargs.get("track_condition")

        if sire is None:
            return None
        if distance is None:
            return None

        sire_line = get_sire_line(sire)
        dam_sire_line = get_sire_line(dam_sire) if dam_sire else "other"

        sire_aptitude = get_line_aptitude(sire_line)
        dam_sire_aptitude = get_line_aptitude(dam_sire_line)

        distance_band = self._get_distance_band(distance)
        track_type = self._get_track_type(track_condition)

        sire_distance_apt = sire_aptitude["distance"][distance_band]
        dam_sire_distance_apt = dam_sire_aptitude["distance"][distance_band]
        distance_score = sire_distance_apt * 0.7 + dam_sire_distance_apt * 0.3

        sire_track_apt = sire_aptitude["track"][track_type]
        dam_sire_track_apt = dam_sire_aptitude["track"][track_type]
        track_score = sire_track_apt * 0.7 + dam_sire_track_apt * 0.3

        total_aptitude = (distance_score + track_score) / 2

        return round(total_aptitude * 100, 1)
