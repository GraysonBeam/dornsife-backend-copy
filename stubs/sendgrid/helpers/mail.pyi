"""Type stubs for sendgrid.helpers.mail module."""

from typing import Any

class Mail:
    def __init__(
        self,
        from_email: str | None = None,
        to_emails: str | list[str] | None = None,
        subject: str | None = None,
        html_content: str | None = None,
    ) -> None: ...

    template_id: str
    dynamic_template_data: dict[str, Any]
