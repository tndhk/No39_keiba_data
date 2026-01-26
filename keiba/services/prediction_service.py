"""PredictionService - 出馬表データから予測を実行するサービス"""

import math
from dataclasses import dataclass
from typing import Protocol

from keiba.utils.grade_extractor import extract_grade
from keiba.analyzers.factors import (
    PastResultsFactor,
    CourseFitFactor,
    TimeIndexFactor,
    Last3FFactor,
    PopularityFactor,
    PedigreeFactor,
    RunningStyleFactor,
)
from keiba.analyzers.score_calculator import ScoreCalculator
from keiba.config.weights import ML_WEIGHT_ALPHA
from keiba.models.entry import ShutubaData, RaceEntry


@dataclass(frozen=True)
class PredictionResult:
    """予測結果（イミュータブル）"""

    horse_number: int
    horse_name: str
    horse_id: str
    ml_probability: float
    factor_scores: dict[str, float | None]
    total_score: float | None
    combined_score: float | None
    rank: int


class RaceResultRepository(Protocol):
    """過去成績リポジトリのプロトコル"""

    def get_past_results(
        self, horse_id: str, before_date: str, limit: int = 20
    ) -> list:
        """指定日より前の過去成績を取得"""
        ...


class PredictionService:
    """出馬表データから予測を実行するサービス"""

    FACTOR_NAMES = [
        "past_results",
        "course_fit",
        "time_index",
        "last_3f",
        "popularity",
        "pedigree",
        "running_style",
    ]

    def __init__(
        self, repository: RaceResultRepository, model_path: str | None = None
    ):
        """初期化

        Args:
            repository: 過去成績リポジトリ
            model_path: 学習済みモデルのパス（Noneの場合は因子スコアのみ）
        """
        self._repository = repository
        self._model_path = model_path
        self._model = None

        # 学習済みモデルのロード（パスが指定されている場合）
        if model_path is not None:
            self._load_model(model_path)

        # Factorインスタンスを作成
        self._factors = {
            "past_results": PastResultsFactor(),
            "course_fit": CourseFitFactor(),
            "time_index": TimeIndexFactor(),
            "last_3f": Last3FFactor(),
            "popularity": PopularityFactor(),
            "pedigree": PedigreeFactor(),
            "running_style": RunningStyleFactor(),
        }

        self._score_calculator = ScoreCalculator()

    def _load_model(self, model_path: str) -> None:
        """学習済みモデルをロードする

        Args:
            model_path: モデルファイルのパス
        """
        try:
            import joblib

            self._model = joblib.load(model_path)
        except Exception:
            # モデルロード失敗時はNoneのまま
            self._model = None

    def predict_from_shutuba(self, shutuba_data: ShutubaData) -> list[PredictionResult]:
        """出馬表データから予測を実行

        Args:
            shutuba_data: 出馬表データ

        Returns:
            予測結果リスト（ML確率降順でソート）
            新馬戦の場合は空リストを返す
        """
        # 新馬戦の場合は予測をスキップ
        if self.is_debut_race(shutuba_data.race_name):
            return []

        race_date = shutuba_data.date
        race_info = {
            "course": shutuba_data.course,
            "distance": shutuba_data.distance,
            "surface": shutuba_data.surface,
        }

        predictions = []

        for entry in shutuba_data.entries:
            # データリーク防止: レース日より前の過去成績のみ取得
            past_results = self._repository.get_past_results(
                horse_id=entry.horse_id, before_date=race_date, limit=20
            )

            # 7因子スコアを計算
            factor_scores = self._calculate_factor_scores(
                entry=entry, past_results=past_results, race_info=race_info
            )

            # 合計スコアを計算
            total_score = self._score_calculator.calculate_total(factor_scores)

            # ML確率を計算（モデルがない場合は0.0）
            ml_probability = self._calculate_ml_probability(
                entry=entry,
                past_results=past_results,
                factor_scores=factor_scores,
                race_info=race_info,
            )

            predictions.append(
                {
                    "horse_number": entry.horse_number,
                    "horse_name": entry.horse_name,
                    "horse_id": entry.horse_id,
                    "ml_probability": ml_probability,
                    "factor_scores": factor_scores,
                    "total_score": total_score,
                }
            )

        # ML確率降順でソート（同値の場合はtotal_score降順）
        predictions.sort(
            key=lambda x: (x["ml_probability"], x["total_score"] or 0.0),
            reverse=True,
        )

        # レース内の最大ML確率を取得
        max_ml_probability = max(
            (p["ml_probability"] for p in predictions), default=0.0
        )

        # 各予測の複合スコアを計算
        for pred in predictions:
            pred["combined_score"] = self._calculate_combined_score(
                ml_probability=pred["ml_probability"],
                max_ml_probability=max_ml_probability,
                total_score=pred["total_score"],
            )

        # 複合スコア降順で再ソート
        predictions.sort(
            key=lambda x: (x["combined_score"] or 0.0, x["ml_probability"]),
            reverse=True,
        )

        # ランキングを付与してPredictionResultに変換
        results = []
        for rank, pred in enumerate(predictions, 1):
            results.append(
                PredictionResult(
                    horse_number=pred["horse_number"],
                    horse_name=pred["horse_name"],
                    horse_id=pred["horse_id"],
                    ml_probability=pred["ml_probability"],
                    factor_scores=pred["factor_scores"],
                    total_score=pred["total_score"],
                    combined_score=pred["combined_score"],
                    rank=rank,
                )
            )

        return results

    def _calculate_factor_scores(
        self, entry: RaceEntry, past_results: list, race_info: dict
    ) -> dict[str, float | None]:
        """7因子スコアを計算

        Args:
            entry: 出走馬エントリー
            past_results: 過去成績リスト
            race_info: レース情報（course, distance, surface）

        Returns:
            7因子スコアの辞書
        """
        scores = {}

        # 過去成績がない場合は全てNone
        if not past_results:
            for factor_name in self.FACTOR_NAMES:
                scores[factor_name] = None
            return scores

        # 各Factorのスコアを計算
        for factor_name, factor in self._factors.items():
            try:
                if factor_name == "past_results":
                    scores[factor_name] = factor.calculate(
                        horse_id=entry.horse_id,
                        race_results=past_results,
                        presorted=True,
                    )
                elif factor_name == "course_fit":
                    scores[factor_name] = factor.calculate(
                        horse_id=entry.horse_id,
                        race_results=past_results,
                        target_course=race_info["course"],
                        target_distance=race_info["distance"],
                    )
                elif factor_name == "time_index":
                    scores[factor_name] = factor.calculate(
                        horse_id=entry.horse_id,
                        race_results=past_results,
                    )
                elif factor_name == "last_3f":
                    scores[factor_name] = factor.calculate(
                        horse_id=entry.horse_id,
                        race_results=past_results,
                    )
                elif factor_name == "popularity":
                    # 人気Factorは過去成績ではなく、直近の人気/オッズを使う
                    # 過去成績から直近の人気を取得
                    latest_result = past_results[0] if past_results else None
                    if latest_result:
                        scores[factor_name] = factor.calculate(
                            horse_id=entry.horse_id,
                            race_results=past_results,
                            odds=latest_result.get("odds"),
                            popularity=latest_result.get("popularity"),
                        )
                    else:
                        scores[factor_name] = None
                elif factor_name == "pedigree":
                    scores[factor_name] = factor.calculate(
                        horse_id=entry.horse_id,
                        race_results=past_results,
                        target_surface=race_info["surface"],
                        target_distance=race_info["distance"],
                    )
                elif factor_name == "running_style":
                    scores[factor_name] = factor.calculate(
                        horse_id=entry.horse_id,
                        race_results=past_results,
                        target_distance=race_info["distance"],
                    )
                else:
                    scores[factor_name] = None
            except Exception:
                # エラー時はNone
                scores[factor_name] = None

        return scores

    def _calculate_ml_probability(
        self,
        entry: RaceEntry,
        past_results: list,
        factor_scores: dict[str, float | None],
        race_info: dict,
    ) -> float:
        """ML確率を計算

        Args:
            entry: 出走馬エントリー
            past_results: 過去成績リスト
            factor_scores: 因子スコア
            race_info: レース情報

        Returns:
            ML確率（0.0-1.0）
        """
        # モデルがない場合は0.0を返す
        if self._model is None:
            return 0.0

        # 過去成績がない場合も0.0
        if not past_results:
            return 0.0

        # 特徴量を構築してモデルで予測
        try:
            from keiba.ml.feature_builder import FeatureBuilder
            import numpy as np

            feature_builder = FeatureBuilder()

            # 派生特徴量を計算
            past_stats = self._calculate_past_stats(past_results, entry.horse_id)

            # 最新の過去成績データ
            latest_result = past_results[0]

            features = feature_builder.build_features(
                race_result=latest_result,
                factor_scores=factor_scores,
                field_size=len(past_results),
                past_stats=past_stats,
            )

            # 特徴量をNumPy配列に変換
            feature_names = feature_builder.get_feature_names()
            feature_values = [features.get(name, -1) for name in feature_names]
            X = np.array([feature_values])

            # 予測
            probability = self._model.predict_proba(X)[:, 1][0]
            return float(max(0.0, min(1.0, probability)))
        except Exception:
            return 0.0

    def _calculate_combined_score(
        self,
        ml_probability: float,
        max_ml_probability: float,
        total_score: float | None,
    ) -> float | None:
        """複合スコアを加重平均で計算

        計算式: alpha * 正規化ML確率 + (1 - alpha) * 総合スコア
        alpha = 0.6 でML確率を60%、総合スコアを40%の重みで合成

        Args:
            ml_probability: 対象馬のML確率
            max_ml_probability: レース内の最大ML確率
            total_score: 7因子の重み付き総合スコア

        Returns:
            複合スコア（0-100）またはNone
        """
        if total_score is None or max_ml_probability <= 0:
            return None

        normalized_ml = (ml_probability / max_ml_probability) * 100
        combined = (
            ML_WEIGHT_ALPHA * normalized_ml
            + (1 - ML_WEIGHT_ALPHA) * total_score
        )
        return round(combined, 1)

    def _calculate_past_stats(
        self, past_results: list, horse_id: str
    ) -> dict[str, float | None]:
        """過去成績から派生統計を計算

        Args:
            past_results: 過去成績リスト
            horse_id: 馬ID

        Returns:
            派生統計の辞書
        """
        if not past_results:
            return {
                "win_rate": None,
                "top3_rate": None,
                "avg_finish_position": None,
                "days_since_last_race": None,
            }

        # 対象馬の成績をフィルタ
        horse_results = [r for r in past_results if r.get("horse_id") == horse_id]
        if not horse_results:
            horse_results = past_results  # フィルタで空になった場合は全てを使用

        total_races = len(horse_results)
        wins = sum(1 for r in horse_results if r.get("finish_position") == 1)
        top3 = sum(1 for r in horse_results if 1 <= (r.get("finish_position") or 99) <= 3)
        finish_positions = [
            r.get("finish_position")
            for r in horse_results
            if r.get("finish_position") is not None
        ]

        win_rate = wins / total_races if total_races > 0 else None
        top3_rate = top3 / total_races if total_races > 0 else None
        avg_finish = (
            sum(finish_positions) / len(finish_positions) if finish_positions else None
        )

        return {
            "win_rate": win_rate,
            "top3_rate": top3_rate,
            "avg_finish_position": avg_finish,
            "days_since_last_race": None,  # 計算には追加の日付処理が必要
        }

    @staticmethod
    def is_debut_race(race_name: str) -> bool:
        """新馬戦かどうかを判定する

        Args:
            race_name: レース名

        Returns:
            新馬戦の場合True、それ以外はFalse
        """
        return extract_grade(race_name) == "DEBUT"
