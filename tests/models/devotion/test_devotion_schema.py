import sqlalchemy as sa

from portal.models import Devotion, DevotionDailyLessonSchedule, DevotionTranslation


def test_devotion_maps_passage_and_two_state_status_to_devotion_schema():
    assert Devotion.__table__.schema == "devotion"
    assert Devotion.__tablename__ == "devotions"
    assert {"passage_start", "passage_end", "status"} <= set(Devotion.__table__.c.keys())
    status_constraint = next(item for item in Devotion.__table__.constraints if isinstance(item, sa.CheckConstraint))
    assert "draft" in str(status_constraint.sqltext)
    assert "ready" in str(status_constraint.sqltext)


def test_devotion_translation_is_unique_per_devotion_and_locale():
    assert DevotionTranslation.__table__.schema == "devotion"
    assert DevotionTranslation.__tablename__ == "translations"
    unique_columns = [
        {column.name for column in constraint.columns}
        for constraint in DevotionTranslation.__table__.constraints
        if isinstance(constraint, sa.UniqueConstraint)
    ]
    assert {"devotion_id", "locale_id"} in unique_columns
    assert isinstance(DevotionTranslation.__table__.c.reflect.type, sa.JSON)
    assert {"apply", "pray"} <= set(DevotionTranslation.__table__.c.keys())


def test_daily_lesson_schedule_is_unique_by_date_and_reuses_devotions():
    assert DevotionDailyLessonSchedule.__table__.schema == "devotion"
    assert DevotionDailyLessonSchedule.__tablename__ == "daily_lesson_schedule"
    assert DevotionDailyLessonSchedule.__table__.c.date.unique is True
    assert DevotionDailyLessonSchedule.__table__.c.devotion_id.unique is not True
