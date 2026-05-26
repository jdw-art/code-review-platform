from app.security.passwords import hash_password, verify_password


def test_passwords_are_hashed_and_verified() -> None:
    password_hash = hash_password("jdw112233")

    assert password_hash != "jdw112233"
    assert verify_password("jdw112233", password_hash) is True
    assert verify_password("wrong", password_hash) is False
