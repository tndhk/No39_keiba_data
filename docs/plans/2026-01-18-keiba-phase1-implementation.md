# 競馬データ収集システム Phase 1 実装計画

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** netkeibaからレースデータを収集しSQLiteに保存するCLIツールを構築する

**Architecture:** Python CLIアプリケーション。SQLAlchemyでDBモデルを定義し、BeautifulSoupでnetkeibaをスクレイピング。clickでCLIを提供。

**Tech Stack:** Python 3.11+, SQLAlchemy, BeautifulSoup4, requests, click, pytest

---

## Task 1: プロジェクトセットアップ

**Files:**
- Create: `pyproject.toml`
- Create: `keiba/__init__.py`
- Create: `keiba/__main__.py`
- Create: `tests/__init__.py`

**Step 1: pyproject.tomlを作成**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "keiba"
version = "0.1.0"
description = "競馬データ収集・分析システム"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "sqlalchemy>=2.0",
    "requests>=2.31",
    "beautifulsoup4>=4.12",
    "lxml>=5.0",
    "click>=8.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
]

[project.scripts]
keiba = "keiba.cli:main"
```

**Step 2: パッケージ初期化ファイルを作成**

`keiba/__init__.py`:
```python
"""競馬データ収集・分析システム"""

__version__ = "0.1.0"
```

`keiba/__main__.py`:
```python
"""CLIエントリーポイント"""

from keiba.cli import main

if __name__ == "__main__":
    main()
```

`tests/__init__.py`:
```python
"""テストパッケージ"""
```

**Step 3: 仮想環境を作成してインストール**

Run:
```bash
python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
```

**Step 4: dataディレクトリを作成**

Run:
```bash
mkdir -p data
```

**Step 5: コミット**

```bash
git add pyproject.toml keiba/ tests/ data/
git commit -m "chore: initialize project structure with dependencies"
```

---

## Task 2: データベース接続モジュール

**Files:**
- Create: `keiba/db.py`
- Create: `tests/test_db.py`

**Step 1: テストを作成**

`tests/test_db.py`:
```python
"""データベース接続のテスト"""

import os
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import text

from keiba.db import get_engine, get_session, init_db


def test_get_engine_creates_engine():
    """エンジンが作成されることを確認"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        engine = get_engine(db_path)
        assert engine is not None


def test_get_session_returns_session():
    """セッションが取得できることを確認"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        engine = get_engine(db_path)
        with get_session(engine) as session:
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1


def test_init_db_creates_tables():
    """init_dbでテーブルが作成されることを確認"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        engine = get_engine(db_path)
        init_db(engine)
        # テーブル存在確認は後のタスクで追加
        assert db_path.exists()
```

**Step 2: テストを実行して失敗を確認**

Run: `pytest tests/test_db.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'keiba.db'"

**Step 3: db.pyを実装**

`keiba/db.py`:
```python
"""データベース接続管理"""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from keiba.models import Base


def get_engine(db_path: Path | None = None) -> Engine:
    """SQLAlchemyエンジンを取得"""
    if db_path is None:
        db_path = Path(__file__).parent.parent / "data" / "keiba.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}", echo=False)


@contextmanager
def get_session(engine: Engine) -> Generator[Session, None, None]:
    """セッションをコンテキストマネージャとして取得"""
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
    """データベースを初期化（テーブル作成）"""
    Base.metadata.create_all(engine)
```

**Step 4: modelsパッケージのスタブを作成（テスト通過用）**

`keiba/models/__init__.py`:
```python
"""データモデル"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemyベースクラス"""
    pass
```

**Step 5: テストを実行して成功を確認**

Run: `pytest tests/test_db.py -v`
Expected: PASS

**Step 6: コミット**

```bash
git add keiba/db.py keiba/models/__init__.py tests/test_db.py
git commit -m "feat: add database connection module"
```

---

## Task 3: 基本データモデル（Horse, Jockey, Trainer）

**Files:**
- Create: `keiba/models/base.py`
- Create: `keiba/models/horse.py`
- Create: `keiba/models/jockey.py`
- Create: `keiba/models/trainer.py`
- Modify: `keiba/models/__init__.py`
- Create: `tests/test_models.py`

**Step 1: テストを作成**

`tests/test_models.py`:
```python
"""データモデルのテスト"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from keiba.db import get_engine, get_session, init_db
from keiba.models import Horse, Jockey, Trainer


@pytest.fixture
def db_session():
    """テスト用DBセッション"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        engine = get_engine(db_path)
        init_db(engine)
        with get_session(engine) as session:
            yield session


def test_create_horse(db_session):
    """馬を作成できることを確認"""
    horse = Horse(
        netkeiba_id="2019104308",
        name="イクイノックス",
        birth_year=2019,
        sex="牡",
        sire="キタサンブラック",
        dam="シャトーブランシュ",
    )
    db_session.add(horse)
    db_session.flush()

    result = db_session.execute(
        select(Horse).where(Horse.netkeiba_id == "2019104308")
    ).scalar_one()
    assert result.name == "イクイノックス"
    assert result.sire == "キタサンブラック"


def test_create_jockey(db_session):
    """騎手を作成できることを確認"""
    jockey = Jockey(netkeiba_id="01170", name="ルメール")
    db_session.add(jockey)
    db_session.flush()

    result = db_session.execute(
        select(Jockey).where(Jockey.netkeiba_id == "01170")
    ).scalar_one()
    assert result.name == "ルメール"


def test_create_trainer(db_session):
    """調教師を作成できることを確認"""
    trainer = Trainer(netkeiba_id="01084", name="木村哲也")
    db_session.add(trainer)
    db_session.flush()

    result = db_session.execute(
        select(Trainer).where(Trainer.netkeiba_id == "01084")
    ).scalar_one()
    assert result.name == "木村哲也"


