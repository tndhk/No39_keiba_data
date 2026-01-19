"""血統マスタデータ

種牡馬→系統マッピングと、系統別適性データを定義する。
"""

# 種牡馬→系統マッピング
SIRE_LINE_MAPPING: dict[str, str] = {
    # サンデーサイレンス系
    "サンデーサイレンス": "sunday_silence",
    "ディープインパクト": "sunday_silence",
    "ステイゴールド": "sunday_silence",
    "ハーツクライ": "sunday_silence",
    "ダイワメジャー": "sunday_silence",
    "マンハッタンカフェ": "sunday_silence",
    "ゼンノロブロイ": "sunday_silence",
    "アグネスタキオン": "sunday_silence",
    "スペシャルウィーク": "sunday_silence",
    "フジキセキ": "sunday_silence",
    "ネオユニヴァース": "sunday_silence",
    "キズナ": "sunday_silence",
    "オルフェーヴル": "sunday_silence",
    "ゴールドシップ": "sunday_silence",
    "ドゥラメンテ": "sunday_silence",
    "エピファネイア": "sunday_silence",
    "コントレイル": "sunday_silence",
    # キングマンボ系
    "キングマンボ": "kingmambo",
    "キングカメハメハ": "kingmambo",
    "ロードカナロア": "kingmambo",
    "ルーラーシップ": "kingmambo",
    "レイデオロ": "kingmambo",
    "ドゥラモンド": "kingmambo",
    # ノーザンダンサー系
    "ノーザンダンサー": "northern_dancer",
    "サドラーズウェルズ": "northern_dancer",
    "ガリレオ": "northern_dancer",
    "フランケル": "northern_dancer",
    "ニジンスキー": "northern_dancer",
    "リファール": "northern_dancer",
    # ミスタープロスペクター系（キングマンボ除く）
    "ミスタープロスペクター": "mr_prospector",
    "フォーティナイナー": "mr_prospector",
    "エンドスウィープ": "mr_prospector",
    "アドマイヤムーン": "mr_prospector",
    "ゴールドアリュール": "mr_prospector",
    "スマートファルコン": "mr_prospector",
    # ロベルト系
    "ロベルト": "roberto",
    "ブライアンズタイム": "roberto",
    "タニノギムレット": "roberto",
    "ウオッカ": "roberto",
    "シンボリクリスエス": "roberto",
    "エピカリス": "roberto",
    "モーリス": "roberto",
    "スクリーンヒーロー": "roberto",
    # ストームキャット系
    "ストームキャット": "storm_cat",
    "ヘネシー": "storm_cat",
    "テイルオブザキャット": "storm_cat",
    "ジャイアンツコーズウェイ": "storm_cat",
    "ヨハネスブルグ": "storm_cat",
    # ヘイルトゥリーズン系（サンデーサイレンス除く）
    "ヘイルトゥリーズン": "hail_to_reason",
    "リアルシャダイ": "hail_to_reason",
    "トニービン": "hail_to_reason",
    "ジャングルポケット": "hail_to_reason",
}

# 系統別適性データ
LINE_APTITUDE: dict[str, dict] = {
    "sunday_silence": {
        "distance": {"sprint": 0.6, "mile": 0.9, "middle": 1.0, "long": 0.8},
        "track": {"good": 1.0, "heavy": 0.7},
    },
    "kingmambo": {
        "distance": {"sprint": 0.8, "mile": 1.0, "middle": 0.9, "long": 0.6},
        "track": {"good": 0.9, "heavy": 0.9},
    },
    "northern_dancer": {
        "distance": {"sprint": 0.5, "mile": 0.8, "middle": 1.0, "long": 0.9},
        "track": {"good": 0.9, "heavy": 1.0},
    },
    "mr_prospector": {
        "distance": {"sprint": 1.0, "mile": 0.9, "middle": 0.7, "long": 0.5},
        "track": {"good": 0.9, "heavy": 1.0},
    },
    "roberto": {
        "distance": {"sprint": 0.6, "mile": 0.9, "middle": 1.0, "long": 0.8},
        "track": {"good": 0.8, "heavy": 1.0},
    },
    "storm_cat": {
        "distance": {"sprint": 1.0, "mile": 0.9, "middle": 0.6, "long": 0.4},
        "track": {"good": 1.0, "heavy": 0.6},
    },
    "hail_to_reason": {
        "distance": {"sprint": 0.5, "mile": 0.7, "middle": 0.9, "long": 1.0},
        "track": {"good": 0.9, "heavy": 0.8},
    },
    "other": {
        "distance": {"sprint": 0.7, "mile": 0.8, "middle": 0.8, "long": 0.7},
        "track": {"good": 0.9, "heavy": 0.9},
    },
}


def get_sire_line(sire_name: str) -> str:
    """種牡馬名から系統を取得する

    Args:
        sire_name: 種牡馬名

    Returns:
        系統名（未知の種牡馬は"other"）
    """
    return SIRE_LINE_MAPPING.get(sire_name, "other")


def get_line_aptitude(line: str) -> dict:
    """系統の適性データを取得する

    Args:
        line: 系統名

    Returns:
        適性データ（距離・馬場）
    """
    return LINE_APTITUDE.get(line, LINE_APTITUDE["other"])
