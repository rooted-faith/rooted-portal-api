"""
Request-scoped database session context helpers.
"""

from contextvars import ContextVar, Token

from portal.libs.database import Session

_request_session_ctx: ContextVar[Session | None] = ContextVar("request_session_ctx", default=None)


def set_request_session(session: Session) -> Token:
    return _request_session_ctx.set(session)


def get_request_session() -> Session | None:
    return _request_session_ctx.get()


def reset_request_session(token) -> None:
    _request_session_ctx.reset(token)