def test_horse_unique_netkeiba_id(db_session):
    """netkeiba_idの重複がエラーになることを確認"""
    horse1 = Horse(netkeiba_id="2019104308", name="イクイノックス")
    horse2 = Horse(netkeiba_id="2019104308", name="別の馬")
    db_session.add(horse1)
    db_session.flush()
    db_session.add(horse2)
    with pytest.raises(Exception):  # IntegrityError
        db_session.flush()
```

**Step 2: テストを実行して失敗を確認**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with "ImportError: cannot import name 'Horse'"

**Step 3: ベースモデルを作成**

`keiba/models/base.py`:
```python
"""モデル共通ベースクラス"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemyベースクラス"""
    pass


class TimestampMixin:
    """作成日時・更新日時を持つMixin"""
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
```

**Step 4: Horseモデルを作成**

`keiba/models/horse.py`:
```python
"""馬モデル"""

from typing import Optional

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from keiba.models.base import Base, TimestampMixin


class Horse(Base, TimestampMixin):
    """馬"""
    __tablename__ = "horses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    netkeiba_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    birth_year: Mapped[Optional[int]] = mapped_column(Integer)
    sex: Mapped[Optional[str]] = mapped_column(String(10))
    sire: Mapped[Optional[str]] = mapped_column(String(100))  # 父
    dam: Mapped[Optional[str]] = mapped_column(String(100))  # 母
    dam_sire: Mapped[Optional[str]] = mapped_column(String(100))  # 母父
    sire_of_sire: Mapped[Optional[str]] = mapped_column(String(100))  # 父父
    dam_of_sire: Mapped[Optional[str]] = mapped_column(String(100))  # 父母
    breeder: Mapped[Optional[str]] = mapped_column(String(100))  # 生産者
    owner: Mapped[Optional[str]] = mapped_column(String(100))  # 馬主
    birthplace: Mapped[Optional[str]] = mapped_column(String(50))  # 産地
    coat_color: Mapped[Optional[str]] = mapped_column(String(20))  # 毛色
    sale_price: Mapped[Optional[int]] = mapped_column(Integer)  # セリ取引価格
    total_races: Mapped[Optional[int]] = mapped_column(Integer)  # 通算出走数
    total_wins: Mapped[Optional[int]] = mapped_column(Integer)  # 通算勝利数
    total_earnings: Mapped[Optional[int]] = mapped_column(Integer)  # 獲得賞金

    def __repr__(self) -> str:
        return f"<Horse(id={self.id}, name={self.name})>"
```

**Step 5: Jockeyモデルを作成**

`keiba/models/jockey.py`:
```python
"""騎手モデル"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from keiba.models.base import Base, TimestampMixin


class Jockey(Base, TimestampMixin):
    """騎手"""
    __tablename__ = "jockeys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    netkeiba_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    def __repr__(self) -> str:
        return f"<Jockey(id={self.id}, name={self.name})>"
```

**Step 6: Trainerモデルを作成**

`keiba/models/trainer.py`:
```python
"""調教師モデル"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from keiba.models.base import Base, TimestampMixin


class Trainer(Base, TimestampMixin):
    """調教師"""
    __tablename__ = "trainers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    netkeiba_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    def __repr__(self) -> str:
        return f"<Trainer(id={self.id}, name={self.name})>"
```

**Step 7: models/__init__.pyを更新**

`keiba/models/__init__.py`:
```python
"""データモデル"""

from keiba.models.base import Base, TimestampMixin
from keiba.models.horse import Horse
from keiba.models.jockey import Jockey
from keiba.models.trainer import Trainer

__all__ = ["Base", "TimestampMixin", "Horse", "Jockey", "Trainer"]
```

**Step 8: テストを実行して成功を確認**

Run: `pytest tests/test_models.py -v`
Expected: PASS

**Step 9: コミット**

```bash
git add keiba/models/ tests/test_models.py
git commit -m "feat: add Horse, Jockey, Trainer models"
```

---

## Task 4: 追加データモデル（Owner, Breeder, Race, RaceResult）

**Files:**
- Create: `keiba/models/owner.py`
- Create: `keiba/models/breeder.py`
- Create: `keiba/models/race.py`
- Create: `keiba/models/race_result.py`
- Modify: `keiba/models/__init__.py`
- Modify: `tests/test_models.py`

**Step 1: テストを追加**

`tests/test_models.py`に追加:
```python
from keiba.models import Owner, Breeder, Race, RaceResult


def test_create_owner(db_session):
    """馬主を作成できることを確認"""
    owner = Owner(netkeiba_id="001234", name="サンデーレーシング")
    db_session.add(owner)
    db_session.flush()

    result = db_session.execute(
        select(Owner).where(Owner.netkeiba_id == "001234")
    ).scalar_one()
    assert result.name == "サンデーレーシング"


def test_create_breeder(db_session):
    """生産者を作成できることを確認"""
    breeder = Breeder(
        netkeiba_id="002345",
        name="ノーザンファーム",
        location="北海道"
    )
    db_session.add(breeder)
    db_session.flush()

    result = db_session.execute(
        select(Breeder).where(Breeder.netkeiba_id == "002345")
    ).scalar_one()
    assert result.name == "ノーザンファーム"
    assert result.location == "北海道"


def test_create_race(db_session):
    """レースを作成できることを確認"""
    from datetime import date
    race = Race(
        netkeiba_id="202306050811",
        name="有馬記念",
        date=date(2023, 12, 24),
        venue="中山",
        race_number=11,
        course_type="芝",
        distance=2500,
        grade="G1",
    )
    db_session.add(race)
    db_session.flush()

    result = db_session.execute(
        select(Race).where(Race.netkeiba_id == "202306050811")
    ).scalar_one()
    assert result.name == "有馬記念"
    assert result.distance == 2500


