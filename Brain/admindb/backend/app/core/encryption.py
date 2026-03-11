from cryptography.fernet import Fernet
from ..config import settings


def get_fernet() -> Fernet:
    key = settings.FERNET_KEY
    if not key:
        raise ValueError(
            "FERNET_KEY is not set. Generate with: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_password(plaintext: str) -> str:
    if not plaintext:
        return ""
    return get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_password(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        return get_fernet().decrypt(ciphertext.encode()).decode()
    except Exception:
        return ""
