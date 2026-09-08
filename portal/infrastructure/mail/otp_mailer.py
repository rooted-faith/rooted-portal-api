"""
Deliver one-time passcodes (log when SMTP is not wired).
"""

import logging
from typing import Optional

from portal.config import settings

logger = logging.getLogger(__name__)


class OtpMailer:
    """Out-of-band delivery of a one-time passcode, in the caller-resolved locale (ADR 0009)."""

    async def send_otp(self, email: str, code: str, *, locale: Optional[str]) -> None:
        # SMTP settings are not yet part of Configuration; log so local/dev
        # verify flows can still capture codes from the mailer stub in tests.
        logger.info("OTP issued for %s in locale %s (expires in %s minutes)", email, locale, settings.OTP_CODE_EXPIRE_MINUTES)
        if settings.IS_DEV:
            logger.debug("OTP code for %s: %s", email, code)
