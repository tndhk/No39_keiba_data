"""Tests for markdown formatter module."""

import tempfile
from pathlib import Path

from keiba.cli.formatters.markdown import parse_predictions_markdown


class TestParsePredictionsMarkdownZeroRaceNumber:
    """Tests for handling 0R race numbers."""

    def test_parses_zero_race_number(self):
        """0Rのレース番号を正しくパースする."""
        markdown = """# 2026-01-31 東京

## 0R テストレース

race_id: 202605010000

| 順位 | 馬番 | 馬名 | 総合スコア |
| ---- | ---- | ---- | ---------- |
| 1 | 1 | テストホース | 85.5 |
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown)
            f.flush()
            result = parse_predictions_markdown(f.name)
            Path(f.name).unlink()

        races = result["races"]
        assert len(races) == 1
        assert races[0]["race_number"] == 0
        assert races[0]["race_name"] == "テストレース"
        assert races[0]["race_id"] == "202605010000"

    def test_uses_race_id_fallback_for_zero_race_number(self):
        """race_numberが0の場合、race_idから推測する."""
        markdown = """# 2026-01-31 東京

## 0R テストレース

race_id: 202605010811

| 順位 | 馬番 | 馬名 | 総合スコア |
| ---- | ---- | ---- | ---------- |
| 1 | 1 | テストホース | 85.5 |
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown)
            f.flush()
            result = parse_predictions_markdown(f.name)
            Path(f.name).unlink()

        races = result["races"]
        assert len(races) == 1
        # race_idの10-11桁目が11なので、race_numberは11に更新される
        assert races[0]["race_number"] == 11
        assert races[0]["race_name"] == "テストレース"
        assert races[0]["race_id"] == "202605010811"


class TestParsePredictionsMarkdownEmptyRaceName:
    """Tests for handling empty race names."""

    def test_parses_empty_race_name(self):
        """レース名が空の場合を正しくパースする."""
        markdown = """# 2026-01-31 東京

## 1R

race_id: 202605010101

| 順位 | 馬番 | 馬名 | 総合スコア |
| ---- | ---- | ---- | ---------- |
| 1 | 1 | テストホース | 85.5 |
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown)
            f.flush()
            result = parse_predictions_markdown(f.name)
            Path(f.name).unlink()

        races = result["races"]
        assert len(races) == 1
        assert races[0]["race_number"] == 1
        assert races[0]["race_name"] == ""
        assert races[0]["race_id"] == "202605010101"

    def test_parses_race_name_with_whitespace(self):
        """レース名が空白のみの場合を正しくパースする."""
        markdown = """# 2026-01-31 東京

## 2R

race_id: 202605010201

| 順位 | 馬番 | 馬名 | 総合スコア |
| ---- | ---- | ---- | ---------- |
| 1 | 1 | テストホース | 85.5 |
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown)
            f.flush()
            result = parse_predictions_markdown(f.name)
            Path(f.name).unlink()

        races = result["races"]
        assert len(races) == 1
        assert races[0]["race_number"] == 2
        # 空白のみの場合は空文字列になる
        assert races[0]["race_name"] == ""
        assert races[0]["race_id"] == "202605010201"


class TestParsePredictionsMarkdownRaceIdFallback:
    """Tests for race_id fallback logic."""

    def test_race_id_fallback_preserves_nonzero_race_number(self):
        """race_numberが0でない場合、race_idから推測しない."""
        markdown = """# 2026-01-31 東京

## 3R テストレース

race_id: 202605010811

| 順位 | 馬番 | 馬名 | 総合スコア |
| ---- | ---- | ---- | ---------- |
| 1 | 1 | テストホース | 85.5 |
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown)
            f.flush()
            result = parse_predictions_markdown(f.name)
            Path(f.name).unlink()

        races = result["races"]
        assert len(races) == 1
        # race_numberが3なので、race_idから推測しない
        assert races[0]["race_number"] == 3
        assert races[0]["race_id"] == "202605010811"

    def test_race_id_fallback_requires_12_digit_race_id(self):
        """race_idが12桁でない場合、フォールバックしない."""
        markdown = """# 2026-01-31 東京

## 0R テストレース

race_id: 123

| 順位 | 馬番 | 馬名 | 総合スコア |
| ---- | ---- | ---- | ---------- |
| 1 | 1 | テストホース | 85.5 |
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown)
            f.flush()
            result = parse_predictions_markdown(f.name)
            Path(f.name).unlink()

        races = result["races"]
        assert len(races) == 1
        # race_idが12桁でないので、race_numberは0のまま
        assert races[0]["race_number"] == 0
        assert races[0]["race_id"] == "123"

    def test_race_id_fallback_with_invalid_race_number_in_id(self):
        """race_idの10-11桁目が0の場合、フォールバックしない."""
        markdown = """# 2026-01-31 東京

## 0R テストレース

race_id: 202605010800

| 順位 | 馬番 | 馬名 | 総合スコア |
| ---- | ---- | ---- | ---------- |
| 1 | 1 | テストホース | 85.5 |
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown)
            f.flush()
            result = parse_predictions_markdown(f.name)
            Path(f.name).unlink()

        races = result["races"]
        assert len(races) == 1
        # race_idの10-11桁目が00なので、race_numberは0のまま
        assert races[0]["race_number"] == 0
        assert races[0]["race_id"] == "202605010800"


class TestParsePredictionsMarkdownMultipleRaces:
    """Tests for parsing multiple races."""

    def test_parses_multiple_races_with_mixed_formats(self):
        """複数レースを正しくパースする（0R、空レース名、通常形式の混在）."""
        markdown = """# 2026-01-31 東京

## 0R

race_id: 202605010811

| 順位 | 馬番 | 馬名 | 総合スコア |
| ---- | ---- | ---- | ---------- |
| 1 | 1 | ホース1 | 85.5 |

## 1R テストレース

race_id: 202605010101

| 順位 | 馬番 | 馬名 | 総合スコア |
| ---- | ---- | ---- | ---------- |
| 1 | 2 | ホース2 | 90.0 |

## 2R

race_id: 202605010201

| 順位 | 馬番 | 馬名 | 総合スコア |
| ---- | ---- | ---- | ---------- |
| 1 | 3 | ホース3 | 88.0 |
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown)
            f.flush()
            result = parse_predictions_markdown(f.name)
            Path(f.name).unlink()

        races = result["races"]
        assert len(races) == 3

        # 1レース目: 0R、空レース名、race_idから推測
        assert races[0]["race_number"] == 11  # race_idから推測
        assert races[0]["race_name"] == ""
        assert races[0]["race_id"] == "202605010811"

        # 2レース目: 通常形式
        assert races[1]["race_number"] == 1
        assert races[1]["race_name"] == "テストレース"
        assert races[1]["race_id"] == "202605010101"

        # 3レース目: 空レース名
        assert races[2]["race_number"] == 2
        assert races[2]["race_name"] == ""
        assert races[2]["race_id"] == "202605010201"
