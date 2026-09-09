from datetime import date, timedelta
from typing import Callable
from uuid import UUID

from portal.application.devotion.results import EncounterResult, RhythmResult
from portal.domain.app.ports import EndUserRepositoryPort
from portal.domain.devotion.constants import DevotionErrorCode
from portal.domain.devotion.entities import AnonymousDailyLesson, DailyLesson, EncounterStreak
from portal.domain.devotion.ports import DevotionRepositoryPort
from portal.exceptions.responses import BadRequestException, NotFoundException, UnauthorizedException
from portal.libs.tracing.distributed_trace import distributed_trace


class DevotionService:
    def __init__(
        self, devotion_repository: DevotionRepositoryPort, end_user_repository: EndUserRepositoryPort, local_date_provider: Callable[[], date] = date.today
    ):
        self._repository = devotion_repository
        self._end_user_repository = end_user_repository
        self._local_date_provider = local_date_provider

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

    async def _get_end_user_id(self, auth_user_id: UUID) -> UUID:
        end_user = await self._end_user_repository.get_by_auth_user_id(auth_user_id)
        if end_user is None:
            raise UnauthorizedException(detail="This credential has no End user")
        return end_user.id

    @distributed_trace()
    async def record_encounter(self, *, auth_user_id: UUID, encounter_date: date) -> EncounterResult:
        if encounter_date != self._local_date_provider():
            raise BadRequestException(detail="Encounter day must be the caller's current local date")
        end_user_id = await self._get_end_user_id(auth_user_id)
        inserted = await self._repository.insert_encounter_day(end_user_id, encounter_date)
        streak = await self._repository.get_encounter_streak(end_user_id)
        welcome_back = bool(streak and streak.last_encounter_date and streak.last_encounter_date < encounter_date - timedelta(days=1))

        if inserted:
            previous_length = streak.current_streak_length if streak and streak.last_encounter_date == encounter_date - timedelta(days=1) else 0
            current_streak = previous_length + 1
            longest_streak = max(streak.longest_streak if streak else 0, current_streak)
            streak = EncounterStreak(
                user_id=end_user_id, longest_streak=longest_streak, current_streak_length=current_streak, last_encounter_date=encounter_date
            )
            await self._repository.save_encounter_streak(streak)

        if streak is None:
            streak = EncounterStreak(user_id=end_user_id, longest_streak=0, current_streak_length=0, last_encounter_date=None)
        current_streak = self._validated_current_streak(streak, encounter_date)
        return EncounterResult(date=encounter_date, current_streak=current_streak, longest_streak=streak.longest_streak, welcome_back=welcome_back)

    @distributed_trace()
    async def get_rhythm(self, *, auth_user_id: UUID, reader_date: date) -> RhythmResult:
        end_user_id = await self._get_end_user_id(auth_user_id)
        streak = await self._repository.get_encounter_streak(end_user_id)
        completed_dates = await self._repository.list_recent_encounter_dates(end_user_id, reader_date)
        if streak is None:
            return RhythmResult(current_streak=0, longest_streak=0, completed_dates=completed_dates)
        return RhythmResult(
            current_streak=self._validated_current_streak(streak, reader_date), longest_streak=streak.longest_streak, completed_dates=completed_dates
        )

    @staticmethod
    def _validated_current_streak(streak: EncounterStreak, reader_date: date) -> int:
        if streak.last_encounter_date in {reader_date, reader_date - timedelta(days=1)}:
            return streak.current_streak_length
        return 0
