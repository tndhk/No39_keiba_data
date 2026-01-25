"""URL解析ユーティリティ"""

import re


def extract_race_id_from_url(url: str) -> str:
    """URLからレースIDを抽出する

    Args:
        url: レースURL（例: https://race.netkeiba.com/race/202401010101.html）

    Returns:
        レースID（例: 202401010101）
    """
    match = re.search(r"/race/(\d+)/?", url)
    if match:
        return match.group(1)
    raise ValueError(f"Invalid race URL: {url}")


def extract_race_id_from_shutuba_url(url: str) -> str:
    """出馬表URLからレースIDを抽出する

    Args:
        url: 出馬表URL（例: https://race.netkeiba.com/race/shutuba.html?race_id=202606010802）

    Returns:
        レースID（例: 202606010802）
    """
    match = re.search(r"race_id=(\d+)", url)
    if match:
        return match.group(1)
    raise ValueError(f"Invalid shutuba URL: {url}")
