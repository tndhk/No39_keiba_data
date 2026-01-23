"""バックテストエンジンモジュール

ML予測と7ファクター予測の時系列バックテストを実行する
"""

from contextlib import contextmanager
from datetime import date, datetime
from typing import TYPE_CHECKING, Generator, Iterator, Literal

from sqlalchemy.orm import Session

from keiba.backtest.cache import FactorCache
from keiba.backtest.factor_calculator import (
    CachedFactorCalculator,
    FactorCalculationContext,
)
from keiba.backtest.metrics import PredictionResult, RaceBacktestResult

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from keiba.models import Horse, Race, RaceResult

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

    # 定数
    MIN_TRAINING_SAMPLES = 100  # 最小学習データ数
    MAX_PAST_RESULTS_PER_HORSE = 20  # 馬の最大過去成績取得数
    DEFAULT_FINISH_POSITION = 99  # デフォルトの着順（未着）

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
        self._db_engine: "Engine | None" = None
        self._session: Session | None = None
        self._factor_cache = FactorCache()
        self._factor_calculator = CachedFactorCalculator(self._factor_cache)

    def _open_session(self) -> None:
        """DBセッションを開始して保持する"""
        if self._session is not None:
            return  # 既にセッションがある場合は何もしない

        from keiba.db import get_engine

        self._db_engine = get_engine(self.db_path)
        self._session = Session(self._db_engine)

    def _close_session(self) -> None:
        """DBセッションを閉じる"""
        if self._session is not None:
            self._session.close()
            self._session = None
        if self._db_engine is not None:
            self._db_engine.dispose()
            self._db_engine = None

    @contextmanager
    def _with_session(
        self, session: Session | None = None
    ) -> Generator[Session, None, None]:
        """セッション管理用コンテキストマネージャー

        sessionが渡された場合はそのまま使用（クローズしない）。
        Noneの場合は新規作成し、使用後にクローズする。

        Args:
            session: 既存のセッション（Noneの場合は新規作成）

        Yields:
            使用可能なセッション
        """
        if session is not None:
            yield session
        else:
            from keiba.db import get_engine

            engine = get_engine(self.db_path)
            new_session = Session(engine)
            try:
                yield new_session
            finally:
                new_session.close()
                engine.dispose()

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

    def _get_training_races(
        self, cutoff_date: str, session: Session | None = None
    ) -> list[dict]:
        """学習用のレースデータを取得

        Args:
            cutoff_date: カットオフ日（この日より前のデータのみ取得）
            session: SQLAlchemyセッション（Noneの場合は新規作成）

        Returns:
            レースデータのリスト
        """
        from sqlalchemy import select

        from keiba.models import Race

        cutoff = _parse_date(cutoff_date)

        with self._with_session(session) as sess:
            stmt = select(Race).where(Race.date < cutoff).order_by(Race.date.desc())
            races = sess.execute(stmt).scalars().all()
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

    def _train_model(self, cutoff_date: str, session: Session | None = None) -> None:
        """cutoff_dateより前のデータでモデルを学習

        Args:
            cutoff_date: カットオフ日（この日より前のデータのみ使用）
            session: SQLAlchemyセッション（Noneの場合は新規作成）
        """
        # 再学習時にキャッシュをクリア（古い計算結果との整合性を保つため）
        self._factor_cache.clear()

        if not self._is_lightgbm_available():
            self._model = None
            return

        # 学習データを取得
        training_races = self._get_training_races(cutoff_date, session=session)

        if not training_races:
            self._model = None
            return

        # cli.pyの_build_training_dataパターンを参考に実装
        try:
            import numpy as np

            from keiba.ml.feature_builder import FeatureBuilder
            from keiba.ml.trainer import Trainer

            cutoff = _parse_date(cutoff_date)

            with self._with_session(session) as sess:
                features_list, labels = self._build_training_data(sess, cutoff)

                if len(features_list) < self.MIN_TRAINING_SAMPLES:
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

        except Exception as e:
            import logging
            logging.warning(f"Model training failed: {e}")
            self._model = None

    def _get_past_races_for_training(
        self, target_date: date, session: Session
    ) -> list["Race"]:
        """学習用の過去レースを取得

        Args:
            target_date: 対象レース日（この日より前のデータを使用）
            session: SQLAlchemyセッション

        Returns:
            過去レースのリスト（日付降順）
        """
        from keiba.models import Race

        return (
            session.query(Race)
            .filter(Race.date < target_date)
            .order_by(Race.date.desc())
            .all()
        )

    def _prepare_horse_data_for_race(
        self,
        race_results: list["RaceResult"],
        session: Session,
        target_date: date | None = None,
    ) -> dict[str, tuple["Horse | None", list[dict], list[str]]]:
        """レース出走馬のデータをバッチ取得

        Args:
            race_results: レース結果リスト
            session: SQLAlchemyセッション
            target_date: この日より前のレースのみ取得（データリーク防止）

        Returns:
            {horse_id: (Horse, past_results, past_race_ids)} の辞書
        """
        # レース内の全馬のhorse_idを収集（中止馬を除く）
        horse_ids = [r.horse_id for r in race_results if r.finish_position != 0]

        # バッチで過去成績を取得（N+1問題解消、日付フィルタ付き）
        horses_past_results = self._get_horses_past_results_batch(
            session, horse_ids, target_date=target_date
        )

        # バッチで馬情報を取得（N+1問題解消）
        horses_batch = self._get_horses_batch(session, horse_ids)

        # 結果を統合
        result: dict[str, tuple["Horse | None", list[dict], list[str]]] = {}
        for horse_id in horse_ids:
            horse = horses_batch.get(horse_id)
            past_results = horses_past_results.get(horse_id, [])
            past_race_ids = [r.get("race_id", "") for r in past_results]
            result[horse_id] = (horse, past_results, past_race_ids)

        return result

    def _create_factor_context_for_training(
        self,
        result: "RaceResult",
        race: "Race",
        horse_data: tuple["Horse | None", list[dict], list[str]],
    ) -> FactorCalculationContext:
        """学習データ用のFactorCalculationContextを生成

        Args:
            result: レース結果
            race: レース情報
            horse_data: (Horse, past_results, past_race_ids) のタプル

        Returns:
            FactorCalculationContext
        """
        horse, past_results, past_race_ids = horse_data

        return FactorCalculationContext(
            horse_id=result.horse_id,
            past_results=past_results,
            past_race_ids=past_race_ids,
            horse=horse,
            race_surface=race.surface,
            race_distance=race.distance,
            race_venue=race.course,
            odds=result.odds,
            popularity=result.popularity,
            passing_order=None,  # 予測時との一貫性のため None
        )

    def _build_training_data(
        self, session: Session, target_date: date
    ) -> tuple[list[dict], list[int]]:
        """ML学習用のデータを構築する

        Args:
            session: SQLAlchemyセッション
            target_date: 対象レース日（この日より前のデータを使用）

        Returns:
            (特徴量リスト, ラベルリスト)のタプル
        """
        from keiba.ml.feature_builder import FeatureBuilder
        from keiba.models import RaceResult

        # 対象日より前のレースを取得
        past_races = self._get_past_races_for_training(target_date, session)

        if not past_races:
            return [], []

        feature_builder = FeatureBuilder()

        features_list = []
        labels = []

        for race in past_races:
            results = (
                session.query(RaceResult).filter(RaceResult.race_id == race.id).all()
            )

            field_size = len(results)

            # レース出走馬のデータをバッチ取得（日付フィルタでデータリーク防止）
            horse_data_map = self._prepare_horse_data_for_race(
                results, session, target_date=race.date
            )

            for result in results:
                # 中止（finish_position=0）は除外
                if result.finish_position == 0:
                    continue

                # horse_dataを取得（中止馬は horse_data_map に含まれない）
                horse_data = horse_data_map.get(result.horse_id)
                if horse_data is None:
                    continue

                # FactorCalculationContextを作成
                context = self._create_factor_context_for_training(
                    result, race, horse_data
                )
                factor_scores = self._factor_calculator.calculate_all(context)

                # 派生特徴量を計算
                _, past_results, _ = horse_data
                past_stats = self._calculate_past_stats(past_results, race.date)

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
            .limit(self.MAX_PAST_RESULTS_PER_HORSE)
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

    def _get_horses_past_results_batch(
        self,
        session: Session,
        horse_ids: list[str],
        max_results_per_horse: int | None = None,
        target_date: date | None = None,
    ) -> dict[str, list[dict]]:
        """複数馬の過去成績を一括取得（N+1問題解消）

        Args:
            session: DBセッション
            horse_ids: 馬IDのリスト
            max_results_per_horse: 各馬の最大取得件数（Noneの場合はクラス定数を使用）
            target_date: この日より前のレースのみ取得（Noneの場合は全て取得）

        Returns:
            dict: {horse_id: [過去成績リスト]}
        """
        from collections import defaultdict

        from sqlalchemy import func

        from keiba.models import Race, RaceResult

        # デフォルト値の設定
        if max_results_per_horse is None:
            max_results_per_horse = self.MAX_PAST_RESULTS_PER_HORSE

        # 空のリストの場合は早期リターン
        if not horse_ids:
            return {}

        # 結果を格納する辞書（存在しない馬IDは空リストで初期化）
        result: dict[str, list[dict]] = {hid: [] for hid in horse_ids}

        # Step 1: 各レースの出走頭数を事前計算するサブクエリ
        runners_subq = (
            session.query(
                RaceResult.race_id,
                func.count(RaceResult.id).label("total_runners"),
            )
            .group_by(RaceResult.race_id)
            .subquery()
        )

        # Step 2: 対象馬の全過去レース結果を取得（出走頭数付き）
        query = (
            session.query(RaceResult, Race, runners_subq.c.total_runners)
            .join(Race, RaceResult.race_id == Race.id)
            .join(runners_subq, RaceResult.race_id == runners_subq.c.race_id)
            .filter(RaceResult.horse_id.in_(horse_ids))
        )
        
        # 日付フィルタ追加（未来データ除外）
        if target_date is not None:
            query = query.filter(Race.date < target_date)
        
        query = query.order_by(RaceResult.horse_id, Race.date.desc())

        # Step 3: 各馬ごとに結果をグループ化し、max_results_per_horse件に制限
        horse_counts: dict[str, int] = defaultdict(int)

        for race_result, race_info, total_runners in query:
            horse_id = race_result.horse_id

            # max_results_per_horse件を超えたらスキップ
            if horse_counts[horse_id] >= max_results_per_horse:
                continue

            result[horse_id].append(
                {
                    "horse_id": race_result.horse_id,
                    "race_id": race_info.id,
                    "finish_position": race_result.finish_position,
                    "total_runners": total_runners,
                    "surface": race_info.surface,
                    "distance": race_info.distance,
                    "time": race_result.time,
                    "last_3f": race_result.last_3f,
                    "race_date": race_info.date,
                }
            )
            horse_counts[horse_id] += 1

        return result

    def _get_horses_batch(
        self,
        session: Session,
        horse_ids: list[str],
    ) -> dict[str, "Horse"]:
        """複数馬の情報を一括取得（N+1問題解消）

        Args:
            session: DBセッション
            horse_ids: 馬IDのリスト

        Returns:
            dict: {horse_id: Horse}
        """
        from keiba.models import Horse

        if not horse_ids:
            return {}

        horses = session.query(Horse).filter(Horse.id.in_(horse_ids)).all()
        return {horse.id: horse for horse in horses}

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
        top3 = sum(
            1
            for r in past_results
            if r.get("finish_position", self.DEFAULT_FINISH_POSITION) <= 3
        )
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

    def _get_races_in_period(self, session: Session | None = None) -> list[dict]:
        """指定期間のレースを時系列順で取得

        Args:
            session: SQLAlchemyセッション（Noneの場合は新規作成）

        Returns:
            レースデータのリスト（時系列順）
        """
        from sqlalchemy import select

        from keiba.models import Race

        start = _parse_date(self.start_date)
        end = _parse_date(self.end_date)

        with self._with_session(session) as sess:
            stmt = (
                select(Race)
                .where(Race.date >= start, Race.date <= end)
                .order_by(Race.date, Race.race_number)
            )
            races = sess.execute(stmt).scalars().all()
            return [
                {
                    "race_id": r.id,
                    "race_date": r.date.strftime("%Y-%m-%d"),
                    "race_name": r.name,
                    "venue": r.course,
                }
                for r in races
            ]

    def _get_race_data(self, race_id: str, session: Session | None = None) -> dict:
        """レースデータを取得

        Args:
            race_id: レースID
            session: SQLAlchemyセッション（Noneの場合は新規作成）

        Returns:
            レースデータの辞書
        """
        from keiba.models import Race, RaceResult

        with self._with_session(session) as sess:
            race = sess.get(Race, race_id)
            if not race:
                return {}

            results = (
                sess.query(RaceResult).filter(RaceResult.race_id == race_id).all()
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

    def _get_race_data_for_prediction(
        self, race_id: str, session: Session | None = None
    ) -> dict:
        """予測用レースデータを取得

        レースデータを取得しますが、実際の結果データ（actual_rank、passing_order）
        は除外します。これは予測時にはこれらが未来データとなるため、使用して
        はいけないためです。

        Args:
            race_id: レースID
            session: SQLAlchemyセッション（Noneの場合は新規作成）

        Returns:
            予測用レースデータの辞書（結果データを除外）
        """
        from keiba.models import Race, RaceResult

        with self._with_session(session) as sess:
            race = sess.get(Race, race_id)
            if not race:
                return {}

            results = (
                sess.query(RaceResult).filter(RaceResult.race_id == race_id).all()
            )

            horses = []
            for r in results:
                horse_name = r.horse.name if r.horse else "Unknown"
                horses.append(
                    {
                        "horse_number": r.horse_number,
                        "horse_name": horse_name,
                        "horse_id": r.horse_id,
                        "odds": r.odds,
                        "popularity": r.popularity,
                        "weight": r.weight,
                        "weight_diff": r.weight_diff,
                        "age": r.age,
                        "impost": r.impost,
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

    def _get_actual_results(
        self, race_id: str, session: Session | None = None
    ) -> dict[int, int]:
        """実際の着順を取得（評価用）

        Args:
            race_id: レースID
            session: SQLAlchemyセッション（Noneの場合は新規作成）

        Returns:
            馬番 -> 着順 のマッピング
        """
        from keiba.models import RaceResult

        with self._with_session(session) as sess:
            results = (
                sess.query(RaceResult).filter(RaceResult.race_id == race_id).all()
            )

            return {
                r.horse_number: r.finish_position
                for r in results
            }

    def _rank_by_factor_score(self, horses_data: list[dict]) -> list[dict]:
        """ファクタースコアでランキング付け

        Args:
            horses_data: 馬データのリスト（各要素に total_score を含む）

        Returns:
            factor_rank を追加した馬データのリスト
        """
        if not horses_data:
            return []

        # スコアが高い順にソート（Noneは0として扱う）
        sorted_by_factor = sorted(
            horses_data, key=lambda x: x.get("total_score") or 0, reverse=True
        )

        # ランキングを付与
        for rank, horse in enumerate(sorted_by_factor, 1):
            horse["factor_rank"] = rank

        return horses_data

    def _rank_by_ml_probability(self, horses_data: list[dict]) -> list[dict]:
        """ML予測確率でランキング付け

        Args:
            horses_data: 馬データのリスト（各要素に ml_probability を含む）

        Returns:
            ml_rank を追加した馬データのリスト
        """
        if not horses_data:
            return []

        # 全てNoneの場合は全馬にNoneを設定
        has_valid_probability = any(
            h.get("ml_probability") is not None for h in horses_data
        )

        if not has_valid_probability:
            for horse in horses_data:
                horse["ml_rank"] = None
            return horses_data

        # 有効な確率を持つ馬のみソート
        valid_horses = [
            h for h in horses_data if h.get("ml_probability") is not None
        ]
        sorted_by_ml = sorted(
            valid_horses, key=lambda x: x["ml_probability"], reverse=True
        )

        # 有効な馬にランキングを付与
        for rank, horse in enumerate(sorted_by_ml, 1):
            horse["ml_rank"] = rank

        # Noneの馬にはNoneを設定
        for horse in horses_data:
            if horse.get("ml_probability") is None:
                horse["ml_rank"] = None

        return horses_data

    def _convert_to_prediction_results(
        self, horses_data: list[dict], race_data: dict
    ) -> list[PredictionResult]:
        """内部データ構造をPredictionResultオブジェクトに変換

        Args:
            horses_data: 馬データのリスト（ランキング情報を含む）
            race_data: レースデータ

        Returns:
            PredictionResultオブジェクトのリスト
        """
        return [
            PredictionResult(
                horse_number=p["horse_number"],
                horse_name=p["horse_name"],
                ml_probability=p.get("ml_probability"),
                ml_rank=p.get("ml_rank"),
                factor_rank=p["factor_rank"],
                actual_rank=p.get("actual_rank") or 99,  # None の場合は 99
            )
            for p in horses_data
        ]

    def _calculate_predictions(
        self, race_data: dict, session: Session | None = None
    ) -> list[PredictionResult]:
        """予測を計算

        Args:
            race_data: レースデータ
            session: SQLAlchemyセッション（Noneの場合は新規作成）

        Returns:
            予測結果リスト
        """
        import numpy as np

        from keiba.analyzers.score_calculator import ScoreCalculator
        from keiba.ml.feature_builder import FeatureBuilder

        calculator = ScoreCalculator()
        feature_builder = FeatureBuilder()

        predictions = []
        ml_features = []
        horse_ids = []

        race_date = _parse_date(race_data["race_date"])

        with self._with_session(session) as sess:
            # 全馬のhorse_idを収集
            all_horse_ids = [
                horse_data["horse_id"] for horse_data in race_data.get("horses", [])
            ]

            # バッチで過去成績を取得（N+1問題解消、日付フィルタでデータリーク防止）
            horses_past_results = self._get_horses_past_results_batch(
                sess, all_horse_ids, target_date=race_date
            )

            # バッチで馬情報を取得（N+1問題解消）
            horses_batch = self._get_horses_batch(sess, all_horse_ids)

            for horse_data in race_data.get("horses", []):
                horse_id = horse_data["horse_id"]

                # バッチ取得した過去成績を使用
                past_results = horses_past_results.get(horse_id, [])

                # バッチ取得した馬情報を使用
                horse = horses_batch.get(horse_id)

                # キャッシュキー生成用の過去レースID
                past_race_ids = [r.get("race_id", "") for r in past_results]

                # CachedFactorCalculatorを使用してファクターを計算
                context = FactorCalculationContext(
                    horse_id=horse_id,
                    past_results=past_results,
                    past_race_ids=past_race_ids,
                    horse=horse,
                    race_surface=race_data["surface"],
                    race_distance=race_data["distance"],
                    race_venue=race_data["venue"],
                    odds=horse_data.get("odds"),
                    popularity=horse_data.get("popularity"),
                    passing_order=None,  # 当該レースの通過順位は未来データのため使用しない
                )
                factor_scores = self._factor_calculator.calculate_all(context)

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
                        "actual_rank": None,  # 予測時点では不明、後でマージ
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

            # ヘルパーメソッドでランキング付け
            self._rank_by_factor_score(predictions)
            self._rank_by_ml_probability(predictions)

            # PredictionResultに変換
            return self._convert_to_prediction_results(predictions, race_data)

    def _predict_race(
        self, race_id: str, session: Session | None = None
    ) -> RaceBacktestResult:
        """1レースの予測を行う

        Args:
            race_id: レースID
            session: SQLAlchemyセッション（Noneの場合は新規作成）

        Returns:
            レースのバックテスト結果
        """
        # 予測用データ取得（未来データを除外）
        race_data = self._get_race_data_for_prediction(race_id, session=session)

        if not race_data:
            return RaceBacktestResult(
                race_id=race_id,
                race_date="",
                race_name="",
                venue="",
                predictions=[],
            )

        predictions = self._calculate_predictions(race_data, session=session)

        # 予測後に実際の着順をマージ
        actual_results = self._get_actual_results(race_id, session=session)
        for pred in predictions:
            pred.actual_rank = actual_results.get(pred.horse_number, 99)

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
        try:
            self._open_session()

            races = self._get_races_in_period(session=self._session)

            if not races:
                return

            for race in races:
                race_date = race["race_date"]

                # 再学習判定
                if self._should_retrain(race_date):
                    self._train_model(race_date, session=self._session)
                    self._last_train_date = race_date

                # 予測
                result = self._predict_race(race["race_id"], session=self._session)
                yield result
        finally:
            self._close_session()
