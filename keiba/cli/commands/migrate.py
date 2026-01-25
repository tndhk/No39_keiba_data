"""マイグレーションコマンド"""

import click

from keiba.db import get_engine, get_session
from keiba.models import Race
from keiba.utils.grade_extractor import extract_grade


@click.command("migrate-grades")
@click.option("--db", required=True, type=click.Path(), help="DBファイルパス")
def migrate_grades(db: str):
    """既存レースにグレード情報を追加する

    gradeがNullのレースに対して、レース名からグレードを抽出して更新する。
    """
    click.echo(f"グレード情報マイグレーション開始")
    click.echo(f"データベース: {db}")

    # DBに接続
    engine = get_engine(db)

    # 統計情報
    total_updated = 0

    with get_session(engine) as session:
        # gradeがNullのレースを取得
        races = session.query(Race).filter(Race.grade.is_(None)).all()

        if not races:
            click.echo("グレード未設定のレースはありません。")
            click.echo("")
            click.echo("完了")
            return

        click.echo(f"グレード未設定のレース: {len(races)}件")
        click.echo("")

        for race in races:
            grade = extract_grade(race.name)
            race.grade = grade
            total_updated += 1

            if total_updated % 100 == 0:
                click.echo(f"  {total_updated}件処理...")

    click.echo("")
    click.echo("=" * 50)
    click.echo("完了")
    click.echo(f"  更新したレース: {total_updated}件")
