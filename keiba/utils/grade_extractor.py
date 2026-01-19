"""レース名からグレード/クラス情報を抽出するモジュール

グレード種別:
- 重賞: G1, G2, G3, Jpn1, Jpn2, Jpn3, L
- オープン: OP
- 条件戦: 3WIN, 2WIN, 1WIN
- 新馬/未勝利: DEBUT, MAIDEN
- 障害: HURDLE_OP, HURDLE_MAIDEN, HURDLE_3WIN, HURDLE_2WIN, HURDLE_1WIN
- 不明: UNKNOWN
"""

import re


def extract_grade(race_name: str | None) -> str:
    """レース名からグレード/クラス情報を抽出する

    Args:
        race_name: レース名

    Returns:
        グレード文字列（G1, G2, G3, Jpn1, Jpn2, Jpn3, L, OP, 3WIN, 2WIN, 1WIN,
                       DEBUT, MAIDEN, HURDLE_OP, HURDLE_MAIDEN, HURDLE_3WIN,
                       HURDLE_2WIN, HURDLE_1WIN, UNKNOWN）
    """
    if not race_name:
        return "UNKNOWN"

    # 全角括弧を半角に変換
    race_name = race_name.replace("（", "(").replace("）", ")")

    # 優先度順にパターンをチェック

    # 1. G1（最優先）
    if _match_g1(race_name):
        return "G1"

    # 2. G2
    if _match_g2(race_name):
        return "G2"

    # 3. G3
    if _match_g3(race_name):
        return "G3"

    # 4. Jpn1/Jpn2/Jpn3
    jpn_grade = _match_jpn(race_name)
    if jpn_grade:
        return jpn_grade

    # 5. リステッド (L)
    if _match_listed(race_name):
        return "L"

    # 6. 障害レース（グレードなしの場合）
    hurdle_grade = _match_hurdle(race_name)
    if hurdle_grade:
        return hurdle_grade

    # 7. オープン
    if _match_open(race_name):
        return "OP"

    # 8. 条件戦（勝クラス / 万下）
    class_grade = _match_class_race(race_name)
    if class_grade:
        return class_grade

    # 9. 新馬戦
    if _match_debut(race_name):
        return "DEBUT"

    # 10. 未勝利戦
    if _match_maiden(race_name):
        return "MAIDEN"

    return "UNKNOWN"


def _match_g1(race_name: str) -> bool:
    """G1パターンにマッチするか判定"""
    patterns = [
        r"\(G1\)",
        r"\(GI\)",
        r"\(g1\)",
        r"\(gi\)",
        r"\(J・G1\)",  # 障害G1
        r"\(J・GI\)",
    ]
    return _match_any_pattern(race_name, patterns)


def _match_g2(race_name: str) -> bool:
    """G2パターンにマッチするか判定"""
    patterns = [
        r"\(G2\)",
        r"\(GII\)",
        r"\(g2\)",
        r"\(gii\)",
        r"\(J・G2\)",  # 障害G2
        r"\(J・GII\)",
    ]
    return _match_any_pattern(race_name, patterns)


def _match_g3(race_name: str) -> bool:
    """G3パターンにマッチするか判定"""
    patterns = [
        r"\(G3\)",
        r"\(GIII\)",
        r"\(g3\)",
        r"\(giii\)",
        r"\(J・G3\)",  # 障害G3
        r"\(J・GIII\)",
    ]
    return _match_any_pattern(race_name, patterns)


def _match_jpn(race_name: str) -> str | None:
    """Jpnグレードにマッチするか判定"""
    # Jpn1
    if re.search(r"\(Jpn1\)", race_name, re.IGNORECASE):
        return "Jpn1"
    if re.search(r"\(JPN1\)", race_name):
        return "Jpn1"

    # Jpn2
    if re.search(r"\(Jpn2\)", race_name, re.IGNORECASE):
        return "Jpn2"
    if re.search(r"\(JPN2\)", race_name):
        return "Jpn2"

    # Jpn3
    if re.search(r"\(Jpn3\)", race_name, re.IGNORECASE):
        return "Jpn3"
    if re.search(r"\(JPN3\)", race_name):
        return "Jpn3"

    return None


def _match_listed(race_name: str) -> bool:
    """リステッド(L)にマッチするか判定"""
    patterns = [
        r"\(L\)",
        r"\(l\)",
    ]
    return _match_any_pattern(race_name, patterns)


def _match_open(race_name: str) -> bool:
    """オープンクラスにマッチするか判定"""
    patterns = [
        r"\(OP\)",
        r"\(オープン\)",
        r"オープン",
    ]
    # 障害オープンは別扱いなので除外
    if "障害" in race_name:
        return False
    return _match_any_pattern(race_name, patterns)


def _match_class_race(race_name: str) -> str | None:
    """条件戦（勝クラス/万下）にマッチするか判定"""
    # 障害レースは別扱い
    if "障害" in race_name:
        return None

    # 新表記: 勝クラス
    if re.search(r"3勝クラス", race_name):
        return "3WIN"
    if re.search(r"2勝クラス", race_name):
        return "2WIN"
    if re.search(r"1勝クラス", race_name):
        return "1WIN"

    # 旧表記: 万下
    if re.search(r"1600万下", race_name):
        return "3WIN"
    if re.search(r"1000万下", race_name):
        return "2WIN"
    if re.search(r"500万下", race_name):
        return "1WIN"

    return None


def _match_hurdle(race_name: str) -> str | None:
    """障害レース（グレードなし）にマッチするか判定"""
    if "障害" not in race_name:
        return None

    # 障害の勝クラス
    if re.search(r"障害.*3勝クラス", race_name):
        return "HURDLE_3WIN"
    if re.search(r"障害.*2勝クラス", race_name):
        return "HURDLE_2WIN"
    if re.search(r"障害.*1勝クラス", race_name):
        return "HURDLE_1WIN"

    # 障害オープン
    if re.search(r"障害.*オープン", race_name):
        return "HURDLE_OP"

    # 障害未勝利
    if re.search(r"障害.*未勝利", race_name):
        return "HURDLE_MAIDEN"

    return None


def _match_debut(race_name: str) -> bool:
    """新馬戦にマッチするか判定"""
    return bool(re.search(r"新馬", race_name))


def _match_maiden(race_name: str) -> bool:
    """未勝利戦にマッチするか判定"""
    # 障害未勝利は別扱い
    if "障害" in race_name:
        return False
    return bool(re.search(r"未勝利", race_name))


def _match_any_pattern(text: str, patterns: list[str]) -> bool:
    """いずれかのパターンにマッチするか判定"""
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False
