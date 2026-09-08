from unittest.mock import Mock

import jwt
import pytest

from portal.providers.apple_id_token_verifier import APPLE_ISSUER, AppleIdTokenVerifier


@pytest.mark.asyncio
async def test_verifies_signature_issuer_audience_and_expiry(monkeypatch: pytest.MonkeyPatch):
    verifier = AppleIdTokenVerifier()
    verifier._jwk_client.get_signing_key_from_jwt = Mock(return_value=Mock(key="public-key"))
    decode = Mock(return_value={"sub": "apple-sub", "email": "jay@example.com", "email_verified": "true", "aud": "com.rooted.app"})
    monkeypatch.setattr(jwt, "decode", decode)

    claims = await verifier.verify("identity-token", ["com.rooted.app"])

    assert claims is not None
    assert claims.email_verified is True
    decode.assert_called_once_with("identity-token", "public-key", algorithms=["RS256"], audience=["com.rooted.app"], issuer=APPLE_ISSUER)


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [jwt.InvalidSignatureError(), jwt.InvalidIssuerError(), jwt.InvalidAudienceError(), jwt.ExpiredSignatureError()])
async def test_invalid_signature_issuer_audience_or_expiry_is_rejected(monkeypatch: pytest.MonkeyPatch, error: jwt.PyJWTError):
    verifier = AppleIdTokenVerifier()
    verifier._jwk_client.get_signing_key_from_jwt = Mock(return_value=Mock(key="public-key"))
    monkeypatch.setattr(jwt, "decode", Mock(side_effect=error))

    assert await verifier.verify("invalid-token", ["com.rooted.app"]) is None
