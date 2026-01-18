"""統合テスト

各コンポーネント（モデル、DB、スクレイパー、CLI）が
正しく連携して動作することを検証する。
"""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from sqlalchemy import select

from keiba.cli import main, _save_race_data, extract_race_id_from_url, parse_race_date
from keiba.db import get_engine, get_session, init_db
from keiba.models import (
    Base,
    Breeder,
    Horse,
    Jockey,
    Owner,
    Race,
    RaceResult,
    Trainer,
)
from keiba.scrapers import RaceDetailScraper, RaceListScraper


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def tmp_db(tmp_path):
    """一時的なSQLiteデータベースを作成"""
    db_path = tmp_path / "test_integration.db"
    engine = get_engine(str(db_path))
    init_db(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def race_list_html():
    """テスト用HTMLフィクスチャを読み込む"""
    fixture_path = Path(__file__).parent / "fixtures" / "race_list.html"
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def race_detail_html():
    """テスト用HTMLフィクスチャを読み込む"""
    fixture_path = Path(__file__).parent / "fixtures" / "race_detail.html"
    return fixture_path.read_text(encoding="utf-8")


# =============================================================================
# Test: Database + Models Integration
# =============================================================================


class TestDatabaseModelIntegration:
    """データベースとモデルの統合テスト"""

    def test_save_and_retrieve_all_models(self, tmp_db):
        """全モデルをDBに保存して取得できる"""
        # データ作成
        with get_session(tmp_db) as session:
            # Horse
            horse = Horse(
                id="2019104251",
                name="ドウデュース",
                sex="牡",
                birth_year=2019,
            )
            session.add(horse)

            # Jockey
            jockey = Jockey(id="01167", name="武豊")
            session.add(jockey)

            # Trainer
            trainer = Trainer(id="01088", name="友道康夫")
            session.add(trainer)

            # Owner
            owner = Owner(id="000001", name="テスト馬主")
            session.add(owner)

            # Breeder
            breeder = Breeder(id="000002", name="テスト生産者")
            session.add(breeder)

            # Race
            race = Race(
                id="202412220511",
                name="有馬記念",
                date=date(2024, 12, 22),
                course="中山",
                race_number=11,
                distance=2500,
                surface="芝",
                weather="晴",
                track_condition="良",
            )
            session.add(race)

            # RaceResult
            race_result = RaceResult(
                race_id="202412220511",
                horse_id="2019104251",
                jockey_id="01167",
                trainer_id="01088",
                finish_position=1,
                bracket_number=3,
                horse_number=5,
                odds=3.5,
                popularity=2,
                weight=512,
                weight_diff=4,
                time="2:31.2",
                margin="",
            )
            session.add(race_result)

        # 検証
        with get_session(tmp_db) as session:
            # Horse
            retrieved_horse = session.execute(
                select(Horse).where(Horse.id == "2019104251")
            ).scalar_one()
            assert retrieved_horse.name == "ドウデュース"

            # Jockey
            retrieved_jockey = session.execute(
                select(Jockey).where(Jockey.id == "01167")
            ).scalar_one()
            assert retrieved_jockey.name == "武豊"

            # Trainer
            retrieved_trainer = session.execute(
                select(Trainer).where(Trainer.id == "01088")
            ).scalar_one()
            assert retrieved_trainer.name == "友道康夫"

            # Owner
            retrieved_owner = session.execute(
                select(Owner).where(Owner.id == "000001")
            ).scalar_one()
            assert retrieved_owner.name == "テスト馬主"

            # Breeder
            retrieved_breeder = session.execute(
                select(Breeder).where(Breeder.id == "000002")
            ).scalar_one()
            assert retrieved_breeder.name == "テスト生産者"

            # Race
            retrieved_race = session.execute(
                select(Race).where(Race.id == "202412220511")
            ).scalar_one()
            assert retrieved_race.name == "有馬記念"

            # RaceResult
            retrieved_result = session.execute(
                select(RaceResult).where(RaceResult.race_id == "202412220511")
            ).scalar_one()
            assert retrieved_result.finish_position == 1

    def test_relationship_navigation(self, tmp_db):
        """リレーションシップを通じた関連データへのアクセス"""
        # データ作成
        with get_session(tmp_db) as session:
            horse = Horse(
                id="2019104251", name="ドウデュース", sex="牡", birth_year=2019
            )
            jockey = Jockey(id="01167", name="武豊")
            trainer = Trainer(id="01088", name="友道康夫")
            race = Race(
                id="202412220511",
                name="有馬記念",
                date=date(2024, 12, 22),
                course="中山",
                race_number=11,
                distance=2500,
                surface="芝",
                weather="晴",
                track_condition="良",
            )
            race_result = RaceResult(
                race_id="202412220511",
                horse_id="2019104251",
                jockey_id="01167",
                trainer_id="01088",
                finish_position=1,
                bracket_number=3,
                horse_number=5,
                odds=3.5,
                popularity=2,
                weight=512,
                weight_diff=4,
                time="2:31.2",
                margin="",
            )
            session.add_all([horse, jockey, trainer, race, race_result])

        # 検証: RaceResult経由でHorse, Jockey, Trainer, Raceにアクセス
        with get_session(tmp_db) as session:
            result = session.execute(
                select(RaceResult).where(RaceResult.race_id == "202412220511")
            ).scalar_one()

            assert result.horse.name == "ドウデュース"
            assert result.jockey.name == "武豊"
            assert result.trainer.name == "友道康夫"
            assert result.race.name == "有馬記念"

    def test_multiple_race_results_for_one_race(self, tmp_db):
        """1レースに複数の結果を関連付けられる"""
        with get_session(tmp_db) as session:
            # 共通データ
            race = Race(
                id="202412220511",
                name="有馬記念",
                date=date(2024, 12, 22),
                course="中山",
                race_number=11,
                distance=2500,
                surface="芝",
                weather="晴",
                track_condition="良",
            )
            session.add(race)

            # 複数の馬・騎手・調教師
            horses = [
                Horse(id="horse001", name="馬1", sex="牡", birth_year=2019),
                Horse(id="horse002", name="馬2", sex="牝", birth_year=2020),
                Horse(id="horse003", name="馬3", sex="牡", birth_year=2018),
            ]
            jockeys = [
                Jockey(id="jockey001", name="騎手1"),
                Jockey(id="jockey002", name="騎手2"),
                Jockey(id="jockey003", name="騎手3"),
            ]
            trainers = [
                Trainer(id="trainer001", name="調教師1"),
                Trainer(id="trainer002", name="調教師2"),
                Trainer(id="trainer003", name="調教師3"),
            ]
            session.add_all(horses + jockeys + trainers)

            # 複数のレース結果
            for i, (h, j, t) in enumerate(zip(horses, jockeys, trainers), 1):
                result = RaceResult(
                    race_id="202412220511",
                    horse_id=h.id,
                    jockey_id=j.id,
                    trainer_id=t.id,
                    finish_position=i,
                    bracket_number=i,
                    horse_number=i,
                    odds=float(i) * 2.0,
                    popularity=i,
                    weight=480 + i * 10,
                    weight_diff=i,
                    time=f"2:31.{i}",
                    margin="" if i == 1 else "1",
                )
                session.add(result)

        # 検証
        with get_session(tmp_db) as session:
            results = session.execute(
                select(RaceResult).where(RaceResult.race_id == "202412220511")
            ).scalars().all()
            assert len(results) == 3

            # 着順で確認
            positions = sorted([r.finish_position for r in results])
            assert positions == [1, 2, 3]


# =============================================================================
# Test: Scraper + Database Integration
# =============================================================================


class TestScraperDatabaseIntegration:
    """スクレイパーとデータベースの統合テスト"""

    def test_parse_race_list_and_extract_ids(self, race_list_html):
        """レースリストHTMLからレースIDを抽出し、URLを生成できる"""
        scraper = RaceListScraper(delay=0)
        soup = scraper.get_soup(race_list_html)
        urls = scraper.parse(soup)

        # URL数の確認
        assert len(urls) == 5

        # レースIDの抽出
        race_ids = [extract_race_id_from_url(url) for url in urls]
        expected_ids = [
            "202401010101",
            "202401010102",
            "202401010103",
            "202401010201",
            "202401010202",
        ]
        assert race_ids == expected_ids

    def test_parse_race_detail_and_save_to_db(self, tmp_db, race_detail_html):
        """レース詳細HTMLをパースしてDBに保存できる"""
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(race_detail_html)
        race_data = scraper.parse(soup, race_id="202401010101")

        # _save_race_dataを使用して保存
        with get_session(tmp_db) as session:
            _save_race_data(session, race_data)

        # 検証: レースデータ
        with get_session(tmp_db) as session:
            race = session.get(Race, "202401010101")
            assert race is not None
            assert race.name == "有馬記念(G1)"
            assert race.course == "中山"
            assert race.distance == 1600
            assert race.surface == "芝"
            assert race.weather == "晴"
            assert race.track_condition == "良"

        # 検証: レース結果データ
        with get_session(tmp_db) as session:
            results = session.execute(
                select(RaceResult).where(RaceResult.race_id == "202401010101")
            ).scalars().all()
            assert len(results) == 5

            # 1着馬の確認
            first_place = next(r for r in results if r.finish_position == 1)
            assert first_place.horse_id == "2019104251"
            assert first_place.jockey_id == "01167"
            assert first_place.odds == 3.5

        # 検証: 馬データ
        with get_session(tmp_db) as session:
            horse = session.get(Horse, "2019104251")
            assert horse is not None
            assert horse.name == "ドウデュース"

        # 検証: 騎手データ
        with get_session(tmp_db) as session:
            jockey = session.get(Jockey, "01167")
            assert jockey is not None
            assert jockey.name == "武豊"

        # 検証: 調教師データ
        with get_session(tmp_db) as session:
            trainer = session.get(Trainer, "01088")
            assert trainer is not None
            assert trainer.name == "友道康夫"

    def test_parse_race_detail_handles_disqualified_horse(
        self, tmp_db, race_detail_html
    ):
        """競走中止馬を含むレースを正しく保存できる"""
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(race_detail_html)
        race_data = scraper.parse(soup, race_id="202401010101")

        with get_session(tmp_db) as session:
            _save_race_data(session, race_data)

        # 中止馬のデータ確認
        with get_session(tmp_db) as session:
            dq_result = session.execute(
                select(RaceResult).where(RaceResult.horse_id == "2019107890")
            ).scalar_one()
            # finish_positionがNoneの場合、_save_race_dataは0として保存
            assert dq_result.finish_position == 0
            assert dq_result.time == ""


# =============================================================================
# Test: CLI + All Components Integration
# =============================================================================


class TestCLIIntegration:
    """CLIと全コンポーネントの統合テスト"""

    @patch("keiba.cli.RaceDetailScraper")
    @patch("keiba.cli.RaceListScraper")
    def test_scrape_command_full_flow(
        self,
        mock_race_list_scraper_class,
        mock_race_detail_scraper_class,
        tmp_path,
        race_list_html,
        race_detail_html,
    ):
        """scrapeコマンドの完全な処理フロー"""
        db_path = tmp_path / "integration_test.db"

        # RaceListScraperのモック設定
        mock_list_scraper = MagicMock()

        def fetch_race_urls_side_effect(year, month, day):
            # 1日目だけレースを返す
            if day == 1:
                return ["https://race.netkeiba.com/race/202401010101.html"]
            return []

        mock_list_scraper.fetch_race_urls.side_effect = fetch_race_urls_side_effect
        mock_race_list_scraper_class.return_value = mock_list_scraper

        # RaceDetailScraperのモック設定
        mock_detail_scraper = MagicMock()
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(race_detail_html)
        mock_detail_scraper.fetch_race_detail.return_value = scraper.parse(
            soup, race_id="202401010101"
        )
        mock_race_detail_scraper_class.return_value = mock_detail_scraper

        # CLIコマンドを実行
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["scrape", "--year", "2024", "--month", "1", "--db", str(db_path)],
        )

        # コマンドが正常終了したことを確認
        assert result.exit_code == 0
        assert "完了" in result.output
        assert "2024年1月" in result.output

        # DBの内容を確認
        engine = get_engine(str(db_path))
        with get_session(engine) as session:
            # レースが保存されているか
            race = session.get(Race, "202401010101")
            assert race is not None
            assert race.name == "有馬記念(G1)"

            # レース結果が保存されているか
            results = session.execute(
                select(RaceResult).where(RaceResult.race_id == "202401010101")
            ).scalars().all()
            assert len(results) == 5

            # 馬が保存されているか
            horse = session.get(Horse, "2019104251")
            assert horse is not None
            assert horse.name == "ドウデュース"

        engine.dispose()

    @patch("keiba.cli.RaceDetailScraper")
    @patch("keiba.cli.RaceListScraper")
    def test_scrape_command_skips_existing_races(
        self,
        mock_race_list_scraper_class,
        mock_race_detail_scraper_class,
        tmp_path,
        race_detail_html,
    ):
        """既存レースをスキップする"""
        db_path = tmp_path / "integration_test.db"

        # 事前にレースを保存
        engine = get_engine(str(db_path))
        init_db(engine)
        with get_session(engine) as session:
            race = Race(
                id="202401010101",
                name="既存レース",
                date=date(2024, 1, 1),
                course="中山",
                race_number=1,
                distance=1600,
                surface="芝",
                weather="晴",
                track_condition="良",
            )
            session.add(race)
        engine.dispose()

        # RaceListScraperのモック
        mock_list_scraper = MagicMock()
        mock_list_scraper.fetch_race_urls.return_value = [
            "https://race.netkeiba.com/race/202401010101.html"
        ]
        mock_race_list_scraper_class.return_value = mock_list_scraper

        # RaceDetailScraperのモック（呼ばれないはず）
        mock_detail_scraper = MagicMock()
        mock_race_detail_scraper_class.return_value = mock_detail_scraper

        # CLIコマンドを実行
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["scrape", "--year", "2024", "--month", "1", "--db", str(db_path)],
        )

        # コマンドが正常終了
        assert result.exit_code == 0
        assert "スキップ" in result.output

        # レース詳細取得が呼ばれていないことを確認
        mock_detail_scraper.fetch_race_detail.assert_not_called()

    def test_scrape_command_missing_options(self):
        """必須オプションが不足している場合はエラー"""
        runner = CliRunner()

        # --yearが不足
        result = runner.invoke(main, ["scrape", "--month", "1", "--db", "test.db"])
        assert result.exit_code != 0

        # --monthが不足
        result = runner.invoke(main, ["scrape", "--year", "2024", "--db", "test.db"])
        assert result.exit_code != 0

        # --dbが不足
        result = runner.invoke(main, ["scrape", "--year", "2024", "--month", "1"])
        assert result.exit_code != 0


