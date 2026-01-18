"""SQLAlchemyベースクラス定義"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """すべてのモデルの基底クラス

    SQLAlchemy 2.0スタイルのDeclarativeBaseを使用。
    Task 3-4で作成するモデルはこのクラスを継承する。
    """

    pass
