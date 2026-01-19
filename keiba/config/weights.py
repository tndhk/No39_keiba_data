"""Factor重み設定

各Factorの重みを定義する。合計は1.0になる必要がある。
"""

FACTOR_WEIGHTS = {
    "past_results": 0.25,  # 過去成績: 25%
    "course_fit": 0.20,  # コース適性: 20%
    "time_index": 0.20,  # タイム指数: 20%
    "last_3f": 0.20,  # 上がり3F: 20%
    "popularity": 0.15,  # 人気: 15%
}
