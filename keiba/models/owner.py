"""Ownerモデル定義"""

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from keiba.models.base import Base


class Owner(Base):
    """馬主モデル

    Attributes:
        id: 馬主ID（主キー）
        name: 馬主名
        created_at: 作成日時
        updated_at: 更新日時
    """

    __tablename__ = "owners"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Owner(id={self.id!r}, name={self.name!r})>"
