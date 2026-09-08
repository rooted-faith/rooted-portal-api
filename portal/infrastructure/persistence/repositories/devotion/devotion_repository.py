from datetime import date
from uuid import UUID

from portal.domain.devotion.entities import AnonymousDailyLesson, Passage
from portal.libs.database import Session
from portal.models import BibleBook, BibleVerse, BibleVersion, Devotion, DevotionDailyLessonSchedule, DevotionTranslation


class DevotionRepository:
    def __init__(self, session: Session):
        self._session = session

    async def daily_lesson_exists(self, lesson_date: date) -> bool:
        schedule_id = await self._session.select(DevotionDailyLessonSchedule.id).where(DevotionDailyLessonSchedule.date == lesson_date).fetchval()
        return schedule_id is not None

    async def fetch_anonymous_daily_lesson(self, lesson_date: date, locale_id: UUID | None, locale_code: str | None) -> AnonymousDailyLesson | None:
        if locale_id is None or locale_code is None:
            return None

        language = locale_code.split("-", maxsplit=1)[0]
        base = await (
            self._session.select(Devotion.passage_start, Devotion.passage_end)
            .join(DevotionDailyLessonSchedule, DevotionDailyLessonSchedule.devotion_id == Devotion.id)
            .join(DevotionTranslation, DevotionTranslation.devotion_id == Devotion.id)
            .where(DevotionDailyLessonSchedule.date == lesson_date)
            .where(DevotionTranslation.locale_id == locale_id)
            .fetchrow()
        )
        if not base:
            return None

        bible_version_id = await (
            self._session.select(BibleVersion.id)
            .where(BibleVersion.is_active == True)  # noqa: E712
            .where(BibleVersion.language_tag.ilike(f"{language}%"))
            .order_by(BibleVersion.youversion_bible_id)
            .fetchval()
        )
        if bible_version_id is None:
            return None

        verses = await (
            self._session.select(BibleBook.title.label("book_name"), BibleVerse.chapter, BibleVerse.verse, BibleVerse.content)
            .join(BibleBook, BibleVerse.book_id == BibleBook.id)
            .join(BibleVersion, BibleBook.bible_version_id == BibleVersion.id)
            .where(BibleVersion.id == bible_version_id)
            .where(BibleVerse.passage_id >= base["passage_start"])
            .where(BibleVerse.passage_id <= base["passage_end"])
            .order_by(BibleVersion.youversion_bible_id, BibleVerse.chapter, BibleVerse.verse)
            .fetch()
        )
        if not verses:
            return None

        first = verses[0]
        last = verses[-1]
        verse_ref = f"{first['book_name']} {first['chapter']}:{first['verse']}"
        if (last["chapter"], last["verse"]) != (first["chapter"], first["verse"]):
            verse_ref += f"–{last['chapter']}:{last['verse']}"
        return AnonymousDailyLesson(
            date=lesson_date, passage=Passage(start=base["passage_start"], end=base["passage_end"], ref=verse_ref, verses=[row["content"] for row in verses])
        )
