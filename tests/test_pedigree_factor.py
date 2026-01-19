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


class TestLineAptitude:
    """系統別適性データのテスト"""

    def test_sunday_silence_middle_distance_aptitude(self):
        """サンデーサイレンス系の中距離適性は1.0"""
        from keiba.config.pedigree_master import get_line_aptitude

        aptitude = get_line_aptitude("sunday_silence")
        assert aptitude["distance"]["middle"] == 1.0

    def test_storm_cat_sprint_aptitude(self):
        """ストームキャット系の短距離適性は1.0"""
        from keiba.config.pedigree_master import get_line_aptitude

        aptitude = get_line_aptitude("storm_cat")
        assert aptitude["distance"]["sprint"] == 1.0

    def test_roberto_heavy_track_aptitude(self):
        """ロベルト系の重馬場適性は1.0"""
        from keiba.config.pedigree_master import get_line_aptitude

        aptitude = get_line_aptitude("roberto")
        assert aptitude["track"]["heavy"] == 1.0

    def test_unknown_line_returns_other_aptitude(self):
        """未知の系統はother適性を返す"""
        from keiba.config.pedigree_master import get_line_aptitude

        aptitude = get_line_aptitude("unknown_line")
        assert aptitude == get_line_aptitude("other")


class TestPedigreeFactor:
    """PedigreeFactor（血統分析）のテスト"""

    @pytest.fixture
    def factor(self):
        from keiba.analyzers.factors.pedigree import PedigreeFactor

        return PedigreeFactor()

    def test_name_is_pedigree(self, factor):
        """nameは'pedigree'である"""
        assert factor.name == "pedigree"

    def test_calculate_with_deep_impact_middle_distance(self, factor):
        """ディープインパクト産駒の中距離レース"""
        result = factor.calculate(
            horse_id="horse123",
            race_results=[],
            sire="ディープインパクト",
            dam_sire="キングカメハメハ",
            distance=2000,
            track_condition="良",
        )
        assert result is not None
        assert result > 80

    def test_calculate_with_storm_cat_sprint(self, factor):
        """ストームキャット系産駒の短距離レース"""
        result = factor.calculate(
            horse_id="horse123",
            race_results=[],
            sire="ストームキャット",
            dam_sire="サンデーサイレンス",
            distance=1200,
            track_condition="良",
        )
        assert result is not None
        assert result > 80

    def test_calculate_with_unknown_sire(self, factor):
        """未知の種牡馬でも計算可能"""
        result = factor.calculate(
            horse_id="horse123",
            race_results=[],
            sire="未登録馬",
            dam_sire="未登録馬",
            distance=1600,
            track_condition="良",
        )
        assert result is not None

    def test_calculate_returns_none_without_sire(self, factor):
        """父情報がない場合はNoneを返す"""
        result = factor.calculate(
            horse_id="horse123",
            race_results=[],
            sire=None,
            dam_sire="キングカメハメハ",
            distance=1600,
            track_condition="良",
        )
        assert result is None

    def test_distance_band_classification(self, factor):
        """距離帯の分類"""
        assert factor._get_distance_band(1200) == "sprint"
        assert factor._get_distance_band(1600) == "mile"
        assert factor._get_distance_band(2000) == "middle"
        assert factor._get_distance_band(2400) == "long"

    def test_track_condition_mapping(self, factor):
        """馬場状態のマッピング"""
        assert factor._get_track_type("良") == "good"
        assert factor._get_track_type("稍重") == "good"
        assert factor._get_track_type("重") == "heavy"
        assert factor._get_track_type("不良") == "heavy"
        assert factor._get_track_type(None) == "good"

    def test_sire_dam_sire_weight_ratio(self, factor):
        """父7:母父3の重み配分

        ディープインパクト(sunday_silence): distance[middle]=1.0, track[good]=1.0
        ストームキャット(storm_cat): distance[middle]=0.6, track[good]=1.0

        距離スコア: 1.0 * 0.7 + 0.6 * 0.3 = 0.88
        馬場スコア: 1.0 * 0.7 + 1.0 * 0.3 = 1.0
        合計: (0.88 + 1.0) / 2 = 0.94 = 94.0
        """
        result = factor.calculate(
            horse_id="horse123",
            race_results=[],
            sire="ディープインパクト",
            dam_sire="ストームキャット",
            distance=2000,
            track_condition="良",
        )
        assert result is not None
        assert result == 94.0
