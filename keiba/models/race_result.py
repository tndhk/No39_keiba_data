"""RaceResultモデル定義"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from keiba.models.base import Base

if TYPE_CHECKING:
    from keiba.models.horse import Horse
    from keiba.models.jockey import Jockey
    from keiba.models.race import Race
    from keiba.models.trainer import Trainer


class RaceResult(Base):
    """レース結果モデル

    Attributes:
        id: 自動採番ID（主キー）
        race_id: レースID（外部キー）
        horse_id: 馬ID（外部キー）
        jockey_id: 騎手ID（外部キー）
        trainer_id: 調教師ID（外部キー）
        finish_position: 着順
        bracket_number: 枠番
        horse_number: 馬番
        odds: 単勝オッズ
        popularity: 人気
        weight: 馬体重
        weight_diff: 馬体重増減
        time: タイム
        margin: 着差
        last_3f: 上がり3F（秒）
        sex: 性別（牡/牝/セ）
        age: 年齢
        impost: 斤量
        passing_order: 通過順位
        created_at: 作成日時
        updated_at: 更新日時
    """

    __tablename__ = "race_results"

    __table_args__ = (
        Index("ix_race_results_race_id", "race_id"),
        Index("ix_race_results_horse_id", "horse_id"),
        Index("ix_race_results_jockey_id", "jockey_id"),
        Index("ix_race_results_trainer_id", "trainer_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    race_id: Mapped[str] = mapped_column(
        String, ForeignKey("races.id"), nullable=False
    )
    horse_id: Mapped[str] = mapped_column(
        String, ForeignKey("horses.id"), nullable=False
    )
    jockey_id: Mapped[str] = mapped_column(
        String, ForeignKey("jockeys.id"), nullable=False
    )
    trainer_id: Mapped[str] = mapped_column(
        String, ForeignKey("trainers.id"), nullable=False
    )
    finish_position: Mapped[int] = mapped_column(nullable=False)
    bracket_number: Mapped[int] = mapped_column(nullable=False)
    horse_number: Mapped[int] = mapped_column(nullable=False)
    odds: Mapped[float | None] = mapped_column(nullable=True)
    popularity: Mapped[int | None] = mapped_column(nullable=True)
    weight: Mapped[int | None] = mapped_column(nullable=True)
    weight_diff: Mapped[int | None] = mapped_column(nullable=True)
    time: Mapped[str] = mapped_column(String, nullable=False)
    margin: Mapped[str] = mapped_column(String, nullable=False)
    last_3f: Mapped[float | None] = mapped_column(nullable=True)
    sex: Mapped[str | None] = mapped_column(String, nullable=True)
    age: Mapped[int | None] = mapped_column(nullable=True)
    impost: Mapped[float | None] = mapped_column(nullable=True)
    passing_order: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # リレーションシップ
    race: Mapped["Race"] = relationship("Race")
    horse: Mapped["Horse"] = relationship("Horse")
    jockey: Mapped["Jockey"] = relationship("Jockey")
    trainer: Mapped["Trainer"] = relationship("Trainer")

    def __repr__(self) -> str:
        return f"<RaceResult(race_id={self.race_id!r}, horse_id={self.horse_id!r})>"
