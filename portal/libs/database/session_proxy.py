"""
Session proxy for request-scoped database session.
"""
import asyncio
from typing import TYPE_CHECKING, Any

from portal.libs.contexts.request_session_context import get_request_session
from portal.libs.database import Session

if TYPE_CHECKING:
    from collections.abc import Callable


class SessionProxy:
    """
    A lightweight proxy that forwards attribute access/calls to
    the request-scoped Session stored in ContextVar.
    """

    def __init__(self) -> None:
        # Intentionally stateless; session is resolved per access from context
        self._noop: Callable[..., Any] | None = None

    def _resolve(self) -> Session:
        session = get_request_session()
        if session is None:
            raise RuntimeError("No request-scoped Session is available in context")
        return session

    def __getattr__(self, name: str) -> Any:
        session = self._resolve()
        attr = getattr(session, name)
        if asyncio.iscoroutinefunction(attr):
            async def _wrapped(*args, **kwargs):
                return await attr(*args, **kwargs)

            return _wrapped
        return attr


