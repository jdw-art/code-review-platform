from datetime import UTC, datetime, timedelta

from authlib.jose import jwt
from authlib.jose.errors import JoseError

from app.core.config import Settings


settings = Settings()


class TokenError(ValueError):
    """Raised when a token cannot be decoded or does not match the expected type."""


def issue_access_token(*, user_id: int, username: str, is_superuser: bool) -> str:
    claims = {
        "sub": str(user_id),
        "username": username,
        "is_superuser": is_superuser,
        "token_type": "access",
        "exp": datetime.now(UTC) + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode({"alg": "HS256"}, claims, settings.jwt_secret_key).decode()


def issue_refresh_token(*, user_id: int, session_jti: str) -> str:
    claims = {
        "sub": str(user_id),
        "jti": session_jti,
        "token_type": "refresh",
        "exp": datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days),
    }
    return jwt.encode({"alg": "HS256"}, claims, settings.jwt_secret_key).decode()


def decode_token(token: str, expected_token_type: str) -> dict:
    try:
        claims = jwt.decode(token, settings.jwt_secret_key)
        claims.validate()
    except JoseError as exc:
        raise TokenError("Invalid or expired token.") from exc

    token_type = claims.get("token_type")
    if token_type != expected_token_type:
        raise TokenError(f"Expected {expected_token_type} token.")

    return dict(claims)
