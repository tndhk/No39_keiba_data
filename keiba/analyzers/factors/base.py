"""Factor基底クラス"""

from abc import ABC, abstractmethod


class BaseFactor(ABC):
    """スコア計算Factorの基底クラス

    全てのFactorはこのクラスを継承し、nameとcalculateメソッドを実装する必要がある。
    """

    name: str

    @abstractmethod
    def calculate(self, horse_id: str, race_results: list, **kwargs) -> float | None:
        """スコアを計算する

        Args:
            horse_id: 馬ID
            race_results: レース結果のリスト
            **kwargs: 追加パラメータ

        Returns:
            0-100の範囲のスコア、データ不足の場合はNone
        """
        pass
