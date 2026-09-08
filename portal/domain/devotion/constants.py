from enum import StrEnum


class DevotionErrorCode(StrEnum):
    DATE_NOT_SCHEDULED = "DATE_NOT_SCHEDULED"
    TRANSLATION_NOT_FOUND = "TRANSLATION_NOT_FOUND"
