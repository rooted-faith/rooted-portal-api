from datetime import date

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query
from starlette import status

from portal.application.devotion.devotion_service import DevotionService
from portal.application.devotion.mappers import anonymous_daily_lesson_to_api
from portal.container import Container
from portal.libs.contexts.request_context import get_request_context, get_resolved_locale_code, get_resolved_locale_id
from portal.serializers.apis.v1.devotion import AnonymousDailyLessonResponse

router = APIRouter()


@router.get(
    path="/today",
    response_model=AnonymousDailyLessonResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    operation_id="get_anonymous_daily_lesson",
    summary="Get today's anonymous Daily lesson",
)
@inject
async def get_anonymous_daily_lesson(
    date_: date = Query(alias="date"), devotion_service: DevotionService = Depends(Provide[Container.devotion_service])
) -> AnonymousDailyLessonResponse:
    locale_id = get_resolved_locale_id()
    locale_code = get_resolved_locale_code()
    request_context = get_request_context()
    if request_context and request_context.locale_candidates and locale_code:
        resolved_language = locale_code.split("-", maxsplit=1)[0].lower()
        accepted_languages = {candidate.split("-", maxsplit=1)[0].lower() for candidate in request_context.locale_candidates if candidate != "*"}
        if "*" not in request_context.locale_candidates and resolved_language not in accepted_languages:
            locale_id = None
            locale_code = None
    result = await devotion_service.get_anonymous_today(lesson_date=date_, locale_id=locale_id, locale_code=locale_code)
    return anonymous_daily_lesson_to_api(result)
