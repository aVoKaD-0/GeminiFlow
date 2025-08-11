from cryptography.fernet import Fernet
import config
import base64
import logging

logger = logging.getLogger(__name__)

def get_cipher():
    """Get Fernet cipher instance"""
    if not config.ENCRYPTION_KEY:
        raise ValueError("ENCRYPTION_KEY не установлен в переменных окружения")
    
    # Ensure key is properly formatted
    key = config.ENCRYPTION_KEY.encode() if isinstance(config.ENCRYPTION_KEY, str) else config.ENCRYPTION_KEY
    if len(key) != 44:  # Base64 encoded 32-byte key
        # If it's not a proper Fernet key, generate one from the string
        key = base64.urlsafe_b64encode(key[:32].ljust(32, b'0'))
    
    return Fernet(key)

def encrypt_api_key(api_key: str) -> str:
    """Encrypt API key"""
    cipher = get_cipher()
    encrypted = cipher.encrypt(api_key.encode())
    return encrypted.decode()

def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt API key"""
    cipher = get_cipher()
    decrypted = cipher.decrypt(encrypted_key.encode())
    return decrypted.decode()