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
