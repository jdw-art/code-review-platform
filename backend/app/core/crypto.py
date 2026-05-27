from cryptography.fernet import Fernet


class SecretCipher:
    """负责对 API Key、Webhook Secret 等可逆敏感字段做加解密。"""

    def __init__(self, raw_key: str) -> None:
        self.fernet = Fernet(raw_key.encode("utf-8"))

    def encrypt_text(self, value: str) -> str:
        return self.fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt_text(self, value: str) -> str:
        return self.fernet.decrypt(value.encode("utf-8")).decode("utf-8")
