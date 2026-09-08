"""
Results for End user / identity provisioning.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProvisionIdentityResult(BaseModel):
    """Outcome of credential (+ optional End user) provisioning."""

    auth_user_id: UUID = Field(...)
    end_user_id: Optional[UUID] = Field(default=None, description="app.user.id when create_end_user was True; None for admin-only")


class ReonboardingFlagResult(BaseModel):
    """Current state of an End user's reonboarding flag."""

    end_user_id: UUID = Field(..., description="app.user.id (End user)")
    reonboarding_requested_at: Optional[datetime] = Field(default=None, description="When an Admin asked for the replay; None when nothing is pending")
