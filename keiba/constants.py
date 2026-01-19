"""Constants for keiba data collection system."""

# JRA（中央競馬）競馬場コード
# レースIDの5-6文字目（YYYYPPNNRRXX形式のPP部分）
JRA_COURSE_CODES: dict[str, str] = {
    "01": "札幌",
    "02": "函館",
    "03": "福島",
    "04": "新潟",
    "05": "東京",
    "06": "中山",
    "07": "中京",
    "08": "京都",
    "09": "阪神",
    "10": "小倉",
}
