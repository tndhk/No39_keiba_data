"""Tests for _update_horse function in scrape command."""

from unittest.mock import MagicMock

import pytest

from keiba.cli.commands.scrape import _update_horse
from keiba.models import Horse


class TestUpdateHorseReturnsFieldCount:
    """_update_horse が更新フィールド数を返すテスト"""

    def test_update_horse_returns_updated_field_count(self):
        """_update_horse()は更新したフィールド数をintで返す"""
        mock_session = MagicMock()
        horse = Horse(
            id="test123",
            name="旧名前",
            sex="不明",
            birth_year=0,
            sire=None,
        )
        horse_data = {
            "name": "新名前",
            "sire": "新父馬",
            "dam": "新母馬",
        }

        # _update_horseの返り値がintであることを確認
        result = _update_horse(mock_session, horse, horse_data)

        assert isinstance(result, int)
        # name, sire, dam の3フィールドが更新される
        assert result == 3

    def test_update_horse_empty_data_returns_zero(self):
        """_update_horse()は空データの場合に0を返す"""
        mock_session = MagicMock()
        horse = Horse(
            id="test123",
            name="既存名前",
            sex="牡",
            birth_year=2020,
        )
        horse_data = {}  # 空データ

        result = _update_horse(mock_session, horse, horse_data)

        assert isinstance(result, int)
        assert result == 0

    def test_update_horse_pedigree_fields(self):
        """_update_horse()はsire, dam, dam_sireを正しくセットする"""
        mock_session = MagicMock()
        horse = Horse(
            id="test123",
            name="テスト馬",
            sex="牡",
            birth_year=2020,
            sire=None,
            dam=None,
            dam_sire=None,
        )
        horse_data = {
            "sire": "ハーツクライ",
            "dam": "ダストアンドダイヤモンズ",
            "dam_sire": "Vindication",
        }

        result = _update_horse(mock_session, horse, horse_data)

        # 3つの血統フィールドが正しく設定される
        assert horse.sire == "ハーツクライ"
        assert horse.dam == "ダストアンドダイヤモンズ"
        assert horse.dam_sire == "Vindication"
        # 3フィールド更新
        assert result == 3
