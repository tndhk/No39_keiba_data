"""バックテストコマンド"""

from datetime import date, datetime as dt, timedelta

import click


@click.command()
@click.option("--db", required=True, type=click.Path(exists=True), help="データベースファイルパス")
@click.option("--from", "from_date", type=str, help="開始日 (YYYY-MM-DD)")
@click.option("--to", "to_date", type=str, help="終了日 (YYYY-MM-DD)")
@click.option("--months", type=int, default=1, help="直近何ヶ月を対象とするか (default: 1)")
@click.option(
    "--retrain-interval",
    type=click.Choice(["daily", "weekly", "monthly"]),
    default="weekly",
    help="再学習間隔",
)
@click.option("-v", "--verbose", is_flag=True, help="詳細表示")
def backtest(
    db: str,
    from_date: str | None,
    to_date: str | None,
    months: int,
    retrain_interval: str,
    verbose: bool,
):
    """ML予測と7ファクタースコアの精度をバックテストで検証"""
    from keiba.backtest import BacktestEngine, BacktestReporter, MetricsCalculator

    click.echo("バックテスト開始")
    click.echo(f"データベース: {db}")

    # 日付範囲を決定
    if from_date and to_date:
        try:
            start_date = dt.strptime(from_date, "%Y-%m-%d").date()
            end_date = dt.strptime(to_date, "%Y-%m-%d").date()
        except ValueError:
            click.echo("日付形式が不正です（YYYY-MM-DD形式で指定してください）")
            return
    else:
        # monthsパラメータから計算
        end_date = dt.now().date()
        start_date = end_date - timedelta(days=months * 30)

    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    click.echo(f"期間: {start_date} ~ {end_date}")
    click.echo(f"再学習間隔: {retrain_interval}")
    click.echo("")

    backtest_engine = BacktestEngine(
        db_path=db,
        start_date=start_date_str,
        end_date=end_date_str,
        retrain_interval=retrain_interval,
    )

    results = list(backtest_engine.run())
    metrics = MetricsCalculator.calculate(results)
    reporter = BacktestReporter(
        start_date=start_date_str,
        end_date=end_date_str,
        retrain_interval=retrain_interval,
    )

    if verbose:
        for race_result in results:
            detail = reporter.print_race_detail(race_result)
            click.echo(detail)
            click.echo("")

    summary = reporter.print_summary(results, metrics)
    click.echo(summary)


