import os
import secrets
from datetime import UTC, datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

_verification_ttl = os.getenv("VERIFICATION_TTL")
if not _verification_ttl or not _verification_ttl.isdigit():
    raise ValueError("VERIFICATION_TTL must be a number that represents minutes.")
VERIFICATION_TTL: str = _verification_ttl


def generateVerificationCode():
    code = secrets.randbelow(1000000)
    codeStr = str(code).zfill(6)

    expiration_time = getUtcNow() + timedelta(minutes=int(VERIFICATION_TTL))

    return codeStr, expiration_time


def getUtcNow():
    return datetime.now(UTC)
