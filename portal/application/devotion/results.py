from datetime import date

from pydantic import BaseModel, Field


class EncounterResult(BaseModel):
    date: date
    current_streak: int
    longest_streak: int
    message: str = "今日已與主相遇"


class RhythmResult(BaseModel):
    current_streak: int
    longest_streak: int
    recent_dates: list[date] = Field(default_factory=list)
