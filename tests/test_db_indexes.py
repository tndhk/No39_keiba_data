"""データベースインデックス存在確認テスト

sqlite_masterテーブルをクエリしてインデックスの存在を検証する。
"""

import pytest
from sqlalchemy import text

from keiba.db import get_engine, get_session, init_db


@pytest.fixture
def engine():
    """インメモリSQLiteエンジンを作成"""
    return get_engine(":memory:")


@pytest.fixture
def initialized_engine(engine):
    """テーブルが初期化されたエンジン"""
    init_db(engine)
    return engine


class TestDatabaseIndexes:
    """データベースインデックスの存在確認テスト"""

    def test_ix_race_results_race_id_index_exists(self, initialized_engine):
        """ix_race_results_race_idインデックスが存在する"""
        with get_session(initialized_engine) as session:
            result = session.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='index' AND name='ix_race_results_race_id'"
                )
            ).fetchone()

            assert result is not None, (
                "ix_race_results_race_idインデックスが存在しません"
            )
            assert result[0] == "ix_race_results_race_id"

    def test_ix_races_date_index_exists(self, initialized_engine):
        """ix_races_dateインデックスが存在する"""
        with get_session(initialized_engine) as session:
            result = session.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='index' AND name='ix_races_date'"
                )
            ).fetchone()

            assert result is not None, (
                "ix_races_dateインデックスが存在しません"
            )
            assert result[0] == "ix_races_date"

    def test_ix_race_results_race_id_on_correct_table(self, initialized_engine):
        """ix_race_results_race_idがrace_resultsテーブルに作成されている"""
        with get_session(initialized_engine) as session:
            result = session.execute(
                text(
                    "SELECT tbl_name FROM sqlite_master "
                    "WHERE type='index' AND name='ix_race_results_race_id'"
                )
            ).fetchone()

            assert result is not None
            assert result[0] == "race_results"

    def test_ix_races_date_on_correct_table(self, initialized_engine):
        """ix_races_dateがracesテーブルに作成されている"""
        with get_session(initialized_engine) as session:
            result = session.execute(
                text(
                    "SELECT tbl_name FROM sqlite_master "
                    "WHERE type='index' AND name='ix_races_date'"
                )
            ).fetchone()

            assert result is not None
            assert result[0] == "races"

    def test_all_expected_indexes_exist(self, initialized_engine):
        """期待されるすべてのインデックスが存在する（一括確認）"""
        expected_indexes = {
            "ix_race_results_race_id",
            "ix_races_date",
        }

        with get_session(initialized_engine) as session:
            result = session.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='index' AND name LIKE 'ix_%'"
                )
            ).fetchall()

            actual_indexes = {row[0] for row in result}

            missing_indexes = expected_indexes - actual_indexes
            assert not missing_indexes, (
                f"以下のインデックスが存在しません: {missing_indexes}"
            )
