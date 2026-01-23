"""FactorCacheのテスト

TDD: RED フェーズ - テスト先行
"""

import pytest

from keiba.backtest.cache import FactorCache


class TestCacheHit:
    """キャッシュヒットのテスト"""

    def test_cache_hit_returns_stored_value(self):
        """setしたものがgetで取得できる"""
        cache = FactorCache(max_size=100)
        cache.set("key1", 0.5)

        hit, value = cache.get("key1")

        assert hit is True
        assert value == 0.5

    def test_cache_hit_with_different_values(self):
        """異なる値を複数格納し、それぞれ正しく取得できる"""
        cache = FactorCache(max_size=100)
        cache.set("key1", 0.1)
        cache.set("key2", 0.9)
        cache.set("key3", -0.5)

        hit1, value1 = cache.get("key1")
        hit2, value2 = cache.get("key2")
        hit3, value3 = cache.get("key3")

        assert hit1 is True and value1 == 0.1
        assert hit2 is True and value2 == 0.9
        assert hit3 is True and value3 == -0.5

    def test_cache_hit_overwrites_existing_key(self):
        """同じキーに再度setすると値が上書きされる"""
        cache = FactorCache(max_size=100)
        cache.set("key1", 0.5)
        cache.set("key1", 0.8)

        hit, value = cache.get("key1")

        assert hit is True
        assert value == 0.8


class TestCacheMiss:
    """キャッシュミスのテスト"""

    def test_cache_miss_returns_none(self):
        """未登録キーはhit=False、value=None"""
        cache = FactorCache(max_size=100)

        hit, value = cache.get("nonexistent_key")

        assert hit is False
        assert value is None

    def test_cache_miss_on_empty_cache(self):
        """空のキャッシュでgetするとミス"""
        cache = FactorCache(max_size=100)

        hit, value = cache.get("any_key")

        assert hit is False
        assert value is None


class TestCacheEviction:
    """キャッシュ削除（エビクション）のテスト"""

    def test_cache_eviction_removes_oldest_entry(self):
        """max_size超過時に古いエントリが削除される"""
        cache = FactorCache(max_size=3)
        cache.set("key1", 0.1)  # 最も古い
        cache.set("key2", 0.2)
        cache.set("key3", 0.3)
        cache.set("key4", 0.4)  # これで max_size 超過、key1 が削除されるべき

        # key1 は削除されている
        hit1, value1 = cache.get("key1")
        assert hit1 is False
        assert value1 is None

        # key2, key3, key4 は残っている
        hit2, _ = cache.get("key2")
        hit3, _ = cache.get("key3")
        hit4, _ = cache.get("key4")
        assert hit2 is True
        assert hit3 is True
        assert hit4 is True

    def test_cache_eviction_maintains_max_size(self):
        """エビクション後もmax_sizeを超えない"""
        cache = FactorCache(max_size=2)
        cache.set("key1", 0.1)
        cache.set("key2", 0.2)
        cache.set("key3", 0.3)
        cache.set("key4", 0.4)

        stats = cache.get_stats()
        assert stats["size"] <= 2

    def test_cache_eviction_with_size_one(self):
        """max_size=1の場合、常に最新のみ保持"""
        cache = FactorCache(max_size=1)
        cache.set("key1", 0.1)
        cache.set("key2", 0.2)

        hit1, _ = cache.get("key1")
        hit2, value2 = cache.get("key2")

        assert hit1 is False
        assert hit2 is True
        assert value2 == 0.2


class TestCacheStats:
    """キャッシュ統計情報のテスト"""

    def test_cache_stats_initial_state(self):
        """初期状態の統計情報"""
        cache = FactorCache(max_size=100)

        stats = cache.get_stats()

        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0
        assert stats["size"] == 0

    def test_cache_stats_after_hit(self):
        """ヒット後の統計情報"""
        cache = FactorCache(max_size=100)
        cache.set("key1", 0.5)
        cache.get("key1")  # ヒット

        stats = cache.get_stats()

        assert stats["hits"] == 1
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 1.0
        assert stats["size"] == 1

    def test_cache_stats_after_miss(self):
        """ミス後の統計情報"""
        cache = FactorCache(max_size=100)
        cache.get("nonexistent")  # ミス

        stats = cache.get_stats()

        assert stats["hits"] == 0
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.0
        assert stats["size"] == 0

    def test_cache_stats_mixed_access(self):
        """複数アクセス後のヒット率計算"""
        cache = FactorCache(max_size=100)
        cache.set("key1", 0.5)
        cache.get("key1")  # ヒット
        cache.get("key1")  # ヒット
        cache.get("key2")  # ミス
        cache.get("key3")  # ミス

        stats = cache.get_stats()

        assert stats["hits"] == 2
        assert stats["misses"] == 2
        assert stats["hit_rate"] == 0.5  # 2/4 = 0.5


