"""table_formatter ユーティリティのテスト"""

from keiba.cli.utils.table_formatter import (
    format_results_table,
    get_display_width,
    pad_to_width,
)


class TestGetDisplayWidth:
    """get_display_width のテスト"""

    def test_get_display_width_ascii(self):
        """ASCII文字の幅は全て1"""
        assert get_display_width("hello") == 5
        assert get_display_width("abc123") == 6
        assert get_display_width("") == 0

    def test_get_display_width_cjk(self):
        """全角文字（日本語・中国語等）の幅は2"""
        assert get_display_width("日本語") == 6
        assert get_display_width("複勝") == 4
        assert get_display_width("三連複") == 6

    def test_get_display_width_mixed(self):
        """混在文字（全角+半角）の幅を正しく計算"""
        assert get_display_width("abc日本") == 7  # 3 + 4
        assert get_display_width("Top3") == 4  # all ASCII
        assert get_display_width("100円") == 5  # 3 + 2


class TestPadToWidth:
    """pad_to_width のテスト"""

    def test_pad_to_width_left(self):
        """左揃え（デフォルト）: テキストの右にスペースを追加"""
        result = pad_to_width("abc", 6)
        assert result == "abc   "
        assert len(result) == 6

    def test_pad_to_width_right(self):
        """右揃え: テキストの左にスペースを追加"""
        result = pad_to_width("abc", 6, align_right=True)
        assert result == "   abc"
        assert len(result) == 6

    def test_pad_to_width_no_padding_needed(self):
        """テキストが既に目標幅以上の場合パディング不要"""
        result = pad_to_width("hello", 5)
        assert result == "hello"

        result_over = pad_to_width("hello world", 5)
        assert result_over == "hello world"  # 超過してもそのまま返す

    def test_pad_to_width_cjk(self):
        """全角文字のパディングも表示幅ベースで正しく動作"""
        # "複勝" は表示幅4なので、幅6にするには2スペース
        result = pad_to_width("複勝", 6)
        assert result == "複勝  "


class _FakeSummary:
    """テスト用のダミーサマリーオブジェクト"""

    def __init__(self, hits, hit_rate, investment, payout, return_rate):
        self.total_hits = hits
        self.hit_rate = hit_rate
        self.total_investment = investment
        self.total_payout = payout
        self.return_rate = return_rate


class TestFormatResultsTable:
    """format_results_table のテスト"""

    def test_format_results_table_structure(self):
        """テーブル構造の検証: 行数、境界線、データ行の存在"""
        fukusho = _FakeSummary(10, 0.5, 3000, 2500, 0.833)
        tansho = _FakeSummary(5, 0.25, 3000, 1500, 0.5)
        umaren = _FakeSummary(3, 0.15, 3000, 4000, 1.333)
        sanrenpuku = _FakeSummary(2, 0.1, 1000, 5000, 5.0)

        result = format_results_table(fukusho, tansho, umaren, sanrenpuku)
        lines = result.split("\n")

        # 構造: 境界線 + ヘッダ + 境界線 + 4データ行 + 境界線 = 8行
        assert len(lines) == 8

        # 境界線は "+" で始まる
        assert lines[0].startswith("+")
        assert lines[2].startswith("+")
        assert lines[7].startswith("+")

        # ヘッダ行は "|" で始まる
        assert lines[1].startswith("|")

        # ヘッダに各カラム名が含まれる
        assert "券種" in lines[1]
        assert "的中数" in lines[1]
        assert "的中率" in lines[1]
        assert "投資額" in lines[1]
        assert "払戻額" in lines[1]
        assert "回収率" in lines[1]

        # データ行に券種名が含まれる
        assert "複勝" in lines[3]
        assert "単勝" in lines[4]
        assert "馬連" in lines[5]
        assert "三連複" in lines[6]

    def test_format_results_table_values(self):
        """テーブルのデータ値が正しくフォーマットされる"""
        fukusho = _FakeSummary(10, 0.5, 3000, 2500, 0.833)
        tansho = _FakeSummary(5, 0.25, 3000, 1500, 0.5)
        umaren = _FakeSummary(3, 0.15, 3000, 4000, 1.333)
        sanrenpuku = _FakeSummary(2, 0.1, 1000, 5000, 5.0)

        result = format_results_table(fukusho, tansho, umaren, sanrenpuku)

        # 的中率のフォーマット
        assert "50.0%" in result
        assert "25.0%" in result

        # 投資額のフォーマット
        assert "3,000円" in result
        assert "1,000円" in result

        # 払戻額のフォーマット
        assert "2,500円" in result
        assert "5,000円" in result
