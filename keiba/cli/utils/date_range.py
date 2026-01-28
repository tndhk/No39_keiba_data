"""日付範囲解決ユーティリティ

バックテストコマンド等で使用する日付範囲を決定するヘルパー関数。
"""

from datetime import date, datetime as dt, timedelta

import click


def resolve_date_range(
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
