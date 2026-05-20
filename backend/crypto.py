import os
import base64
import hashlib
from cryptography.fernet import Fernet


def _get_fernet():
    secret = os.environ.get('SECRET_KEY', 'change-this-secret')
    # derive 32-byte key
    key = hashlib.sha256(secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_text(plaintext: str) -> str:
    if plaintext is None:
        return ''
    f = _get_fernet()
    token = f.encrypt(plaintext.encode())
    return token.decode()


def decrypt_text(token: str) -> str:
    if not token:
        return ''
    f = _get_fernet()
    try:
        return f.decrypt(token.encode()).decode()
    except Exception:
        return ''
