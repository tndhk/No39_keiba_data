"""keiba.utils モジュールのテスト

TDDのREDフェーズ: まずテストを作成し、FAILを確認する。
"""

import pytest

from keiba.utils.grade_extractor import extract_grade


class TestExtractGradeG1:
    """G1レースのグレード抽出テスト"""

    def test_g1_in_parentheses(self):
        """括弧内のG1を抽出"""
        assert extract_grade("有馬記念(G1)") == "G1"

    def test_g1_with_space(self):
        """スペース付きG1を抽出"""
        assert extract_grade("有馬記念 (G1)") == "G1"

    def test_gi_roman_numeral(self):
        """ローマ数字GIを抽出"""
        assert extract_grade("有馬記念(GI)") == "G1"

    def test_g1_lowercase(self):
        """小文字g1を抽出"""
        assert extract_grade("有馬記念(g1)") == "G1"


class TestExtractGradeG2:
    """G2レースのグレード抽出テスト"""

    def test_g2_in_parentheses(self):
        """括弧内のG2を抽出"""
        assert extract_grade("毎日王冠(G2)") == "G2"

    def test_gii_roman_numeral(self):
        """ローマ数字GIIを抽出"""
        assert extract_grade("毎日王冠(GII)") == "G2"


class TestExtractGradeG3:
    """G3レースのグレード抽出テスト"""

    def test_g3_in_parentheses(self):
        """括弧内のG3を抽出"""
        assert extract_grade("シンザン記念(G3)") == "G3"

    def test_giii_roman_numeral(self):
        """ローマ数字GIIIを抽出"""
        assert extract_grade("シンザン記念(GIII)") == "G3"


class TestExtractGradeJpn:
    """地方交流重賞のグレード抽出テスト"""

    def test_jpn1(self):
        """Jpn1を抽出"""
        assert extract_grade("川崎記念(Jpn1)") == "Jpn1"

    def test_jpn2(self):
        """Jpn2を抽出"""
        assert extract_grade("浦和記念(Jpn2)") == "Jpn2"

    def test_jpn3(self):
        """Jpn3を抽出"""
        assert extract_grade("マーチステークス(Jpn3)") == "Jpn3"

    def test_jpn1_uppercase(self):
        """JPN1（大文字）を抽出"""
        assert extract_grade("川崎記念(JPN1)") == "Jpn1"


class TestExtractGradeListed:
    """リステッドレースのグレード抽出テスト"""

    def test_listed_l(self):
        """(L)を抽出"""
        assert extract_grade("白富士ステークス(L)") == "L"

    def test_listed_lowercase(self):
        """(l)を抽出"""
        assert extract_grade("白富士ステークス(l)") == "L"


class TestExtractGradeOpen:
    """オープンクラスのグレード抽出テスト"""

    def test_open_op(self):
        """(OP)を抽出"""
        assert extract_grade("東京新聞杯(OP)") == "OP"

    def test_open_with_class(self):
        """オープン（含む特指）のパターン"""
        assert extract_grade("ターコイズS(オープン)") == "OP"

    def test_open_in_class_description(self):
        """クラス説明にオープンがある場合"""
        assert extract_grade("3歳以上オープン") == "OP"


class TestExtractGradeClassRaces:
    """条件戦のグレード抽出テスト"""

    def test_3_wins_class(self):
        """3勝クラスを抽出"""
        assert extract_grade("3歳以上3勝クラス") == "3WIN"

    def test_2_wins_class(self):
        """2勝クラスを抽出"""
        assert extract_grade("3歳以上2勝クラス") == "2WIN"

    def test_1_win_class(self):
        """1勝クラスを抽出"""
        assert extract_grade("3歳以上1勝クラス") == "1WIN"

    def test_1600_man_class(self):
        """1600万下（旧表記）を抽出"""
        assert extract_grade("3歳以上1600万下") == "3WIN"

    def test_1000_man_class(self):
        """1000万下（旧表記）を抽出"""
        assert extract_grade("3歳以上1000万下") == "2WIN"

    def test_500_man_class(self):
        """500万下（旧表記）を抽出"""
        assert extract_grade("3歳以上500万下") == "1WIN"


class TestExtractGradeNewMaiden:
    """新馬・未勝利のグレード抽出テスト"""

    def test_debut_race(self):
        """新馬戦を抽出"""
        assert extract_grade("2歳新馬") == "DEBUT"

    def test_maiden_race(self):
        """未勝利戦を抽出"""
        assert extract_grade("3歳未勝利") == "MAIDEN"

    def test_maiden_with_age(self):
        """年齢付き未勝利戦を抽出"""
        assert extract_grade("2歳未勝利") == "MAIDEN"


class TestExtractGradeHurdle:
    """障害レースのグレード抽出テスト"""

    def test_hurdle_open(self):
        """障害オープンを抽出"""
        assert extract_grade("障害オープン") == "HURDLE_OP"

    def test_hurdle_maiden(self):
        """障害未勝利を抽出"""
        assert extract_grade("障害4歳以上未勝利") == "HURDLE_MAIDEN"

    def test_hurdle_3_wins(self):
        """障害3勝クラスを抽出"""
        assert extract_grade("障害3勝クラス") == "HURDLE_3WIN"

    def test_hurdle_2_wins(self):
        """障害2勝クラスを抽出"""
        assert extract_grade("障害2勝クラス") == "HURDLE_2WIN"

    def test_hurdle_1_win(self):
        """障害1勝クラスを抽出"""
        assert extract_grade("障害1勝クラス") == "HURDLE_1WIN"

    def test_hurdle_g1(self):
        """障害G1を抽出"""
        assert extract_grade("中山大障害(G1)") == "G1"

    def test_hurdle_g2(self):
        """障害G2を抽出"""
        assert extract_grade("東京ハイジャンプ(G2)") == "G2"

    def test_hurdle_g3(self):
        """障害G3を抽出"""
        assert extract_grade("京都ハイジャンプ(G3)") == "G3"

    def test_hurdle_jpn1(self):
        """障害Jpn1を抽出"""
        assert extract_grade("中山グランドジャンプ(J・G1)") == "G1"


class TestExtractGradeUnknown:
    """不明なグレードのテスト"""

    def test_empty_string(self):
        """空文字列"""
        assert extract_grade("") == "UNKNOWN"

    def test_no_grade_info(self):
        """グレード情報なし"""
        assert extract_grade("テストレース") == "UNKNOWN"

    def test_none_input(self):
        """None入力"""
        assert extract_grade(None) == "UNKNOWN"


class TestExtractGradeEdgeCases:
    """エッジケースのテスト"""

    def test_multiple_patterns(self):
        """複数パターンがある場合は優先度の高いものを返す"""
        # G1が含まれていればG1を返す
        assert extract_grade("有馬記念(G1)3歳以上") == "G1"

    def test_real_race_names(self):
        """実際のレース名でのテスト"""
        # 有馬記念
        assert extract_grade("有馬記念(G1)") == "G1"
        # ジャパンカップ
        assert extract_grade("ジャパンC(G1)") == "G1"
        # 日本ダービー
        assert extract_grade("東京優駿(G1)") == "G1"
        # 皐月賞
        assert extract_grade("皐月賞(G1)") == "G1"
        # 安田記念
        assert extract_grade("安田記念(G1)") == "G1"

    def test_special_characters(self):
        """特殊文字を含むレース名"""
        assert extract_grade("ヴィクトリアマイル(G1)") == "G1"
        assert extract_grade("フェブラリーS(G1)") == "G1"

    def test_full_width_parentheses(self):
        """全角括弧のレース名"""
        assert extract_grade("有馬記念（G1）") == "G1"
