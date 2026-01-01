"""
User Context (per-request)
"""
from contextvars import ContextVar, Token
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from portal.libs.consts.enums import Gender


class UserContext(BaseModel):
    """Per-request user information"""
    user_id: UUID | None = None
    phone_number: str | None = None
    email: str | None = None
    verified: bool = False
    is_active: bool = False
    is_superuser: bool = False
    is_admin: bool = False
    last_login_at: datetime | None = None
    display_name: str | None = None
    gender: Gender | None = None
    is_ministry: bool = False
    login_admin: bool = False
    # token
    token: str | None = None
    token_payload: dict | None = None
    # other
    username: str | None = None


user_context_var: ContextVar[UserContext] = ContextVar("UserContext")


def set_user_context(context: UserContext) -> Token:
    """
    Set the user context for current request.
    Prefer initializing this once in middleware and mutate thereafter.
    """
    return user_context_var.set(context)


def get_user_context() -> UserContext | None:
    """
    Get current request's user context. Middleware should have set it.
    """
    try:
        return user_context_var.get()
    except LookupError:
        return None


def reset_user_context(token) -> None:
    """
    Reset the user context for current request.
    :param token:
    :return:
    """
    user_context_var.reset(token)