@click.command("backtest-fukusho")
@click.option("--from", "from_date", type=str, default=None, help="開始日（YYYY-MM-DD形式）")
@click.option("--to", "to_date", type=str, default=None, help="終了日（YYYY-MM-DD形式）")
@click.option("--last-week", is_flag=True, help="先週を対象（デフォルト）")
@click.option("--top-n", type=int, default=3, help="Top何頭に賭けるか（デフォルト: 3）")
@click.option("--venue", multiple=True, help="競馬場フィルタ（複数可）")
@click.option("--db", required=True, type=click.Path(exists=True), help="DBファイルパス")
@click.option("-v", "--verbose", is_flag=True, help="レース別詳細表示")
def backtest_fukusho(
    from_date: str | None,
    to_date: str | None,
    last_week: bool,
    top_n: int,
    venue: tuple[str, ...],
    db: str,
    verbose: bool,
):
    """複勝馬券のバックテストシミュレーションを実行する"""
    from keiba.backtest.fukusho_simulator import FukushoSimulator

    # 日付範囲の決定
    if last_week or (from_date is None and to_date is None):
        # 先週の月曜日から日曜日
        today = date.today()
        # 今週の月曜日を取得
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        # 先週の月曜日と日曜日
        last_monday = this_monday - timedelta(days=7)
        last_sunday = this_monday - timedelta(days=1)
        from_date = last_monday.strftime("%Y-%m-%d")
        to_date = last_sunday.strftime("%Y-%m-%d")
    elif from_date is None or to_date is None:
        click.echo("--from と --to の両方を指定してください")
        raise SystemExit(1)

    # 日付の検証
    try:
        dt.strptime(from_date, "%Y-%m-%d")
        dt.strptime(to_date, "%Y-%m-%d")
    except ValueError:
        click.echo("日付形式が不正です（YYYY-MM-DD形式で指定してください）")
        raise SystemExit(1)

    # 会場リストの準備
    venues = list(venue) if venue else None

    # シミュレーション実行
    click.echo("=" * 40)
    click.echo(f"複勝シミュレーション: {from_date} ~ {to_date}")
    click.echo("=" * 40)

    simulator = FukushoSimulator(db)
    summary = simulator.simulate_period(
        from_date=from_date,
        to_date=to_date,
        venues=venues,
        top_n=top_n,
    )

    # 詳細表示
    if verbose:
        click.echo("")
        click.echo("レース別結果:")
        click.echo("-" * 60)
        for result in summary.race_results:
            hit_mark = "○" if result.hits else "×"
            click.echo(
                f"{result.race_date} {result.venue} {result.race_name}: "
                f"予測{result.top_n_predictions} -> "
                f"的中{result.hits} ({hit_mark}) "
                f"払戻{result.payout_total}円"
            )
        click.echo("")

    # サマリー表示
    click.echo(f"対象レース数: {summary.total_races}")
    click.echo("")
    click.echo(f"予測Top{top_n}に各100円賭けた場合:")
    click.echo(f"  総賭け数: {summary.total_bets}")
    click.echo(f"  的中数: {summary.total_hits}")
    click.echo(f"  的中率: {summary.hit_rate * 100:.1f}%")
    click.echo(f"  投資額: {summary.total_investment:,}円")
    click.echo(f"  払戻額: {summary.total_payout:,}円")
    click.echo(f"  回収率: {summary.return_rate * 100:.1f}%")
    click.echo("-" * 40)


@click.command("backtest-tansho")
@click.option("--from", "from_date", type=str, default=None, help="開始日（YYYY-MM-DD形式）")
@click.option("--to", "to_date", type=str, default=None, help="終了日（YYYY-MM-DD形式）")
@click.option("--last-week", is_flag=True, help="先週を対象（デフォルト）")
@click.option("--top-n", type=int, default=3, help="Top何頭に賭けるか（デフォルト: 3）")
@click.option("--venue", multiple=True, help="競馬場フィルタ（複数可）")
@click.option("--db", required=True, type=click.Path(exists=True), help="DBファイルパス")
@click.option("-v", "--verbose", is_flag=True, help="レース別詳細表示")
def backtest_tansho(
    from_date: str | None,
    to_date: str | None,
    last_week: bool,
    top_n: int,
    venue: tuple[str, ...],
    db: str,
    verbose: bool,
):
    """単勝馬券のバックテストシミュレーションを実行する"""
    from keiba.backtest.tansho_simulator import TanshoSimulator

    # 日付範囲の決定
    if last_week or (from_date is None and to_date is None):
        # 先週の月曜日から日曜日
        today = date.today()
        # 今週の月曜日を取得
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        # 先週の月曜日と日曜日
        last_monday = this_monday - timedelta(days=7)
        last_sunday = this_monday - timedelta(days=1)
        from_date = last_monday.strftime("%Y-%m-%d")
        to_date = last_sunday.strftime("%Y-%m-%d")
    elif from_date is None or to_date is None:
        click.echo("--from と --to の両方を指定してください")
        raise SystemExit(1)

    # 日付の検証
    try:
        dt.strptime(from_date, "%Y-%m-%d")
        dt.strptime(to_date, "%Y-%m-%d")
    except ValueError:
        click.echo("日付形式が不正です（YYYY-MM-DD形式で指定してください）")
        raise SystemExit(1)

    # 会場リストの準備
    venues = list(venue) if venue else None

    # シミュレーション実行
    click.echo("=" * 40)
    click.echo(f"単勝シミュレーション: {from_date} ~ {to_date}")
    click.echo("=" * 40)

    simulator = TanshoSimulator(db)
    summary = simulator.simulate_period(
        from_date=from_date,
        to_date=to_date,
        venues=venues,
        top_n=top_n,
    )

    # 詳細表示
    if verbose:
        click.echo("")
        click.echo("レース別結果:")
        click.echo("-" * 60)
        for result in summary.race_results:
            hit_mark = "○" if result.hit else "×"
            click.echo(
                f"{result.race_date} {result.venue} {result.race_name}: "
                f"予測{result.top_n_predictions} -> "
                f"1着{result.winning_horse} ({hit_mark}) "
                f"払戻{result.payout}円"
            )
        click.echo("")

    # サマリー表示
    click.echo(f"対象レース数: {summary.total_races}")
    click.echo("")
    click.echo(f"予測Top{top_n}に各100円賭けた場合:")
    click.echo(f"  総賭け数: {summary.total_bets}")
    click.echo(f"  的中数: {summary.total_hits}")
    click.echo(f"  的中率: {summary.hit_rate * 100:.1f}%")
    click.echo(f"  投資額: {summary.total_investment:,}円")
    click.echo(f"  払戻額: {summary.total_payout:,}円")
    click.echo(f"  回収率: {summary.return_rate * 100:.1f}%")
    click.echo("-" * 40)


