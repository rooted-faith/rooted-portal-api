"""Devotion editorial pool, translations, and calendar schedule."""

import sqlalchemy as sa
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB, UUID

from portal.libs.database.orm import ModelBase
from portal.models.mixins import AuditCreatedAtMixin, AuditUpdatedAtMixin
from portal.models.system_locale import SystemLocale


class Devotion(ModelBase, AuditCreatedAtMixin, AuditUpdatedAtMixin):
    __tablename__ = "devotions"
    __extra_table_args__ = (sa.CheckConstraint("status IN ('draft', 'ready')", name="devotion_status"), {"comment": "Devotion editorial content pool"})

    passage_start = Column(sa.String(50), nullable=False, comment="First bible.verses passage_id")
    passage_end = Column(sa.String(50), nullable=False, comment="Last bible.verses passage_id")
    status = Column(sa.String(10), nullable=False, server_default="draft", index=True)


class DevotionTranslation(ModelBase, AuditCreatedAtMixin, AuditUpdatedAtMixin):
    __tablename__ = "translations"
    __extra_table_args__ = (sa.UniqueConstraint("devotion_id", "locale_id"), {"comment": "Locale-specific authored Devotion content"})

    devotion_id = Column(UUID, sa.ForeignKey(Devotion.id, ondelete="CASCADE"), nullable=False, index=True)
    locale_id = Column(UUID, sa.ForeignKey(SystemLocale.id), nullable=False, index=True)
    reflect = Column(JSONB, nullable=False, comment="Ordered reflection prompt strings")
    apply = Column(sa.Text, nullable=False, comment="Today's application")
    pray = Column(sa.Text, nullable=False, comment="Prayer")


class DevotionDailyLessonSchedule(ModelBase, AuditCreatedAtMixin, AuditUpdatedAtMixin):
    __tablename__ = "daily_lesson_schedule"
    __extra_table_args__ = ({"comment": "One scheduled Devotion per calendar date"},)

    date = Column(sa.Date, nullable=False, unique=True)
    devotion_id = Column(UUID, sa.ForeignKey(Devotion.id), nullable=False, index=True)