def test_create_race_result(db_session):
    """レース結果を作成できることを確認"""
    from datetime import date
    # 先に関連データを作成
    horse = Horse(netkeiba_id="2019104308", name="イクイノックス")
    jockey = Jockey(netkeiba_id="01170", name="ルメール")
    trainer = Trainer(netkeiba_id="01084", name="木村哲也")
    race = Race(
        netkeiba_id="202306050811",
        name="有馬記念",
        date=date(2023, 12, 24),
        venue="中山",
        race_number=11,
    )
    db_session.add_all([horse, jockey, trainer, race])
    db_session.flush()

    result = RaceResult(
        race_id=race.id,
        horse_id=horse.id,
        jockey_id=jockey.id,
        trainer_id=trainer.id,
        post_position=5,
        horse_number=7,
        finish_position=1,
        odds=1.4,
        popularity=1,
    )
    db_session.add(result)
    db_session.flush()

    fetched = db_session.execute(
        select(RaceResult).where(RaceResult.race_id == race.id)
    ).scalar_one()
    assert fetched.finish_position == 1
    assert fetched.horse.name == "イクイノックス"
```

**Step 2: テストを実行して失敗を確認**

Run: `pytest tests/test_models.py::test_create_owner -v`
Expected: FAIL with "ImportError: cannot import name 'Owner'"

**Step 3: Owner, Breederモデルを作成**

`keiba/models/owner.py`:
```python
"""馬主モデル"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from keiba.models.base import Base, TimestampMixin


class Owner(Base, TimestampMixin):
    """馬主"""
    __tablename__ = "owners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    netkeiba_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    def __repr__(self) -> str:
        return f"<Owner(id={self.id}, name={self.name})>"
```

`keiba/models/breeder.py`:
```python
"""生産者モデル"""

from typing import Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from keiba.models.base import Base, TimestampMixin


class Breeder(Base, TimestampMixin):
    """生産者"""
    __tablename__ = "breeders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    netkeiba_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(50))

    def __repr__(self) -> str:
        return f"<Breeder(id={self.id}, name={self.name})>"
```

**Step 4: Raceモデルを作成**

`keiba/models/race.py`:
```python
"""レースモデル"""

from datetime import date
from typing import Optional

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from keiba.models.base import Base, TimestampMixin


class Race(Base, TimestampMixin):
    """レース"""
    __tablename__ = "races"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    netkeiba_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    venue: Mapped[Optional[str]] = mapped_column(String(20))  # 開催場
    race_number: Mapped[Optional[int]] = mapped_column(Integer)
    course_type: Mapped[Optional[str]] = mapped_column(String(10))  # 芝/ダート
    distance: Mapped[Optional[int]] = mapped_column(Integer)
    weather: Mapped[Optional[str]] = mapped_column(String(20))
    track_condition: Mapped[Optional[str]] = mapped_column(String(20))  # 馬場状態
    grade: Mapped[Optional[str]] = mapped_column(String(20))

    results: Mapped[list["RaceResult"]] = relationship(back_populates="race")

    def __repr__(self) -> str:
        return f"<Race(id={self.id}, name={self.name}, date={self.date})>"


# 循環インポート回避のため後からインポート
from keiba.models.race_result import RaceResult
```

**Step 5: RaceResultモデルを作成**

`keiba/models/race_result.py`:
```python
"""レース結果モデル"""

from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from keiba.models.base import Base, TimestampMixin


class RaceResult(Base, TimestampMixin):
    """レース結果"""
    __tablename__ = "race_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), nullable=False)
    horse_id: Mapped[int] = mapped_column(ForeignKey("horses.id"), nullable=False)
    jockey_id: Mapped[Optional[int]] = mapped_column(ForeignKey("jockeys.id"))
    trainer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("trainers.id"))
    post_position: Mapped[Optional[int]] = mapped_column(Integer)  # 枠番
    horse_number: Mapped[Optional[int]] = mapped_column(Integer)  # 馬番
    finish_position: Mapped[Optional[int]] = mapped_column(Integer)  # 着順
    finish_time: Mapped[Optional[str]] = mapped_column(String(20))  # タイム
    margin: Mapped[Optional[str]] = mapped_column(String(20))  # 着差
    weight: Mapped[Optional[int]] = mapped_column(Integer)  # 馬体重
    weight_change: Mapped[Optional[int]] = mapped_column(Integer)  # 馬体重増減
    odds: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))  # 単勝オッズ
    popularity: Mapped[Optional[int]] = mapped_column(Integer)  # 人気

    race: Mapped["Race"] = relationship(back_populates="results")
    horse: Mapped["Horse"] = relationship()
    jockey: Mapped[Optional["Jockey"]] = relationship()
    trainer: Mapped[Optional["Trainer"]] = relationship()

    def __repr__(self) -> str:
        return f"<RaceResult(race_id={self.race_id}, horse_id={self.horse_id}, position={self.finish_position})>"


# 循環インポート回避
from keiba.models.horse import Horse
from keiba.models.jockey import Jockey
from keiba.models.race import Race
from keiba.models.trainer import Trainer
```

**Step 6: models/__init__.pyを更新**

`keiba/models/__init__.py`:
```python
"""データモデル"""

from keiba.models.base import Base, TimestampMixin
from keiba.models.horse import Horse
from keiba.models.jockey import Jockey
from keiba.models.trainer import Trainer
from keiba.models.owner import Owner
from keiba.models.breeder import Breeder
from keiba.models.race import Race
from keiba.models.race_result import RaceResult

__all__ = [
    "Base",
    "TimestampMixin",
    "Horse",
    "Jockey",
    "Trainer",
    "Owner",
    "Breeder",
    "Race",
    "RaceResult",
]
```

**Step 7: テストを実行して成功を確認**

Run: `pytest tests/test_models.py -v`
Expected: PASS

**Step 8: コミット**

```bash
git add keiba/models/ tests/test_models.py
git commit -m "feat: add Owner, Breeder, Race, RaceResult models"
```

---

## Task 5: ベーススクレイパー

**Files:**
- Create: `keiba/scrapers/__init__.py`
- Create: `keiba/scrapers/base.py`
- Create: `tests/test_scrapers.py`

**Step 1: テストを作成**

`tests/test_scrapers.py`:
```python
"""スクレイパーのテスト"""

import pytest
from unittest.mock import Mock, patch

from keiba.scrapers.base import BaseScraper


class TestBaseScraper:
    """ベーススクレイパーのテスト"""

    def test_init_with_default_delay(self):
        """デフォルトのリクエスト間隔で初期化"""
        scraper = BaseScraper()
        assert scraper.request_delay == 1.0

    def test_init_with_custom_delay(self):
        """カスタムのリクエスト間隔で初期化"""
        scraper = BaseScraper(request_delay=2.0)
        assert scraper.request_delay == 2.0

    @patch("keiba.scrapers.base.requests.get")
    def test_fetch_returns_soup(self, mock_get):
        """fetchがBeautifulSoupオブジェクトを返す"""
        mock_response = Mock()
        mock_response.text = "<html><body><h1>Test</h1></body></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper = BaseScraper(request_delay=0)
        soup = scraper.fetch("https://example.com")

        assert soup.h1.text == "Test"

    @patch("keiba.scrapers.base.requests.get")
    def test_fetch_retries_on_error(self, mock_get):
        """エラー時にリトライする"""
        from requests.exceptions import RequestException

        mock_get.side_effect = [
            RequestException("Connection error"),
            Mock(text="<html></html>", raise_for_status=Mock()),
        ]

        scraper = BaseScraper(request_delay=0, max_retries=3)
        soup = scraper.fetch("https://example.com")

        assert soup is not None
        assert mock_get.call_count == 2

    @patch("keiba.scrapers.base.requests.get")
    def test_fetch_raises_after_max_retries(self, mock_get):
        """最大リトライ回数を超えるとエラー"""
        from requests.exceptions import RequestException

        mock_get.side_effect = RequestException("Connection error")

        scraper = BaseScraper(request_delay=0, max_retries=3)
        with pytest.raises(RequestException):
            scraper.fetch("https://example.com")

        assert mock_get.call_count == 3
```

**Step 2: テストを実行して失敗を確認**

Run: `pytest tests/test_scrapers.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'keiba.scrapers'"

**Step 3: ベーススクレイパーを実装**

`keiba/scrapers/__init__.py`:
```python
"""スクレイパーパッケージ"""

from keiba.scrapers.base import BaseScraper

__all__ = ["BaseScraper"]
```

`keiba/scrapers/base.py`:
```python
"""ベーススクレイパー"""

import time
from typing import Optional

import requests
from bs4 import BeautifulSoup


class BaseScraper:
    """スクレイパーの基底クラス"""

    BASE_URL = "https://db.netkeiba.com"

    def __init__(
        self,
        request_delay: float = 1.0,
        max_retries: int = 3,
    ):
        self.request_delay = request_delay
        self.max_retries = max_retries
        self._last_request_time: Optional[float] = None

    def _wait(self) -> None:
        """リクエスト間隔を守る"""
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.request_delay:
                time.sleep(self.request_delay - elapsed)

    def fetch(self, url: str) -> BeautifulSoup:
        """URLからHTMLを取得してパース"""
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                self._wait()
                response = requests.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                    },
                    timeout=30,
                )
                self._last_request_time = time.time()
                response.raise_for_status()
                return BeautifulSoup(response.text, "lxml")
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    time.sleep(1)  # リトライ前に少し待つ

        raise last_exception
```

**Step 4: テストを実行して成功を確認**

Run: `pytest tests/test_scrapers.py -v`
Expected: PASS

**Step 5: コミット**

```bash
git add keiba/scrapers/ tests/test_scrapers.py
git commit -m "feat: add base scraper with retry logic"
```

---

## Task 6: レース一覧スクレイパー

**Files:**
- Create: `keiba/scrapers/race_list.py`
- Create: `tests/fixtures/race_list.html`
- Modify: `tests/test_scrapers.py`

**Step 1: テスト用HTMLフィクスチャを作成**

`tests/fixtures/race_list.html`:
```html
<!DOCTYPE html>
<html>
<head><title>レース一覧</title></head>
<body>
<table class="race_table_01">
  <tr>
    <td class="race_date"><a href="/race/202401010101/">2024/01/06</a></td>
    <td><a href="/race/202401010101/">中山1R</a></td>
  </tr>
  <tr>
    <td class="race_date"><a href="/race/202401010102/">2024/01/06</a></td>
    <td><a href="/race/202401010102/">中山2R</a></td>
  </tr>
  <tr>
    <td class="race_date"><a href="/race/202401010111/">2024/01/06</a></td>
    <td><a href="/race/202401010111/">中山11R</a></td>
  </tr>
</table>
</body>
</html>
```

**Step 2: テストを追加**

`tests/test_scrapers.py`に追加:
```python
from pathlib import Path

from keiba.scrapers.race_list import RaceListScraper


class TestRaceListScraper:
    """レース一覧スクレイパーのテスト"""

    @pytest.fixture
    def sample_html(self):
        """テスト用HTML"""
        fixture_path = Path(__file__).parent / "fixtures" / "race_list.html"
        return fixture_path.read_text()

    def test_parse_race_ids(self, sample_html):
        """レースIDを抽出できる"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(sample_html, "lxml")

        scraper = RaceListScraper()
        race_ids = scraper.parse_race_ids(soup)

        assert len(race_ids) == 3
        assert "202401010101" in race_ids
        assert "202401010102" in race_ids
        assert "202401010111" in race_ids

    @patch("keiba.scrapers.base.requests.get")
    def test_get_race_ids_for_month(self, mock_get, sample_html):
        """月のレースID一覧を取得"""
        mock_response = Mock()
        mock_response.text = sample_html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper = RaceListScraper(request_delay=0)
        race_ids = scraper.get_race_ids_for_month(2024, 1)

        assert len(race_ids) == 3
