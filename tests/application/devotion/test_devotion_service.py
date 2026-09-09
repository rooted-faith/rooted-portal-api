from datetime import date

import pytest

from portal.application.devotion.devotion_service import DevotionService
from portal.domain.devotion.constants import DevotionErrorCode
from portal.domain.devotion.entities import AnonymousDailyLesson, DailyLesson, Passage
from portal.exceptions.responses import NotFoundException


class StubDevotionRepository:
    def __init__(self, lesson=None, scheduled=True):
        self.lesson = lesson
        self.scheduled = scheduled

    async def fetch_daily_lesson(self, lesson_date, locale_id, locale_code, include_authored_sections):
        return self.lesson

    async def daily_lesson_exists(self, lesson_date):
        return self.scheduled


@pytest.mark.asyncio
async def test_get_daily_lesson_returns_verse_and_locked_sections_for_anonymous_end_user():
    lesson = AnonymousDailyLesson(
        date=date(2026, 9, 8), passage=Passage(start="JHN.3.16", end="JHN.3.16", ref="John 3:16", verses=["For God so loved the world"])
    )
    service = DevotionService(StubDevotionRepository(lesson=lesson))

    result = await service.get_daily_lesson(date(2026, 9, 8), locale_id=None, locale_code="en", include_authored_sections=False)

    assert result == lesson
    assert result.locked == ["reflect", "apply", "pray", "note"]


@pytest.mark.asyncio
async def test_get_daily_lesson_returns_all_authored_sections_for_signed_in_end_user():
    lesson = DailyLesson(
        date=date(2026, 9, 8),
        passage=Passage(start="JHN.3.16", end="JHN.3.16", ref="John 3:16", verses=["For God so loved the world"]),
        reflect=["Where do you see God's love today?", "Who can you love practically?"],
        apply="Encourage one person today.",
        pray="God, help me receive and share your love.",
    )
    service = DevotionService(StubDevotionRepository(lesson=lesson))

    result = await service.get_daily_lesson(date(2026, 9, 8), locale_id=None, locale_code="en", include_authored_sections=True)

    assert result == lesson
    assert result.locked == []
    assert result.reflect == ["Where do you see God's love today?", "Who can you love practically?"]
    assert result.apply == "Encourage one person today."
    assert result.pray == "God, help me receive and share your love."


@pytest.mark.asyncio
async def test_get_daily_lesson_anonymous_result_withholds_authored_sections():
    lesson = AnonymousDailyLesson(
        date=date(2026, 9, 7), passage=Passage(start="PSA.23.1", end="PSA.23.1", ref="Psalm 23:1", verses=["The Lord is my shepherd"])
    )
    service = DevotionService(StubDevotionRepository(lesson=lesson))

    result = await service.get_daily_lesson(date(2026, 9, 7), locale_id=None, locale_code="en", include_authored_sections=False)

    assert result == lesson
    assert result.locked == ["reflect", "apply", "pray", "note"]
    assert not hasattr(result, "reflect")
    assert not hasattr(result, "apply")
    assert not hasattr(result, "pray")


@pytest.mark.asyncio
async def test_get_daily_lesson_raises_when_date_is_not_scheduled():
    service = DevotionService(StubDevotionRepository(lesson=None, scheduled=False))

    with pytest.raises(NotFoundException) as error:
        await service.get_daily_lesson(date(2026, 9, 9), locale_id=None, locale_code="en", include_authored_sections=False)

    assert error.value.error_code == DevotionErrorCode.DATE_NOT_SCHEDULED


@pytest.mark.asyncio
async def test_get_daily_lesson_raises_when_translation_is_missing_for_anonymous_end_user():
    service = DevotionService(StubDevotionRepository(lesson=None, scheduled=True))

    with pytest.raises(NotFoundException) as error:
        await service.get_daily_lesson(date(2026, 9, 8), locale_id=None, locale_code="fr", include_authored_sections=False)

    assert error.value.error_code == DevotionErrorCode.TRANSLATION_NOT_FOUND


@pytest.mark.asyncio
async def test_get_daily_lesson_raises_when_translation_is_missing_for_signed_in_end_user():
    service = DevotionService(StubDevotionRepository(lesson=None, scheduled=True))

    with pytest.raises(NotFoundException) as error:
        await service.get_daily_lesson(date(2026, 9, 8), locale_id=None, locale_code="fr", include_authored_sections=True)

    assert error.value.error_code == DevotionErrorCode.TRANSLATION_NOT_FOUND
