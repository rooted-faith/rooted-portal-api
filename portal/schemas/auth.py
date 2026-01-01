"""
Auth schemas
"""
from pydantic import BaseModel


class TokenPayload(BaseModel):
    """Token payload"""
    uid: str | None = None
    email: str | None = None
    phone_number: str | None = None
    verified: bool = False

