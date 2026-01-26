"""バックテストコマンド"""

from datetime import date, datetime as dt, timedelta

import click

from keiba.backtest.fukusho_simulator import FukushoSimulator
from keiba.backtest.tansho_simulator import TanshoSimulator
from keiba.backtest.umaren_simulator import UmarenSimulator
from keiba.backtest.sanrenpuku_simulator import SanrenpukuSimulator


def _get_display_width(text: str) -> int:
    """文字列の表示幅を計算（全角文字は2、半角は1）

    Args:
        text: 計算対象の文字列

    Returns:
        int: 表示幅
    """
    import unicodedata

    width = 0
    for char in text:
        east_asian_width = unicodedata.east_asian_width(char)
        if east_asian_width in ("F", "W", "A"):  # Full, Wide, Ambiguous
            width += 2
        else:
            width += 1
    return width


def _pad_to_width(text: str, target_width: int, align_right: bool = False) -> str:
    """文字列を指定の表示幅にパディング

    Args:
        text: パディング対象の文字列
        target_width: 目標の表示幅
        align_right: True なら右揃え、False なら左揃え

    Returns:
        str: パディングされた文字列
    """
    current_width = _get_display_width(text)
    padding_needed = target_width - current_width
    if padding_needed <= 0:
        return text
    padding = " " * padding_needed
    if align_right:
        return padding + text
    return text + padding


def _format_results_table(
    fukusho_summary,
    tansho_summary,
    umaren_summary,
    sanrenpuku_summary,
) -> str:
    """結果テーブルを動的幅で生成

    Args:
        fukusho_summary: 複勝シミュレーション結果サマリー
        tansho_summary: 単勝シミュレーション結果サマリー
        umaren_summary: 馬連シミュレーション結果サマリー
        sanrenpuku_summary: 三連複シミュレーション結果サマリー

    Returns:
        str: フォーマット済みテーブル文字列
    """
    # データ行を構築
    rows = [
        (
            "複勝",
            fukusho_summary.total_hits,
            fukusho_summary.hit_rate * 100,
            fukusho_summary.total_investment,
            fukusho_summary.total_payout,
            fukusho_summary.return_rate * 100,
        ),
        (
            "単勝",
            tansho_summary.total_hits,
            tansho_summary.hit_rate * 100,
            tansho_summary.total_investment,
            tansho_summary.total_payout,
            tansho_summary.return_rate * 100,
        ),
        (
            "馬連",
            umaren_summary.total_hits,
            umaren_summary.hit_rate * 100,
            umaren_summary.total_investment,
            umaren_summary.total_payout,
            umaren_summary.return_rate * 100,
        ),
        (
            "三連複",
            sanrenpuku_summary.total_hits,
            sanrenpuku_summary.hit_rate * 100,
            sanrenpuku_summary.total_investment,
            sanrenpuku_summary.total_payout,
            sanrenpuku_summary.return_rate * 100,
        ),
    ]

    # ヘッダ
    headers = ("券種", "的中数", "的中率", "投資額", "払戻額", "回収率")

    # 各列の最大幅を計算
    def format_cell(value, col_idx: int) -> str:
        """セルをフォーマット"""
        if col_idx == 0:  # 券種
            return str(value)
        elif col_idx == 1:  # 的中数
            return str(value)
        elif col_idx == 2:  # 的中率
            return f"{value:.1f}%"
        elif col_idx == 3:  # 投資額
            return f"{value:,}円"
        elif col_idx == 4:  # 払戻額
            return f"{value:,}円"
        elif col_idx == 5:  # 回収率
            return f"{value:.1f}%"
        return str(value)

    # 各列のフォーマット済み文字列を計算
    formatted_rows = []
    for row in rows:
        formatted_row = tuple(format_cell(val, i) for i, val in enumerate(row))
        formatted_rows.append(formatted_row)

    # 各列の最大表示幅を計算（ヘッダ含む）
    col_widths = []
    for col_idx in range(len(headers)):
        max_width = _get_display_width(headers[col_idx])
        for row in formatted_rows:
            max_width = max(max_width, _get_display_width(row[col_idx]))
        col_widths.append(max_width)

    # テーブル構築
    def make_border() -> str:
        return "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

    def make_row(cells: tuple) -> str:
        parts = []
        for i, cell in enumerate(cells):
            if i == 0:  # 左揃え
                padded = _pad_to_width(cell, col_widths[i], align_right=False)
            else:  # 右揃え
                padded = _pad_to_width(cell, col_widths[i], align_right=True)
            parts.append(f" {padded} ")
        return "|" + "|".join(parts) + "|"

    lines = [
        make_border(),
        make_row(headers),
        make_border(),
    ]
    for row in formatted_rows:
        lines.append(make_row(row))
    lines.append(make_border())

    return "\n".join(lines)


def _resolve_date_range(
    from_date: str | None, to_date: str | None, last_week: bool
) -> tuple[str, str]:
    """日付範囲を決定するヘルパー関数

    Args:
        from_date: 開始日（YYYY-MM-DD形式）
        to_date: 終了日（YYYY-MM-DD形式）
        last_week: 先週フラグ

    Returns:
        (from_date, to_date) のタプル

    Raises:
        SystemExit: 日付指定が不正な場合
    """
    if last_week or (from_date is None and to_date is None):
        today = date.today()
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        last_monday = this_monday - timedelta(days=7)
        last_sunday = this_monday - timedelta(days=1)
        return last_monday.strftime("%Y-%m-%d"), last_sunday.strftime("%Y-%m-%d")

    if from_date is None or to_date is None:
        click.echo("--from と --to の両方を指定してください")
        raise SystemExit(1)

    try:
        dt.strptime(from_date, "%Y-%m-%d")
        dt.strptime(to_date, "%Y-%m-%d")
    except ValueError:
        click.echo("日付形式が不正です（YYYY-MM-DD形式で指定してください）")
        raise SystemExit(1)

    return from_date, to_date


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
    # 日付範囲の決定
    from_date, to_date = _resolve_date_range(from_date, to_date, last_week)

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
    # 日付範囲の決定
    from_date, to_date = _resolve_date_range(from_date, to_date, last_week)

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
    # 日付範囲の決定
    from_date, to_date = _resolve_date_range(from_date, to_date, last_week)

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
    # 日付範囲の決定
    from_date, to_date = _resolve_date_range(from_date, to_date, last_week)

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


