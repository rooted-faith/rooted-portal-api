from datetime import date
from typing import Protocol
from uuid import UUID

from portal.domain.devotion.entities import AnonymousDailyLesson


class DevotionRepositoryPort(Protocol):
    async def fetch_anonymous_daily_lesson(self, lesson_date: date, locale_id: UUID | None, locale_code: str | None) -> AnonymousDailyLesson | None: ...

    async def daily_lesson_exists(self, lesson_date: date) -> bool: ...
