from datetime import date, timedelta
from uuid import UUID

import sqlalchemy as sa

from portal.domain.devotion.entities import AnonymousDailyLesson, DailyLesson, EncounterStreak, Passage
from portal.libs.database import Session
from portal.models import BibleBook, BibleVerse, BibleVersion, Devotion, DevotionDailyLessonSchedule, DevotionTranslation, EncounterDay
from portal.models import EncounterStreak as EncounterStreakModel


class DevotionRepository:
    def __init__(self, session: Session):
        self._session = session

    async def daily_lesson_exists(self, lesson_date: date) -> bool:
        schedule_id = await self._session.select(DevotionDailyLessonSchedule.id).where(DevotionDailyLessonSchedule.date == lesson_date).fetchval()
        return schedule_id is not None

    async def insert_encounter_day(self, user_id: UUID, encounter_date: date) -> bool:
        status = await (
            self._session.insert(EncounterDay).values(user_id=user_id, date=encounter_date).on_conflict_do_nothing(index_elements=["user_id", "date"]).execute()
        )
        return status == "INSERT 0 1"

    async def get_encounter_streak(self, user_id: UUID) -> EncounterStreak | None:
        return await (
            self._session.select(
                EncounterStreakModel.user_id,
                EncounterStreakModel.longest_streak,
                EncounterStreakModel.current_streak_length,
                EncounterStreakModel.last_encounter_date,
            )
            .where(EncounterStreakModel.user_id == user_id)
            .fetchrow(as_model=EncounterStreak)
        )

    async def save_encounter_streak(self, streak: EncounterStreak) -> None:
        await (
            self._session.insert(EncounterStreakModel)
            .values(**streak.model_dump())
            .on_conflict_do_update(
                index_elements=["user_id"],
                set_={
                    "longest_streak": sa.func.greatest(EncounterStreakModel.longest_streak, streak.longest_streak),
                    "current_streak_length": streak.current_streak_length,
                    "last_encounter_date": streak.last_encounter_date,
                    "updated_at": sa.func.now(),
                },
            )
            .execute()
        )

    async def list_recent_encounter_dates(self, user_id: UUID, through_date: date) -> list[date]:
        return await (
            self._session.select(EncounterDay.date)
            .where(EncounterDay.user_id == user_id)
            .where(EncounterDay.date >= through_date - timedelta(days=34))
            .where(EncounterDay.date <= through_date)
            .order_by(EncounterDay.date)
            .fetchvals()
        )

    async def fetch_daily_lesson(
        self, lesson_date: date, locale_id: UUID | None, locale_code: str | None, include_authored_sections: bool
    ) -> AnonymousDailyLesson | DailyLesson | None:
        if locale_id is None or locale_code is None:
            return None

        language = locale_code.split("-", maxsplit=1)[0]
        selected_columns = [Devotion.passage_start, Devotion.passage_end]
        if include_authored_sections:
            selected_columns.extend([DevotionTranslation.reflect, DevotionTranslation.apply, DevotionTranslation.pray])
        scheduled_passage = await (
            self._session.select(*selected_columns)
            .join(DevotionDailyLessonSchedule, DevotionDailyLessonSchedule.devotion_id == Devotion.id)
            .join(DevotionTranslation, DevotionTranslation.devotion_id == Devotion.id)
            .where(DevotionDailyLessonSchedule.date == lesson_date)
            .where(DevotionTranslation.locale_id == locale_id)
            .where(Devotion.status == "ready")
            .fetchrow()
        )
        if not scheduled_passage:
            return None

        start_book, start_chapter, start_verse = self._parse_passage_id(scheduled_passage["passage_start"])
        end_book, end_chapter, end_verse = self._parse_passage_id(scheduled_passage["passage_end"])
        if start_book != end_book:
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
            .where(BibleBook.book_code == start_book)
            .where(sa.or_(BibleVerse.chapter > start_chapter, sa.and_(BibleVerse.chapter == start_chapter, BibleVerse.verse >= start_verse)))
            .where(sa.or_(BibleVerse.chapter < end_chapter, sa.and_(BibleVerse.chapter == end_chapter, BibleVerse.verse <= end_verse)))
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
        passage = Passage(
            start=scheduled_passage["passage_start"], end=scheduled_passage["passage_end"], ref=verse_ref, verses=[row["content"] for row in verses]
        )
        if include_authored_sections:
            return DailyLesson(
                date=lesson_date, passage=passage, reflect=scheduled_passage["reflect"], apply=scheduled_passage["apply"], pray=scheduled_passage["pray"]
            )
        return AnonymousDailyLesson(date=lesson_date, passage=passage)

    @staticmethod
    def _parse_passage_id(passage_id: str) -> tuple[str, int, int]:
        book_code, chapter, verse = passage_id.split(".", maxsplit=2)
        return book_code, int(chapter), int(verse)
