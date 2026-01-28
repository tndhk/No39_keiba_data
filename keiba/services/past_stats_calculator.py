"""過去成績統計計算の純粋関数

prediction_serviceとtraining_serviceの両方で使われる
統計計算ロジックを1箇所に集約する。
"""

from datetime import date, datetime


def calculate_past_stats(
    past_results: list[dict],
    current_date: date,
    horse_id: str | None = None,
) -> dict[str, float | None]:
    """過去成績から派生統計を計算する

    Args:
        past_results: 過去成績リスト（日付降順を想定）
        current_date: 現在のレース日
        horse_id: 特定の馬でフィルタリング（Noneなら全て使用）

    Returns:
        win_rate, top3_rate, avg_finish_position, days_since_last_race の辞書
    """
    if not past_results:
        return {
            "win_rate": None,
            "top3_rate": None,
            "avg_finish_position": None,
            "days_since_last_race": None,
        }

    # horse_idが指定されている場合はフィルタリング
    if horse_id is not None:
        filtered = [r for r in past_results if r.get("horse_id") == horse_id]
        target_results = filtered if filtered else past_results
    else:
        target_results = past_results

    total_races = len(target_results)
    wins = sum(1 for r in target_results if r.get("finish_position") == 1)
    top3 = sum(
        1 for r in target_results
        if 1 <= (r.get("finish_position") or 0) <= 3
    )
    valid_positions = [
        r.get("finish_position")
        for r in target_results
        if r.get("finish_position") is not None and r.get("finish_position") > 0
    ]

    win_rate = wins / total_races if total_races > 0 else None
    top3_rate = top3 / total_races if total_races > 0 else None
    avg_finish = (
        sum(valid_positions) / len(valid_positions) if valid_positions else None
    )

    # 最新レースからの経過日数を計算
    days_since_last_race = _calculate_days_since(target_results, current_date)

    return {
        "win_rate": win_rate,
        "top3_rate": top3_rate,
        "avg_finish_position": avg_finish,
        "days_since_last_race": days_since_last_race,
    }


def _calculate_days_since(
    results: list[dict], current_date: date
) -> int | None:
    """最新レースからの経過日数を計算する

    Args:
        results: 成績リスト（日付降順を想定）
        current_date: 現在のレース日

    Returns:
        経過日数。計算不能な場合はNone。
    """
    if not results:
        return None

    last_race_date_raw = results[0].get("race_date")
    if last_race_date_raw is None:
        return None

    try:
        last_date = _parse_date_value(last_race_date_raw)
        return (current_date - last_date).days
    except (ValueError, TypeError):
        return None


def _parse_date_value(value: str | date | datetime) -> date:
    """様々な形式の日付値をdateオブジェクトに変換する

    Args:
        value: 日付値（str "YYYY-MM-DD", date, datetime のいずれか）

    Returns:
        dateオブジェクト
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return datetime.strptime(value, "%Y-%m-%d").date()
    raise TypeError(f"Unsupported date type: {type(value)}")
