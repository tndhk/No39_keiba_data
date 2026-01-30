"""会場フィルタリングユーティリティ"""

import re


def get_race_ids_for_venue(race_urls: list[str], venue_code: str) -> list[str]:
    """指定競馬場のレースIDをフィルタリングする

    Args:
        race_urls: レースURLのリスト
        venue_code: 競馬場コード（2桁の文字列、例: "06"）

    Returns:
        指定競馬場のレースIDリスト
    """
    race_ids = []

    for url in race_urls:
        # URLからレースIDを抽出
        match = re.search(r"/race/(\d{12})/?", url)
        if match:
            race_id = match.group(1)
            # race_idの5-6桁目が競馬場コード
            if len(race_id) >= 6 and race_id[4:6] == venue_code:
                race_ids.append(race_id)

    return race_ids


def filter_race_ids_by_venue(race_ids: list[str], venue_code: str) -> list[str]:
    """レースIDリストを指定競馬場でフィルタリングする

    Args:
        race_ids: レースIDのリスト（12桁の文字列）
        venue_code: 競馬場コード（2桁の文字列、例: "06"）

    Returns:
        指定競馬場のレースIDリスト
    """
    return [
        race_id
        for race_id in race_ids
        if len(race_id) >= 6 and race_id[4:6] == venue_code
    ]
