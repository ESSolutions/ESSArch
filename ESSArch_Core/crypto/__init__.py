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


def encrypt_remote_credentials(remote_server_string):
    user, passw = remote_server_string.split(',')[1:]
    return encrypt(','.join([user, passw]).encode('utf-8')).decode('utf-8')


def decrypt_remote_credentials(encrypted_credentials):
    return decrypt(encrypted_credentials.encode('utf-8')).decode('utf-8').split(',')
