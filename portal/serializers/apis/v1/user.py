"""
Member End user serializers (camelCase JSON via serialization_alias).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MemberReonboarding(BaseModel):
    """Reonboarding flag state after the client acknowledges it."""

    reonboarding_requested_at: Optional[datetime] = Field(
        default=None, serialization_alias="reonboardingRequestedAt", description="Null once the replay has been acknowledged"
    )
