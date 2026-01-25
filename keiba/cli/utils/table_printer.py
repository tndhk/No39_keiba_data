"""テーブル表示ユーティリティ"""

import click


def print_score_table(scores: list[dict]) -> None:
    """スコアテーブルを表示する

    Args:
        scores: スコアリスト
    """
    # ヘッダー
    click.echo(
        f"{'順位':^4} | {'馬番':^4} | {'馬名':^12} | {'総合':^6} | {'過去':^6} | "
        f"{'適性':^6} | {'タイム':^6} | {'上がり':^6} | {'人気':^6}"
    )
    click.echo("-" * 82)

    # 各馬のスコア
    for rank, score in enumerate(scores, 1):
        total = f"{score['total']:.1f}" if score["total"] is not None else "-"
        past = f"{score['past_results']:.1f}" if score["past_results"] is not None else "-"
        course = f"{score['course_fit']:.1f}" if score["course_fit"] is not None else "-"
        time_idx = f"{score['time_index']:.1f}" if score["time_index"] is not None else "-"
        last_3f = f"{score['last_3f']:.1f}" if score["last_3f"] is not None else "-"
        pop = f"{score['popularity']:.1f}" if score["popularity"] is not None else "-"

        # 馬名を12文字に切り詰め
        horse_name = score["horse_name"][:12] if len(score["horse_name"]) > 12 else score["horse_name"]

        click.echo(
            f"{rank:^4} | {score['horse_number']:^4} | {horse_name:^12} | "
            f"{total:^6} | {past:^6} | {course:^6} | {time_idx:^6} | {last_3f:^6} | {pop:^6}"
        )


def print_score_table_with_ml(scores: list[dict], with_ml: bool) -> None:
    """スコアテーブルを表示する（ML予測付き）

    Args:
        scores: スコアリスト
        with_ml: ML予測を含むかどうか
    """
    if with_ml:
        # ML予測あり
        click.echo(
            f"{'予測':^4} | {'馬番':^4} | {'馬名':^12} | {'3着内確率':^8} | "
            f"{'総合':^6} | {'過去':^6} | {'適性':^6} | {'タイム':^6} | {'上がり':^6} | {'人気':^6}"
        )
        click.echo("-" * 100)

        for score in scores:
            rank = f"{score['ml_rank']}" if score["ml_rank"] else "-"
            prob = f"{score['probability']:.1%}" if score["probability"] is not None else "-"
            total = f"{score['total']:.1f}" if score["total"] is not None else "-"
            past = f"{score['past_results']:.1f}" if score["past_results"] is not None else "-"
            course = f"{score['course_fit']:.1f}" if score["course_fit"] is not None else "-"
            time_idx = f"{score['time_index']:.1f}" if score["time_index"] is not None else "-"
            last_3f = f"{score['last_3f']:.1f}" if score["last_3f"] is not None else "-"
            pop = f"{score['popularity']:.1f}" if score["popularity"] is not None else "-"

            horse_name = score["horse_name"][:12] if len(score["horse_name"]) > 12 else score["horse_name"]

            click.echo(
                f"{rank:^4} | {score['horse_number']:^4} | {horse_name:^12} | "
                f"{prob:^8} | {total:^6} | {past:^6} | {course:^6} | {time_idx:^6} | {last_3f:^6} | {pop:^6}"
            )

        # 確率50%以上の馬数
        high_prob_count = sum(1 for s in scores if s["probability"] and s["probability"] >= 0.5)
        if high_prob_count > 0:
            click.echo(f"\n※ 確率50%以上: {high_prob_count}頭")
    else:
        # 従来のスコアのみ表示
        print_score_table(scores)


