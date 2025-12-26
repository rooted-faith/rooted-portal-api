"""
Auth schemas
"""
from typing import Optional
from pydantic import BaseModel


class TokenPayload(BaseModel):
    """Token payload"""
    uid: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    verified: bool = False

