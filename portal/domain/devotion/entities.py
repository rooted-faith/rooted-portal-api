from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class Passage(BaseModel):
    start: str
    end: str
    ref: str
    verses: list[str] = Field(default_factory=list)


class AnonymousDailyLesson(BaseModel):
    date: date
    passage: Passage
    locked: list[str] = Field(default_factory=lambda: ["reflect", "apply", "pray", "note"])


class DailyLesson(BaseModel):
    date: date
    passage: Passage
    reflect: list[str] = Field(default_factory=list)
    apply: str
    pray: str
    locked: list[str] = Field(default_factory=list)


class EncounterStreak(BaseModel):
    user_id: UUID
    longest_streak: int
    current_streak_length: int
    last_encounter_date: date | None
