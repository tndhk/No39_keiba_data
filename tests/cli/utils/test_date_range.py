"""date_range ユーティリティのテスト"""

from datetime import date, timedelta
from unittest.mock import patch

import pytest

from keiba.cli.utils.date_range import resolve_date_range


class TestResolveDateRange:
    """resolve_date_range のテスト"""

    def test_resolve_date_range_last_week(self):
        """last_week=True の場合、先週月曜〜日曜が返る"""
        fake_today = date(2026, 1, 28)  # 水曜日
        with patch("keiba.cli.utils.date_range.date") as mock_date:
            mock_date.today.return_value = fake_today
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            from_d, to_d = resolve_date_range(None, None, last_week=True)

        # 2026-01-28 は水曜日
        # 今週月曜 = 2026-01-26
        # 先週月曜 = 2026-01-19
        # 先週日曜 = 2026-01-25
        assert from_d == "2026-01-19"
        assert to_d == "2026-01-25"

    def test_resolve_date_range_explicit(self):
        """from_date, to_date が明示的に指定された場合、そのまま返す"""
        from_d, to_d = resolve_date_range("2025-10-01", "2025-12-31", last_week=False)
        assert from_d == "2025-10-01"
        assert to_d == "2025-12-31"

    def test_resolve_date_range_default_to_last_week(self):
        """両方None かつ last_week=False の場合もデフォルトで先週になる"""
        fake_today = date(2026, 1, 28)
        with patch("keiba.cli.utils.date_range.date") as mock_date:
            mock_date.today.return_value = fake_today
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            from_d, to_d = resolve_date_range(None, None, last_week=False)

        assert from_d == "2026-01-19"
        assert to_d == "2026-01-25"

    def test_resolve_date_range_missing_from(self):
        """from_date のみ None でエラー"""
        with pytest.raises(SystemExit):
            resolve_date_range(None, "2025-12-31", last_week=False)

    def test_resolve_date_range_missing_to(self):
        """to_date のみ None でエラー"""
        with pytest.raises(SystemExit):
            resolve_date_range("2025-10-01", None, last_week=False)

    def test_resolve_date_range_invalid_format(self):
        """不正な日付形式でエラー"""
        with pytest.raises(SystemExit):
            resolve_date_range("2025/10/01", "2025-12-31", last_week=False)

        with pytest.raises(SystemExit):
            resolve_date_range("2025-10-01", "bad-date", last_week=False)