```

**Step 3: テストを実行して失敗を確認**

Run: `pytest tests/test_scrapers.py::TestRaceListScraper -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'keiba.scrapers.race_list'"

**Step 4: レース一覧スクレイパーを実装**

`keiba/scrapers/race_list.py`:
```python
"""レース一覧スクレイパー"""

import re
from typing import List

from bs4 import BeautifulSoup

from keiba.scrapers.base import BaseScraper


class RaceListScraper(BaseScraper):
    """レース一覧を取得するスクレイパー"""

    def parse_race_ids(self, soup: BeautifulSoup) -> List[str]:
        """HTMLからレースIDを抽出"""
        race_ids = []
        pattern = re.compile(r"/race/(\d+)/")

        for link in soup.find_all("a", href=pattern):
            match = pattern.search(link["href"])
            if match:
                race_id = match.group(1)
                if race_id not in race_ids:
                    race_ids.append(race_id)

        return race_ids

    def get_race_ids_for_month(self, year: int, month: int) -> List[str]:
        """指定年月のレースID一覧を取得"""
        url = f"{self.BASE_URL}/?pid=race_list&word=&track%5B%5D=1&track%5B%5D=2&start_year={year}&start_mon={month}&end_year={year}&end_mon={month}"
        soup = self.fetch(url)
        return self.parse_race_ids(soup)

    def get_race_ids_for_year(self, year: int) -> List[str]:
        """指定年のレースID一覧を取得"""
        all_race_ids = []
        for month in range(1, 13):
            race_ids = self.get_race_ids_for_month(year, month)
            all_race_ids.extend(race_ids)
        return all_race_ids
```

