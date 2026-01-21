"""バックテストエンジンモジュール

ML予測と7ファクター予測の時系列バックテストを実行する
"""

from datetime import date, datetime
from typing import Iterator, Literal

from keiba.backtest.metrics import PredictionResult, RaceBacktestResult

RetrainInterval = Literal["daily", "weekly", "monthly"]


def _parse_date(date_str: str) -> date:
    """日付文字列をdateオブジェクトに変換"""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def _get_iso_week(d: date) -> tuple[int, int]:
    """ISO週番号を取得（年と週番号のタプル）"""
    iso = d.isocalendar()
    return (iso[0], iso[1])


class BacktestEngine:
    """バックテストエンジン

    時系列順にレースを処理し、未来データ漏洩なしで予測を評価する。
    再学習間隔を指定可能（daily/weekly/monthly）。
    """

    def __init__(
        self,
        db_path: str,
        start_date: str,  # YYYY-MM-DD
        end_date: str,  # YYYY-MM-DD
        retrain_interval: RetrainInterval = "weekly",
    ):
        """初期化

        Args:
            db_path: データベースファイルパス
            start_date: バックテスト開始日（YYYY-MM-DD）
            end_date: バックテスト終了日（YYYY-MM-DD）
            retrain_interval: 再学習間隔（daily/weekly/monthly）
        """
        self.db_path = db_path
        self.start_date = start_date
        self.end_date = end_date
        self.retrain_interval = retrain_interval
        self._model = None
        self._last_train_date: str | None = None
        self._lightgbm_available: bool | None = None

    def _is_lightgbm_available(self) -> bool:
        """LightGBMが利用可能か確認"""
        if self._lightgbm_available is None:
            try:
                import lightgbm  # noqa: F401

                self._lightgbm_available = True
            except ImportError:
                self._lightgbm_available = False
        return self._lightgbm_available

    def _should_retrain(self, race_date: str) -> bool:
        """再学習が必要か判定

        Args:
            race_date: 現在処理中のレース日（YYYY-MM-DD）

        Returns:
            再学習が必要ならTrue
        """
        # 初回は必ず再学習
        if self._last_train_date is None:
            return True

        current = _parse_date(race_date)
        last = _parse_date(self._last_train_date)

        if self.retrain_interval == "daily":
            # 日付が変わったら再学習
            return current > last

        elif self.retrain_interval == "weekly":
            # ISO週番号が変わったら再学習
            current_week = _get_iso_week(current)
            last_week = _get_iso_week(last)
            return current_week != last_week

        elif self.retrain_interval == "monthly":
            # 月が変わったら再学習
            return (current.year, current.month) != (last.year, last.month)

        return True  # 不明な間隔は常に再学習

    def _get_training_races(self, cutoff_date: str) -> list[dict]:
        """学習用のレースデータを取得

        Args:
            cutoff_date: カットオフ日（この日より前のデータのみ取得）

        Returns:
            レースデータのリスト
        """
        from sqlalchemy import select

        from keiba.db import get_engine, get_session
        from keiba.models import Race

        engine = get_engine(self.db_path)
        cutoff = _parse_date(cutoff_date)

        with get_session(engine) as session:
            stmt = select(Race).where(Race.date < cutoff).order_by(Race.date.desc())
            races = session.execute(stmt).scalars().all()
            return [
                {
                    "race_id": r.id,
                    "race_date": r.date.strftime("%Y-%m-%d"),
                    "race_name": r.name,
                    "venue": r.course,
                    "surface": r.surface,
                    "distance": r.distance,
                }
                for r in races
            ]

    def _train_model(self, cutoff_date: str) -> None:
        """cutoff_dateより前のデータでモデルを学習

        Args:
            cutoff_date: カットオフ日（この日より前のデータのみ使用）
        """
        if not self._is_lightgbm_available():
            self._model = None
            return

        # 学習データを取得
        training_races = self._get_training_races(cutoff_date)

        if not training_races:
            self._model = None
            return

        # cli.pyの_build_training_dataパターンを参考に実装
        try:
            import numpy as np

            from keiba.db import get_engine, get_session
            from keiba.ml.feature_builder import FeatureBuilder
            from keiba.ml.trainer import Trainer
            from keiba.models import Horse, Race, RaceResult

            engine = get_engine(self.db_path)
            cutoff = _parse_date(cutoff_date)

            with get_session(engine) as session:
                features_list, labels = self._build_training_data(session, cutoff)

                if len(features_list) < 100:
                    self._model = None
                    return

                feature_builder = FeatureBuilder()
                feature_names = feature_builder.get_feature_names()

                X = np.array(
                    [[f[name] for name in feature_names] for f in features_list]
                )
                y = np.array(labels)

                trainer = Trainer()
                trainer.train(X, y)
                self._model = trainer.model

        except Exception:
            self._model = None

    def _build_training_data(
        self, session, target_date: date
    ) -> tuple[list[dict], list[int]]:
        """ML学習用のデータを構築する

        Args:
            session: SQLAlchemyセッション
            target_date: 対象レース日（この日より前のデータを使用）

        Returns:
            (特徴量リスト, ラベルリスト)のタプル
        """
        from keiba.analyzers.factors import (
            CourseFitFactor,
            Last3FFactor,
            PastResultsFactor,
            PedigreeFactor,
            PopularityFactor,
            RunningStyleFactor,
            TimeIndexFactor,
        )
        from keiba.ml.feature_builder import FeatureBuilder
        from keiba.models import Horse, Race, RaceResult

        # 対象日より前のレースを取得
        past_races = (
            session.query(Race)
            .filter(Race.date < target_date)
            .order_by(Race.date.desc())
            .all()
        )

        if not past_races:
            return [], []

        feature_builder = FeatureBuilder()
        factors = {
            "past_results": PastResultsFactor(),
            "course_fit": CourseFitFactor(),
            "time_index": TimeIndexFactor(),
            "last_3f": Last3FFactor(),
            "popularity": PopularityFactor(),
            "pedigree": PedigreeFactor(),
            "running_style": RunningStyleFactor(),
        }

        features_list = []
        labels = []

        for race in past_races:
            results = (
                session.query(RaceResult).filter(RaceResult.race_id == race.id).all()
            )

            field_size = len(results)

            for result in results:
                # 中止（finish_position=0）は除外
                if result.finish_position == 0:
                    continue

                # 過去成績を取得
                horse_past = self._get_horse_past_results(session, result.horse_id)

                # 馬情報を取得
                horse = session.get(Horse, result.horse_id)

                # ファクタースコアを計算
                factor_scores = {
                    "past_results": factors["past_results"].calculate(
                        result.horse_id, horse_past
                    ),
                    "course_fit": factors["course_fit"].calculate(
                        result.horse_id,
                        horse_past,
                        target_surface=race.surface,
                        target_distance=race.distance,
                    ),
                    "time_index": factors["time_index"].calculate(
                        result.horse_id,
                        horse_past,
                        target_surface=race.surface,
                        target_distance=race.distance,
                    ),
                    "last_3f": factors["last_3f"].calculate(
                        result.horse_id, horse_past
                    ),
                    "popularity": factors["popularity"].calculate(
                        result.horse_id,
                        [],
                        odds=result.odds,
                        popularity=result.popularity,
                    ),
                    "pedigree": factors["pedigree"].calculate(
                        result.horse_id,
                        [],
                        sire=horse.sire if horse else None,
                        dam_sire=horse.dam_sire if horse else None,
                        target_surface=race.surface,
                        target_distance=race.distance,
                    ),
                    "running_style": factors["running_style"].calculate(
                        result.horse_id,
                        horse_past,
                        passing_order=result.passing_order,
                        course=race.course,
                        distance=race.distance,
                    ),
                }

                # 派生特徴量を計算
                past_stats = self._calculate_past_stats(horse_past, race.date)

                # 生データ
                race_result_data = {
                    "horse_id": result.horse_id,
                    "odds": result.odds,
                    "popularity": result.popularity,
                    "weight": result.weight,
                    "weight_diff": result.weight_diff,
                    "age": result.age,
                    "impost": result.impost,
                    "horse_number": result.horse_number,
                }

                features = feature_builder.build_features(
                    race_result=race_result_data,
                    factor_scores=factor_scores,
                    field_size=field_size,
                    past_stats=past_stats,
                )

                features_list.append(features)

                # ラベル: 3着以内=1, 4着以下=0
                label = 1 if result.finish_position <= 3 else 0
                labels.append(label)

        return features_list, labels

    def _get_horse_past_results(self, session, horse_id: str) -> list[dict]:
        """馬の過去成績を取得する

        Args:
            session: SQLAlchemyセッション
            horse_id: 馬ID

        Returns:
            過去成績のリスト
        """
        from sqlalchemy import func

        from keiba.models import Race, RaceResult

        # 過去のレース結果を取得
        past_results_query = (
            session.query(
                RaceResult, Race, func.count(RaceResult.id).over().label("total_runners")
            )
            .join(Race, RaceResult.race_id == Race.id)
            .filter(RaceResult.horse_id == horse_id)
            .order_by(Race.date.desc())
            .limit(20)
        )

        results = []
        for race_result, race_info, _ in past_results_query:
            # 同じレースの出走頭数を取得
            total_runners = (
                session.query(RaceResult)
                .filter(RaceResult.race_id == race_info.id)
                .count()
            )

            results.append(
                {
                    "horse_id": race_result.horse_id,
                    "finish_position": race_result.finish_position,
                    "total_runners": total_runners,
                    "surface": race_info.surface,
                    "distance": race_info.distance,
                    "time": race_result.time,
                    "last_3f": race_result.last_3f,
                    "race_date": race_info.date,
                }
            )

        return results

    def _calculate_past_stats(self, past_results: list[dict], current_date: date) -> dict:
        """派生特徴量を計算する

        Args:
            past_results: 過去成績リスト
            current_date: 現在のレース日

        Returns:
            派生特徴量の辞書
        """
        if not past_results:
            return {
                "win_rate": None,
                "top3_rate": None,
                "avg_finish_position": None,
                "days_since_last_race": None,
            }

        total = len(past_results)
        wins = sum(1 for r in past_results if r.get("finish_position") == 1)
        top3 = sum(1 for r in past_results if r.get("finish_position", 99) <= 3)
        positions = [
            r.get("finish_position", 0)
            for r in past_results
            if r.get("finish_position", 0) > 0
        ]

        # 前走からの日数
        days_since = None
        if past_results and past_results[0].get("race_date"):
            last_date = past_results[0]["race_date"]
            if hasattr(last_date, "date"):
                last_date = last_date.date()
            days_since = (current_date - last_date).days

        return {
            "win_rate": wins / total if total > 0 else None,
            "top3_rate": top3 / total if total > 0 else None,
            "avg_finish_position": sum(positions) / len(positions) if positions else None,
            "days_since_last_race": days_since,
        }

    def _get_races_in_period(self) -> list[dict]:
        """指定期間のレースを時系列順で取得

        Returns:
            レースデータのリスト（時系列順）
        """
        from sqlalchemy import select

        from keiba.db import get_engine, get_session
        from keiba.models import Race

        engine = get_engine(self.db_path)
        start = _parse_date(self.start_date)
        end = _parse_date(self.end_date)

        with get_session(engine) as session:
            stmt = (
                select(Race)
                .where(Race.date >= start, Race.date <= end)
                .order_by(Race.date, Race.race_number)
            )
            races = session.execute(stmt).scalars().all()
            return [
                {
                    "race_id": r.id,
                    "race_date": r.date.strftime("%Y-%m-%d"),
                    "race_name": r.name,
                    "venue": r.course,
                }
                for r in races
            ]

    def _get_race_data(self, race_id: str) -> dict:
        """レースデータを取得

        Args:
            race_id: レースID

        Returns:
            レースデータの辞書
        """
        from keiba.db import get_engine, get_session
        from keiba.models import Race, RaceResult

        engine = get_engine(self.db_path)

        with get_session(engine) as session:
            race = session.get(Race, race_id)
            if not race:
                return {}

            results = (
                session.query(RaceResult).filter(RaceResult.race_id == race_id).all()
            )

            horses = []
            for r in results:
                horse_name = r.horse.name if r.horse else "Unknown"
                horses.append(
                    {
                        "horse_number": r.horse_number,
                        "horse_name": horse_name,
                        "horse_id": r.horse_id,
                        "actual_rank": r.finish_position,
                        "odds": r.odds,
                        "popularity": r.popularity,
                        "weight": r.weight,
                        "weight_diff": r.weight_diff,
                        "age": r.age,
                        "impost": r.impost,
                        "passing_order": r.passing_order,
                    }
                )

            return {
                "race_id": race.id,
                "race_date": race.date.strftime("%Y-%m-%d"),
                "race_name": race.name,
                "venue": race.course,
                "surface": race.surface,
                "distance": race.distance,
                "horses": horses,
            }

    def _calculate_predictions(self, race_data: dict) -> list[PredictionResult]:
        """予測を計算

        Args:
            race_data: レースデータ

        Returns:
            予測結果リスト
        """
        import numpy as np

        from keiba.analyzers.factors import (
            CourseFitFactor,
            Last3FFactor,
            PastResultsFactor,
            PedigreeFactor,
            PopularityFactor,
            RunningStyleFactor,
            TimeIndexFactor,
        )
        from keiba.analyzers.score_calculator import ScoreCalculator
        from keiba.db import get_engine, get_session
        from keiba.ml.feature_builder import FeatureBuilder
        from keiba.models import Horse

        engine = get_engine(self.db_path)

        calculator = ScoreCalculator()
        factors = {
            "past_results": PastResultsFactor(),
            "course_fit": CourseFitFactor(),
            "time_index": TimeIndexFactor(),
            "last_3f": Last3FFactor(),
            "popularity": PopularityFactor(),
            "pedigree": PedigreeFactor(),
            "running_style": RunningStyleFactor(),
        }
        feature_builder = FeatureBuilder()

        predictions = []
        ml_features = []
        horse_ids = []

        race_date = _parse_date(race_data["race_date"])

        with get_session(engine) as session:
            for horse_data in race_data.get("horses", []):
                horse_id = horse_data["horse_id"]

                # 過去成績を取得
                past_results = self._get_horse_past_results(session, horse_id)

                # 馬情報を取得
                horse = session.get(Horse, horse_id)

                # ファクタースコアを計算
                factor_scores = {
                    "past_results": factors["past_results"].calculate(
                        horse_id, past_results
                    ),
                    "course_fit": factors["course_fit"].calculate(
                        horse_id,
                        past_results,
                        target_surface=race_data["surface"],
                        target_distance=race_data["distance"],
                    ),
                    "time_index": factors["time_index"].calculate(
                        horse_id,
                        past_results,
                        target_surface=race_data["surface"],
                        target_distance=race_data["distance"],
                    ),
                    "last_3f": factors["last_3f"].calculate(horse_id, past_results),
                    "popularity": factors["popularity"].calculate(
                        horse_id,
                        [],
                        odds=horse_data.get("odds"),
                        popularity=horse_data.get("popularity"),
                    ),
                    "pedigree": factors["pedigree"].calculate(
                        horse_id,
                        [],
                        sire=horse.sire if horse else None,
                        dam_sire=horse.dam_sire if horse else None,
                        target_surface=race_data["surface"],
                        target_distance=race_data["distance"],
                    ),
                    "running_style": factors["running_style"].calculate(
                        horse_id,
                        past_results,
                        passing_order=horse_data.get("passing_order"),
                        course=race_data["venue"],
                        distance=race_data["distance"],
                    ),
                }

                total_score = calculator.calculate_total(factor_scores)

                # ML用特徴量を構築
                if self._model is not None:
                    past_stats = self._calculate_past_stats(past_results, race_date)
                    race_result_data = {
                        "horse_id": horse_id,
                        "odds": horse_data.get("odds"),
                        "popularity": horse_data.get("popularity"),
                        "weight": horse_data.get("weight"),
                        "weight_diff": horse_data.get("weight_diff"),
                        "age": horse_data.get("age"),
                        "impost": horse_data.get("impost"),
                        "horse_number": horse_data["horse_number"],
                    }
                    features = feature_builder.build_features(
                        race_result=race_result_data,
                        factor_scores=factor_scores,
                        field_size=len(race_data["horses"]),
                        past_stats=past_stats,
                    )
                    feature_names = feature_builder.get_feature_names()
                    ml_features.append([features[name] for name in feature_names])
                    horse_ids.append(horse_id)

                predictions.append(
                    {
                        "horse_number": horse_data["horse_number"],
                        "horse_name": horse_data["horse_name"],
                        "horse_id": horse_id,
                        "actual_rank": horse_data["actual_rank"],
                        "total_score": total_score,
                        "ml_probability": None,
                    }
                )

        # ML予測を実行
        if self._model is not None and ml_features:
            X = np.array(ml_features)
            probabilities = self._model.predict_proba(X)[:, 1]

            # 予測確率をマージ
            for i, pred in enumerate(predictions):
                pred["ml_probability"] = float(probabilities[i])

        # ファクタースコアでランキング
        sorted_by_factor = sorted(
            predictions, key=lambda x: x["total_score"] or 0, reverse=True
        )
        for rank, pred in enumerate(sorted_by_factor, 1):
            pred["factor_rank"] = rank

        # ML確率でランキング
        if self._model is not None:
            sorted_by_ml = sorted(
                predictions, key=lambda x: x["ml_probability"] or 0, reverse=True
            )
            for rank, pred in enumerate(sorted_by_ml, 1):
                pred["ml_rank"] = rank
        else:
            for pred in predictions:
                pred["ml_rank"] = None

        # PredictionResultに変換
        return [
            PredictionResult(
                horse_number=p["horse_number"],
                horse_name=p["horse_name"],
                ml_probability=p["ml_probability"],
                ml_rank=p["ml_rank"],
                factor_rank=p["factor_rank"],
                actual_rank=p["actual_rank"],
            )
            for p in predictions
        ]

    def _predict_race(self, race_id: str) -> RaceBacktestResult:
        """1レースの予測を行う

        Args:
            race_id: レースID

        Returns:
            レースのバックテスト結果
        """
        race_data = self._get_race_data(race_id)

        if not race_data:
            return RaceBacktestResult(
                race_id=race_id,
                race_date="",
                race_name="",
                venue="",
                predictions=[],
            )

        predictions = self._calculate_predictions(race_data)

        return RaceBacktestResult(
            race_id=race_data["race_id"],
            race_date=race_data["race_date"],
            race_name=race_data["race_name"],
            venue=race_data["venue"],
            predictions=predictions,
        )

    def run(self) -> Iterator[RaceBacktestResult]:
        """バックテストを実行し、結果をyield

        時系列順にレースを処理し、
        必要に応じて再学習を行いながら予測を行う。

        Yields:
            各レースのバックテスト結果
        """
        races = self._get_races_in_period()

        if not races:
            return

        for race in races:
            race_date = race["race_date"]

            # 再学習判定
            if self._should_retrain(race_date):
                self._train_model(race_date)
                self._last_train_date = race_date

            # 予測
            result = self._predict_race(race["race_id"])
            yield result
