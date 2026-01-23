#!/usr/bin/env python3
"""既存のSQLiteデータベースにインデックスを追加するスクリプト."""

import argparse
import sqlite3
import sys
from pathlib import Path


def add_indexes(db_path: str) -> bool:
    """データベースにインデックスを追加する.

    Args:
        db_path: データベースファイルのパス

    Returns:
        成功した場合True、失敗した場合False
    """
    db_file = Path(db_path)

    if not db_file.exists():
        print(f"Error: データベースファイルが見つかりません: {db_path}")
        return False

    indexes = [
        ("ix_race_results_race_id", "race_results", "race_id"),
        ("ix_races_date", "races", "date"),
    ]

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print(f"データベース: {db_path}")
        print("-" * 50)

        for index_name, table_name, column_name in indexes:
            sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})"
            try:
                cursor.execute(sql)
                conn.commit()
                print(f"[OK] {index_name} ({table_name}.{column_name})")
            except sqlite3.OperationalError as e:
                print(f"[FAILED] {index_name}: {e}")

        conn.close()
        print("-" * 50)
        print("インデックス追加が完了しました")
        return True

    except sqlite3.Error as e:
        print(f"Error: データベースエラー: {e}")
        return False


def main() -> int:
    """メインエントリーポイント."""
    parser = argparse.ArgumentParser(
        description="SQLiteデータベースにインデックスを追加する"
    )
    parser.add_argument(
        "db_path",
        nargs="?",
        default="data/keiba.db",
        help="データベースファイルのパス (デフォルト: data/keiba.db)",
    )

    args = parser.parse_args()

    success = add_indexes(args.db_path)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