@click.command("backtest-all")
@click.option("--from", "from_date", type=str, default=None, help="開始日（YYYY-MM-DD形式）")
@click.option("--to", "to_date", type=str, default=None, help="終了日（YYYY-MM-DD形式）")
@click.option("--last-week", is_flag=True, help="先週を対象（デフォルト）")
@click.option("--top-n", type=int, default=3, help="単勝・複勝Top何頭に賭けるか（デフォルト: 3）")
@click.option("--venue", multiple=True, help="競馬場フィルタ（複数可）")
@click.option("--db", required=True, type=click.Path(exists=True), help="DBファイルパス")
@click.option("-v", "--verbose", is_flag=True, help="レース別詳細表示")
def backtest_all(
    from_date: str | None,
    to_date: str | None,
    last_week: bool,
    top_n: int,
    venue: tuple[str, ...],
    db: str,
    verbose: bool,
):
    """全券種（複勝・単勝・馬連・三連複）のバックテストを一括実行する"""
    # 日付範囲の決定
    from_date, to_date = _resolve_date_range(from_date, to_date, last_week)

    # 会場リストの準備
    venues = list(venue) if venue else None

    # ヘッダー表示
    click.echo("=" * 40)
    click.echo(f"全券種バックテスト: {from_date} ~ {to_date}")
    click.echo("=" * 40)

    # 各シミュレータを実行
    fukusho_sim = FukushoSimulator(db)
    fukusho_summary = fukusho_sim.simulate_period(
        from_date=from_date,
        to_date=to_date,
        venues=venues,
        top_n=top_n,
    )

    tansho_sim = TanshoSimulator(db)
    tansho_summary = tansho_sim.simulate_period(
        from_date=from_date,
        to_date=to_date,
        venues=venues,
        top_n=top_n,
    )

    umaren_sim = UmarenSimulator(db)
    umaren_summary = umaren_sim.simulate_period(
        from_date=from_date,
        to_date=to_date,
        venues=venues,
    )

    sanrenpuku_sim = SanrenpukuSimulator(db)
    sanrenpuku_summary = sanrenpuku_sim.simulate_period(
        from_date=from_date,
        to_date=to_date,
        venues=venues,
    )

    # 対象レース数の表示
    click.echo(f"対象レース数: {fukusho_summary.total_races}")
    click.echo("")

    # テーブル形式で結果表示（動的幅計算）
    table = _format_results_table(
        fukusho_summary,
        tansho_summary,
        umaren_summary,
        sanrenpuku_summary,
    )
    click.echo(table)
    click.echo("")

    # 総計
    total_investment = (
        fukusho_summary.total_investment
        + tansho_summary.total_investment
        + umaren_summary.total_investment
        + sanrenpuku_summary.total_investment
    )
    total_payout = (
        fukusho_summary.total_payout
        + tansho_summary.total_payout
        + umaren_summary.total_payout
        + sanrenpuku_summary.total_payout
    )
    total_return_rate = total_payout / total_investment if total_investment > 0 else 0.0

    click.echo(f"総投資額: {total_investment:,}円")
    click.echo(f"総払戻額: {total_payout:,}円")
    click.echo(f"総回収率: {total_return_rate * 100:.1f}%")

    # verbose モード: 各券種のレース別詳細を表示
    if verbose:
        click.echo("")
        click.echo("-" * 40)
        click.echo("【複勝】レース別詳細")
        click.echo("-" * 40)
        for result in fukusho_summary.race_results:
            hit_mark = "○" if result.hits else "×"
            click.echo(
                f"{result.race_date} {result.venue} {result.race_name}: "
                f"予測{result.top_n_predictions} -> 的中{result.hits} ({hit_mark}) "
                f"払戻{result.payout_total}円"
            )

        click.echo("")
        click.echo("-" * 40)
        click.echo("【単勝】レース別詳細")
        click.echo("-" * 40)
        for result in tansho_summary.race_results:
            hit_mark = "○" if result.hit else "×"
            click.echo(
                f"{result.race_date} {result.venue} {result.race_name}: "
                f"予測{result.top_n_predictions} -> 1着{result.winning_horse} ({hit_mark}) "
                f"払戻{result.payout}円"
            )

        click.echo("")
        click.echo("-" * 40)
        click.echo("【馬連】レース別詳細")
        click.echo("-" * 40)
        for result in umaren_summary.race_results:
            hit_mark = "○" if result.hit else "×"
            click.echo(
                f"{result.race_date} {result.venue} {result.race_name}: "
                f"購入{result.bet_combinations} -> 結果{result.actual_pair} ({hit_mark}) "
                f"払戻{result.payout}円"
            )

        click.echo("")
        click.echo("-" * 40)
        click.echo("【三連複】レース別詳細")
        click.echo("-" * 40)
        for result in sanrenpuku_summary.race_results:
            hit_mark = "○" if result.hit else "×"
            click.echo(
                f"{result.race_date} {result.venue} {result.race_name}: "
                f"予測{result.predicted_trio} -> 結果{result.actual_trio} ({hit_mark}) "
                f"払戻{result.payout}円"
            )
