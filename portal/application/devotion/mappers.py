from portal.domain.devotion.entities import AnonymousDailyLesson, DailyLesson
from portal.serializers.apis.v1.devotion import AnonymousDailyLessonResponse, DailyLessonResponse, PassageResponse


def anonymous_daily_lesson_to_api(result: AnonymousDailyLesson) -> AnonymousDailyLessonResponse:
    return AnonymousDailyLessonResponse(date=result.date, passage=PassageResponse(**result.passage.model_dump()), locked=result.locked)


def daily_lesson_to_api(result: AnonymousDailyLesson | DailyLesson) -> AnonymousDailyLessonResponse | DailyLessonResponse:
    if isinstance(result, DailyLesson):
        return DailyLessonResponse(
            date=result.date,
            passage=PassageResponse(**result.passage.model_dump()),
            reflect=result.reflect,
            apply=result.apply,
            pray=result.pray,
            locked=result.locked,
        )
    return anonymous_daily_lesson_to_api(result)
