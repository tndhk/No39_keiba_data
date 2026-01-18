"""Breederモデル定義"""

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from keiba.models.base import Base


class Breeder(Base):
    """生産者モデル

    Attributes:
        id: 生産者ID（主キー）
        name: 生産者名
        created_at: 作成日時
        updated_at: 更新日時
    """

    __tablename__ = "breeders"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Breeder(id={self.id!r}, name={self.name!r})>"
