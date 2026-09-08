from portal.domain.devotion.entities import AnonymousDailyLesson
from portal.serializers.apis.v1.devotion import AnonymousDailyLessonResponse, PassageResponse


def anonymous_daily_lesson_to_api(result: AnonymousDailyLesson) -> AnonymousDailyLessonResponse:
    return AnonymousDailyLessonResponse(date=result.date, passage=PassageResponse(**result.passage.model_dump()), locked=result.locked)
