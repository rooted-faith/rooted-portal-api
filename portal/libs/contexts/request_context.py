"""
Request Context (per-request)
"""
from contextvars import ContextVar, Token

from pydantic import BaseModel


class RequestContext(BaseModel):
    """Per-request HTTP information"""

    ip: str | None = None
    client_ip: str | None = None
    user_agent: str | None = None
    method: str | None = None
    host: str | None = None
    url: str | None = None
    path: str | None = None
    request_id: str | None = None


request_context_var: ContextVar[RequestContext] = ContextVar("RequestContext")


def set_request_context(context: RequestContext) -> Token:
    """
    Set the request context for current request.
    """
    return request_context_var.set(context)


def get_request_context() -> RequestContext:
    """
    Get current request's request context.
    """
    return request_context_var.get()


def reset_request_context(token) -> None:
    """
    Reset the request context for current request.
    :param token:
    :return:
    """
    request_context_var.reset(token)
