"""
Admin routers package
"""
from fastapi import FastAPI


def register_routers(app: FastAPI) -> None:
    """
    Register all admin routers
    :param app: FastAPI application instance
    :return:
    """
    # Register admin routers
    # Example:
    # from .auth import router as auth_router
    # app.include_router(auth_router, prefix="/api/v1/auth", tags=["Admin - Authentication"])
    
    # For now, create a simple health check endpoint
    @app.get("/healthz")
    async def admin_healthz():
        """
        Admin healthcheck endpoint
        """
        return {
            "message": "ok",
            "service": "admin"
        }
