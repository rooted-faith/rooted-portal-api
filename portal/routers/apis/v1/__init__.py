"""
v1 API router
"""
from fastapi import APIRouter

from .bible import router as bible_router

router = APIRouter()

router.include_router(bible_router, prefix="/bible", tags=["Bible"])

