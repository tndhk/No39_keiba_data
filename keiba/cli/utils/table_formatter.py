"""テーブルフォーマッタユーティリティ

バックテスト結果などを整形されたテーブル形式で出力するための関数群。
全角文字の表示幅を考慮した動的幅計算に対応。
"""

import unicodedata


def get_display_width(text: str) -> int:
    """文字列の表示幅を計算（全角文字は2、半角は1）

    Args:
        text: 計算対象の文字列

    Returns:
        int: 表示幅
    """
    width = 0
    for char in text:
        east_asian_width = unicodedata.east_asian_width(char)
        if east_asian_width in ("F", "W", "A"):  # Full, Wide, Ambiguous
            width += 2
        else:
            width += 1
    return width


def pad_to_width(text: str, target_width: int, align_right: bool = False) -> str:
    """文字列を指定の表示幅にパディング

    Args:
        text: パディング対象の文字列
        target_width: 目標の表示幅
        align_right: True なら右揃え、False なら左揃え

    Returns:
        str: パディングされた文字列
    """
    current_width = get_display_width(text)
    padding_needed = target_width - current_width
    if padding_needed <= 0:
        return text
    padding = " " * padding_needed
    if align_right:
        return padding + text
    return text + padding


def format_results_table(
    fukusho_summary,
    tansho_summary,
    umaren_summary,
    sanrenpuku_summary,
) -> str:
    """結果テーブルを動的幅で生成

    Args:
        fukusho_summary: 複勝シミュレーション結果サマリー
        tansho_summary: 単勝シミュレーション結果サマリー
        umaren_summary: 馬連シミュレーション結果サマリー
        sanrenpuku_summary: 三連複シミュレーション結果サマリー

    Returns:
        str: フォーマット済みテーブル文字列
    """
    # データ行を構築
    rows = [
        (
            "複勝",
            fukusho_summary.total_hits,
            fukusho_summary.hit_rate * 100,
            fukusho_summary.total_investment,
            fukusho_summary.total_payout,
            fukusho_summary.return_rate * 100,
        ),
        (
            "単勝",
            tansho_summary.total_hits,
            tansho_summary.hit_rate * 100,
            tansho_summary.total_investment,
            tansho_summary.total_payout,
            tansho_summary.return_rate * 100,
        ),
        (
            "馬連",
            umaren_summary.total_hits,
            umaren_summary.hit_rate * 100,
            umaren_summary.total_investment,
            umaren_summary.total_payout,
            umaren_summary.return_rate * 100,
        ),
        (
            "三連複",
            sanrenpuku_summary.total_hits,
            sanrenpuku_summary.hit_rate * 100,
            sanrenpuku_summary.total_investment,
            sanrenpuku_summary.total_payout,
            sanrenpuku_summary.return_rate * 100,
        ),
    ]

    # ヘッダ
    headers = ("券種", "的中数", "的中率", "投資額", "払戻額", "回収率")

    # 各列の最大幅を計算
    def format_cell(value, col_idx: int) -> str:
        """セルをフォーマット"""
        if col_idx == 0:  # 券種
            return str(value)
        elif col_idx == 1:  # 的中数
            return str(value)
        elif col_idx == 2:  # 的中率
            return f"{value:.1f}%"
        elif col_idx == 3:  # 投資額
            return f"{value:,}円"
        elif col_idx == 4:  # 払戻額
            return f"{value:,}円"
        elif col_idx == 5:  # 回収率
            return f"{value:.1f}%"
        return str(value)

    # 各列のフォーマット済み文字列を計算
    formatted_rows = []
    for row in rows:
        formatted_row = tuple(format_cell(val, i) for i, val in enumerate(row))
        formatted_rows.append(formatted_row)

    # 各列の最大表示幅を計算（ヘッダ含む）
    col_widths = []
    for col_idx in range(len(headers)):
        max_width = get_display_width(headers[col_idx])
        for row in formatted_rows:
            max_width = max(max_width, get_display_width(row[col_idx]))
        col_widths.append(max_width)

    # テーブル構築
    def make_border() -> str:
        return "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

    def make_row(cells: tuple) -> str:
        parts = []
        for i, cell in enumerate(cells):
            if i == 0:  # 左揃え
                padded = pad_to_width(cell, col_widths[i], align_right=False)
            else:  # 右揃え
                padded = pad_to_width(cell, col_widths[i], align_right=True)
            parts.append(f" {padded} ")
        return "|" + "|".join(parts) + "|"

    lines = [
        make_border(),
        make_row(headers),
        make_border(),
    ]
    for row in formatted_rows:
        lines.append(make_row(row))
    lines.append(make_border())

    return "\n".join(lines)