**Step 5: scrapers/__init__.pyを更新**

`keiba/scrapers/__init__.py`:
```python
"""スクレイパーパッケージ"""

from keiba.scrapers.base import BaseScraper
from keiba.scrapers.race_list import RaceListScraper

__all__ = ["BaseScraper", "RaceListScraper"]
```

**Step 6: fixturesディレクトリを作成してテスト**

Run:
```bash
mkdir -p tests/fixtures
```

**Step 7: テストを実行して成功を確認**

Run: `pytest tests/test_scrapers.py -v`
Expected: PASS

**Step 8: コミット**

```bash
git add keiba/scrapers/ tests/
git commit -m "feat: add race list scraper"
```

---

## Task 7: レース詳細スクレイパー

**Files:**
- Create: `keiba/scrapers/race_detail.py`
- Create: `tests/fixtures/race_detail.html`
- Modify: `tests/test_scrapers.py`

**Step 1: テスト用HTMLフィクスチャを作成**

`tests/fixtures/race_detail.html`:
```html
<!DOCTYPE html>
<html>
<head><title>有馬記念</title></head>
<body>
<div class="RaceData01">
  <span>芝右2500m / 天候:晴 / 馬場:良</span>
</div>
<div class="RaceData02">
  <span>2023年12月24日</span>
  <span>中山11R</span>
  <span>G1</span>
</div>
<dl class="RaceName">
  <dd>有馬記念</dd>
</dl>
<table class="RaceTable01" id="All_Result_Table">
  <tr class="HorseList">
    <td class="Rank">1</td>
    <td class="Waku"><span>5</span></td>
    <td class="Umaban">7</td>
    <td class="Horse">
      <a href="/horse/2019104308/">イクイノックス</a>
    </td>
    <td class="Jockey">
      <a href="/jockey/01170/">ルメール</a>
    </td>
    <td class="Trainer">
      <a href="/trainer/01084/">木村哲也</a>
    </td>
    <td class="Weight">486(-2)</td>
    <td class="Time">2:30.9</td>
    <td class="Odds">1.4</td>
    <td class="Popular">1</td>
  </tr>
  <tr class="HorseList">
    <td class="Rank">2</td>
    <td class="Waku"><span>3</span></td>
    <td class="Umaban">5</td>
    <td class="Horse">
      <a href="/horse/2019103456/">ドウデュース</a>
    </td>
    <td class="Jockey">
      <a href="/jockey/05339/">武豊</a>
    </td>
    <td class="Trainer">
      <a href="/trainer/01076/">友道康夫</a>
    </td>
    <td class="Weight">502(+4)</td>
    <td class="Time">2:31.2</td>
    <td class="Odds">5.8</td>
    <td class="Popular">3</td>
  </tr>
</table>
</body>
</html>
```

**Step 2: テストを追加**

`tests/test_scrapers.py`に追加:
```python
from keiba.scrapers.race_detail import RaceDetailScraper, RaceData, HorseEntry


class TestRaceDetailScraper:
    """レース詳細スクレイパーのテスト"""

    @pytest.fixture
    def sample_html(self):
        """テスト用HTML"""
        fixture_path = Path(__file__).parent / "fixtures" / "race_detail.html"
        return fixture_path.read_text()

    def test_parse_race_info(self, sample_html):
        """レース情報を抽出できる"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(sample_html, "lxml")

        scraper = RaceDetailScraper()
        race_data = scraper.parse_race_info(soup, "202306050811")

        assert race_data.name == "有馬記念"
        assert race_data.venue == "中山"
        assert race_data.race_number == 11
        assert race_data.distance == 2500
        assert race_data.course_type == "芝"
        assert race_data.grade == "G1"

    def test_parse_race_results(self, sample_html):
        """レース結果を抽出できる"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(sample_html, "lxml")

        scraper = RaceDetailScraper()
        entries = scraper.parse_race_results(soup)

        assert len(entries) == 2

        first = entries[0]
        assert first.horse_id == "2019104308"
        assert first.horse_name == "イクイノックス"
        assert first.jockey_id == "01170"
        assert first.finish_position == 1
        assert first.odds == 1.4

        second = entries[1]
        assert second.horse_id == "2019103456"
        assert second.finish_position == 2
```

**Step 3: テストを実行して失敗を確認**

Run: `pytest tests/test_scrapers.py::TestRaceDetailScraper -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 4: レース詳細スクレイパーを実装**

`keiba/scrapers/race_detail.py`:
```python
"""レース詳細スクレイパー"""

import re
from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from bs4 import BeautifulSoup

from keiba.scrapers.base import BaseScraper


