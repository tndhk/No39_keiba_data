"""Tests for keiba.models.entry module (Entry DTOs)."""

import pytest
from dataclasses import FrozenInstanceError


class TestRaceEntryImmutability:
    """test_race_entry_is_immutable: RaceEntryがイミュータブルであること"""

    def test_cannot_modify_horse_id(self):
        """horse_id フィールドは変更不可"""
        from keiba.models.entry import RaceEntry

        entry = RaceEntry(
            horse_id="123",
            horse_name="テスト馬",
            horse_number=1,
            bracket_number=1,
            jockey_id="j001",
            jockey_name="テスト騎手",
            impost=56.0,
            sex="牡",
            age=3,
        )

        with pytest.raises(FrozenInstanceError):
            entry.horse_id = "999"

    def test_cannot_modify_horse_name(self):
        """horse_name フィールドは変更不可"""
        from keiba.models.entry import RaceEntry

        entry = RaceEntry(
            horse_id="123",
            horse_name="テスト馬",
            horse_number=1,
            bracket_number=1,
            jockey_id="j001",
            jockey_name="テスト騎手",
            impost=56.0,
            sex="牡",
            age=3,
        )

        with pytest.raises(FrozenInstanceError):
            entry.horse_name = "変更馬"

    def test_cannot_modify_impost(self):
        """impost フィールドは変更不可"""
        from keiba.models.entry import RaceEntry

        entry = RaceEntry(
            horse_id="123",
            horse_name="テスト馬",
            horse_number=1,
            bracket_number=1,
            jockey_id="j001",
            jockey_name="テスト騎手",
            impost=56.0,
            sex="牡",
            age=3,
        )

        with pytest.raises(FrozenInstanceError):
            entry.impost = 58.0


class TestRaceEntryFields:
    """test_race_entry_fields: 必要なフィールドが全て存在すること"""

    def test_has_horse_id(self):
        """horse_id フィールドが存在"""
        from keiba.models.entry import RaceEntry

        entry = RaceEntry(
            horse_id="2023104001",
            horse_name="テスト馬",
            horse_number=1,
            bracket_number=1,
            jockey_id="01167",
            jockey_name="武豊",
            impost=56.0,
            sex="牡",
            age=3,
        )

        assert entry.horse_id == "2023104001"

    def test_has_horse_name(self):
        """horse_name フィールドが存在"""
        from keiba.models.entry import RaceEntry

        entry = RaceEntry(
            horse_id="2023104001",
            horse_name="テスト馬",
            horse_number=1,
            bracket_number=1,
            jockey_id="01167",
            jockey_name="武豊",
            impost=56.0,
            sex="牡",
            age=3,
        )

        assert entry.horse_name == "テスト馬"

    def test_has_horse_number(self):
        """horse_number フィールドが存在"""
        from keiba.models.entry import RaceEntry

        entry = RaceEntry(
            horse_id="2023104001",
            horse_name="テスト馬",
            horse_number=5,
            bracket_number=1,
            jockey_id="01167",
            jockey_name="武豊",
            impost=56.0,
            sex="牡",
            age=3,
        )

        assert entry.horse_number == 5

    def test_has_bracket_number(self):
        """bracket_number フィールドが存在"""
        from keiba.models.entry import RaceEntry

        entry = RaceEntry(
            horse_id="2023104001",
            horse_name="テスト馬",
            horse_number=1,
            bracket_number=3,
            jockey_id="01167",
            jockey_name="武豊",
            impost=56.0,
            sex="牡",
            age=3,
        )

        assert entry.bracket_number == 3

    def test_has_jockey_id(self):
        """jockey_id フィールドが存在"""
        from keiba.models.entry import RaceEntry

        entry = RaceEntry(
            horse_id="2023104001",
            horse_name="テスト馬",
            horse_number=1,
            bracket_number=1,
            jockey_id="01167",
            jockey_name="武豊",
            impost=56.0,
            sex="牡",
            age=3,
        )

        assert entry.jockey_id == "01167"

    def test_has_jockey_name(self):
        """jockey_name フィールドが存在"""
        from keiba.models.entry import RaceEntry

        entry = RaceEntry(
            horse_id="2023104001",
            horse_name="テスト馬",
            horse_number=1,
            bracket_number=1,
            jockey_id="01167",
            jockey_name="武豊",
            impost=56.0,
            sex="牡",
            age=3,
        )

        assert entry.jockey_name == "武豊"

    def test_has_impost(self):
        """impost フィールドが存在"""
        from keiba.models.entry import RaceEntry

        entry = RaceEntry(
            horse_id="2023104001",
            horse_name="テスト馬",
            horse_number=1,
            bracket_number=1,
            jockey_id="01167",
            jockey_name="武豊",
            impost=56.0,
            sex="牡",
            age=3,
        )

        assert entry.impost == 56.0

    def test_has_sex(self):
        """sex フィールドが存在"""
        from keiba.models.entry import RaceEntry

        entry = RaceEntry(
            horse_id="2023104001",
            horse_name="テスト馬",
            horse_number=1,
            bracket_number=1,
            jockey_id="01167",
            jockey_name="武豊",
            impost=56.0,
            sex="牡",
            age=3,
        )

        assert entry.sex == "牡"

    def test_has_age(self):
        """age フィールドが存在"""
        from keiba.models.entry import RaceEntry

        entry = RaceEntry(
            horse_id="2023104001",
            horse_name="テスト馬",
            horse_number=1,
            bracket_number=1,
            jockey_id="01167",
            jockey_name="武豊",
            impost=56.0,
            sex="牡",
            age=3,
        )

        assert entry.age == 3


