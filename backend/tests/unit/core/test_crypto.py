from cryptography.fernet import Fernet

from app.core.crypto import SecretCipher


def test_secret_cipher_round_trip() -> None:
    cipher = SecretCipher(Fernet.generate_key().decode("utf-8"))
    encrypted = cipher.encrypt_text("top-secret")

    assert encrypted != "top-secret"
    assert cipher.decrypt_text(encrypted) == "top-secret"
