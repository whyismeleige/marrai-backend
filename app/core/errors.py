class AuditError(Exception):
    """An audit failure with a message that is safe to show end users."""


class UrlSafetyError(AuditError):
    """Raised when a URL is blocked by SSRF protections."""

    def __init__(self, message: str, code: str = "blocked") -> None:
        super().__init__(message)
        self.code = code
