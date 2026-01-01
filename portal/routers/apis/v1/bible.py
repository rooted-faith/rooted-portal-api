"""
Bible API Router
"""
from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query
from starlette import status

from portal.container import Container
from portal.handlers.bible import BibleHandler
from portal.serializers.v1.bible import (
    BibleBookList,
    BibleChapterDetail,
    BibleSearchResponse,
    BibleVersionList,
)

router = APIRouter()


@router.get(
    path="/versions",
    response_model=BibleVersionList,
    status_code=status.HTTP_200_OK,
    operation_id="get_bible_versions",
    summary="Get bible versions",
    description="Get list of available bible versions",
)
@inject
async def get_bible_versions(
    language: Annotated[str | None, Query(description="Language filter (e.g., 'zh-TW', 'zh-CN')")] = None,
    bible_handler: BibleHandler = Depends(Provide[Container.bible_handler]),
) -> BibleVersionList:
    """
    Get bible versions
    :param language: Optional language filter
    :param bible_handler:
    :return:
    """
    return await bible_handler.get_versions(language=language)


@router.get(
    path="/versions/{bible_version_id}/books",
    response_model=BibleBookList,
    status_code=status.HTTP_200_OK,
    operation_id="get_bible_books",
    summary="Get bible books",
    description="Get list of bible books for a specific version",
)
@inject
async def get_bible_books(
    bible_version_id: UUID,
    bible_handler: BibleHandler = Depends(Provide[Container.bible_handler]),
) -> BibleBookList:
    """
    Get bible books for a specific version
    :param bible_version_id: Bible version ID (UUID)
    :param bible_handler:
    :return:
    """
    return await bible_handler.get_books(bible_version_id=bible_version_id)


@router.get(
    path="/books/{book_id}/chapters/{chapter}",
    response_model=BibleChapterDetail,
    status_code=status.HTTP_200_OK,
    operation_id="get_bible_chapter",
    summary="Get bible chapter",
    description="Get bible chapter content",
)
@inject
async def get_bible_chapter(
    book_id: UUID,
    chapter: int,
    bible_handler: BibleHandler = Depends(Provide[Container.bible_handler]),
) -> BibleChapterDetail:
    """
    Get bible chapter content
    :param book_id: Book ID (UUID)
    :param chapter: Chapter number
    :param bible_handler:
    :return:
    """
    return await bible_handler.get_chapter(
        book_id=book_id,
        chapter=chapter,
    )


@router.get(
    path="/search",
    response_model=BibleSearchResponse,
    status_code=status.HTTP_200_OK,
    operation_id="search_bible_verses",
    summary="Search bible verses",
    description="Search bible verses by keyword",
)
@inject
async def search_bible_verses(
    q: Annotated[str, Query(description="Search keyword")],
    bible_version_id: Annotated[UUID | None, Query(description="Bible version ID filter (UUID)")] = None,
    book_id: Annotated[UUID | None, Query(description="Book ID filter (UUID)")] = None,
    limit: Annotated[int, Query(description="Result limit", ge=1, le=100)] = 20,
    offset: Annotated[int, Query(description="Result offset", ge=0)] = 0,
    bible_handler: BibleHandler = Depends(Provide[Container.bible_handler]),
) -> BibleSearchResponse:
    """
    Search bible verses
    :param q: Search keyword
    :param bible_version_id: Optional bible version ID filter (UUID)
    :param book_id: Optional book ID filter (UUID)
    :param limit: Result limit
    :param offset: Result offset
    :param bible_handler:
    :return:
    """
    return await bible_handler.search_verses(
        q=q,
        bible_version_id=bible_version_id,
        book_id=book_id,
        limit=limit,
        offset=offset,
    )

