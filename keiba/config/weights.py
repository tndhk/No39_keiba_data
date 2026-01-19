"""Factor重み設定

各Factorの重みを定義する。合計は1.0になる必要がある。
"""

FACTOR_WEIGHTS = {
    "past_results": 0.143,  # 過去成績: 14.3%
    "course_fit": 0.143,  # コース適性: 14.3%
    "time_index": 0.143,  # タイム指数: 14.3%
    "last_3f": 0.143,  # 上がり3F: 14.3%
    "popularity": 0.143,  # 人気: 14.3%
    "pedigree": 0.143,  # 血統: 14.3%
    "running_style": 0.142,  # 脚質: 14.2%（端数調整）
}
