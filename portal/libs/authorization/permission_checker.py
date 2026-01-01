"""
Permission Checker Service
"""

from typing import TYPE_CHECKING
from uuid import UUID

from portal.config import settings
from portal.exceptions.responses import UnauthorizedException
from portal.libs.consts.cache_keys import CacheKeys
from portal.libs.contexts.user_context import get_user_context
from portal.libs.database import RedisPool
from portal.libs.decorators.sentry_tracer import distributed_trace

if TYPE_CHECKING:
    from redis.asyncio import Redis


class PermissionChecker:
    """Permission Checker Service for authorization"""

    def __init__(self, redis_client: RedisPool):
        self._redis: Redis = redis_client.create(db=settings.REDIS_DB)

    @distributed_trace()
    async def has_permission(
        self, permission_code: str, user_id: UUID | None = None
    ) -> bool:
        """
        Check if user has specific permission
        Permission is checked against Redis cache only (single source of truth)
        :param permission_code: Permission code (e.g., "user:read")
        :param user_id: User ID, if None, get from context
        :return: True if user has permission
        """
        user_context = get_user_context()

        # Superuser has all permissions
        if user_context.is_superuser:
            return True

        # Get user_id from context if not provided
        if user_id is None:
            user_id = user_context.user_id

        if not user_id:
            raise UnauthorizedException(detail="User not authenticated")

        # Check permission cache (using hash field)
        # Redis cache is the single source of truth for permissions
        key = CacheKeys(resource="permission").add_attribute(str(user_id)).build()
        return await self._redis.hexists(key, permission_code)

    @distributed_trace()
    async def has_any_permission(
        self, permission_codes: list[str], user_id: UUID | None = None
    ) -> bool:
        """
        Check if user has any of the specified permissions
        :param permission_codes: List of permission codes
        :param user_id: User ID, if None, get from context
        :return: True if user has any permission
        """
        for permission_code in permission_codes:
            if await self.has_permission(permission_code, user_id):
                return True
        return False

    @distributed_trace()
    async def has_all_permissions(
        self, permission_codes: list[str], user_id: UUID | None = None
    ) -> bool:
        """
        Check if user has all of the specified permissions
        :param permission_codes: List of permission codes
        :param user_id: User ID, if None, get from context
        :return: True if user has all permissions
        """
        for permission_code in permission_codes:
            if not await self.has_permission(permission_code, user_id):
                return False
        return True

    @distributed_trace()
    async def get_user_permissions(self, user_id: UUID | None = None) -> list[str]:
        """
        Get all permissions for user
        Permissions are retrieved from Redis cache only (single source of truth)
        :param user_id: User ID, if None, get from context
        :return: List of permission codes
        """
        user_context = get_user_context()

        if user_id is None:
            user_id = user_context.user_id

        if not user_id:
            return []

        # Get permissions from cache (hash keys)
        # Redis cache is the single source of truth for permissions
        key = CacheKeys(resource="permission").add_attribute(str(user_id)).build()
        permission_codes = await self._redis.hkeys(key)
        return [
            code.decode() if isinstance(code, bytes) else code
            for code in permission_codes
        ]
