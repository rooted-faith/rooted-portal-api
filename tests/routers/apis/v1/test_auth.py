"""HTTP route contract for End-user and Admin authentication."""

from fastapi.routing import APIRoute

from portal.routers.admin.v1.auth import router as admin_auth_router
from portal.routers.apis.v1.auth import router as app_auth_router


def _post_paths(router) -> set[str]:
    return {route.path for route in router.routes if isinstance(route, APIRoute) and "POST" in route.methods}


def test_end_user_password_register_and_login_routes_are_unreachable() -> None:
    post_paths = _post_paths(app_auth_router)

    assert "/register" not in post_paths
    assert "/login" not in post_paths


def test_admin_password_login_route_remains_available() -> None:
    assert "/login" in _post_paths(admin_auth_router)
