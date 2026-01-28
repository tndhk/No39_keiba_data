"""Factor重み設定

各Factorの重みを定義する。合計は1.0になる必要がある。
"""

# ML確率と総合スコアの合成比率（0.0-1.0）
# 0.6 = ML確率60%、総合スコア40%の重みで合成
ML_WEIGHT_ALPHA = 0.6

FACTOR_WEIGHTS = {
    "past_results": 0.25,  # 過去成績: 25%（相関-0.426、最も予測力が高い）
    "time_index": 0.18,  # タイム指数: 18%（的中率高め）
    "last_3f": 0.14,  # 上がり3F: 14%（中程度の予測力）
    "course_fit": 0.12,  # コース適性: 12%（データ不足のため控えめ）
    "popularity": 0.12,  # 人気: 12%（データ不足のため控えめ）
    "pedigree": 0.10,  # 血統: 10%（未測定のため低めに設定）
    "running_style": 0.09,  # 脚質: 9%（相関-0.073、予測力が低い）
}

# FACTOR_WEIGHTSのキーをイミュータブルなタプルとして提供
FACTOR_NAMES = tuple(FACTOR_WEIGHTS.keys())
