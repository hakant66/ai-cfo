import base64
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from app.core.config import settings


def _normalize_pem(value: str) -> bytes:
    return value.replace("\\n", "\n").encode("utf-8")


def _load_public_key():
    if not settings.wise_public_key:
        raise ValueError("WISE_PUBLIC_KEY is not set")
    return serialization.load_pem_public_key(_normalize_pem(settings.wise_public_key))


def _load_private_key():
    if not settings.wise_private_key:
        raise ValueError("WISE_PRIVATE_KEY is not set")
    return serialization.load_pem_private_key(_normalize_pem(settings.wise_private_key), password=None)


def wise_encrypt(value: str) -> str:
    public_key = _load_public_key()
    ciphertext = public_key.encrypt(
        value.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.urlsafe_b64encode(ciphertext).decode("utf-8")


def wise_decrypt(value: str) -> str:
    private_key = _load_private_key()
    ciphertext = base64.urlsafe_b64decode(value.encode("utf-8"))
    plaintext = private_key.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return plaintext.decode("utf-8")
