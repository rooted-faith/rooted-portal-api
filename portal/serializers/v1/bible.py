"""
Bible serializers
"""
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_serializer


class BibleVersionBase(BaseModel):
    """
    Bible Version Base
    """
    id: UUID = Field(..., description="Bible version ID (UUID)")
    youversion_bible_id: str = Field(..., description="YouVersion bible_id, e.g., '1392'")
    abbreviation: str = Field(..., description="English abbreviation, e.g., 'CCBT'")
    title: str = Field(..., description="English title")
    localized_title: str = Field(..., description="Localized title, e.g., '當代譯本'")
    localized_abbreviation: Optional[str] = Field(None, description="Localized abbreviation, e.g., 'CCB'")
    language_tag: str = Field(..., description="Language tag, e.g., 'zh-Hant-TW'")
    is_active: bool = Field(..., description="Is version active")

    @field_serializer("id")
    def serialize_uuid(self, value: UUID, _info) -> str:
        """Serialize UUID to string"""
        return str(value)


class BibleVersionList(BaseModel):
    """
    Bible Version List
    """
    versions: list[BibleVersionBase] = Field(..., description="Bible versions")


class BibleBookBase(BaseModel):
    """
    Bible Book Base
    """
    id: UUID = Field(..., description="Book ID (UUID)")
    book_code: str = Field(..., description="Book code, e.g., 'GEN', 'MAT'")
    title: str = Field(..., description="Book title")
    full_title: Optional[str] = Field(None, description="Full book title")
    abbreviation: Optional[str] = Field(None, description="Book abbreviation, e.g., '創'")
    canon: str = Field(..., description="Canon type: 'old_testament' or 'new_testament'")
    sequence: float = Field(..., description="Display sort order (small to large, standard Bible book order)")
    chapter_count: int = Field(..., description="Number of chapters in this book")

    @field_serializer("id")
    def serialize_uuid(self, value: UUID, _info) -> str:
        """Serialize UUID to string"""
        return str(value)


class BibleBookList(BaseModel):
    """
    Bible Book List
    """
    old_testament: list[BibleBookBase] = Field(..., description="Old Testament books")
    new_testament: list[BibleBookBase] = Field(..., description="New Testament books")


class BibleVerseBase(BaseModel):
    """
    Bible Verse Base
    """
    verse: int = Field(..., description="Verse number")
    content: str = Field(..., description="Verse content")


class BibleChapterDetail(BaseModel):
    """
    Bible Chapter Detail
    """
    bible_version_id: UUID = Field(..., description="Bible version ID (UUID)")
    youversion_bible_id: str = Field(..., description="YouVersion bible_id")
    bible_title: str = Field(..., description="Bible version title")
    book_id: UUID = Field(..., description="Book ID (UUID)")
    book_code: str = Field(..., description="Book code")
    book_name: str = Field(..., description="Book name")
    chapter: int = Field(..., description="Chapter number")
    verses: list[BibleVerseBase] = Field(..., description="Verses")

    @field_serializer("bible_version_id", "book_id")
    def serialize_uuid(self, value: UUID, _info) -> str:
        """Serialize UUID to string"""
        return str(value)


class BibleSearchResult(BaseModel):
    """
    Bible Search Result
    """
    bible_version_id: UUID = Field(..., description="Bible version ID (UUID)")
    youversion_bible_id: str = Field(..., description="YouVersion bible_id")
    bible_title: str = Field(..., description="Bible version title")
    book_id: UUID = Field(..., description="Book ID (UUID)")
    book_code: str = Field(..., description="Book code")
    book_name: str = Field(..., description="Book name")
    chapter: int = Field(..., description="Chapter number")
    verse: int = Field(..., description="Verse number")
    content: str = Field(..., description="Verse content")
    highlight: Optional[str] = Field(None, description="Highlighted search keyword")

    @field_serializer("bible_version_id", "book_id")
    def serialize_uuid(self, value: UUID, _info) -> str:
        """Serialize UUID to string"""
        return str(value)


class BibleSearchResponse(BaseModel):
    """
    Bible Search Response
    """
    results: list[BibleSearchResult] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of results")
    limit: int = Field(..., description="Result limit")
    offset: int = Field(..., description="Result offset")

