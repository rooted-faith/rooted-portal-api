from datetime import date

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, Path, Query
from starlette import status

from portal.application.devotion.devotion_service import DevotionService
from portal.application.devotion.mappers import daily_lesson_to_api
from portal.container import Container
from portal.libs.contexts.request_context import get_request_context, get_resolved_locale_code, get_resolved_locale_id
from portal.libs.contexts.user_context import get_user_context
from portal.routers.auth_router import AuthRouter
from portal.serializers.apis.v1.devotion import AnonymousDailyLessonResponse, DailyLessonResponse

router: AuthRouter = AuthRouter(require_auth=False, optional_auth=True)


async def _read_daily_lesson(lesson_date: date, devotion_service: DevotionService) -> AnonymousDailyLessonResponse | DailyLessonResponse:
    locale_id = get_resolved_locale_id()
    locale_code = get_resolved_locale_code()
    request_context = get_request_context()
    if request_context and request_context.locale_candidates and locale_code:
        resolved_language = locale_code.split("-", maxsplit=1)[0].lower()
        accepted_languages = {candidate.split("-", maxsplit=1)[0].lower() for candidate in request_context.locale_candidates if candidate != "*"}
        if "*" not in request_context.locale_candidates and resolved_language not in accepted_languages:
            locale_id = None
            locale_code = None
    user_context = get_user_context()
    result = await devotion_service.get_daily_lesson(
        lesson_date=lesson_date, locale_id=locale_id, locale_code=locale_code, include_authored_sections=bool(user_context and user_context.user_id)
    )
    return daily_lesson_to_api(result)


@router.get(
    path="/today",
    response_model=AnonymousDailyLessonResponse | DailyLessonResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    operation_id="get_anonymous_daily_lesson",
    summary="Get today's Daily lesson",
)
@inject
async def get_today_daily_lesson(
    date_: date = Query(alias="date"), devotion_service: DevotionService = Depends(Provide[Container.devotion_service])
) -> AnonymousDailyLessonResponse | DailyLessonResponse:
    return await _read_daily_lesson(date_, devotion_service)


@router.get(
    path="/lessons/{date}",
    response_model=AnonymousDailyLessonResponse | DailyLessonResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    operation_id="get_daily_lesson",
    summary="Get a Daily lesson by date",
)
@inject
async def get_daily_lesson(
    date_: date = Path(alias="date"), devotion_service: DevotionService = Depends(Provide[Container.devotion_service])
) -> AnonymousDailyLessonResponse | DailyLessonResponse:
    return await _read_daily_lesson(date_, devotion_service)
