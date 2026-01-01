"""
BibleHandler
"""

from typing import TYPE_CHECKING
from uuid import UUID

from portal.config import settings
from portal.exceptions.responses import NotFoundException
from portal.libs.database import RedisPool, Session
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.models import BibleBook, BibleVerse, BibleVersion
from portal.serializers.v1.bible import (
    BibleBookBase,
    BibleBookList,
    BibleChapterDetail,
    BibleSearchResponse,
    BibleSearchResult,
    BibleVerseBase,
    BibleVersionBase,
    BibleVersionList,
)

if TYPE_CHECKING:
    from redis.asyncio import Redis


class BibleHandler:
    """BibleHandler"""

    def __init__(
        self,
        session: Session,
        redis_client: RedisPool,
    ):
        self._session = session
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)

    @distributed_trace()
    async def get_versions(self, language: str | None = None) -> BibleVersionList:
        """
        Get bible versions
        :param language: Optional language filter (e.g., 'zh-TW', 'zh-CN')
        :return:
        """
        query = self._session.select(
            BibleVersion.id,
            BibleVersion.youversion_bible_id,
            BibleVersion.abbreviation,
            BibleVersion.title,
            BibleVersion.localized_title,
            BibleVersion.localized_abbreviation,
            BibleVersion.language_tag,
            BibleVersion.is_active,
        ).where(
            BibleVersion.is_active.is_(True)
        )

        if language:
            query = query.where(BibleVersion.language_tag.ilike(f"{language}%"))

        versions: list[BibleVersionBase] = await query.order_by(
            BibleVersion.language_tag, BibleVersion.youversion_bible_id
        ).fetch(as_model=BibleVersionBase)

        return BibleVersionList(versions=versions)

    @distributed_trace()
    async def get_books(self, bible_version_id: UUID) -> BibleBookList:
        """
        Get bible books for a specific version
        :param bible_version_id: Bible version ID (UUID)
        :return:
        """
        # Verify version exists and is active
        version_exists = await (
            self._session.select(BibleVersion.id)
            .where(BibleVersion.id == bible_version_id)
            .where(BibleVersion.is_active == True)  # noqa
            .fetchval()
        )
        if not version_exists:
            raise NotFoundException(
                detail=f"Bible version {bible_version_id} not found or inactive"
            )

        books: list[BibleBookBase] = await (
            self._session.select(
                BibleBook.id,
                BibleBook.book_code,
                BibleBook.title,
                BibleBook.full_title,
                BibleBook.abbreviation,
                BibleBook.canon,
                BibleBook.sequence,
                BibleBook.chapter_count,
            )
            .where(BibleBook.bible_version_id == bible_version_id)
            .order_by(BibleBook.sequence)
            .fetch(as_model=BibleBookBase)
        )

        # Split into old and new testament
        old_testament = [book for book in books if book.canon == "old_testament"]
        new_testament = [book for book in books if book.canon == "new_testament"]

        return BibleBookList(old_testament=old_testament, new_testament=new_testament)

    @distributed_trace()
    async def get_chapter(
        self,
        book_id: UUID,
        chapter: int,
    ) -> BibleChapterDetail:
        """
        Get bible chapter content
        :param book_id: Book ID (UUID)
        :param chapter: Chapter number
        :return:
        """
        # Get book info with version info
        book_with_version = await (
            self._session.select(
                BibleBook.id,
                BibleBook.book_code,
                BibleBook.title,
                BibleVersion.id.label("bible_version_id"),
                BibleVersion.youversion_bible_id,
                BibleVersion.localized_title.label("bible_title"),
            )
            .join(BibleVersion, BibleBook.bible_version_id == BibleVersion.id)
            .where(BibleBook.id == book_id)
            .where(BibleVersion.is_active == True)  # noqa
            .fetchrow()
        )

        if not book_with_version:
            raise NotFoundException(
                detail=f"Book {book_id} not found or version is inactive"
            )

        # Get verses
        verses: list[BibleVerseBase] = await (
            self._session.select(
                BibleVerse.verse,
                BibleVerse.content,
            )
            .where(BibleVerse.book_id == book_id)
            .where(BibleVerse.chapter == chapter)
            .order_by(BibleVerse.verse)
            .fetch(as_model=BibleVerseBase)
        )

        return BibleChapterDetail(
            bible_version_id=book_with_version["bible_version_id"],
            youversion_bible_id=book_with_version["youversion_bible_id"],
            bible_title=book_with_version["bible_title"],
            book_id=book_with_version["id"],
            book_code=book_with_version["book_code"],
            book_name=book_with_version["title"],
            chapter=chapter,
            verses=verses,
        )

    @distributed_trace()
    async def search_verses(
        self,
        q: str,
        bible_version_id: UUID | None = None,
        book_id: UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> BibleSearchResponse:
        """
        Search bible verses
        :param q: Search query
        :param bible_version_id: Optional bible version ID filter (UUID)
        :param book_id: Optional book ID filter (UUID)
        :param limit: Result limit
        :param offset: Result offset
        :return:
        """
        # Build query - join through book to get version info
        query = (
            self._session.select(
                BibleVersion.id.label("bible_version_id"),
                BibleVersion.youversion_bible_id,
                BibleVersion.localized_title.label("bible_title"),
                BibleVerse.book_id,
                BibleBook.book_code,
                BibleBook.title.label("book_name"),
                BibleVerse.chapter,
                BibleVerse.verse,
                BibleVerse.content,
            )
            .join(BibleBook, BibleVerse.book_id == BibleBook.id)
            .join(BibleVersion, BibleBook.bible_version_id == BibleVersion.id)
            .where(BibleVersion.is_active == True)  # noqa
            .where(BibleVerse.content.ilike(f"%{q}%"))
        )

        if bible_version_id:
            query = query.where(BibleVersion.id == bible_version_id)
        if book_id:
            query = query.where(BibleVerse.book_id == book_id)

        # Get total count
        total = await query.count()

        # Get results
        results: list[BibleSearchResult] = await (
            query.order_by(
                BibleVersion.youversion_bible_id,
                BibleBook.sequence,
                BibleVerse.chapter,
                BibleVerse.verse,
            )
            .limit(limit)
            .offset(offset)
            .fetch(as_model=BibleSearchResult)
        )

        return BibleSearchResponse(
            results=results,
            total=total,
            limit=limit,
            offset=offset,
        )
