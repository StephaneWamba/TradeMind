"""Simple encryption utility for API keys (using Fernet symmetric encryption)."""

import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings

# Use a fixed salt for deterministic encryption (in production, store securely)
_SALT = b"trademind_salt_v1"  # In production, use environment variable


def _get_encryption_key() -> bytes:
    """Get encryption key from environment or generate from app secret."""
    # Use a secret key from environment, or derive from app name
    secret = os.getenv("ENCRYPTION_SECRET", settings.APP_NAME)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
    return key


_fernet = Fernet(_get_encryption_key())


def encrypt(plaintext: str) -> str:
    """Encrypt a string."""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a string."""
    return _fernet.decrypt(ciphertext.encode()).decode()


