from datetime import date
from typing import Protocol
from uuid import UUID

from portal.domain.devotion.entities import AnonymousDailyLesson, DailyLesson, EncounterStreak


class DevotionRepositoryPort(Protocol):
    async def fetch_daily_lesson(
        self, lesson_date: date, locale_id: UUID | None, locale_code: str | None, include_authored_sections: bool
    ) -> AnonymousDailyLesson | DailyLesson | None: ...

    async def daily_lesson_exists(self, lesson_date: date) -> bool: ...

    async def insert_encounter_day(self, user_id: UUID, encounter_date: date) -> bool: ...

    async def get_encounter_streak(self, user_id: UUID) -> EncounterStreak | None: ...

    async def save_encounter_streak(self, streak: EncounterStreak) -> None: ...

    async def list_recent_encounter_dates(self, user_id: UUID, through_date: date) -> list[date]: ...
