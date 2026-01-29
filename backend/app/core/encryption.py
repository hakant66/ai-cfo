import base64
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings


def _load_key() -> bytes:
    key = settings.encryption_key
    if not key:
        raise ValueError("ENCRYPTION_KEY is not set")
    try:
        return key.encode("utf-8")
    except Exception as exc:
        raise ValueError("Invalid ENCRYPTION_KEY") from exc


def encrypt_value(value: str) -> str:
    fernet = Fernet(_load_key())
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(value: str) -> str:
    fernet = Fernet(_load_key())
    try:
        return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Invalid encryption token") from exc
