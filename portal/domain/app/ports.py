"""
Ports for End user identity and Preferences persistence.
"""

from datetime import datetime
from typing import Optional, Protocol
from uuid import UUID

from portal.domain.app.entities import EndUser, UserPreferences


class EndUserRepositoryPort(Protocol):
    """Persist End user rows keyed by app.user.id."""

    async def create_end_user(self, *, end_user_id: UUID, auth_user_id: UUID) -> EndUser: ...

    async def get_by_auth_user_id(self, auth_user_id: UUID) -> Optional[EndUser]: ...

    async def get_by_id(self, end_user_id: UUID) -> Optional[EndUser]: ...

    async def set_reonboarding_requested_at(self, end_user_id: UUID, requested_at: Optional[datetime]) -> Optional[EndUser]:
        """Set (Admin request) or clear (client acknowledgement) the reonboarding flag; None when no such End user."""
        ...


class PreferencesRepositoryPort(Protocol):
    """Persist 1:1 Preferences for an End user."""

    async def create_preferences(self, preferences: UserPreferences) -> UserPreferences: ...

    async def get_by_user_id(self, user_id: UUID) -> Optional[UserPreferences]: ...
