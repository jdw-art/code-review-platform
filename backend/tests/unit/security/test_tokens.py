import pytest

from app.security.tokens import (
    TokenError,
    decode_token,
    issue_access_token,
    issue_refresh_token,
)


def test_tokens_include_expected_claims() -> None:
    access_token = issue_access_token(
        user_id=1,
        username="admin",
        is_superuser=True,
    )
    refresh_token = issue_refresh_token(user_id=1, session_jti="jti-123")

    assert isinstance(access_token, str)
    assert isinstance(refresh_token, str)

    access_claims = decode_token(access_token, expected_token_type="access")
    refresh_claims = decode_token(refresh_token, expected_token_type="refresh")

    assert access_claims["sub"] == "1"
    assert access_claims["username"] == "admin"
    assert access_claims["is_superuser"] is True
    assert access_claims["token_type"] == "access"
    assert "exp" in access_claims

    assert refresh_claims["sub"] == "1"
    assert refresh_claims["jti"] == "jti-123"
    assert refresh_claims["token_type"] == "refresh"
    assert "exp" in refresh_claims


def test_decode_token_rejects_wrong_token_type() -> None:
    refresh_token = issue_refresh_token(user_id=1, session_jti="jti-123")

    with pytest.raises(TokenError, match="Expected access token."):
        decode_token(refresh_token, expected_token_type="access")
