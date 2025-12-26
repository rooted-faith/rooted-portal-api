"""
Base schemas
"""
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class AccessTokenPayload(BaseModel):
    """Access token payload"""
    user_id: Optional[UUID] = None
    username: Optional[str] = None
    is_admin: bool = False
    is_superuser: bool = False

