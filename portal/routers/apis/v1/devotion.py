from datetime import date

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query
from starlette import status

from portal.application.devotion.devotion_service import DevotionService
from portal.application.devotion.mappers import anonymous_daily_lesson_to_api
from portal.container import Container
from portal.libs.contexts.request_context import get_resolved_locale_code, get_resolved_locale_id
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
    result = await devotion_service.get_anonymous_today(lesson_date=date_, locale_id=get_resolved_locale_id(), locale_code=get_resolved_locale_code())
    return anonymous_daily_lesson_to_api(result)