class TestShutubaDataImmutability:
    """test_shutuba_data_is_immutable: ShutubaDataがイミュータブルであること"""

    def test_cannot_modify_race_id(self):
        """race_id フィールドは変更不可"""
        from keiba.models.entry import RaceEntry, ShutubaData

        entry = RaceEntry(
            horse_id="123",
            horse_name="テスト馬",
            horse_number=1,
            bracket_number=1,
            jockey_id="j001",
            jockey_name="テスト騎手",
            impost=56.0,
            sex="牡",
            age=3,
        )

        data = ShutubaData(
            race_id="202606010802",
            race_name="京成杯",
            race_number=11,
            course="中山",
            distance=2000,
            surface="芝",
            date="2026年1月8日",
            entries=(entry,),
        )

        with pytest.raises(FrozenInstanceError):
            data.race_id = "999"

    def test_cannot_modify_race_name(self):
        """race_name フィールドは変更不可"""
        from keiba.models.entry import RaceEntry, ShutubaData

        entry = RaceEntry(
            horse_id="123",
            horse_name="テスト馬",
            horse_number=1,
            bracket_number=1,
            jockey_id="j001",
            jockey_name="テスト騎手",
            impost=56.0,
            sex="牡",
            age=3,
        )

        data = ShutubaData(
            race_id="202606010802",
            race_name="京成杯",
            race_number=11,
            course="中山",
            distance=2000,
            surface="芝",
            date="2026年1月8日",
            entries=(entry,),
        )

        with pytest.raises(FrozenInstanceError):
            data.race_name = "変更レース"

    def test_cannot_modify_entries(self):
        """entries フィールドは変更不可"""
        from keiba.models.entry import RaceEntry, ShutubaData

        entry = RaceEntry(
            horse_id="123",
            horse_name="テスト馬",
            horse_number=1,
            bracket_number=1,
            jockey_id="j001",
            jockey_name="テスト騎手",
            impost=56.0,
            sex="牡",
            age=3,
        )

        data = ShutubaData(
            race_id="202606010802",
            race_name="京成杯",
            race_number=11,
            course="中山",
            distance=2000,
            surface="芝",
            date="2026年1月8日",
            entries=(entry,),
        )

        with pytest.raises(FrozenInstanceError):
            data.entries = ()


