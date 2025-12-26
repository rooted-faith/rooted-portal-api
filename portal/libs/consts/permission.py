"""
Permission constants
"""
from enum import Enum


class Verb(Enum):
    """Verb enum"""
    READ = "read"
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"


class Resource(Enum):
    """Resource enum"""
    # System resources
    SYSTEM_LOG = "system:log"
    SYSTEM_PERMISSION = "system:permission"
    SYSTEM_RESOURCE = "system:resource"
    SYSTEM_ROLE = "system:role"
    SYSTEM_USER = "system:user"

    # General resources


class Permission:
    """
    Permission
    usage: Permission.{resource}.{verb} can get permission code.
    E.g., Permission.SYSTEM_USER.READ = "system:user:read"
    """

    class PermissionCode:
        """Internal class for generating permission codes"""

        def __init__(self, resource_value: str):
            self._resource_value = resource_value

        @property
        def all(self):
            return f"{self._resource_value}:*"

        @property
        def read(self):
            return f"{self._resource_value}:{Verb.READ.value}"

        @property
        def create(self):
            return f"{self._resource_value}:{Verb.CREATE.value}"

        @property
        def modify(self):
            return f"{self._resource_value}:{Verb.MODIFY.value}"

        @property
        def delete(self):
            return f"{self._resource_value}:{Verb.DELETE.value}"

    # System resources
    SYSTEM_LOG = PermissionCode(Resource.SYSTEM_LOG.value)
    SYSTEM_PERMISSION = PermissionCode(Resource.SYSTEM_PERMISSION.value)
    SYSTEM_RESOURCE = PermissionCode(Resource.SYSTEM_RESOURCE.value)
    SYSTEM_ROLE = PermissionCode(Resource.SYSTEM_ROLE.value)
    SYSTEM_USER = PermissionCode(Resource.SYSTEM_USER.value)

    # General resources
