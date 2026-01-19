"""Raceモデル定義"""

from datetime import date, datetime

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from keiba.models.base import Base


class Race(Base):
    """レースモデル

    Attributes:
        id: レースID（主キー、例: "202405020811"）
        name: レース名
        date: 開催日
        course: 競馬場
        race_number: レース番号
        distance: 距離（メートル）
        surface: 芝/ダート
        weather: 天候
        track_condition: 馬場状態
        created_at: 作成日時
        updated_at: 更新日時
    """

    __tablename__ = "races"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    course: Mapped[str] = mapped_column(String, nullable=False)
    race_number: Mapped[int] = mapped_column(nullable=False)
    distance: Mapped[int] = mapped_column(nullable=False)
    surface: Mapped[str] = mapped_column(String, nullable=False)
    weather: Mapped[str | None] = mapped_column(String, nullable=True)
    track_condition: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Race(id={self.id!r}, name={self.name!r})>"
