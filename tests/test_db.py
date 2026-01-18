"""データベース接続モジュールのテスト"""

from pathlib import Path

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from keiba.db import get_engine, get_session, init_db


class TestGetEngine:
    """get_engine関数のテスト"""

    def test_エンジンを作成できる(self, tmp_path: Path) -> None:
        """SQLiteエンジンを作成できることを確認"""
        db_path = tmp_path / "test.db"
        engine = get_engine(str(db_path))

        try:
            assert isinstance(engine, Engine)
            assert "sqlite" in str(engine.url)
        finally:
            engine.dispose()

    def test_指定したパスにデータベースファイルを作成する(self, tmp_path: Path) -> None:
        """指定したパスにSQLiteファイルが作成されることを確認"""
        db_path = tmp_path / "subdir" / "test.db"
        engine = get_engine(str(db_path))

        try:
            # エンジン接続時にファイルが作成される
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            assert db_path.exists()
        finally:
            engine.dispose()

    def test_メモリDBを作成できる(self) -> None:
        """インメモリSQLiteデータベースを作成できることを確認"""
        engine = get_engine(":memory:")

        try:
            assert isinstance(engine, Engine)
            assert "memory" in str(engine.url)
        finally:
            engine.dispose()


class TestGetSession:
    """get_session関数のテスト"""

    def test_セッションを取得できる(self, tmp_path: Path) -> None:
        """Sessionオブジェクトを取得できることを確認"""
        db_path = tmp_path / "test.db"
        engine = get_engine(str(db_path))

        try:
            with get_session(engine) as session:
                assert isinstance(session, Session)
        finally:
            engine.dispose()

    def test_コンテキストマネージャーで自動コミットされる(self, tmp_path: Path) -> None:
        """コンテキストマネージャー終了時に自動コミットされることを確認"""
        db_path = tmp_path / "test.db"
        engine = get_engine(str(db_path))

        try:
            # テスト用テーブルを作成
            with engine.connect() as conn:
                conn.execute(text("CREATE TABLE test_table (id INTEGER PRIMARY KEY, value TEXT)"))
                conn.commit()

            # セッションでデータを挿入
            with get_session(engine) as session:
                session.execute(text("INSERT INTO test_table (value) VALUES ('test')"))
                # 明示的なcommitなしでコンテキストを抜ける

            # 別セッションでデータが存在することを確認（コミットされている証拠）
            with get_session(engine) as session:
                result = session.execute(text("SELECT value FROM test_table")).fetchone()
                assert result is not None
                assert result[0] == "test"
        finally:
            engine.dispose()

    def test_例外発生時にロールバックされる(self, tmp_path: Path) -> None:
        """例外発生時にロールバックされることを確認"""
        db_path = tmp_path / "test.db"
        engine = get_engine(str(db_path))

        try:
            # テスト用テーブルを作成
            with engine.connect() as conn:
                conn.execute(text("CREATE TABLE test_table (id INTEGER PRIMARY KEY, value TEXT)"))
                conn.commit()

            # 例外を発生させるセッション
            with pytest.raises(ValueError):
                with get_session(engine) as session:
                    session.execute(text("INSERT INTO test_table (value) VALUES ('should_rollback')"))
                    raise ValueError("テスト用例外")

            # データが存在しないことを確認（ロールバックされている証拠）
            with get_session(engine) as session:
                result = session.execute(text("SELECT value FROM test_table")).fetchall()
                assert len(result) == 0
        finally:
            engine.dispose()


class TestInitDb:
    """init_db関数のテスト"""

    def test_テーブルを作成できる(self, tmp_path: Path) -> None:
        """Base.metadata.create_allでテーブルを作成できることを確認"""
        db_path = tmp_path / "test.db"
        engine = get_engine(str(db_path))

        try:
            # init_dbを呼び出し
            init_db(engine)

            # エラーなく完了することを確認（空のBaseでもOK）
            assert True
        finally:
            engine.dispose()

    def test_複数回呼び出しても安全(self, tmp_path: Path) -> None:
        """init_dbを複数回呼び出してもエラーにならないことを確認"""
        db_path = tmp_path / "test.db"
        engine = get_engine(str(db_path))

        try:
            # 複数回呼び出し
            init_db(engine)
            init_db(engine)

            # エラーなく完了することを確認
            assert True
        finally:
            engine.dispose()
