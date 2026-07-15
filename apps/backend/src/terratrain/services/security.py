from cryptography.fernet import Fernet

from terratrain.config import get_settings


def _get_fernet() -> Fernet:
    settings = get_settings()
    return Fernet(settings.encryption_key.encode())


def encrypt_value(value: str) -> str:
    """Encrypt a plaintext string using the configured Fernet key."""
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt_value(token: str) -> str:
    """Decrypt a Fernet-encrypted token back to plaintext."""
    return _get_fernet().decrypt(token.encode()).decode()
