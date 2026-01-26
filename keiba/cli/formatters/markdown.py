"""Markdown予測結果ファイルの生成・パース・更新機能を提供するモジュール"""

import re
from datetime import datetime as dt
from pathlib import Path


def save_predictions_markdown(
    predictions_data: list,
    date_str: str,
    venue: str,
    output_dir: str | None = None,
) -> str:
    """予測結果をMarkdownファイルに保存する

    Args:
        predictions_data: 予測データのリスト
        date_str: 日付文字列（YYYY-MM-DD形式）
        venue: 競馬場名
        output_dir: 出力ディレクトリ（Noneの場合はdocs/predictions）

    Returns:
        保存したファイルパス
    """
    # 出力ディレクトリを決定
    if output_dir is None:
        base_path = Path(__file__).parent.parent.parent.parent / "docs" / "predictions"
    else:
        base_path = Path(output_dir)

    # ディレクトリが存在しない場合は作成
    base_path.mkdir(parents=True, exist_ok=True)

    # ファイル名を生成（日本語競馬場名をローマ字に変換）
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
    filename = f"{date_str}-{venue_name}.md"
    filepath = base_path / filename

    # Markdownコンテンツを生成
    lines = [
        f"# {date_str} {venue} 予測結果",
        "",
        f"生成日時: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    for race_data in predictions_data:
        race_id = race_data.get("race_id", "")
        race_number = race_data.get("race_number", "?")
        race_name = race_data.get("race_name", "")
        surface = race_data.get("surface", "")
        distance = race_data.get("distance", "")

        lines.append(f"## {race_number}R {race_name}")
        if race_id:
            lines.append(f"race_id: {race_id}")
        # skipped フラグがある場合は出力
        if race_data.get("skipped", False):
            lines.append("skipped: true")
        if surface and distance:
            lines.append(f"{surface}{distance}m")
        lines.append("")

        predictions = race_data.get("predictions", [])
        if predictions:
            lines.append("| 順位 | 馬番 | 馬名 | ML確率 | 複合 | 総合 |")
            lines.append("|:---:|:---:|:---|:---:|:---:|:---:|")

            for pred in predictions[:5]:  # 上位5頭のみ
                rank = pred.get("rank", "")
                horse_number = pred.get("horse_number", "")
                horse_name = pred.get("horse_name", "")
                ml_prob = pred.get("ml_probability", 0)
                total_score = pred.get("total_score")

                combined_score = pred.get("combined_score")
                prob_str = f"{ml_prob:.1%}" if ml_prob > 0 else "-"
                combined_str = f"{combined_score:.1f}" if combined_score else "-"
                total_str = f"{total_score:.1f}" if total_score else "-"

                lines.append(
                    f"| {rank} | {horse_number} | {horse_name} | {prob_str} | {combined_str} | {total_str} |"
                )
        else:
            lines.append("予測データなし")

        lines.append("")

    # ファイルに書き込み
    content = "\n".join(lines)
    filepath.write_text(content, encoding="utf-8")

    return str(filepath)


def parse_predictions_markdown(filepath: str) -> dict:
    """予測結果Markdownファイルをパースする

    Args:
        filepath: Markdownファイルパス

    Returns:
        パースされた予測データ
        {
            "races": [
                {
                    "race_id": str,
                    "race_number": int,
                    "race_name": str,
                    "predictions": [
                        {"horse_number": int, "horse_name": str, "rank": int, "ml_probability": float}
                    ]
                }
            ]
        }
    """
    result = {"races": []}

    path = Path(filepath)
    if not path.exists():
        return result

    content = path.read_text(encoding="utf-8")
    lines = content.split("\n")

    current_race = None
    in_table = False
    header_skipped = False

    for line in lines:
        line = line.strip()

        # レースヘッダー（## 1R テストレース）
        if line.startswith("## ") and "R " in line:
            # 前のレースがあれば保存
            if current_race is not None:
                result["races"].append(current_race)

            # レース番号とレース名を抽出
            race_header = line[3:]  # "## "を除去
            race_match = re.match(r"(\d+)R\s+(.+)", race_header)
            if race_match:
                race_number = int(race_match.group(1))
                race_name = race_match.group(2)
            else:
                race_number = 0
                race_name = race_header

            current_race = {
                "race_id": "",
                "race_number": race_number,
                "race_name": race_name,
                "predictions": [],
                "skipped": False,
            }
            in_table = False
            header_skipped = False

        # race_id行を検出（race_id: 202606010801）
        elif line.startswith("race_id:") and current_race is not None:
            race_id_match = re.match(r"race_id:\s*(\d+)", line)
            if race_id_match:
                current_race["race_id"] = race_id_match.group(1)

        # skipped行を検出（skipped: true）
        elif line.startswith("skipped:") and current_race is not None:
            if "true" in line.lower():
                current_race["skipped"] = True

        # テーブル開始検出
        elif line.startswith("|") and "順位" in line:
            in_table = True
            header_skipped = False

        # テーブルヘッダー区切り行をスキップ
        elif in_table and line.startswith("|") and "---" in line:
            header_skipped = True

        # テーブルデータ行
        elif in_table and header_skipped and line.startswith("|") and current_race is not None:
            cells = [c.strip() for c in line.split("|")]
            # 空セルを除去（先頭と末尾の"|"による）
            cells = [c for c in cells if c]

            if len(cells) >= 4:
                try:
                    rank = int(cells[0])
                    horse_number = int(cells[1])
                    horse_name = cells[2]

                    # ML確率をパース（"-"の場合は0.0）
                    ml_prob_str = cells[3].replace("%", "")
                    if ml_prob_str == "-":
                        ml_probability = 0.0
                    else:
                        ml_probability = float(ml_prob_str) / 100.0

                    current_race["predictions"].append({
                        "rank": rank,
                        "horse_number": horse_number,
                        "horse_name": horse_name,
                        "ml_probability": ml_probability,
                    })
                except (ValueError, IndexError):
                    # パースエラーはスキップ
                    pass

        # 空行でテーブル終了
        elif in_table and not line:
            in_table = False

    # 最後のレースを保存
    if current_race is not None:
        result["races"].append(current_race)

    return result


def append_review_to_markdown(filepath: str, review_data: dict) -> None:
    """検証結果をMarkdownファイルに追記する

    Args:
        filepath: Markdownファイルパス
        review_data: 検証結果データ
    """
    path = Path(filepath)
    if not path.exists():
        return

    original_content = path.read_text(encoding="utf-8")

    # 検証結果セクションを生成
    lines = [
        "",
        "---",
        "",
        "## 検証結果",
        "",
        f"検証日時: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "### 複勝シミュレーション",
        "",
        "#### 予測1位のみに賭けた場合",
        "",
        f"- 対象レース数: {review_data['top1']['total_races']}",
        f"- 的中数: {review_data['top1']['hits']}",
        f"- 的中率: {review_data['top1']['hit_rate'] * 100:.1f}%",
        f"- 投資額: {review_data['top1']['investment']}円",
        f"- 払戻額: {review_data['top1']['payout']}円",
        f"- 回収率: {review_data['top1']['return_rate'] * 100:.1f}%",
        "",
        "#### 予測1-3位に各100円賭けた場合",
        "",
        f"- 賭け数: {review_data['top3']['total_bets']}",
        f"- 的中数: {review_data['top3']['hits']}",
        f"- 的中率: {review_data['top3']['hit_rate'] * 100:.1f}%",
        f"- 投資額: {review_data['top3']['investment']}円",
        f"- 払戻額: {review_data['top3']['payout']}円",
        f"- 回収率: {review_data['top3']['return_rate'] * 100:.1f}%",
        "",
        "### 馬連シミュレーション（予測1-2, 1-3, 2-3の3点買い）",
        "",
        f"- 対象レース数: {review_data.get('umaren', {}).get('total_races', 0)}",
        f"- 的中数: {review_data.get('umaren', {}).get('hits', 0)}",
        f"- 的中率: {review_data.get('umaren', {}).get('hit_rate', 0.0) * 100:.1f}%",
        f"- 投資額: {review_data.get('umaren', {}).get('investment', 0)}円",
        f"- 払戻額: {review_data.get('umaren', {}).get('payout', 0)}円",
        f"- 回収率: {review_data.get('umaren', {}).get('return_rate', 0.0) * 100:.1f}%",
        "",
        "### 3連複シミュレーション（予測1-2-3の1点買い）",
        "",
        f"- 対象レース数: {review_data.get('sanrenpuku', {}).get('total_races', 0)}",
        f"- 的中数: {review_data.get('sanrenpuku', {}).get('hits', 0)}",
        f"- 的中率: {review_data.get('sanrenpuku', {}).get('hit_rate', 0.0) * 100:.1f}%",
        f"- 投資額: {review_data.get('sanrenpuku', {}).get('investment', 0)}円",
        f"- 払戻額: {review_data.get('sanrenpuku', {}).get('payout', 0)}円",
        f"- 回収率: {review_data.get('sanrenpuku', {}).get('return_rate', 0.0) * 100:.1f}%",
        "",
        "### 単勝シミュレーション",
        "",
        "#### 予測1位（本命のみ）",
        "",
        "| 指標 | 値 |",
        "|------|------|",
        f"| 対象レース | {review_data.get('tansho', {}).get('top1', {}).get('total_races', 0)} |",
        f"| 的中数 | {review_data.get('tansho', {}).get('top1', {}).get('hits', 0)} |",
        f"| 的中率 | {review_data.get('tansho', {}).get('top1', {}).get('hit_rate', 0.0) * 100:.1f}% |",
        f"| 投資額 | {review_data.get('tansho', {}).get('top1', {}).get('investment', 0):,}円 |",
        f"| 払戻額 | {review_data.get('tansho', {}).get('top1', {}).get('payout', 0):,}円 |",
        f"| 回収率 | {review_data.get('tansho', {}).get('top1', {}).get('return_rate', 0.0) * 100:.1f}% |",
        "",
        "#### 予測1-3位",
        "",
        "| 指標 | 値 |",
        "|------|------|",
        f"| 対象レース | {review_data.get('tansho', {}).get('top3', {}).get('total_races', 0)} |",
        f"| 賭け数 | {review_data.get('tansho', {}).get('top3', {}).get('total_bets', 0)} |",
        f"| 的中数 | {review_data.get('tansho', {}).get('top3', {}).get('hits', 0)} |",
        f"| 的中率 | {review_data.get('tansho', {}).get('top3', {}).get('hit_rate', 0.0) * 100:.1f}% |",
        f"| 投資額 | {review_data.get('tansho', {}).get('top3', {}).get('investment', 0):,}円 |",
        f"| 払戻額 | {review_data.get('tansho', {}).get('top3', {}).get('payout', 0):,}円 |",
        f"| 回収率 | {review_data.get('tansho', {}).get('top3', {}).get('return_rate', 0.0) * 100:.1f}% |",
        "",
        "### レース別結果",
        "",
        "| R | 実際の3着以内 | 予測Top3 | Top1的中 | Top3的中数 |",
        "|:---:|:---|:---|:---:|:---:|",
    ]

    for race_result in review_data.get("race_results", []):
        race_num = race_result["race_number"]
        actual = ", ".join(str(h) for h in race_result["actual_top3"])
        predicted = ", ".join(str(h) for h in race_result["predicted_top3"])
        top1_hit = "O" if race_result["top1_hit"] else "X"
        top3_hits = race_result["top3_hits"]
        lines.append(f"| {race_num} | {actual} | {predicted} | {top1_hit} | {top3_hits} |")

    lines.append("")

    # ファイルに追記
    new_content = original_content + "\n".join(lines)
    path.write_text(new_content, encoding="utf-8")
