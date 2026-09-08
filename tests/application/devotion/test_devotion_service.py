from datetime import date

import pytest

from portal.application.devotion.devotion_service import DevotionService
from portal.domain.devotion.constants import DevotionErrorCode
from portal.domain.devotion.entities import AnonymousDailyLesson, Passage
from portal.exceptions.responses import NotFoundException


class StubDevotionRepository:
    def __init__(self, lesson=None, scheduled=True):
        self.lesson = lesson
        self.scheduled = scheduled

    async def fetch_anonymous_daily_lesson(self, lesson_date, locale_id, locale_code):
        return self.lesson

    async def daily_lesson_exists(self, lesson_date):
        return self.scheduled


@pytest.mark.asyncio
async def test_get_anonymous_today_returns_verse_and_locked_sections():
    lesson = AnonymousDailyLesson(
        date=date(2026, 9, 8), passage=Passage(start="JHN.3.16", end="JHN.3.16", ref="John 3:16", verses=["For God so loved the world"])
    )
    service = DevotionService(StubDevotionRepository(lesson=lesson))

    result = await service.get_anonymous_today(date(2026, 9, 8), locale_id=None, locale_code="en")

    assert result == lesson
    assert result.locked == ["reflect", "apply", "pray", "note"]


@pytest.mark.asyncio
async def test_get_anonymous_today_raises_when_date_is_not_scheduled():
    service = DevotionService(StubDevotionRepository(lesson=None, scheduled=False))

    with pytest.raises(NotFoundException) as error:
        await service.get_anonymous_today(date(2026, 9, 9), locale_id=None, locale_code="en")

    assert error.value.error_code == DevotionErrorCode.DATE_NOT_SCHEDULED


@pytest.mark.asyncio
async def test_get_anonymous_today_raises_when_translation_is_missing():
    service = DevotionService(StubDevotionRepository(lesson=None, scheduled=True))

    with pytest.raises(NotFoundException) as error:
        await service.get_anonymous_today(date(2026, 9, 8), locale_id=None, locale_code="fr")

    assert error.value.error_code == DevotionErrorCode.TRANSLATION_NOT_FOUND
