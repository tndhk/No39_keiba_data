"""日付解析ユーティリティ"""

import re
from datetime import date, datetime


def parse_race_date(date_str: str) -> date:
    """レース日付文字列をdateオブジェクトに変換する

    対応形式:
        - "2024年1月1日"（日本語形式）
        - "2024-01-01"（ISO形式）

    Args:
        date_str: 日付文字列

    Returns:
        dateオブジェクト
    """
    # 日本語形式: "2024年1月1日"
    match = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_str)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        return date(year, month, day)

    # ISO形式: "2024-01-01"
    iso_match = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", date_str)
    if iso_match:
        return datetime.strptime(date_str, "%Y-%m-%d").date()

    raise ValueError(f"Invalid date string: {date_str}")
