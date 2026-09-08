"""Application-service seam: Admin password login remains supported."""

from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from portal.application.auth.commands import LoginCommand
from portal.application.auth.login_service import LoginService
from portal.application.auth.results import UserSensitive


@pytest.mark.asyncio
async def test_admin_can_log_in_with_password(mocker: MockerFixture) -> None:
    user = UserSensitive(
        id=uuid4(), email="admin@example.com", password_hash="hashed-password", verified=True, is_active=True, is_admin=True, first_name="Ada", last_name="Min"
    )
    user_repository = mocker.Mock()
    user_repository.get_sensitive_by_email = mocker.AsyncMock(return_value=user)
    user_repository.update_last_login_at = mocker.AsyncMock()
    password_provider = mocker.Mock()
    password_provider.verify_password.return_value = True
    role_service = mocker.Mock()
    role_service.init_user_roles_cache = mocker.AsyncMock(return_value=["admin"])
    permission_service = mocker.Mock()
    permission_service.init_user_permissions_cache = mocker.AsyncMock(return_value=["content:read"])
    jwt_provider = mocker.Mock()
    jwt_provider.create_access_token.return_value = "access-token"
    refresh_token_provider = mocker.Mock()
    refresh_token_provider.issue = mocker.AsyncMock(return_value="refresh-token")
    service = LoginService(
        user_repository=user_repository,
        jwt_provider=jwt_provider,
        refresh_token_provider=refresh_token_provider,
        password_provider=password_provider,
        role_service=role_service,
        permission_service=permission_service,
    )

    result = await service.login_with_password(LoginCommand(email="admin@example.com", password="Secure1!"))

    password_provider.verify_password.assert_called_once_with("Secure1!", "hashed-password")
    assert result.admin.id == user.id
    assert result.token.access_token == "access-token"
    assert result.token.refresh_token == "refresh-token"
