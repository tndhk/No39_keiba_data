"""血統分析（PedigreeFactor）のテスト"""

import pytest


class TestSireLineMapping:
    """種牡馬→系統マッピングのテスト"""

    def test_deep_impact_is_sunday_silence_line(self):
        """ディープインパクトはサンデーサイレンス系"""
        from keiba.config.pedigree_master import get_sire_line

        assert get_sire_line("ディープインパクト") == "sunday_silence"

    def test_lord_kanaloa_is_kingmambo_line(self):
        """ロードカナロアはキングマンボ系"""
        from keiba.config.pedigree_master import get_sire_line

        assert get_sire_line("ロードカナロア") == "kingmambo"

    def test_unknown_sire_is_other(self):
        """未知の種牡馬はother"""
        from keiba.config.pedigree_master import get_sire_line

        assert get_sire_line("未登録の種牡馬") == "other"

    def test_stay_gold_is_sunday_silence_line(self):
        """ステイゴールドはサンデーサイレンス系"""
        from keiba.config.pedigree_master import get_sire_line

        assert get_sire_line("ステイゴールド") == "sunday_silence"

    def test_king_kamehameha_is_kingmambo_line(self):
        """キングカメハメハはキングマンボ系"""
        from keiba.config.pedigree_master import get_sire_line

        assert get_sire_line("キングカメハメハ") == "kingmambo"

    def test_brian_time_is_roberto_line(self):
        """ブライアンズタイムはロベルト系"""
        from keiba.config.pedigree_master import get_sire_line

        assert get_sire_line("ブライアンズタイム") == "roberto"
