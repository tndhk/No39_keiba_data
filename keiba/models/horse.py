"""Horseモデル定義"""

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from keiba.models.base import Base


class Horse(Base):
    """馬モデル

    Attributes:
        id: netkeiba馬ID（主キー）
        name: 馬名
        sex: 性別
        birth_year: 生年
        created_at: 作成日時
        updated_at: 更新日時
    """

    __tablename__ = "horses"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    sex: Mapped[str] = mapped_column(String, nullable=False)
    birth_year: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Horse(id={self.id!r}, name={self.name!r})>"
