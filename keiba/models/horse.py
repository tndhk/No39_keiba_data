"""Horseモデル定義"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from keiba.models.base import Base


class Horse(Base):
    """馬モデル

    Attributes:
        id: netkeiba馬ID（主キー）
        name: 馬名
        sex: 性別
        birth_year: 生年
        sire: 父
        dam: 母
        dam_sire: 母父
        coat_color: 毛色
        birthplace: 産地
        trainer_id: 調教師ID
        owner_id: 馬主ID
        breeder_id: 生産者ID
        total_races: 通算出走数
        total_wins: 通算勝利数
        total_earnings: 獲得賞金（万円）
        created_at: 作成日時
        updated_at: 更新日時
    """

    __tablename__ = "horses"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    sex: Mapped[str] = mapped_column(String, nullable=False)
    birth_year: Mapped[int] = mapped_column(nullable=False)

    # 血統情報
    sire: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    dam: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    dam_sire: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # 基本情報
    coat_color: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    birthplace: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # 関連ID
    trainer_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    owner_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    breeder_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # 成績情報
    total_races: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_wins: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_earnings: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Horse(id={self.id!r}, name={self.name!r})>"