def print_prediction_table(predictions: list, with_ml: bool) -> None:
    """予測結果テーブルを表示する

    Args:
        predictions: PredictionResultのリスト
        with_ml: ML予測を含むかどうか
    """
    if with_ml:
        # ML予測あり
        click.echo(
            f"{'順位':^4} | {'馬番':^4} | {'馬名':^12} | {'ML確率':^8} | {'複合':^6} | "
            f"{'総合':^6} | {'過去':^6} | {'適性':^6} | {'指数':^6} | {'上り':^6} | "
            f"{'人気':^6} | {'血統':^6} | {'脚質':^6}"
        )
        click.echo("-" * 122)

        for pred in predictions:
            rank = f"{pred.rank}"
            prob = f"{pred.ml_probability:.1%}" if pred.ml_probability > 0 else "-"
            combined = (
                f"{pred.combined_score:.1f}"
                if pred.combined_score is not None
                else "-"
            )
            total = f"{pred.total_score:.1f}" if pred.total_score is not None else "-"
            past = (
                f"{pred.factor_scores.get('past_results', 0):.1f}"
                if pred.factor_scores.get("past_results") is not None
                else "-"
            )
            course = (
                f"{pred.factor_scores.get('course_fit', 0):.1f}"
                if pred.factor_scores.get("course_fit") is not None
                else "-"
            )
            time_idx = (
                f"{pred.factor_scores.get('time_index', 0):.1f}"
                if pred.factor_scores.get("time_index") is not None
                else "-"
            )
            last_3f = (
                f"{pred.factor_scores.get('last_3f', 0):.1f}"
                if pred.factor_scores.get("last_3f") is not None
                else "-"
            )
            pop = (
                f"{pred.factor_scores.get('popularity', 0):.1f}"
                if pred.factor_scores.get("popularity") is not None
                else "-"
            )
            pedigree = (
                f"{pred.factor_scores.get('pedigree', 0):.1f}"
                if pred.factor_scores.get("pedigree") is not None
                else "-"
            )
            running = (
                f"{pred.factor_scores.get('running_style', 0):.1f}"
                if pred.factor_scores.get("running_style") is not None
                else "-"
            )

            # 馬名を12文字に切り詰め
            horse_name = (
                pred.horse_name[:12]
                if len(pred.horse_name) > 12
                else pred.horse_name
            )

            click.echo(
                f"{rank:^4} | {pred.horse_number:^4} | {horse_name:^12} | "
                f"{prob:^8} | {combined:^6} | {total:^6} | {past:^6} | {course:^6} | {time_idx:^6} | "
                f"{last_3f:^6} | {pop:^6} | {pedigree:^6} | {running:^6}"
            )
    else:
        # 因子スコアのみ（総合スコア順でソート）
        sorted_predictions = sorted(
            predictions,
            key=lambda x: x.total_score if x.total_score is not None else 0,
            reverse=True,
        )

        click.echo(
            f"{'順位':^4} | {'馬番':^4} | {'馬名':^12} | "
            f"{'総合':^6} | {'過去':^6} | {'適性':^6} | {'指数':^6} | {'上り':^6} | "
            f"{'人気':^6} | {'血統':^6} | {'脚質':^6}"
        )
        click.echo("-" * 100)

        for rank, pred in enumerate(sorted_predictions, 1):
            total = f"{pred.total_score:.1f}" if pred.total_score is not None else "-"
            past = (
                f"{pred.factor_scores.get('past_results', 0):.1f}"
                if pred.factor_scores.get("past_results") is not None
                else "-"
            )
            course = (
                f"{pred.factor_scores.get('course_fit', 0):.1f}"
                if pred.factor_scores.get("course_fit") is not None
                else "-"
            )
            time_idx = (
                f"{pred.factor_scores.get('time_index', 0):.1f}"
                if pred.factor_scores.get("time_index") is not None
                else "-"
            )
            last_3f = (
                f"{pred.factor_scores.get('last_3f', 0):.1f}"
                if pred.factor_scores.get("last_3f") is not None
                else "-"
            )
            pop = (
                f"{pred.factor_scores.get('popularity', 0):.1f}"
                if pred.factor_scores.get("popularity") is not None
                else "-"
            )
            pedigree = (
                f"{pred.factor_scores.get('pedigree', 0):.1f}"
                if pred.factor_scores.get("pedigree") is not None
                else "-"
            )
            running = (
                f"{pred.factor_scores.get('running_style', 0):.1f}"
                if pred.factor_scores.get("running_style") is not None
                else "-"
            )

            # 馬名を12文字に切り詰め
            horse_name = (
                pred.horse_name[:12]
                if len(pred.horse_name) > 12
                else pred.horse_name
            )

            click.echo(
                f"{rank:^4} | {pred.horse_number:^4} | {horse_name:^12} | "
                f"{total:^6} | {past:^6} | {course:^6} | {time_idx:^6} | "
                f"{last_3f:^6} | {pop:^6} | {pedigree:^6} | {running:^6}"
            )
