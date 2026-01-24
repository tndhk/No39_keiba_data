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

        # URL数の確認（JRA5 + NAR2）
        assert len(urls) == 7

        # レースIDの抽出
        race_ids = [extract_race_id_from_url(url) for url in urls]
        expected_ids = [
            "202401010101",
            "202401010102",
            "202401010103",
            "202401010201",
            "202401010202",
            "202445010101",
            "202445010102",
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

        def fetch_race_urls_side_effect(year, month, day, jra_only=False):
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
        # Step 1: レースリストをパース（JRAのみ）
        list_scraper = RaceListScraper(delay=0)
        list_soup = list_scraper.get_soup(race_list_html)
        race_urls = list_scraper.parse(list_soup, jra_only=True)

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


# =============================================================================
# Test: Shutuba to Prediction Integration (Phase 5)
# =============================================================================


class TestShutubaToPredicitionIntegration:
    """出馬表から予測までの統合テスト"""

    @pytest.fixture
    def shutuba_html(self):
        """テスト用HTMLフィクスチャを読み込む"""
        fixture_path = Path(__file__).parent / "fixtures" / "shutuba.html"
        return fixture_path.read_text(encoding="utf-8")

    @pytest.fixture
    def shutuba_scraper(self):
        """ShutubaScraper インスタンスを返す"""
        from keiba.scrapers.shutuba import ShutubaScraper

        return ShutubaScraper(delay=0)

    @pytest.fixture
    def mock_repository(self):
        """モック過去成績リポジトリを返す"""
        from unittest.mock import Mock
        from keiba.services.prediction_service import RaceResultRepository

        mock_repo = Mock(spec=RaceResultRepository)
        mock_repo.get_past_results.return_value = []
        return mock_repo

    def test_shutuba_to_prediction_full_flow(
        self, shutuba_scraper, shutuba_html, mock_repository
    ):
        """出馬表スクレイピング -> 予測サービス -> 結果出力の全フロー"""
        from keiba.services.prediction_service import PredictionService

        # Step 1: テスト用HTMLからパース（_parse_entriesを使用）
        soup = shutuba_scraper.get_soup(shutuba_html)
        entries = shutuba_scraper._parse_entries(soup)
        race_info = shutuba_scraper._parse_race_info(soup)

        # 出走馬が5頭抽出されること
        assert len(entries) == 5

        # ShutubaDataを構築
        from keiba.models.entry import ShutubaData

        shutuba_data = ShutubaData(
            race_id="202601080211",
            race_name=race_info.get("race_name", ""),
            race_number=race_info.get("race_number", 0),
            course=race_info.get("course", ""),
            distance=race_info.get("distance", 0),
            surface=race_info.get("surface", ""),
            date=race_info.get("date", ""),
            entries=tuple(entries),
        )

        # Step 2: 予測を実行
        service = PredictionService(repository=mock_repository)
        results = service.predict_from_shutuba(shutuba_data)

        # Step 3: 予測結果が全出走馬分返ること
        assert len(results) == 5

        # Step 4: 各予測結果に必要なフィールドが含まれること
        for result in results:
            assert hasattr(result, "horse_number")
            assert hasattr(result, "horse_name")
            assert hasattr(result, "horse_id")
            assert hasattr(result, "ml_probability")
            assert hasattr(result, "factor_scores")
            assert hasattr(result, "total_score")
            assert hasattr(result, "rank")

            # horse_numberは1-5の範囲
            assert 1 <= result.horse_number <= 5

            # horse_idは馬データから抽出されたもの
            assert result.horse_id.startswith("2023104")

            # horse_nameは日本語を含む
            assert "テストホース" in result.horse_name

            # rankは1-5の範囲
            assert 1 <= result.rank <= 5

    def test_prediction_with_db_data(self, tmp_db, shutuba_scraper, shutuba_html):
        """DBに既存の過去成績がある場合の予測"""
        from keiba.services.prediction_service import (
            PredictionService,
            RaceResultRepository,
        )
        from keiba.models.entry import ShutubaData
        from datetime import date as dt_date

        # Step 1: インメモリDBにテスト用の馬と過去成績データを挿入
        with get_session(tmp_db) as session:
            # 馬データ
            horse1 = Horse(
                id="2023104001",
                name="テストホース1",
                sex="牡",
                birth_year=2023,
            )
            horse2 = Horse(
                id="2023104002",
                name="テストホース2",
                sex="牝",
                birth_year=2023,
            )
            session.add_all([horse1, horse2])

            # 騎手データ
            jockey = Jockey(id="01167", name="武豊")
            session.add(jockey)

            # 調教師データ
            trainer = Trainer(id="01088", name="友道康夫")
            session.add(trainer)

            # 過去のレースデータ
            past_race = Race(
                id="202512010101",
                name="過去レース",
                date=dt_date(2025, 12, 1),
                course="中山",
                race_number=1,
                distance=2000,
                surface="芝",
                weather="晴",
                track_condition="良",
            )
            session.add(past_race)

            # 過去成績データ
            past_result1 = RaceResult(
                race_id="202512010101",
                horse_id="2023104001",
                jockey_id="01167",
                trainer_id="01088",
                finish_position=1,
                bracket_number=1,
                horse_number=1,
                odds=3.5,
                popularity=2,
                weight=480,
                weight_diff=0,
                time="2:01.0",
                margin="",
            )
            past_result2 = RaceResult(
                race_id="202512010101",
                horse_id="2023104002",
                jockey_id="01167",
                trainer_id="01088",
                finish_position=3,
                bracket_number=2,
                horse_number=2,
                odds=5.0,
                popularity=3,
                weight=450,
                weight_diff=-2,
                time="2:01.5",
                margin="3",
            )
            session.add_all([past_result1, past_result2])

        # Step 2: DBベースのリポジトリを作成
        class DBRepository:
            """テスト用DBリポジトリ"""

            def __init__(self, engine):
                self._engine = engine

            def get_past_results(
                self, horse_id: str, before_date: str, limit: int = 20
            ) -> list:
                with get_session(self._engine) as session:
                    results = (
                        session.execute(
                            select(RaceResult).where(RaceResult.horse_id == horse_id)
                        )
                        .scalars()
                        .all()
                    )
                    # 辞書形式に変換
                    return [
                        {
                            "horse_id": r.horse_id,
                            "finish_position": r.finish_position,
                            "total_runners": 10,
                            "race_date": "2025-12-01",
                            "course": "中山",
                            "distance": 2000,
                            "surface": "芝",
                            "time_index": 100.0,
                            "last_3f": 34.0,
                            "odds": r.odds,
                            "popularity": r.popularity,
                        }
                        for r in results[:limit]
                    ]

        repository = DBRepository(tmp_db)

        # Step 3: 出馬表データを作成
        soup = shutuba_scraper.get_soup(shutuba_html)
        entries = shutuba_scraper._parse_entries(soup)
        race_info = shutuba_scraper._parse_race_info(soup)

        shutuba_data = ShutubaData(
            race_id="202601080211",
            race_name=race_info.get("race_name", ""),
            race_number=race_info.get("race_number", 0),
            course=race_info.get("course", ""),
            distance=race_info.get("distance", 0),
            surface=race_info.get("surface", ""),
            date="2026年1月8日",
            entries=tuple(entries),
        )

        # Step 4: 予測を実行
        service = PredictionService(repository=repository)
        results = service.predict_from_shutuba(shutuba_data)

        # Step 5: 予測結果を検証
        assert len(results) == 5

        # DBに過去成績がある馬を取得
        horse1_result = next(
            (r for r in results if r.horse_id == "2023104001"), None
        )
        horse2_result = next(
            (r for r in results if r.horse_id == "2023104002"), None
        )

        # 過去成績がある馬は因子スコアが計算されている
        assert horse1_result is not None
        assert horse1_result.factor_scores is not None
        # 全ての因子スコアが含まれていること
        expected_factors = [
            "past_results",
            "course_fit",
            "time_index",
            "last_3f",
            "popularity",
            "pedigree",
            "running_style",
        ]
        for factor in expected_factors:
            assert factor in horse1_result.factor_scores

        # 過去成績がある馬はスコアが計算されていること
        # (少なくともNone以外の値を持つ因子があること)
        has_non_none_score = any(
            score is not None for score in horse1_result.factor_scores.values()
        )
        assert has_non_none_score, "過去成績がある馬は因子スコアが計算されているべき"

    def test_prediction_without_db_data(self, tmp_db, shutuba_scraper, shutuba_html):
        """DBに過去成績がない場合（新馬戦相当）の予測"""
        from keiba.services.prediction_service import PredictionService
        from keiba.models.entry import ShutubaData

        # Step 1: 空のDBでリポジトリを作成
        class EmptyDBRepository:
            """空のDBリポジトリ"""

            def get_past_results(
                self, horse_id: str, before_date: str, limit: int = 20
            ) -> list:
                return []

        repository = EmptyDBRepository()

        # Step 2: 出馬表データを作成
        soup = shutuba_scraper.get_soup(shutuba_html)
        entries = shutuba_scraper._parse_entries(soup)
        race_info = shutuba_scraper._parse_race_info(soup)

        shutuba_data = ShutubaData(
            race_id="202601080211",
            race_name=race_info.get("race_name", ""),
            race_number=race_info.get("race_number", 0),
            course=race_info.get("course", ""),
            distance=race_info.get("distance", 0),
            surface=race_info.get("surface", ""),
            date="2026年1月8日",
            entries=tuple(entries),
        )

        # Step 3: 予測を実行
        service = PredictionService(repository=repository)
        results = service.predict_from_shutuba(shutuba_data)

        # Step 4: 予測結果を検証
        assert len(results) == 5

        for result in results:
            # 因子スコアがNoneでも動作すること
            assert result.factor_scores is not None

            # 全ての因子スコアがNoneであること（新馬なので過去成績なし）
            for factor_name, score in result.factor_scores.items():
                assert score is None, (
                    f"Factor '{factor_name}' should be None for new horse, "
                    f"got {score}"
                )

            # ML確率が0.0であること
            assert result.ml_probability == 0.0

            # total_scoreもNoneであること
            assert result.total_score is None

            # ランクは付与されること
            assert 1 <= result.rank <= 5
