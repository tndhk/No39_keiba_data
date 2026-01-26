#!/usr/bin/env python3
"""ファクター重要度測定スクリプト

各ファクター単体での予測力を測定し、ウェイト調整の参考データを提供する。

使用方法:
    python scripts/factor_importance.py --db data/keiba.db --from 2024-01-01 --to 2024-12-31
"""

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from scipy import stats

# keibaパッケージをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class FactorImportanceResult:
    """ファクター重要度測定結果

    Attributes:
        factor_name: ファクター名
        hit_rate_top1: Top1的中率
        hit_rate_top3: Top3的中率
        recovery_rate: 回収率（投資に対する回収の比率）
        correlation: スピアマン相関係数（スコアと着順の相関）
        sample_count: サンプル数
    """

    factor_name: str
    hit_rate_top1: float
    hit_rate_top3: float
    recovery_rate: float
    correlation: float
    sample_count: int


def calculate_factor_hit_rate(data: list[dict], top_n: int = 3) -> float:
    """ファクター単体での的中率を計算

    Args:
        data: [{"factor_score": float, "finish_position": int}, ...]
        top_n: 何着以内を的中とするか

    Returns:
        的中率（0.0-1.0）
    """
    if not data:
        return 0.0

    hits = sum(1 for d in data if d["finish_position"] <= top_n)
    return hits / len(data)


def calculate_factor_ranking_correlation(data: list[dict]) -> float:
    """ファクタースコアと着順の相関を計算

    Args:
        data: [{"factor_score": float, "finish_position": int}, ...]

    Returns:
        スピアマン相関係数（-1.0 to 1.0、負の値が良い）
    """
    if len(data) < 2:
        return 0.0

    scores = [d["factor_score"] for d in data]
    positions = [d["finish_position"] for d in data]

    correlation, _ = stats.spearmanr(scores, positions)
    return float(correlation)


def calculate_recovery_rate(data: list[dict], top_n: int = 3) -> float:
    """回収率を計算（複勝想定）

    Args:
        data: [{"factor_score": float, "finish_position": int, "odds": float}, ...]
        top_n: 何着以内を的中とするか

    Returns:
        回収率（投資に対する回収の比率）
    """
    if not data:
        return 0.0

    investment = len(data) * 100  # 1件100円投資
    returns = 0.0

    for d in data:
        if d["finish_position"] <= top_n:
            odds = d.get("odds")
            if odds is not None:
                returns += odds * 100

    if investment == 0:
        return 0.0

    return returns / investment


def measure_factor_importance(factor_name: str, data: list[dict]) -> FactorImportanceResult:
    """ファクターの重要度を総合的に測定

    Args:
        factor_name: ファクター名
        data: [{"factor_score": float, "finish_position": int, "odds": float}, ...]

    Returns:
        FactorImportanceResult
    """
    hit_rate_top1 = calculate_factor_hit_rate(data, top_n=1)
    hit_rate_top3 = calculate_factor_hit_rate(data, top_n=3)
    recovery_rate = calculate_recovery_rate(data, top_n=3)
    correlation = calculate_factor_ranking_correlation(data)

    return FactorImportanceResult(
        factor_name=factor_name,
        hit_rate_top1=hit_rate_top1,
        hit_rate_top3=hit_rate_top3,
        recovery_rate=recovery_rate,
        correlation=correlation,
        sample_count=len(data),
    )