class TestShutubaDataContainsEntries:
    """test_shutuba_data_contains_entries: entriesフィールドが正しく動作すること"""

    def test_entries_is_tuple(self):
        """entries はタプル型"""
        from keiba.models.entry import RaceEntry, ShutubaData

        entry = RaceEntry(
            horse_id="123",
            horse_name="テスト馬",
            horse_number=1,
            bracket_number=1,
            jockey_id="j001",
            jockey_name="テスト騎手",
            impost=56.0,
            sex="牡",
            age=3,
        )

        data = ShutubaData(
            race_id="202606010802",
            race_name="京成杯",
            race_number=11,
            course="中山",
            distance=2000,
            surface="芝",
            date="2026年1月8日",
            entries=(entry,),
        )

        assert isinstance(data.entries, tuple)

    def test_entries_contains_race_entry_objects(self):
        """entries は RaceEntry オブジェクトを含む"""
        from keiba.models.entry import RaceEntry, ShutubaData

        entry1 = RaceEntry(
            horse_id="123",
            horse_name="テスト馬1",
            horse_number=1,
            bracket_number=1,
            jockey_id="j001",
            jockey_name="騎手1",
            impost=56.0,
            sex="牡",
            age=3,
        )
        entry2 = RaceEntry(
            horse_id="456",
            horse_name="テスト馬2",
            horse_number=2,
            bracket_number=2,
            jockey_id="j002",
            jockey_name="騎手2",
            impost=54.0,
            sex="牝",
            age=4,
        )

        data = ShutubaData(
            race_id="202606010802",
            race_name="京成杯",
            race_number=11,
            course="中山",
            distance=2000,
            surface="芝",
            date="2026年1月8日",
            entries=(entry1, entry2),
        )

        assert len(data.entries) == 2
        assert all(isinstance(e, RaceEntry) for e in data.entries)

    def test_entries_empty_tuple_allowed(self):
        """空のタプルも許容される"""
        from keiba.models.entry import ShutubaData

        data = ShutubaData(
            race_id="202606010802",
            race_name="京成杯",
            race_number=11,
            course="中山",
            distance=2000,
            surface="芝",
            date="2026年1月8日",
            entries=(),
        )

        assert data.entries == ()
        assert len(data.entries) == 0

    def test_entries_are_accessible_by_index(self):
        """entries はインデックスアクセス可能"""
        from keiba.models.entry import RaceEntry, ShutubaData

        entry1 = RaceEntry(
            horse_id="123",
            horse_name="テスト馬1",
            horse_number=1,
            bracket_number=1,
            jockey_id="j001",
            jockey_name="騎手1",
            impost=56.0,
            sex="牡",
            age=3,
        )
        entry2 = RaceEntry(
            horse_id="456",
            horse_name="テスト馬2",
            horse_number=2,
            bracket_number=2,
            jockey_id="j002",
            jockey_name="騎手2",
            impost=54.0,
            sex="牝",
            age=4,
        )

        data = ShutubaData(
            race_id="202606010802",
            race_name="京成杯",
            race_number=11,
            course="中山",
            distance=2000,
            surface="芝",
            date="2026年1月8日",
            entries=(entry1, entry2),
        )

        assert data.entries[0].horse_name == "テスト馬1"
        assert data.entries[1].horse_name == "テスト馬2"


class TestRaceEntryOptionalFields:
    """test_race_entry_optional_fields: オプショナルフィールドがNoneを許容すること"""

    def test_sex_can_be_none(self):
        """sex フィールドは None を許容"""
        from keiba.models.entry import RaceEntry

        entry = RaceEntry(
            horse_id="123",
            horse_name="テスト馬",
            horse_number=1,
            bracket_number=1,
            jockey_id="j001",
            jockey_name="テスト騎手",
            impost=56.0,
            sex=None,
            age=3,
        )

        assert entry.sex is None

    def test_age_can_be_none(self):
        """age フィールドは None を許容"""
        from keiba.models.entry import RaceEntry

        entry = RaceEntry(
            horse_id="123",
            horse_name="テスト馬",
            horse_number=1,
            bracket_number=1,
            jockey_id="j001",
            jockey_name="テスト騎手",
            impost=56.0,
            sex="牡",
            age=None,
        )

        assert entry.age is None

    def test_both_sex_and_age_can_be_none(self):
        """sex と age 両方が None でも可"""
        from keiba.models.entry import RaceEntry

        entry = RaceEntry(
            horse_id="123",
            horse_name="テスト馬",
            horse_number=1,
            bracket_number=1,
            jockey_id="j001",
            jockey_name="テスト騎手",
            impost=56.0,
            sex=None,
            age=None,
        )

        assert entry.sex is None
        assert entry.age is None

    def test_optional_fields_have_default_none(self):
        """オプショナルフィールドはデフォルト値 None"""
        from keiba.models.entry import RaceEntry

        entry = RaceEntry(
            horse_id="123",
            horse_name="テスト馬",
            horse_number=1,
            bracket_number=1,
            jockey_id="j001",
            jockey_name="テスト騎手",
            impost=56.0,
        )

        assert entry.sex is None
        assert entry.age is None
