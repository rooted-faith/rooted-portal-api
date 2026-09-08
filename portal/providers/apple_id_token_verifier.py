"""Sign in with Apple identity-token verification (ADR 0008)."""

from typing import Optional

import jwt

from portal.domain.auth.entities import AppleIdentityClaims
from portal.libs.logger import logger
from portal.libs.tracing.distributed_trace import distributed_trace

APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"


class AppleIdTokenVerifier:
    """Verify Apple RS256 tokens against Apple's published signing keys."""

    def __init__(self):
        self._jwk_client = jwt.PyJWKClient(APPLE_JWKS_URL)

    @distributed_trace()
    async def verify(self, id_token: str, audiences: list[str]) -> Optional[AppleIdentityClaims]:
        if not id_token or not audiences:
            return None
        try:
            signing_key = self._jwk_client.get_signing_key_from_jwt(id_token)
            claims = jwt.decode(id_token, signing_key.key, algorithms=["RS256"], audience=audiences, issuer=APPLE_ISSUER)
        except jwt.PyJWTError as error:
            logger.warning(f"Apple identity token verification failed: {error}")
            return None

        subject = claims.get("sub")
        audience = claims.get("aud")
        if not subject or not audience:
            return None
        email_verified = claims.get("email_verified")
        return AppleIdentityClaims(
            subject=subject, email=claims.get("email"), email_verified=email_verified is True or email_verified == "true", audience=audience
        )
