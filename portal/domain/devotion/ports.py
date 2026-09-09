from datetime import date
from typing import Protocol
from uuid import UUID

from portal.domain.devotion.entities import AnonymousDailyLesson, DailyLesson


class DevotionRepositoryPort(Protocol):
    async def fetch_daily_lesson(
        self, lesson_date: date, locale_id: UUID | None, locale_code: str | None, include_authored_sections: bool
    ) -> AnonymousDailyLesson | DailyLesson | None: ...

    async def daily_lesson_exists(self, lesson_date: date) -> bool: ...
