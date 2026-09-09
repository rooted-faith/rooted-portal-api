"""Application seam for signed-in End-user Preferences."""

from uuid import UUID, uuid4

import pytest

from portal.application.app.commands import UpdatePreferencesCommand
from portal.application.app.preferences_service import PreferencesService
from portal.domain.app.entities import EndUser, UserPreferences
from portal.exceptions.responses import UnauthorizedException


class StubEndUserRepository:
    def __init__(self, end_user: EndUser | None):
        self.end_user = end_user

    async def get_by_auth_user_id(self, auth_user_id: UUID):
        if self.end_user is not None and self.end_user.auth_user_id == auth_user_id:
            return self.end_user
        return None


class StubPreferencesRepository:
    def __init__(self, preferences: UserPreferences):
        self.preferences = preferences

    async def get_by_user_id(self, user_id: UUID):
        return self.preferences if self.preferences.user_id == user_id else None

    async def update_preferences(self, user_id: UUID, values: dict[str, object]):
        if self.preferences.user_id != user_id:
            return None
        self.preferences = self.preferences.model_copy(update=values)
        return self.preferences


def build_service() -> tuple[PreferencesService, EndUser, StubPreferencesRepository]:
    end_user = EndUser(id=uuid4(), auth_user_id=uuid4())
    repository = StubPreferencesRepository(UserPreferences(user_id=end_user.id, display_name="林安"))
    service = PreferencesService(end_user_repository=StubEndUserRepository(end_user), preferences_repository=repository)
    return service, end_user, repository


@pytest.mark.asyncio
async def test_get_preferences_returns_sunday_week_start_by_default() -> None:
    service, end_user, _ = build_service()

    result = await service.get_preferences(auth_user_id=end_user.auth_user_id)

    assert result.week_start == "sunday"


@pytest.mark.asyncio
async def test_update_preferences_persists_week_start_with_other_preferences() -> None:
    service, end_user, repository = build_service()

    result = await service.update_preferences(auth_user_id=end_user.auth_user_id, command=UpdatePreferencesCommand(week_start="monday", theme="dark"))

    assert result.week_start == "monday"
    assert result.theme == "dark"
    assert repository.preferences.week_start == "monday"


@pytest.mark.asyncio
async def test_get_preferences_rejects_a_credential_without_an_end_user() -> None:
    _, _, repository = build_service()
    service = PreferencesService(end_user_repository=StubEndUserRepository(None), preferences_repository=repository)

    with pytest.raises(UnauthorizedException):
        await service.get_preferences(auth_user_id=uuid4())