class TestMakeKey:
    """キー生成のテスト"""

    def test_make_key_consistency(self):
        """同じ入力なら同じキーが生成される"""
        key1 = FactorCache._make_key(
            factor_name="speed_factor",
            horse_id="horse001",
            past_race_ids=["race001", "race002"],
        )
        key2 = FactorCache._make_key(
            factor_name="speed_factor",
            horse_id="horse001",
            past_race_ids=["race001", "race002"],
        )

        assert key1 == key2

    def test_make_key_different_factor_name(self):
        """ファクター名が異なればキーも異なる"""
        key1 = FactorCache._make_key(
            factor_name="speed_factor",
            horse_id="horse001",
            past_race_ids=["race001"],
        )
        key2 = FactorCache._make_key(
            factor_name="stamina_factor",
            horse_id="horse001",
            past_race_ids=["race001"],
        )

        assert key1 != key2

    def test_make_key_different_horse_id(self):
        """馬IDが異なればキーも異なる"""
        key1 = FactorCache._make_key(
            factor_name="speed_factor",
            horse_id="horse001",
            past_race_ids=["race001"],
        )
        key2 = FactorCache._make_key(
            factor_name="speed_factor",
            horse_id="horse002",
            past_race_ids=["race001"],
        )

        assert key1 != key2

    def test_make_key_different_past_race_ids(self):
        """過去レースIDが異なればキーも異なる"""
        key1 = FactorCache._make_key(
            factor_name="speed_factor",
            horse_id="horse001",
            past_race_ids=["race001", "race002"],
        )
        key2 = FactorCache._make_key(
            factor_name="speed_factor",
            horse_id="horse001",
            past_race_ids=["race001", "race003"],
        )

        assert key1 != key2

    def test_make_key_order_of_past_race_ids_matters(self):
        """過去レースIDの順序が異なればキーも異なる"""
        key1 = FactorCache._make_key(
            factor_name="speed_factor",
            horse_id="horse001",
            past_race_ids=["race001", "race002"],
        )
        key2 = FactorCache._make_key(
            factor_name="speed_factor",
            horse_id="horse001",
            past_race_ids=["race002", "race001"],
        )

        assert key1 != key2

    def test_make_key_with_params(self):
        """追加パラメータも含めてキー生成"""
        key1 = FactorCache._make_key(
            factor_name="speed_factor",
            horse_id="horse001",
            past_race_ids=["race001"],
            window=5,
        )
        key2 = FactorCache._make_key(
            factor_name="speed_factor",
            horse_id="horse001",
            past_race_ids=["race001"],
            window=10,
        )

        assert key1 != key2

    def test_make_key_params_consistency(self):
        """同じパラメータなら同じキー"""
        key1 = FactorCache._make_key(
            factor_name="speed_factor",
            horse_id="horse001",
            past_race_ids=["race001"],
            window=5,
            threshold=0.8,
        )
        key2 = FactorCache._make_key(
            factor_name="speed_factor",
            horse_id="horse001",
            past_race_ids=["race001"],
            window=5,
            threshold=0.8,
        )

        assert key1 == key2

    def test_make_key_empty_past_race_ids(self):
        """空のpast_race_idsでもキー生成可能"""
        key = FactorCache._make_key(
            factor_name="speed_factor",
            horse_id="horse001",
            past_race_ids=[],
        )

        assert key is not None
        assert isinstance(key, str)
        assert len(key) > 0


class TestCacheClear:
    """キャッシュクリアのテスト"""

    def test_clear_removes_all_data(self):
        """clearで全データが削除される"""
        cache = FactorCache(max_size=100)
        cache.set("key1", 0.1)
        cache.set("key2", 0.2)
        cache.set("key3", 0.3)

        cache.clear()

        hit1, _ = cache.get("key1")
        hit2, _ = cache.get("key2")
        hit3, _ = cache.get("key3")

        assert hit1 is False
        assert hit2 is False
        assert hit3 is False

    def test_clear_resets_size(self):
        """clearでsizeが0にリセットされる"""
        cache = FactorCache(max_size=100)
        cache.set("key1", 0.1)
        cache.set("key2", 0.2)

        cache.clear()

        stats = cache.get_stats()
        assert stats["size"] == 0

    def test_clear_resets_stats(self):
        """clearで統計情報もリセットされる"""
        cache = FactorCache(max_size=100)
        cache.set("key1", 0.1)
        cache.get("key1")  # ヒット
        cache.get("key2")  # ミス

        cache.clear()

        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0

    def test_cache_usable_after_clear(self):
        """clear後も正常に使用可能"""
        cache = FactorCache(max_size=100)
        cache.set("key1", 0.1)
        cache.clear()
        cache.set("key2", 0.2)

        hit, value = cache.get("key2")

        assert hit is True
        assert value == 0.2
