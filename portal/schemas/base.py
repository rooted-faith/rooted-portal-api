"""
Base schemas
"""
from uuid import UUID

from pydantic import BaseModel


class AccessTokenPayload(BaseModel):
    """Access token payload"""
    user_id: UUID | None = None
    username: str | None = None
    is_admin: bool = False
    is_superuser: bool = False