# =============================================================================
# Test: Helper Functions
# =============================================================================


class TestHelperFunctions:
    """ヘルパー関数のテスト"""

    def test_extract_race_id_from_url_various_formats(self):
        """様々な形式のURLからレースIDを抽出"""
        test_cases = [
            (
                "https://race.netkeiba.com/race/202401010101.html",
                "202401010101",
            ),
            (
                "https://race.netkeiba.com/race/202412251211.html",
                "202412251211",
            ),
            (
                "https://race.netkeiba.com/race/202506030512.html",
                "202506030512",
            ),
        ]
        for url, expected_id in test_cases:
            assert extract_race_id_from_url(url) == expected_id

    def test_extract_race_id_from_url_invalid(self):
        """無効なURLではValueError"""
        with pytest.raises(ValueError):
            extract_race_id_from_url("https://example.com/invalid")

    def test_parse_race_date_various_formats(self):
        """様々な形式の日付文字列をパース"""
        test_cases = [
            ("2024年1月1日", date(2024, 1, 1)),
            ("2024年12月25日", date(2024, 12, 25)),
            ("2025年6月15日", date(2025, 6, 15)),
        ]
        for date_str, expected_date in test_cases:
            assert parse_race_date(date_str) == expected_date

    def test_parse_race_date_invalid(self):
        """無効な日付文字列ではValueError"""
        with pytest.raises(ValueError):
            parse_race_date("invalid date")


