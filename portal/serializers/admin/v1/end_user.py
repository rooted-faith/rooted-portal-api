"""
Admin End user serializers (camelCase JSON via serialization_alias).
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer


class AdminEndUserReonboarding(BaseModel):
    """Current state of an End user's reonboarding flag."""

    end_user_id: UUID = Field(..., serialization_alias="endUserId", description="app.user.id (End user)")
    reonboarding_requested_at: Optional[datetime] = Field(
        default=None, serialization_alias="reonboardingRequestedAt", description="When the replay was requested; null when nothing is pending"
    )

    @field_serializer("end_user_id")
    def serialize_uuid(self, value: UUID, _info) -> str:
        return str(value)
