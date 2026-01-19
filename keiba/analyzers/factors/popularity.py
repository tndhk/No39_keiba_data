"""PopularityFactor - 人気Factor"""

from keiba.analyzers.factors.base import BaseFactor


class PopularityFactor(BaseFactor):
    """人気に基づくスコア計算

    オッズまたは人気順位からスコアを算出する。
    """

    name = "popularity"

    def calculate(
        self,
        horse_id: str,
        race_results: list,
        odds: float | None = None,
        popularity: int | None = None,
        **kwargs,
    ) -> float | None:
        """人気スコアを計算する

        Args:
            horse_id: 馬ID
            race_results: レース結果のリスト（未使用だが基底クラスに合わせて）
            odds: 単勝オッズ
            popularity: 人気順位

        Returns:
            0-100の範囲のスコア、データ不足の場合はNone
        """
        # 人気順位が指定されていればそれを使用
        if popularity is not None:
            # 1番人気=100, 2番人気=90, ...の線形スケール
            # 10番人気以降は10点
            score = max(10, 100 - (popularity - 1) * 10)
            return float(score)

        # オッズが指定されていればそれを使用
        if odds is not None:
            # オッズから人気スコアを計算
            # 1.0-2.0倍: 100-90点
            # 2.0-5.0倍: 90-60点
            # 5.0-10.0倍: 60-30点
            # 10.0倍以上: 30-10点
            if odds <= 2.0:
                score = 100 - (odds - 1.0) * 10
            elif odds <= 5.0:
                score = 90 - (odds - 2.0) * 10
            elif odds <= 10.0:
                score = 60 - (odds - 5.0) * 6
            else:
                score = max(10, 30 - (odds - 10.0) * 2)

            return round(score, 1)

        return None
