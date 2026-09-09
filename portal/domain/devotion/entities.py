from datetime import date

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
