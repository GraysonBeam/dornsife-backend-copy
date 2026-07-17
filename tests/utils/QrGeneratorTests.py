import re

from src.Utils.QrGenerator import generate_qr_token


def test_token_is_string():
    token = generate_qr_token()
    assert isinstance(token, str)


def test_token_has_sufficient_length():
    token = generate_qr_token()

    assert len(token) >= 43


def test_token_is_url_safe():
    token = generate_qr_token()

    assert re.fullmatch(r"[A-Za-z0-9\-_]+", token)


def test_tokens_are_unique():
    tokens = {generate_qr_token() for _ in range(2000)}
    assert len(tokens) == 2000


def test_token_generation_is_not_deterministic():
    tokens = [generate_qr_token() for _ in range(10)]
    assert len(set(tokens)) == len(tokens)
