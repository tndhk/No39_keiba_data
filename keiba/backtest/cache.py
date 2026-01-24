"""ファクター計算結果のキャッシュ

LRUキャッシュによりファクター計算の重複を回避する。
"""

import hashlib
from collections import OrderedDict


class FactorCache:
    """ファクター計算結果のLRUキャッシュ

    同一馬・同一過去レース・同一パラメータでのファクター計算結果をキャッシュし、
    重複計算を回避することでバックテストのパフォーマンスを向上させる。

    Attributes:
        max_size: キャッシュの最大エントリ数
    """

    def __init__(self, max_size: int = 100_000):
        """キャッシュを初期化

        Args:
            max_size: キャッシュの最大エントリ数。超過時はLRUで古いエントリを削除
        """
        self._max_size = max_size
        self._cache: OrderedDict[str, float] = OrderedDict()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _make_key(
        factor_name: str, horse_id: str, past_race_ids: list[str], **params
    ) -> str:
        """キャッシュキーを生成

        同じ入力なら同じキーを返す。paramsはソートして一貫性を確保。

        Args:
            factor_name: ファクター名
            horse_id: 馬ID
            past_race_ids: 過去レースIDのリスト（順序は保持）
            **params: 追加パラメータ

        Returns:
            SHA256ハッシュ化されたキャッシュキー
        """
        # パラメータをソートしてタプル化（効率化）
        params_tuple = tuple(sorted(params.items())) if params else ()

        # キー生成用のタプル構造（JSON使用を回避）
        key_tuple = (factor_name, horse_id, tuple(past_race_ids), params_tuple)

        # reprを使用して文字列化し、ハッシュ
        key_str = repr(key_tuple)
        return hashlib.sha256(key_str.encode("utf-8")).hexdigest()

    def get(self, key: str) -> tuple[bool, float | None]:
        """キャッシュから値を取得

        Args:
            key: キャッシュキー

        Returns:
            (hit, value)のタプル。hitがTrueなら値が存在、Falseならキャッシュミス
        """
        if key in self._cache:
            self._hits += 1
            # LRU: アクセスされたエントリを末尾に移動
            self._cache.move_to_end(key)
            return True, self._cache[key]
        else:
            self._misses += 1
            return False, None

    def set(self, key: str, value: float) -> None:
        """キャッシュに値を保存

        max_size超過時はLRUで最も古いエントリを削除。

        Args:
            key: キャッシュキー
            value: 保存する値
        """
        # 既存キーの場合は更新して末尾に移動
        if key in self._cache:
            self._cache[key] = value
            self._cache.move_to_end(key)
            return

        # 新規追加前にサイズチェック
        if len(self._cache) >= self._max_size:
            # LRU: 最も古いエントリ（先頭）を削除
            self._cache.popitem(last=False)

        self._cache[key] = value

    def get_stats(self) -> dict:
        """統計情報を取得

        Returns:
            統計情報の辞書:
            - hits: ヒット数
            - misses: ミス数
            - hit_rate: ヒット率（0-1）
            - size: 現在のキャッシュサイズ
        """
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "size": len(self._cache),
        }

    def clear(self) -> None:
        """キャッシュを完全にクリア

        全エントリと統計情報をリセットする。
        """
        self._cache.clear()
        self._hits = 0
        self._misses = 0
