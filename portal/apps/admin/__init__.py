"""
Admin sub application
"""
from fastapi import FastAPI

from portal.container import Container
from portal.libs.utils.lifespan import lifespan

from .routers import register_routers


def create_admin_app(container: Container) -> FastAPI:
    """
    Create admin sub application
    :param container: Dependency injection container
    :return: FastAPI application instance
    """
    admin_app = FastAPI(
        title="Rooted Portal Admin API",
        description="Admin API for Rooted Portal",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Share container with admin app
    admin_app.container = container

    # Register routers
    register_routers(admin_app)

    return admin_app

