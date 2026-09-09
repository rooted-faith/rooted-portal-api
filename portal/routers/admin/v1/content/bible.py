"""Admin Scripture lookup routes for Devotion authoring."""

from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, Query, status

from portal.application.bible.bible_service import BibleService
from portal.application.bible.commands import ListVersionsQuery
from portal.application.bible.mappers import bible_book_list_to_admin_api, bible_chapter_to_admin_api, bible_version_list_to_admin_api
from portal.container import Container
from portal.libs.consts.permission import Permission
from portal.routers.auth_router import AuthRouter
from portal.serializers.admin.v1.bible import AdminBibleBookList, AdminBibleChapterDetail, AdminBibleVersionList

router = AuthRouter(is_admin=True)


@router.get(
    path="/versions",
    response_model=AdminBibleVersionList,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    permissions=[Permission.CONTENT_DEVOTION.read],
)
@inject
async def get_bible_versions(
    language: Annotated[str | None, Query(description="Language filter (e.g., 'zh-TW', 'zh-CN')")] = None,
    bible_service: BibleService = Depends(Provide[Container.bible_service]),
) -> AdminBibleVersionList:
    result = await bible_service.list_versions(ListVersionsQuery(language=language))
    return bible_version_list_to_admin_api(result)


@router.get(
    path="/versions/{bible_version_id}/books",
    response_model=AdminBibleBookList,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    permissions=[Permission.CONTENT_DEVOTION.read],
)
@inject
async def get_bible_books(bible_version_id: UUID, bible_service: BibleService = Depends(Provide[Container.bible_service])) -> AdminBibleBookList:
    result = await bible_service.list_books(bible_version_id=bible_version_id)
    return bible_book_list_to_admin_api(result)


@router.get(
    path="/books/{book_id}/chapters/{chapter}",
    response_model=AdminBibleChapterDetail,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    permissions=[Permission.CONTENT_DEVOTION.read],
)
@inject
async def get_bible_chapter(book_id: UUID, chapter: int, bible_service: BibleService = Depends(Provide[Container.bible_service])) -> AdminBibleChapterDetail:
    result = await bible_service.get_chapter(book_id=book_id, chapter=chapter)
    return bible_chapter_to_admin_api(result)
