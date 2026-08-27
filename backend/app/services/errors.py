class UpstreamServiceError(Exception):
    """Raised when an external service (GitHub, Groq) fails in a categorizable way.

    Carries enough structure for callers to return a machine-readable error to the
    frontend instead of a raw exception message or a silently-faked result.
    """

    def __init__(self, service: str, error_type: str, message: str, retryable: bool, status_code: int = 502):
        self.service = service
        self.error_type = error_type
        self.message = message
        self.retryable = retryable
        self.status_code = status_code
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "error": self.error_type,
            "service": self.service,
            "retryable": self.retryable,
            "message": self.message,
        }


# Canonical error_type values used across GitHub/Groq integrations.
AUTH_FAILURE = "AUTH_FAILURE"
RATE_LIMIT = "RATE_LIMIT"
NOT_FOUND = "NOT_FOUND"
FORBIDDEN = "FORBIDDEN"
TIMEOUT = "TIMEOUT"
MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
UPSTREAM_SERVICE_ERROR = "UPSTREAM_SERVICE_ERROR"
