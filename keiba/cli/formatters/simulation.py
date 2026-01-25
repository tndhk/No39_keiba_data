"""馬券シミュレーション計算モジュール"""


def calculate_fukusho_simulation(
    predictions: dict,
    actual_results: dict,
    payouts: dict,
) -> dict:
    """複勝シミュレーションを計算する

    Args:
        predictions: パースされた予測データ
        actual_results: レース番号 -> [1着馬番, 2着馬番, 3着馬番] のマップ
        payouts: レース番号 -> {馬番: 払戻金} のマップ

    Returns:
        シミュレーション結果
        {
            "top1": {
                "hits": int,
                "total_races": int,
                "hit_rate": float,
                "payout": int,
                "investment": int,
                "return_rate": float,
            },
            "top3": {
                "hits": int,
                "total_bets": int,
                "hit_rate": float,
                "payout": int,
                "investment": int,
                "return_rate": float,
            },
            "race_results": [...]
        }
    """
    result = {
        "top1": {
            "hits": 0,
            "total_races": 0,
            "hit_rate": 0.0,
            "payout": 0,
            "investment": 0,
            "return_rate": 0.0,
        },
        "top3": {
            "hits": 0,
            "total_bets": 0,
            "hit_rate": 0.0,
            "payout": 0,
            "investment": 0,
            "return_rate": 0.0,
        },
        "race_results": [],
    }

    races = predictions.get("races", [])
    if not races:
        return result

    for race in races:
        race_number = race.get("race_number")
        race_predictions = race.get("predictions", [])

        if not race_predictions or race_number not in actual_results:
            continue

        actual_top3 = actual_results[race_number]
        race_payouts = payouts.get(race_number, {})

        # 予測上位3頭の馬番
        predicted_top3 = [p["horse_number"] for p in race_predictions[:3]]

        # Top1シミュレーション（予測1位に100円賭け）
        result["top1"]["total_races"] += 1
        result["top1"]["investment"] += 100

        if race_predictions:
            top1_horse = race_predictions[0]["horse_number"]
            if top1_horse in actual_top3:
                result["top1"]["hits"] += 1
                result["top1"]["payout"] += race_payouts.get(top1_horse, 0)

        # Top3シミュレーション（予測1-3位に各100円賭け）
        race_top3_hits = 0
        for pred in race_predictions[:3]:
            horse_num = pred["horse_number"]
            result["top3"]["total_bets"] += 1
            result["top3"]["investment"] += 100

            if horse_num in actual_top3:
                result["top3"]["hits"] += 1
                result["top3"]["payout"] += race_payouts.get(horse_num, 0)
                race_top3_hits += 1

        # レース結果を記録
        result["race_results"].append({
            "race_number": race_number,
            "actual_top3": actual_top3,
            "predicted_top3": predicted_top3,
            "top1_hit": (race_predictions[0]["horse_number"] in actual_top3) if race_predictions else False,
            "top3_hits": race_top3_hits,
        })

    # 的中率と回収率を計算
    if result["top1"]["total_races"] > 0:
        result["top1"]["hit_rate"] = result["top1"]["hits"] / result["top1"]["total_races"]
        result["top1"]["return_rate"] = result["top1"]["payout"] / result["top1"]["investment"]

    if result["top3"]["total_bets"] > 0:
        result["top3"]["hit_rate"] = result["top3"]["hits"] / result["top3"]["total_bets"]
        result["top3"]["return_rate"] = result["top3"]["payout"] / result["top3"]["investment"]

    return result


def calculate_tansho_simulation(predictions: dict, tansho_payouts: dict) -> dict:
    """単勝シミュレーション

    Args:
        predictions: {"races": [{"race_number": int, "predictions": [{"horse_number": int, "rank": int}, ...]}]}
        tansho_payouts: {race_number: {"horse_number": int, "payout": int}}

    Returns:
        {
            "top1": {"total_races", "hits", "hit_rate", "investment", "payout", "return_rate"},
            "top3": {"total_races", "total_bets", "hits", "hit_rate", "investment", "payout", "return_rate"}
        }
    """
    result = {
        "top1": {
            "total_races": 0,
            "hits": 0,
            "hit_rate": 0.0,
            "investment": 0,
            "payout": 0,
            "return_rate": 0.0,
        },
        "top3": {
            "total_races": 0,
            "total_bets": 0,
            "hits": 0,
            "hit_rate": 0.0,
            "investment": 0,
            "payout": 0,
            "return_rate": 0.0,
        },
    }

    races = predictions.get("races", [])
    if not races:
        return result

    for race in races:
        race_number = race.get("race_number")
        race_predictions = race.get("predictions", [])

        # 予測がないレースまたはtansho_payoutsにないレースはスキップ
        if not race_predictions or race_number not in tansho_payouts:
            continue

        tansho_data = tansho_payouts[race_number]
        winning_horse = tansho_data["horse_number"]
        payout = tansho_data["payout"]

        # Top1シミュレーション（予測1位に100円賭け）
        result["top1"]["total_races"] += 1
        result["top1"]["investment"] += 100

        top1_horse = race_predictions[0]["horse_number"]
        if top1_horse == winning_horse:
            result["top1"]["hits"] += 1
            result["top1"]["payout"] += payout

        # Top3シミュレーション（予測1-3位に各100円賭け）
        result["top3"]["total_races"] += 1
        bet_count = min(len(race_predictions), 3)
        result["top3"]["total_bets"] += bet_count
        result["top3"]["investment"] += bet_count * 100

        # 予測1-3位のいずれかが1着か判定
        predicted_horses = [p["horse_number"] for p in race_predictions[:3]]
        if winning_horse in predicted_horses:
            result["top3"]["hits"] += 1
            result["top3"]["payout"] += payout

    # 的中率と回収率を計算
    if result["top1"]["total_races"] > 0:
        result["top1"]["hit_rate"] = result["top1"]["hits"] / result["top1"]["total_races"]
        result["top1"]["return_rate"] = result["top1"]["payout"] / result["top1"]["investment"]

    if result["top3"]["total_races"] > 0:
        result["top3"]["hit_rate"] = result["top3"]["hits"] / result["top3"]["total_races"]
        result["top3"]["return_rate"] = result["top3"]["payout"] / result["top3"]["investment"]

    return result


