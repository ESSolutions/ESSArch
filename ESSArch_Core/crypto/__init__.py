from cryptography.fernet import Fernet
from django.conf import settings


def generate_key():
    return Fernet.generate_key()


def encrypt(value):
    f = Fernet(settings.ENCRYPTION_KEY)
    return f.encrypt(value)


def decrypt(token):
    f = Fernet(settings.ENCRYPTION_KEY)
    return f.decrypt(token)
