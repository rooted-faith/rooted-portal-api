from datetime import date
from uuid import UUID

from portal.domain.devotion.constants import DevotionErrorCode
from portal.domain.devotion.entities import AnonymousDailyLesson, DailyLesson
from portal.domain.devotion.ports import DevotionRepositoryPort
from portal.exceptions.responses import NotFoundException
from portal.libs.tracing.distributed_trace import distributed_trace


class DevotionService:
    def __init__(self, devotion_repository: DevotionRepositoryPort):
        self._repository = devotion_repository

    @distributed_trace()
    async def get_daily_lesson(
        self, lesson_date: date, locale_id: UUID | None, locale_code: str | None, include_authored_sections: bool
    ) -> AnonymousDailyLesson | DailyLesson:
        lesson = await self._repository.fetch_daily_lesson(lesson_date, locale_id, locale_code, include_authored_sections)
        if lesson is not None:
            return lesson
        if not await self._repository.daily_lesson_exists(lesson_date):
            raise NotFoundException(detail=f"No Daily lesson scheduled for {lesson_date}", error_code=DevotionErrorCode.DATE_NOT_SCHEDULED)
        raise NotFoundException(detail="Devotion translation not found for the requested locale", error_code=DevotionErrorCode.TRANSLATION_NOT_FOUND)