@dataclass
class HorseEntry:
    """出走馬情報"""
    horse_id: str
    horse_name: str
    jockey_id: Optional[str] = None
    jockey_name: Optional[str] = None
    trainer_id: Optional[str] = None
    trainer_name: Optional[str] = None
    post_position: Optional[int] = None
    horse_number: Optional[int] = None
    finish_position: Optional[int] = None
    finish_time: Optional[str] = None
    weight: Optional[int] = None
    weight_change: Optional[int] = None
    odds: Optional[float] = None
    popularity: Optional[int] = None


@dataclass
class RaceData:
    """レース情報"""
    netkeiba_id: str
    name: str
    date: Optional[date] = None
    venue: Optional[str] = None
    race_number: Optional[int] = None
    course_type: Optional[str] = None
    distance: Optional[int] = None
    weather: Optional[str] = None
    track_condition: Optional[str] = None
    grade: Optional[str] = None
    entries: Optional[List[HorseEntry]] = None


class RaceDetailScraper(BaseScraper):
    """レース詳細を取得するスクレイパー"""

    def parse_race_info(self, soup: BeautifulSoup, race_id: str) -> RaceData:
        """HTMLからレース情報を抽出"""
        # レース名
        name_elem = soup.select_one("dl.RaceName dd, .RaceName")
        name = name_elem.get_text(strip=True) if name_elem else "不明"

        # 距離・馬場情報
        data01 = soup.select_one(".RaceData01")
        distance = None
        course_type = None
        weather = None
        track_condition = None

        if data01:
            text = data01.get_text()
            # 芝/ダート と距離
            match = re.search(r"(芝|ダート)[^\d]*(\d+)m", text)
            if match:
                course_type = match.group(1)
                distance = int(match.group(2))
            # 天候
            weather_match = re.search(r"天候:(\S+)", text)
            if weather_match:
                weather = weather_match.group(1)
            # 馬場状態
            track_match = re.search(r"馬場:(\S+)", text)
            if track_match:
                track_condition = track_match.group(1)

        # 開催場・レース番号
        data02 = soup.select_one(".RaceData02")
        venue = None
        race_number = None
        grade = None

        if data02:
            text = data02.get_text()
            # 開催場とレース番号
            venue_match = re.search(r"(東京|中山|阪神|京都|中京|小倉|新潟|福島|札幌|函館)(\d+)R", text)
            if venue_match:
                venue = venue_match.group(1)
                race_number = int(venue_match.group(2))
            # グレード
            grade_match = re.search(r"(G[1-3]|OP|L|新馬|未勝利|\dR)", text)
            if grade_match:
                grade = grade_match.group(1)

        return RaceData(
            netkeiba_id=race_id,
            name=name,
            venue=venue,
            race_number=race_number,
            course_type=course_type,
            distance=distance,
            weather=weather,
            track_condition=track_condition,
            grade=grade,
        )

    def parse_race_results(self, soup: BeautifulSoup) -> List[HorseEntry]:
        """HTMLからレース結果を抽出"""
        entries = []
        rows = soup.select("table.RaceTable01 tr.HorseList, table#All_Result_Table tr.HorseList")

        for row in rows:
            # 馬ID・馬名
            horse_link = row.select_one("td.Horse a")
            if not horse_link:
                continue

            horse_href = horse_link.get("href", "")
            horse_id_match = re.search(r"/horse/(\d+)/", horse_href)
            horse_id = horse_id_match.group(1) if horse_id_match else ""
            horse_name = horse_link.get_text(strip=True)

            # 騎手
            jockey_link = row.select_one("td.Jockey a")
            jockey_id = None
            jockey_name = None
            if jockey_link:
                jockey_href = jockey_link.get("href", "")
                jockey_match = re.search(r"/jockey/(\d+)/", jockey_href)
                jockey_id = jockey_match.group(1) if jockey_match else None
                jockey_name = jockey_link.get_text(strip=True)

            # 調教師
            trainer_link = row.select_one("td.Trainer a")
            trainer_id = None
            trainer_name = None
            if trainer_link:
                trainer_href = trainer_link.get("href", "")
                trainer_match = re.search(r"/trainer/(\d+)/", trainer_href)
                trainer_id = trainer_match.group(1) if trainer_match else None
                trainer_name = trainer_link.get_text(strip=True)

            # 着順
            rank_elem = row.select_one("td.Rank")
            finish_position = None
            if rank_elem:
                rank_text = rank_elem.get_text(strip=True)
                if rank_text.isdigit():
                    finish_position = int(rank_text)

            # 枠番
            waku_elem = row.select_one("td.Waku span")
            post_position = None
            if waku_elem:
                waku_text = waku_elem.get_text(strip=True)
                if waku_text.isdigit():
                    post_position = int(waku_text)

            # 馬番
            umaban_elem = row.select_one("td.Umaban")
            horse_number = None
            if umaban_elem:
                umaban_text = umaban_elem.get_text(strip=True)
                if umaban_text.isdigit():
                    horse_number = int(umaban_text)

            # タイム
            time_elem = row.select_one("td.Time")
            finish_time = time_elem.get_text(strip=True) if time_elem else None

            # 馬体重
            weight_elem = row.select_one("td.Weight")
            weight = None
            weight_change = None
            if weight_elem:
                weight_text = weight_elem.get_text(strip=True)
                weight_match = re.search(r"(\d+)\(([+-]?\d+)\)", weight_text)
                if weight_match:
                    weight = int(weight_match.group(1))
                    weight_change = int(weight_match.group(2))

            # オッズ
            odds_elem = row.select_one("td.Odds")
            odds = None
            if odds_elem:
                odds_text = odds_elem.get_text(strip=True)
                try:
                    odds = float(odds_text)
                except ValueError:
                    pass

            # 人気
            popular_elem = row.select_one("td.Popular")
            popularity = None
            if popular_elem:
                pop_text = popular_elem.get_text(strip=True)
                if pop_text.isdigit():
                    popularity = int(pop_text)

            entries.append(HorseEntry(
                horse_id=horse_id,
                horse_name=horse_name,
                jockey_id=jockey_id,
                jockey_name=jockey_name,
                trainer_id=trainer_id,
                trainer_name=trainer_name,
                post_position=post_position,
                horse_number=horse_number,
                finish_position=finish_position,
                finish_time=finish_time,
                weight=weight,
                weight_change=weight_change,
                odds=odds,
                popularity=popularity,
            ))

        return entries

    def get_race(self, race_id: str) -> RaceData:
        """レースIDからレース情報と結果を取得"""
        url = f"{self.BASE_URL}/race/{race_id}/"
        soup = self.fetch(url)

        race_data = self.parse_race_info(soup, race_id)
        race_data.entries = self.parse_race_results(soup)

        return race_data
