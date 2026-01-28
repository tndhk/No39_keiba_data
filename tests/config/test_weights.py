"""weights.py の設定値テスト"""

import pytest


class TestFactorNames:
    """FACTOR_NAMES の定数テスト"""

    def test_factor_names_matches_weights_keys(self):
        """FACTOR_NAMES が FACTOR_WEIGHTS のキーと一致する"""
        from keiba.config.weights import FACTOR_NAMES, FACTOR_WEIGHTS

        assert set(FACTOR_NAMES) == set(FACTOR_WEIGHTS.keys())

    def test_factor_names_is_tuple(self):
        """FACTOR_NAMES がタプルである（イミュータブル）"""
        from keiba.config.weights import FACTOR_NAMES

        assert isinstance(FACTOR_NAMES, tuple)

    def test_factor_names_length(self):
        """FACTOR_NAMES が7つの要素を持つ"""
        from keiba.config.weights import FACTOR_NAMES

        assert len(FACTOR_NAMES) == 7

    def test_factor_names_order(self):
        """FACTOR_NAMES が FACTOR_WEIGHTS のキー順序と一致する（Python 3.7+辞書順序保証）"""
        from keiba.config.weights import FACTOR_NAMES, FACTOR_WEIGHTS

        assert FACTOR_NAMES == tuple(FACTOR_WEIGHTS.keys())


class TestMLWeightAlpha:
    """ML_WEIGHT_ALPHA の設定テスト"""

    def test_ml_weight_alpha_exists_and_is_valid(self):
        """ML_WEIGHT_ALPHA が存在し、0-1の範囲内である"""
        from keiba.config.weights import ML_WEIGHT_ALPHA

        assert ML_WEIGHT_ALPHA is not None
        assert 0.0 <= ML_WEIGHT_ALPHA <= 1.0

    def test_ml_weight_alpha_default_value(self):
        """ML_WEIGHT_ALPHA のデフォルト値が0.6である"""
        from keiba.config.weights import ML_WEIGHT_ALPHA

        assert ML_WEIGHT_ALPHA == 0.6


class TestFactorWeights:
    """FACTOR_WEIGHTS の設定テスト"""

    def test_factor_weights_sum_to_one(self):
        """FACTOR_WEIGHTS の合計が1.0である"""
        from keiba.config.weights import FACTOR_WEIGHTS

        total = sum(FACTOR_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001  # 浮動小数点の誤差を許容

    def test_factor_weights_reflect_importance(self):
        """ファクターウェイトが測定された重要度を反映している"""
        from keiba.config.weights import FACTOR_WEIGHTS

        # past_resultsが最も高いウェイトを持つ（相関係数-0.426で最高）
        other_weights = [v for k, v in FACTOR_WEIGHTS.items() if k != "past_results"]
        assert FACTOR_WEIGHTS["past_results"] >= max(other_weights)

        # past_resultsは0.20以上（測定結果に基づく最低基準）
        assert FACTOR_WEIGHTS["past_results"] >= 0.20

        # running_styleは予測力が低いため、最も低いウェイトの一つ（0.12以下）
        assert FACTOR_WEIGHTS["running_style"] <= 0.12

        # 重要度の順序: past_results > time_index > last_3f > running_style
        assert FACTOR_WEIGHTS["past_results"] > FACTOR_WEIGHTS["time_index"]
        assert FACTOR_WEIGHTS["time_index"] > FACTOR_WEIGHTS["last_3f"]
        assert FACTOR_WEIGHTS["last_3f"] > FACTOR_WEIGHTS["running_style"]
