import os
from datetime import datetime
from unittest.mock import patch

from src.Utils.Validators import Validator

with patch.dict(os.environ, {"VERIFICATION_TTL": "15"}):
    import src.Utils.CodeGenerator as CodeGenerator


def test_code_passes_verification():
    for _ in range(10):
        testcode, _ = CodeGenerator.generateVerificationCode()
        assert Validator.validate_verification_token(testcode)


def test_code_correct_length():
    for _ in range(10):
        testCode, _ = CodeGenerator.generateVerificationCode()
        assert len(testCode) == 6


def test_code_is_digit():
    for _ in range(10):
        testCode, _ = CodeGenerator.generateVerificationCode()
        assert testCode.isdigit()


def test_code_range():
    for _ in range(20):
        code, _ = CodeGenerator.generateVerificationCode()
        code_int = int(code)
        assert 0 <= code_int <= 999999


def test_expiration_time_returned():
    _, expiration = CodeGenerator.generateVerificationCode()
    assert isinstance(expiration, datetime)


def test_expiration_time_is_future():
    _, expiration = CodeGenerator.generateVerificationCode()
    now = CodeGenerator.getUtcNow()
    assert expiration > now