```

**Step 5: scrapers/__init__.pyを更新**

`keiba/scrapers/__init__.py`:
```python
"""スクレイパーパッケージ"""

from keiba.scrapers.base import BaseScraper
from keiba.scrapers.race_list import RaceListScraper
from keiba.scrapers.race_detail import RaceDetailScraper, RaceData, HorseEntry

__all__ = [
    "BaseScraper",
    "RaceListScraper",
    "RaceDetailScraper",
    "RaceData",
    "HorseEntry",
]
```

**Step 6: テストを実行して成功を確認**

Run: `pytest tests/test_scrapers.py -v`
Expected: PASS

**Step 7: コミット**

```bash
git add keiba/scrapers/ tests/
git commit -m "feat: add race detail scraper"
```

---

## Task 8: CLIコマンド

**Files:**
- Create: `keiba/cli.py`
- Create: `tests/test_cli.py`

**Step 1: テストを作成**

`tests/test_cli.py`:
```python
"""CLIのテスト"""

import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

import pytest
from click.testing import CliRunner

from keiba.cli import main, scrape


@pytest.fixture
def runner():
    """CLIテストランナー"""
    return CliRunner()


def test_main_shows_help(runner):
    """ヘルプが表示される"""
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "競馬データ収集" in result.output


def test_scrape_shows_help(runner):
    """scrapeコマンドのヘルプが表示される"""
    result = runner.invoke(scrape, ["--help"])
    assert result.exit_code == 0
    assert "--year" in result.output


@patch("keiba.cli.RaceListScraper")
@patch("keiba.cli.RaceDetailScraper")
def test_scrape_fetches_races(mock_detail, mock_list, runner):
    """レースを取得する"""
    # モックの設定
    mock_list_instance = Mock()
    mock_list_instance.get_race_ids_for_month.return_value = ["202401010101"]
    mock_list.return_value = mock_list_instance

    mock_detail_instance = Mock()
    mock_race = Mock()
    mock_race.netkeiba_id = "202401010101"
    mock_race.name = "テストレース"
    mock_race.date = None
    mock_race.venue = "中山"
    mock_race.race_number = 1
    mock_race.course_type = "芝"
    mock_race.distance = 2000
    mock_race.weather = "晴"
    mock_race.track_condition = "良"
    mock_race.grade = None
    mock_race.entries = []
    mock_detail_instance.get_race.return_value = mock_race
    mock_detail.return_value = mock_detail_instance

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        result = runner.invoke(scrape, [
            "--year", "2024",
            "--month", "1",
            "--db", str(db_path),
        ])

        assert result.exit_code == 0
        mock_list_instance.get_race_ids_for_month.assert_called_once_with(2024, 1)
```

**Step 2: テストを実行して失敗を確認**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: CLIを実装**

`keiba/cli.py`:
```python
"""CLIコマンド"""

from datetime import date
from pathlib import Path
from typing import Optional

import click

from keiba.db import get_engine, get_session, init_db
from keiba.models import Horse, Jockey, Trainer, Race, RaceResult
from keiba.scrapers import RaceListScraper, RaceDetailScraper


@click.group()
def main():
    """競馬データ収集CLIツール"""
    pass


@main.command()
@click.option("--year", type=int, required=True, help="収集する年")
@click.option("--month", type=int, default=None, help="収集する月（省略時は年全体）")
@click.option("--db", type=click.Path(), default=None, help="データベースパス")
@click.option("--delay", type=float, default=1.0, help="リクエスト間隔（秒）")
def scrape(year: int, month: Optional[int], db: Optional[str], delay: float):
    """レースデータを収集"""
    db_path = Path(db) if db else None
    engine = get_engine(db_path)
    init_db(engine)

    list_scraper = RaceListScraper(request_delay=delay)
    detail_scraper = RaceDetailScraper(request_delay=delay)

    # レースID一覧を取得
    if month:
        click.echo(f"{year}年{month}月のレース一覧を取得中...")
        race_ids = list_scraper.get_race_ids_for_month(year, month)
    else:
        click.echo(f"{year}年のレース一覧を取得中...")
        race_ids = list_scraper.get_race_ids_for_year(year)

    click.echo(f"{len(race_ids)}件のレースを発見")

    # 各レースの詳細を取得
    with get_session(engine) as session:
        for i, race_id in enumerate(race_ids, 1):
            # 既存チェック
            existing = session.query(Race).filter_by(netkeiba_id=race_id).first()
            if existing:
                click.echo(f"[{i}/{len(race_ids)}] {race_id}: スキップ（取得済み）")
                continue

            try:
                click.echo(f"[{i}/{len(race_ids)}] {race_id}: 取得中...")
                race_data = detail_scraper.get_race(race_id)

                # レースを保存
                race = Race(
                    netkeiba_id=race_data.netkeiba_id,
                    name=race_data.name,
                    date=race_data.date or date.today(),
                    venue=race_data.venue,
                    race_number=race_data.race_number,
                    course_type=race_data.course_type,
                    distance=race_data.distance,
                    weather=race_data.weather,
                    track_condition=race_data.track_condition,
                    grade=race_data.grade,
                )
                session.add(race)
                session.flush()

                # 出走馬・結果を保存
                for entry in race_data.entries or []:
                    # 馬を取得または作成
                    horse = session.query(Horse).filter_by(
                        netkeiba_id=entry.horse_id
                    ).first()
                    if not horse:
                        horse = Horse(
                            netkeiba_id=entry.horse_id,
                            name=entry.horse_name,
                        )
                        session.add(horse)
                        session.flush()

                    # 騎手を取得または作成
                    jockey = None
                    if entry.jockey_id:
                        jockey = session.query(Jockey).filter_by(
                            netkeiba_id=entry.jockey_id
                        ).first()
                        if not jockey:
                            jockey = Jockey(
                                netkeiba_id=entry.jockey_id,
                                name=entry.jockey_name or "",
                            )
                            session.add(jockey)
                            session.flush()

                    # 調教師を取得または作成
                    trainer = None
                    if entry.trainer_id:
                        trainer = session.query(Trainer).filter_by(
                            netkeiba_id=entry.trainer_id
                        ).first()
                        if not trainer:
                            trainer = Trainer(
                                netkeiba_id=entry.trainer_id,
                                name=entry.trainer_name or "",
                            )
                            session.add(trainer)
                            session.flush()

                    # レース結果を保存
                    result = RaceResult(
                        race_id=race.id,
                        horse_id=horse.id,
                        jockey_id=jockey.id if jockey else None,
                        trainer_id=trainer.id if trainer else None,
                        post_position=entry.post_position,
                        horse_number=entry.horse_number,
                        finish_position=entry.finish_position,
                        finish_time=entry.finish_time,
                        weight=entry.weight,
                        weight_change=entry.weight_change,
                        odds=entry.odds,
                        popularity=entry.popularity,
                    )
                    session.add(result)

                session.commit()
                click.echo(f"  -> {race_data.name} を保存しました")

            except Exception as e:
                click.echo(f"  -> エラー: {e}", err=True)
                session.rollback()

    click.echo("完了")


