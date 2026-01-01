"""
main application
"""
from collections import defaultdict

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.asyncpg import AsyncPGIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.tracing import Span
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse

from portal.apps.admin import create_admin_app
from portal.config import settings
from portal.container import Container
from portal.exceptions.responses import ApiBaseException
from portal.libs.contexts.request_session_context import get_request_session
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.logger import logger
from portal.libs.utils.lifespan import lifespan
from portal.middlewares import AuthMiddleware, CoreRequestMiddleware
from portal.routers import api_router

__all__ = ["app"]


def setup_tracing():
    """
    Setup tracing
    :return:
    """
    if not settings.SENTRY_URL:
        return
    sentry_sdk.init(
        dsn=settings.SENTRY_URL,
        integrations=[
            AsyncPGIntegration(),
            FastApiIntegration(),
            HttpxIntegration(),
            RedisIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        environment=settings.ENV.upper(),
        enable_tracing=True,
    )


def register_middleware(application: FastAPI) -> None:
    """
    register middleware
    Middleware order (from outer to inner, executed in reverse order):
    1. CORSMiddleware - Handle CORS (outermost, executed last)
    2. CoreRequestMiddleware - Setup request context and database session
    3. AuthMiddleware - Verify token and set UserContext (innermost, executed first)

    Note: AuthMiddleware executes after CoreRequestMiddleware to ensure database session is available.
    Both authentication (token verification) and authorization (permission checking) are handled in AuthMiddleware.
    No dependency injection is used for auth logic.
    :param application:
    :return:
    """
    # CORS middleware should be outermost (added first, executed last)
    application.add_middleware(AuthMiddleware)
    application.add_middleware(CoreRequestMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_origin_regex=settings.CORS_ALLOW_ORIGINS_REGEX
    )


def register_router(application: FastAPI) -> None:
    """
    register router
    :param application:
    :return:
    """
    application.include_router(api_router, prefix="/api")


def mount_admin_app(application: FastAPI, container: Container) -> None:
    """
    Mount Admin sub-application
    :param application: Main FastAPI application
    :param container: Dependency injection container
    :return:
    """
    # Create and mount Admin sub-app
    admin_app = create_admin_app(container=container)
    application.mount("/admin", admin_app)
    logger.info("Mounted Admin sub-application at /admin")


def get_application() -> FastAPI:
    """
    get application
    """
    setup_tracing()
    application = FastAPI(
        lifespan=lifespan,
    )

    # set container
    _container = Container()
    application.container = _container

    # Register middleware (applied to all routes and sub-apps)
    register_middleware(application=application)

    # Register API routers
    register_router(application=application)

    # Mount Admin sub-application
    mount_admin_app(application=application, container=_container)

    return application


app = get_application()


@app.get("/")
async def root():
    """
    Root path redirects to /docs in development environment
    """
    if settings.is_dev:
        return RedirectResponse(url="/docs")
    return {"message": "Welcome to Rooted Portal API"}


@app.exception_handler(HTTPException)
@distributed_trace(inject_span=True)
async def root_http_exception_handler(request, exc: HTTPException, _span: Span = None):
    """

    :param request:
    :param exc:
    :param _span:
    :return:
    """
    session = get_request_session()
    if session is not None:
        await session.rollback()
    try:
        _span.set_data("error.detail", exc.detail)
        _span.set_data("error.url", str(request.url))
    except Exception:
        pass
    return await http_exception_handler(request, exc)


@app.exception_handler(ApiBaseException)
@distributed_trace(inject_span=True)
async def root_api_exception_handler(request, exc: ApiBaseException, _span: Span = None):
    """

    :param request:
    :param exc:
    :param _span:
    :return:
    """
    session = get_request_session()
    if session is not None:
        await session.rollback()
    content = defaultdict()
    content["detail"] = exc.detail
    if settings.is_dev:
        content["debug_detail"] = exc.debug_detail
        content["url"] = str(request.url)
    try:
        _span.set_data("error.detail", exc.detail)
        _span.set_data("error.debug_detail", exc.debug_detail)
        _span.set_data("error.url", str(request.url))
    except Exception:
        pass
    return JSONResponse(
        content=content,
        status_code=exc.status_code
    )


@app.exception_handler(Exception)
@distributed_trace(inject_span=True)
async def exception_handler(request: Request, exc, _span: Span = None):
    """

    :param request:
    :param exc:
    :param _span:
    :return:
    """
    content = defaultdict()
    content["detail"] = {
        "message": "Internal Server Error",
        "url": str(request.url)
    }
    if settings.is_dev:
        content["debug_detail"] = f"{exc.__class__.__name__}: {exc}"
    try:
        _span.set_data("error.detail", content["detail"])
        _span.set_data("error.debug_detail", content["debug_detail"])
        _span.set_data("error.url", str(request.url))
    except Exception:
        pass
    return JSONResponse(
        content=content,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )

