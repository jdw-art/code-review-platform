from app.security.tokens import issue_access_token, issue_refresh_token


def test_tokens_include_expected_claims() -> None:
    access_token = issue_access_token(
        user_id=1,
        username="admin",
        is_superuser=True,
    )
    refresh_token = issue_refresh_token(user_id=1, session_jti="jti-123")

    assert isinstance(access_token, str)
    assert isinstance(refresh_token, str)
