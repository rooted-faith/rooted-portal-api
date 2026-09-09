from datetime import date

from pydantic import BaseModel, Field


class PassageResponse(BaseModel):
    start: str
    end: str
    ref: str
    verses: list[str] = Field(default_factory=list)


class AnonymousDailyLessonResponse(BaseModel):
    date: date
    passage: PassageResponse
    locked: list[str] = Field(default_factory=list)


class DailyLessonResponse(BaseModel):
    date: date
    passage: PassageResponse
    reflect: list[str] = Field(default_factory=list)
    apply: str
    pray: str
    locked: list[str] = Field(default_factory=list)


class EncounterRequest(BaseModel):
    date: date


class EncounterResponse(BaseModel):
    date: date
    current_streak: int = Field(serialization_alias="currentStreak")
    longest_streak: int = Field(serialization_alias="longestStreak")
    message: str


class RhythmResponse(BaseModel):
    current_streak: int = Field(serialization_alias="currentStreak")
    longest_streak: int = Field(serialization_alias="longestStreak")
    recent_dates: list[date] = Field(default_factory=list, serialization_alias="recentDates")
