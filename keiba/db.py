"""データベース接続モジュール

SQLAlchemyを使用してSQLiteデータベースへの接続を管理する。
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from keiba.models.base import Base


def get_engine(db_path: str) -> Engine:
    """SQLiteデータベースエンジンを作成する

    Args:
        db_path: データベースファイルのパス。
                 ":memory:" を指定するとインメモリDBを作成。

    Returns:
        SQLAlchemyのEngineオブジェクト
    """
    # インメモリDB以外の場合、親ディレクトリを作成
    if db_path != ":memory:":
        parent_dir = Path(db_path).parent
        parent_dir.mkdir(parents=True, exist_ok=True)

    url = f"sqlite:///{db_path}"
    return create_engine(url)


@contextmanager
def get_session(engine: Engine) -> Generator[Session, None, None]:
    """データベースセッションを取得するコンテキストマネージャー

    正常終了時は自動コミット、例外発生時は自動ロールバックを行う。

    Args:
        engine: SQLAlchemyのEngineオブジェクト

    Yields:
        Sessionオブジェクト

    Example:
        with get_session(engine) as session:
            session.execute(text("INSERT INTO ..."))
            # 自動コミットされる
    """
    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine: Engine) -> None:
    """データベースのテーブルを初期化する

    Base.metadata.create_all()を呼び出し、
    定義されているすべてのテーブルを作成する。
    すでにテーブルが存在する場合は何もしない（冪等性あり）。

    Args:
        engine: SQLAlchemyのEngineオブジェクト
    """
    Base.metadata.create_all(engine)