def fetch_factor_data_from_db(
    db_path: str, factor_name: str, from_date: str | None, to_date: str | None
) -> list[dict]:
    """DBからファクターデータを取得

    Args:
        db_path: DBファイルパス
        factor_name: ファクター名
        from_date: 開始日（YYYY-MM-DD）
        to_date: 終了日（YYYY-MM-DD）

    Returns:
        [{
            "factor_score": float,
            "finish_position": int,
            "odds": float | None
        }, ...]
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from keiba.analyzers.factors import (
        CourseFitFactor,
        Last3FFactor,
        PastResultsFactor,
        PedigreeFactor,
        PopularityFactor,
        RunningStyleFactor,
        TimeIndexFactor,
    )
    from keiba.models import Horse, Race, RaceResult
    from keiba.repositories.race_result_repository import SQLAlchemyRaceResultRepository

    # ファクター名からファクタークラスをマッピング
    factor_classes = {
        "past_results": PastResultsFactor,
        "course_fit": CourseFitFactor,
        "time_index": TimeIndexFactor,
        "last_3f": Last3FFactor,
        "popularity": PopularityFactor,
        "pedigree": PedigreeFactor,
        "running_style": RunningStyleFactor,
    }

    if factor_name not in factor_classes:
        raise ValueError(f"Unknown factor: {factor_name}")

    factor = factor_classes[factor_name]()

    # DB接続
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # レース一覧を取得
        query = session.query(Race).order_by(Race.date)

        if from_date:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
            query = query.filter(Race.date >= from_dt)

        if to_date:
            to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
            query = query.filter(Race.date <= to_dt)

        races = query.all()
        results = []
        repo = SQLAlchemyRaceResultRepository(session)

        for race in races:
            # レース結果を取得
            race_results = (
                session.query(RaceResult)
                .filter(RaceResult.race_id == race.id)
                .all()
            )

            for rr in race_results:
                # 過去成績を取得
                race_date_str = race.date.strftime("%Y年%m月%d日")
                past_results = repo.get_past_results(
                    rr.horse_id, race_date_str, limit=20
                )

                if not past_results:
                    continue

                # ファクター固有のkwargs取得
                kwargs = _get_factor_kwargs(factor_name, race, rr, session)

                # ファクタースコアを計算
                score = factor.calculate(rr.horse_id, past_results, **kwargs)

                if score is not None:
                    results.append({
                        "factor_score": score,
                        "finish_position": rr.finish_position,
                        "odds": rr.odds,
                    })

        return results

    finally:
        session.close()


def _get_factor_kwargs(
    factor_name: str, race: "Race", race_result: "RaceResult", session
) -> dict:
    """ファクター計算に必要なkwargsを取得"""
    from keiba.models import Horse

    kwargs = {}

    if factor_name == "course_fit":
        kwargs["surface"] = race.surface
        kwargs["distance"] = race.distance

    elif factor_name == "time_index":
        kwargs["target_distance"] = race.distance
        kwargs["target_surface"] = race.surface

    elif factor_name == "last_3f":
        kwargs["target_distance"] = race.distance

    elif factor_name == "pedigree":
        horse = session.query(Horse).filter(Horse.id == race_result.horse_id).first()
        if horse:
            kwargs["sire"] = horse.sire
            kwargs["dam_sire"] = horse.dam_sire
        kwargs["surface"] = race.surface
        kwargs["distance"] = race.distance

    elif factor_name == "running_style":
        kwargs["target_distance"] = race.distance

    return kwargs


def print_results(results: list[FactorImportanceResult]) -> None:
    """結果を表形式で出力"""
    print("\n" + "=" * 80)
    print("                        ファクター重要度測定結果")
    print("=" * 80)
    print(
        f"{'ファクター':<16} {'Top1的中率':>10} {'Top3的中率':>10} "
        f"{'回収率':>10} {'相関係数':>10} {'サンプル数':>10}"
    )
    print("-" * 80)

    for r in sorted(results, key=lambda x: x.correlation):
        print(
            f"{r.factor_name:<16} {r.hit_rate_top1:>10.1%} {r.hit_rate_top3:>10.1%} "
            f"{r.recovery_rate:>10.1%} {r.correlation:>10.3f} {r.sample_count:>10,}"
        )

    print("=" * 80)
    print("\n[解釈ガイド]")
    print("- Top1/Top3的中率: 高いほど予測力が高い")
    print("- 回収率: 100%以上で利益が出る")
    print("- 相関係数: 負の値が良い（スコア高い=着順良い）、-1に近いほど予測力が高い")


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="ファクター重要度測定",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
    python scripts/factor_importance.py --db data/keiba.db --from 2024-01-01 --to 2024-12-31
    python scripts/factor_importance.py --db data/keiba.db --factor past_results
        """,
    )
    parser.add_argument("--db", required=True, help="DBファイルパス")
    parser.add_argument("--from", dest="from_date", help="開始日（YYYY-MM-DD）")
    parser.add_argument("--to", dest="to_date", help="終了日（YYYY-MM-DD）")
    parser.add_argument(
        "--factor",
        help="特定ファクターのみ測定（未指定で全ファクター）",
        choices=[
            "past_results",
            "course_fit",
            "time_index",
            "last_3f",
            "popularity",
            "pedigree",
            "running_style",
        ],
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="詳細出力")
    args = parser.parse_args()

    # DB存在確認
    if not Path(args.db).exists():
        print(f"Error: Database file not found: {args.db}", file=sys.stderr)
        sys.exit(1)

    # 対象ファクター
    if args.factor:
        factor_names = [args.factor]
    else:
        factor_names = [
            "past_results",
            "course_fit",
            "time_index",
            "last_3f",
            "popularity",
            "pedigree",
            "running_style",
        ]

    print(f"データベース: {args.db}")
    if args.from_date:
        print(f"開始日: {args.from_date}")
    if args.to_date:
        print(f"終了日: {args.to_date}")
    print(f"対象ファクター: {', '.join(factor_names)}")
    print("\n測定中...")

    results = []
    for factor_name in factor_names:
        if args.verbose:
            print(f"  - {factor_name} を測定中...")

        data = fetch_factor_data_from_db(
            args.db, factor_name, args.from_date, args.to_date
        )
        result = measure_factor_importance(factor_name, data)
        results.append(result)

        if args.verbose:
            print(f"    サンプル数: {result.sample_count}")

    print_results(results)


if __name__ == "__main__":
    main()
