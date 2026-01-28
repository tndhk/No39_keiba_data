"""Entry DTOs for race entry data.

This module provides immutable data transfer objects for race entries
and shutuba (race entry table) data.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RaceEntry:
    """Represents a single race entry (horse).

    This is an immutable dataclass to ensure data integrity.

    Attributes:
        horse_id: The horse's unique identifier.
        horse_name: The horse's name.
        horse_number: The horse's number in the race.
        bracket_number: The bracket (waku) number.
        jockey_id: The jockey's unique identifier.
        jockey_name: The jockey's name.
        impost: The weight carried (in kg).
        sex: The horse's sex (optional).
        age: The horse's age (optional).
    """

    horse_id: str
    horse_name: str
    horse_number: int
    bracket_number: int
    jockey_id: str
    jockey_name: str
    impost: float
    sex: str | None = None
    age: int | None = None


@dataclass(frozen=True)
class ShutubaData:
    """Represents the complete shutuba (race entry) data.

    This is an immutable dataclass containing race information
    and all entries.

    Attributes:
        race_id: The race's unique identifier.
        race_name: The race name.
        race_number: The race number (1-12).
        course: The racecourse name.
        distance: The race distance in meters.
        surface: The track surface.
        date: The race date.
        entries: Tuple of RaceEntry objects (immutable).
        track_condition: The track condition (e.g., "良", "稍重", "重", "不良").
    """

    race_id: str
    race_name: str
    race_number: int
    course: str
    distance: int
    surface: str
    date: str
    entries: tuple[RaceEntry, ...]
    track_condition: str | None = None
