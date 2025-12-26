"""
Container
"""
from dependency_injector import containers, providers

from portal import handlers
from portal.config import settings
from portal.libs.database import RedisPool, PostgresConnection, Session
from portal.libs.database.session_proxy import SessionProxy


# pylint: disable=too-few-public-methods,c-extension-no-member
class Container(containers.DeclarativeContainer):
    """Container"""

    wiring_config = containers.WiringConfiguration(
        modules=[],
        packages=[
            "portal.authorization",
            "portal.handlers",
            "portal.routers",
            "portal.middlewares",
        ],
    )

    # [App Base]
    config = providers.Configuration()
    config.from_pydantic(settings)

    # [Database]
    postgres_connection = providers.Singleton(PostgresConnection)
    # Real session factory (per-use); lifecycle is handled by middleware request context
    db_session = providers.Factory(Session, postgres_connection=postgres_connection)
    # Request-scoped session proxy that resolves to the ContextVar session
    request_session = providers.Factory(SessionProxy)

    # [Redis]
    redis_client = providers.Singleton(RedisPool)

    # [Handlers]
    bible_handler = providers.Factory(
        handlers.BibleHandler,
        session=request_session,
        redis_client=redis_client,
    )

