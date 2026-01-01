"""
API Context
"""
from contextvars import ContextVar, Token

from pydantic import BaseModel

from portal.schemas.auth import TokenPayload

auth_context = ContextVar("APIContext")


class APIContext(BaseModel):
    """API Context"""
    model_config = {
        "arbitrary_types_allowed": True
    }
    token: str | None = None
    token_payload: TokenPayload | None = None
    uid: str | None = None
    email: str | None = None
    username: str | None = None
    display_name: str | None = None
    host: str | None = None
    url: str | None = None
    path: str | None = None
    verified: bool | None = False


def set_api_context(context: APIContext) -> Token:
    """

    :param context:
    :return:
    """
    return auth_context.set(context)


def get_api_context() -> APIContext:
    """

    :return:
    """
    try:
        return auth_context.get()
    except LookupError:
        return APIContext()
