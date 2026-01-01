"""
Enums for the application
"""

from enum import Enum, IntEnum


class AccessTokenAudType(Enum):
    """
    Access token audience type
    """

    ADMIN = "admin"
    APP = "app"


class AuthProvider(Enum):
    """
    Third-party authentication provider
    """


class Gender(IntEnum):
    """
    Gender
    """

    UNKNOWN = 0
    MALE = 1
    FEMALE = 2
    OTHER = 3


class ResourceType(IntEnum):
    """
    Resource type
    """

    SYSTEM = 0
    GENERAL = 1