if __name__ == "__main__":
    main()
```

**Step 4: テストを実行して成功を確認**

Run: `pytest tests/test_cli.py -v`
Expected: PASS

**Step 5: コミット**

```bash
git add keiba/cli.py tests/test_cli.py
git commit -m "feat: add CLI scrape command"
```

---

## Task 9: 統合テストとドキュメント

**Files:**
- Create: `tests/test_integration.py`

**Step 1: 統合テストを作成**

`tests/test_integration.py`:
```python
"""統合テスト"""

import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

import pytest
from click.testing import CliRunner
from sqlalchemy import select

from keiba.cli import scrape
from keiba.db import get_engine, get_session
from keiba.models import Race, Horse, RaceResult


@pytest.fixture
def mock_scrapers():
    """スクレイパーをモック"""
    with patch("keiba.cli.RaceListScraper") as mock_list, \
         patch("keiba.cli.RaceDetailScraper") as mock_detail:

        # レース一覧
        mock_list_instance = Mock()
        mock_list_instance.get_race_ids_for_month.return_value = [
            "202401010101",
            "202401010102",
        ]
        mock_list.return_value = mock_list_instance

        # レース詳細
        def get_race(race_id):
            race = Mock()
            race.netkeiba_id = race_id
            race.name = f"テストレース{race_id[-2:]}"
            race.date = None
            race.venue = "中山"
            race.race_number = int(race_id[-2:])
            race.course_type = "芝"
            race.distance = 2000
            race.weather = "晴"
            race.track_condition = "良"
            race.grade = None

            entry = Mock()
            entry.horse_id = f"horse{race_id[-2:]}"
            entry.horse_name = f"テスト馬{race_id[-2:]}"
            entry.jockey_id = "jockey01"
            entry.jockey_name = "テスト騎手"
            entry.trainer_id = "trainer01"
            entry.trainer_name = "テスト調教師"
            entry.post_position = 1
            entry.horse_number = 1
            entry.finish_position = 1
            entry.finish_time = "2:00.0"
            entry.weight = 480
            entry.weight_change = 0
            entry.odds = 2.5
            entry.popularity = 1

            race.entries = [entry]
            return race

        mock_detail_instance = Mock()
        mock_detail_instance.get_race.side_effect = get_race
        mock_detail.return_value = mock_detail_instance

        yield


def test_full_scrape_workflow(mock_scrapers):
    """スクレイプの完全なワークフロー"""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # スクレイプ実行
        result = runner.invoke(scrape, [
            "--year", "2024",
            "--month", "1",
            "--db", str(db_path),
        ])

        assert result.exit_code == 0
        assert "2件のレースを発見" in result.output
        assert "テストレース01" in result.output
        assert "テストレース02" in result.output

        # DBを確認
        engine = get_engine(db_path)
        with get_session(engine) as session:
            races = session.execute(select(Race)).scalars().all()
            assert len(races) == 2

            horses = session.execute(select(Horse)).scalars().all()
            assert len(horses) == 2

            results = session.execute(select(RaceResult)).scalars().all()
            assert len(results) == 2


def test_skip_existing_races(mock_scrapers):
    """既存レースをスキップする"""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # 1回目
        result1 = runner.invoke(scrape, [
            "--year", "2024",
            "--month", "1",
            "--db", str(db_path),
        ])
        assert result1.exit_code == 0

        # 2回目（スキップされるはず）
        result2 = runner.invoke(scrape, [
            "--year", "2024",
            "--month", "1",
            "--db", str(db_path),
        ])
        assert result2.exit_code == 0
        assert "スキップ" in result2.output
```

**Step 2: テストを実行して成功を確認**

Run: `pytest tests/test_integration.py -v`
Expected: PASS

**Step 3: 全テストを実行**

Run: `pytest tests/ -v`
Expected: ALL PASS

**Step 4: コミット**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests"
```

---

## 完了チェックリスト

- [ ] Task 1: プロジェクトセットアップ
- [ ] Task 2: データベース接続モジュール
- [ ] Task 3: 基本データモデル（Horse, Jockey, Trainer）
- [ ] Task 4: 追加データモデル（Owner, Breeder, Race, RaceResult）
- [ ] Task 5: ベーススクレイパー
- [ ] Task 6: レース一覧スクレイパー
- [ ] Task 7: レース詳細スクレイパー
- [ ] Task 8: CLIコマンド
- [ ] Task 9: 統合テストとドキュメント
