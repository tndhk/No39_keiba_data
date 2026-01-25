"""日付解析ユーティリティ"""

import re
from datetime import date


def parse_race_date(date_str: str) -> date:
    """レース日付文字列をdateオブジェクトに変換する

    Args:
        date_str: 日付文字列（例: "2024年1月1日"）

    Returns:
        dateオブジェクト
    """
    match = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_str)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        return date(year, month, day)
    raise ValueError(f"Invalid date string: {date_str}")
