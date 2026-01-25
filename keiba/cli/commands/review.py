"""review-day コマンド: 予測結果と実際の結果を比較検証する"""

from datetime import date
from datetime import datetime as dt
from pathlib import Path

import click

from keiba.scrapers import RaceDetailScraper
from keiba.cli.formatters.markdown import parse_predictions_markdown, append_review_to_markdown
from keiba.cli.formatters.simulation import (
    calculate_fukusho_simulation,
    calculate_umaren_simulation,
    calculate_sanrenpuku_simulation,
    calculate_tansho_simulation,
)


@click.command()
@click.option("--date", "date_str", type=str, default=None, help="開催日（YYYY-MM-DD形式）")
@click.option("--venue", required=True, type=str, help="競馬場名（例: 中山）")
@click.option("--db", required=True, type=click.Path(), help="DBファイルパス")
def review_day(date_str: str | None, venue: str, db: str):
    """予測結果と実際の結果を比較検証する"""
    # 日付を決定（デフォルトは今日）
    if date_str is None:
        target_date = date.today()
        date_str = target_date.strftime("%Y-%m-%d")
    else:
        try:
            target_date = dt.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            click.echo(f"日付形式が不正です: {date_str}（YYYY-MM-DD形式で指定してください）")
            raise SystemExit(1)

    # 競馬場名をローマ字に変換
    venue_romanized = {
        "札幌": "sapporo",
        "函館": "hakodate",
        "福島": "fukushima",
        "新潟": "niigata",
        "東京": "tokyo",
        "中山": "nakayama",
        "中京": "chukyo",
        "京都": "kyoto",
        "阪神": "hanshin",
        "小倉": "kokura",
    }
    venue_name = venue_romanized.get(venue, venue.lower())

    # 予測ファイルパスを構築
    base_path = Path(__file__).parent.parent.parent.parent / "docs" / "predictions"
    prediction_file = base_path / f"{date_str}-{venue_name}.md"

    click.echo(f"検証開始: {date_str} {venue}")
    click.echo(f"予測ファイル: {prediction_file}")
    click.echo("")

    # 予測ファイルを読み込み
    if not prediction_file.exists():
        click.echo(f"予測ファイルが見つかりません: {prediction_file}")
        raise SystemExit(1)

    predictions = parse_predictions_markdown(str(prediction_file))

    if not predictions["races"]:
        click.echo("予測データがありません")
        raise SystemExit(1)

    # レース結果と払戻金を取得
    scraper = RaceDetailScraper()
    actual_results = {}
    payouts = {}
    tansho_payouts = {}
    umaren_payouts = {}
    sanrenpuku_payouts = {}

    for race in predictions["races"]:
        race_number = race["race_number"]
        race_id = race.get("race_id", "")

        # race_idが予測ファイルに保存されていない場合はスキップ
        if not race_id:
            click.echo(f"{race_number}R: race_idが予測ファイルに含まれていません。スキップします。")
            continue

        try:
            # 払戻金を取得
            payout_data = scraper.fetch_payouts(race_id)

            # 払戻金データを辞書形式に変換
            race_payouts = {}
            actual_top3 = []
            for p in payout_data:
                horse_num = p["horse_number"]
                race_payouts[horse_num] = p["payout"]
                actual_top3.append(horse_num)

            if actual_top3:
                actual_results[race_number] = actual_top3
                payouts[race_number] = race_payouts
                click.echo(f"{race_number}R: 結果取得完了 - 3着以内: {actual_top3}")
            else:
                click.echo(f"{race_number}R: 結果データなし")

            # 馬連払戻金を取得
            umaren_data = scraper.fetch_umaren_payout(race_id)
            if umaren_data:
                umaren_payouts[race_number] = umaren_data

            # 3連複払戻金を取得
            sanrenpuku_data = scraper.fetch_sanrenpuku_payout(race_id)
            if sanrenpuku_data:
                sanrenpuku_payouts[race_number] = sanrenpuku_data

            # 単勝払戻金を取得
            tansho_data = scraper.fetch_tansho_payout(race_id)
            if tansho_data:
                tansho_payouts[race_number] = tansho_data

        except Exception as e:
            click.echo(f"{race_number}R: 結果取得エラー - {e}")

    click.echo("")

    # シミュレーションを計算
    review_data = calculate_fukusho_simulation(predictions, actual_results, payouts)

    # 馬連シミュレーション
    umaren_data = calculate_umaren_simulation(predictions, umaren_payouts)
    review_data["umaren"] = umaren_data

    # 3連複シミュレーション
    sanrenpuku_data = calculate_sanrenpuku_simulation(predictions, sanrenpuku_payouts)
    review_data["sanrenpuku"] = sanrenpuku_data

    # 単勝シミュレーション
    tansho_data = calculate_tansho_simulation(predictions, tansho_payouts)
    review_data["tansho"] = tansho_data

    # 検証結果をMarkdownに追記
    append_review_to_markdown(str(prediction_file), review_data)
    click.echo(f"検証結果をファイルに追記しました: {prediction_file}")

    # サマリーを表示
    click.echo("")
    click.echo("=" * 60)
    click.echo("検証サマリー")
    click.echo("=" * 60)
    click.echo("")
    click.echo("【予測1位のみに賭けた場合】")
    click.echo(f"  対象レース数: {review_data['top1']['total_races']}")
    click.echo(f"  的中数: {review_data['top1']['hits']}")
    click.echo(f"  的中率: {review_data['top1']['hit_rate'] * 100:.1f}%")
    click.echo(f"  投資額: {review_data['top1']['investment']}円")
    click.echo(f"  払戻額: {review_data['top1']['payout']}円")
    click.echo(f"  回収率: {review_data['top1']['return_rate'] * 100:.1f}%")
    click.echo("")
    click.echo("【予測1-3位に各100円賭けた場合】")
    click.echo(f"  賭け数: {review_data['top3']['total_bets']}")
    click.echo(f"  的中数: {review_data['top3']['hits']}")
    click.echo(f"  的中率: {review_data['top3']['hit_rate'] * 100:.1f}%")
    click.echo(f"  投資額: {review_data['top3']['investment']}円")
    click.echo(f"  払戻額: {review_data['top3']['payout']}円")
    click.echo(f"  回収率: {review_data['top3']['return_rate'] * 100:.1f}%")
    click.echo("")
    click.echo("【馬連（予測1-2, 1-3, 2-3の3点買い）】")
    click.echo(f"  対象レース数: {review_data['umaren']['total_races']}")
    click.echo(f"  的中数: {review_data['umaren']['hits']}")
    click.echo(f"  的中率: {review_data['umaren']['hit_rate'] * 100:.1f}%")
    click.echo(f"  投資額: {review_data['umaren']['investment']}円")
    click.echo(f"  払戻額: {review_data['umaren']['payout']}円")
    click.echo(f"  回収率: {review_data['umaren']['return_rate'] * 100:.1f}%")
    click.echo("")
    click.echo("【3連複（予測1-2-3の1点買い）】")
    click.echo(f"  対象レース数: {review_data['sanrenpuku']['total_races']}")
    click.echo(f"  的中数: {review_data['sanrenpuku']['hits']}")
    click.echo(f"  的中率: {review_data['sanrenpuku']['hit_rate'] * 100:.1f}%")
    click.echo(f"  投資額: {review_data['sanrenpuku']['investment']}円")
    click.echo(f"  払戻額: {review_data['sanrenpuku']['payout']}円")
    click.echo(f"  回収率: {review_data['sanrenpuku']['return_rate'] * 100:.1f}%")
    click.echo("")
    click.echo("=== 単勝シミュレーション ===")
    click.echo("")
    click.echo("予測1位:")
    click.echo(f"  レース数: {review_data['tansho']['top1']['total_races']}, 的中: {review_data['tansho']['top1']['hits']}, 的中率: {review_data['tansho']['top1']['hit_rate'] * 100:.1f}%")
    click.echo(f"  投資額: {review_data['tansho']['top1']['investment']:,}円, 払戻: {review_data['tansho']['top1']['payout']:,}円, 回収率: {review_data['tansho']['top1']['return_rate'] * 100:.1f}%")
    click.echo("")
    click.echo("予測1-3位:")
    click.echo(f"  レース数: {review_data['tansho']['top3']['total_races']}, 賭け数: {review_data['tansho']['top3']['total_bets']}, 的中: {review_data['tansho']['top3']['hits']}, 的中率: {review_data['tansho']['top3']['hit_rate'] * 100:.1f}%")
    click.echo(f"  投資額: {review_data['tansho']['top3']['investment']:,}円, 払戻: {review_data['tansho']['top3']['payout']:,}円, 回収率: {review_data['tansho']['top3']['return_rate'] * 100:.1f}%")
    click.echo("")
    click.echo("完了")
