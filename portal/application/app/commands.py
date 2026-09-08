"""
Commands for End user / identity provisioning.
"""

from datetime import time
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProvisionIdentityCommand(BaseModel):
    """
    Provision a shared auth credential.

    When create_end_user is True (app signup), also create app.user + Preferences.
    When False (admin-only), skip End user identity entirely.
    """

    email: str = Field(...)
    password: Optional[str] = Field(default=None, description="Required for Admin/password paths; null for passwordless End users")
    display_name: Optional[str] = Field(default=None)
    create_end_user: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    is_superuser: bool = Field(default=False)
    theme: str = Field(default="system")
    font_scale: str = Field(default="M")
    bible_version: str = Field(default="cuv1919")
    stage: Optional[str] = Field(default=None)
    reminder_time: Optional[time] = Field(default=None)
    reminder_enabled: bool = Field(default=False)


class RequestReonboardingCommand(BaseModel):
    """Admin asks one End user to go through onboarding again (ADR 0008)."""

    end_user_id: UUID = Field(..., description="app.user.id of the End user to flag")