@click.command("backtest-umaren")
@click.option("--from", "from_date", type=str, default=None, help="開始日（YYYY-MM-DD形式）")
@click.option("--to", "to_date", type=str, default=None, help="終了日（YYYY-MM-DD形式）")
@click.option("--last-week", is_flag=True, help="先週を対象（デフォルト）")
@click.option("--venue", multiple=True, help="競馬場フィルタ（複数可）")
@click.option("--db", required=True, type=click.Path(exists=True), help="DBファイルパス")
@click.option("-v", "--verbose", is_flag=True, help="レース別詳細表示")
def backtest_umaren(
    from_date: str | None,
    to_date: str | None,
    last_week: bool,
    venue: tuple[str, ...],
    db: str,
    verbose: bool,
):
    """馬連馬券のバックテストシミュレーションを実行する"""
    from keiba.backtest.umaren_simulator import UmarenSimulator

    # 日付範囲の決定
    if last_week or (from_date is None and to_date is None):
        # 先週の月曜日から日曜日
        today = date.today()
        # 今週の月曜日を取得
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        # 先週の月曜日と日曜日
        last_monday = this_monday - timedelta(days=7)
        last_sunday = this_monday - timedelta(days=1)
        from_date = last_monday.strftime("%Y-%m-%d")
        to_date = last_sunday.strftime("%Y-%m-%d")
    elif from_date is None or to_date is None:
        click.echo("--from と --to の両方を指定してください")
        raise SystemExit(1)

    # 日付の検証
    try:
        dt.strptime(from_date, "%Y-%m-%d")
        dt.strptime(to_date, "%Y-%m-%d")
    except ValueError:
        click.echo("日付形式が不正です（YYYY-MM-DD形式で指定してください）")
        raise SystemExit(1)

    # 会場リストの準備
    venues = list(venue) if venue else None

    # シミュレーション実行
    click.echo("=" * 40)
    click.echo(f"馬連シミュレーション: {from_date} ~ {to_date}")
    click.echo("=" * 40)

    simulator = UmarenSimulator(db)
    summary = simulator.simulate_period(
        from_date=from_date,
        to_date=to_date,
        venues=venues,
    )

    # 詳細表示
    if verbose:
        click.echo("")
        click.echo("レース別結果:")
        click.echo("-" * 60)
        for result in summary.race_results:
            hit_mark = "○" if result.hit else "×"
            click.echo(
                f"{result.race_date} {result.venue} {result.race_name}: "
                f"購入{result.bet_combinations} -> "
                f"結果{result.actual_pair} ({hit_mark}) "
                f"払戻{result.payout}円"
            )
        click.echo("")

    # サマリー表示
    click.echo(f"対象レース数: {summary.total_races}")
    click.echo("")
    click.echo("予測Top3から3点買いした場合:")
    click.echo(f"  的中数: {summary.total_hits}")
    click.echo(f"  的中率: {summary.hit_rate * 100:.1f}%")
    click.echo(f"  投資額: {summary.total_investment:,}円")
    click.echo(f"  払戻額: {summary.total_payout:,}円")
    click.echo(f"  回収率: {summary.return_rate * 100:.1f}%")
    click.echo("-" * 40)


