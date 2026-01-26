# utils/encryption.py
from cryptography.fernet import Fernet
import base64
from django.conf import settings

# Generate a key one time and store in settings
# key = Fernet.generate_key()

def get_cipher():
    key = settings.ENCRYPTION_KEY.encode()  # Keep this secret and safe
    return Fernet(key)

def encrypt(text):
    return get_cipher().encrypt(text.encode()).decode()

def decrypt(token):
    return get_cipher().decrypt(token.encode()).decode()