# =============================================================================
# Test: End-to-End Data Flow
# =============================================================================


class TestEndToEndDataFlow:
    """エンドツーエンドのデータフローテスト"""

    def test_complete_data_flow(self, tmp_db, race_list_html, race_detail_html):
        """完全なデータフロー: スクレイピング -> パース -> 保存 -> 取得"""
        # Step 1: レースリストをパース
        list_scraper = RaceListScraper(delay=0)
        list_soup = list_scraper.get_soup(race_list_html)
        race_urls = list_scraper.parse(list_soup)

        assert len(race_urls) == 5

        # Step 2: 最初のレースの詳細をパース
        detail_scraper = RaceDetailScraper(delay=0)
        detail_soup = detail_scraper.get_soup(race_detail_html)
        race_id = extract_race_id_from_url(race_urls[0])
        race_data = detail_scraper.parse(detail_soup, race_id=race_id)

        assert race_data["race"]["name"] == "有馬記念(G1)"
        assert len(race_data["results"]) == 5

        # Step 3: データをDBに保存
        with get_session(tmp_db) as session:
            _save_race_data(session, race_data)

        # Step 4: 保存したデータを取得して検証
        with get_session(tmp_db) as session:
            # レースを取得
            race = session.get(Race, race_id)
            assert race.name == "有馬記念(G1)"
            assert race.course == "中山"

            # レース結果を取得してリレーションシップを確認
            results = session.execute(
                select(RaceResult).where(RaceResult.race_id == race_id)
            ).scalars().all()

            # 1着馬のリレーションシップを確認
            first_place = next(r for r in results if r.finish_position == 1)
            assert first_place.horse.name == "ドウデュース"
            assert first_place.jockey.name == "武豊"
            assert first_place.trainer.name == "友道康夫"
            assert first_place.race.name == "有馬記念(G1)"

    def test_data_integrity_after_multiple_saves(self, tmp_db, race_detail_html):
        """複数回保存後のデータ整合性"""
        detail_scraper = RaceDetailScraper(delay=0)
        detail_soup = detail_scraper.get_soup(race_detail_html)

        # 同じデータを2回保存しようとする（2回目は既存データとして扱われるべき）
        race_data = detail_scraper.parse(detail_soup, race_id="race001")
        with get_session(tmp_db) as session:
            _save_race_data(session, race_data)

        # 2つ目のレースとして別のIDで保存
        race_data2 = detail_scraper.parse(detail_soup, race_id="race002")
        with get_session(tmp_db) as session:
            _save_race_data(session, race_data2)

        # 検証: 2つのレースが存在
        with get_session(tmp_db) as session:
            races = session.execute(select(Race)).scalars().all()
            assert len(races) == 2

            # 馬は重複しない（同じ馬が複数のレースに出走しても1レコード）
            horses = session.execute(select(Horse)).scalars().all()
            # 5頭のユニークな馬
            assert len(horses) == 5
