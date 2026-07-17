"""Type stubs for sendgrid package."""

from typing import Any

class Response:
    status_code: int
    body: str
    headers: dict[str, str]

class SendGridAPIClient:
    def __init__(self, api_key: str) -> None: ...
    def send(self, message: Any) -> Response: ...