@click.command("backtest-sanrenpuku")
@click.option("--from", "from_date", type=str, default=None, help="開始日（YYYY-MM-DD形式）")
@click.option("--to", "to_date", type=str, default=None, help="終了日（YYYY-MM-DD形式）")
@click.option("--last-week", is_flag=True, help="先週を対象（デフォルト）")
@click.option("--venue", multiple=True, help="競馬場フィルタ（複数可）")
@click.option("--db", required=True, type=click.Path(exists=True), help="DBファイルパス")
@click.option("-v", "--verbose", is_flag=True, help="レース別詳細表示")
def backtest_sanrenpuku(
    from_date: str | None,
    to_date: str | None,
    last_week: bool,
    venue: tuple[str, ...],
    db: str,
    verbose: bool,
):
    """三連複馬券のバックテストシミュレーションを実行する"""
    from keiba.backtest.sanrenpuku_simulator import SanrenpukuSimulator

    # 日付範囲の決定
    if last_week or (from_date is None and to_date is None):
        # 先週の月曜日から日曜日
        today = date.today()
        # 今週の月曜日を取得
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        # 先週の月曜日と日曜日
        last_monday = this_monday - timedelta(days=7)
        last_sunday = this_monday - timedelta(days=1)
        from_date = last_monday.strftime("%Y-%m-%d")
        to_date = last_sunday.strftime("%Y-%m-%d")
    elif from_date is None or to_date is None:
        click.echo("--from と --to の両方を指定してください")
        raise SystemExit(1)

    # 日付の検証
    try:
        dt.strptime(from_date, "%Y-%m-%d")
        dt.strptime(to_date, "%Y-%m-%d")
    except ValueError:
        click.echo("日付形式が不正です（YYYY-MM-DD形式で指定してください）")
        raise SystemExit(1)

    # 会場リストの準備
    venues = list(venue) if venue else None

    # シミュレーション実行
    click.echo("=" * 40)
    click.echo(f"三連複シミュレーション: {from_date} ~ {to_date}")
    click.echo("=" * 40)

    simulator = SanrenpukuSimulator(db)
    summary = simulator.simulate_period(
        from_date=from_date,
        to_date=to_date,
        venues=venues,
    )

    # 詳細表示
    if verbose:
        click.echo("")
        click.echo("レース別結果:")
        click.echo("-" * 60)
        for result in summary.race_results:
            hit_mark = "○" if result.hit else "×"
            click.echo(
                f"{result.race_date} {result.venue} {result.race_name}: "
                f"予測{result.bet_combination} -> "
                f"結果{result.actual_combination} ({hit_mark}) "
                f"払戻{result.payout}円"
            )
        click.echo("")

    # サマリー表示
    click.echo(f"対象レース数: {summary.total_races}")
    click.echo("")
    click.echo("予測Top3の1点買いした場合:")
    click.echo(f"  的中数: {summary.total_hits}")
    click.echo(f"  的中率: {summary.hit_rate * 100:.1f}%")
    click.echo(f"  投資額: {summary.total_investment:,}円")
    click.echo(f"  払戻額: {summary.total_payout:,}円")
    click.echo(f"  回収率: {summary.return_rate * 100:.1f}%")
    click.echo("-" * 40)