def calculate_umaren_simulation(predictions: dict, umaren_payouts: dict) -> dict:
    """馬連シミュレーション（予測1-2, 1-3, 2-3の3点買い）

    Args:
        predictions: パースされた予測データ
        umaren_payouts: レース番号 -> {"horse_numbers": [5, 6], "payout": 2470}

    Returns:
        {
            "total_races": int,  # 対象レース数
            "hits": int,  # 的中数
            "hit_rate": float,  # 的中率
            "investment": int,  # 投資額（レース数 x 3点 x 100円）
            "payout": int,  # 払戻額
            "return_rate": float,  # 回収率
        }
    """
    result = {
        "total_races": 0,
        "hits": 0,
        "hit_rate": 0.0,
        "investment": 0,
        "payout": 0,
        "return_rate": 0.0,
    }

    races = predictions.get("races", [])
    if not races:
        return result

    for race in races:
        race_number = race.get("race_number")
        if not race_number:
            continue  # race_numberがない場合はスキップ

        # キーの型を整数に統一
        race_key = int(race_number) if isinstance(race_number, str) else race_number

        race_predictions = race.get("predictions", [])

        # 予測が3頭未満またはumaren_payoutsにないレースはスキップ
        if len(race_predictions) < 3 or race_key not in umaren_payouts:
            continue

        result["total_races"] += 1
        result["investment"] += 300  # 3点 x 100円

        # 予測上位3頭の馬番
        top3_horses = [p["horse_number"] for p in race_predictions[:3]]

        # 3組の馬連を生成: (1,2), (1,3), (2,3)
        combinations = [
            {top3_horses[0], top3_horses[1]},
            {top3_horses[0], top3_horses[2]},
            {top3_horses[1], top3_horses[2]},
        ]

        # 実際の馬連結果
        payout_data = umaren_payouts[race_key]
        actual_pair = set(payout_data["horse_numbers"])

        # 的中判定
        if actual_pair in combinations:
            result["hits"] += 1
            result["payout"] += payout_data["payout"]

    # 的中率と回収率を計算
    if result["total_races"] > 0:
        result["hit_rate"] = result["hits"] / result["total_races"]
        result["return_rate"] = result["payout"] / result["investment"]

    return result


def calculate_sanrenpuku_simulation(predictions: dict, sanrenpuku_payouts: dict) -> dict:
    """3連複シミュレーション（予測1-2-3の1点買い）

    Args:
        predictions: パースされた予測データ
        sanrenpuku_payouts: レース番号 -> {"horse_numbers": [3, 5, 6], "payout": 11060}

    Returns:
        {
            "total_races": int,  # 対象レース数
            "hits": int,  # 的中数
            "hit_rate": float,  # 的中率
            "investment": int,  # 投資額（レース数 x 1点 x 100円）
            "payout": int,  # 払戻額
            "return_rate": float,  # 回収率
        }
    """
    result = {
        "total_races": 0,
        "hits": 0,
        "hit_rate": 0.0,
        "investment": 0,
        "payout": 0,
        "return_rate": 0.0,
    }

    races = predictions.get("races", [])
    if not races:
        return result

    for race in races:
        race_number = race.get("race_number")
        if not race_number:
            continue  # race_numberがない場合はスキップ

        # キーの型を整数に統一
        race_key = int(race_number) if isinstance(race_number, str) else race_number

        race_predictions = race.get("predictions", [])

        # 予測が3頭未満またはsanrenpuku_payoutsにないレースはスキップ
        if len(race_predictions) < 3 or race_key not in sanrenpuku_payouts:
            continue

        result["total_races"] += 1
        result["investment"] += 100  # 1点 x 100円

        # 予測上位3頭の馬番
        top3_horses = {p["horse_number"] for p in race_predictions[:3]}

        # 実際の3連複結果
        payout_data = sanrenpuku_payouts[race_key]
        actual_trio = set(payout_data["horse_numbers"])

        # 的中判定（3頭すべて一致）
        if actual_trio == top3_horses:
            result["hits"] += 1
            result["payout"] += payout_data["payout"]

    # 的中率と回収率を計算
    if result["total_races"] > 0:
        result["hit_rate"] = result["hits"] / result["total_races"]
        result["return_rate"] = result["payout"] / result["investment"]

    return result
