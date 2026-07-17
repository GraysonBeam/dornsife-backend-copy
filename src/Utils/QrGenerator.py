import secrets


def generate_qr_token():
    return secrets.token_urlsafe(32)
