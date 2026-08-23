class ApplicationError(Exception):
    """Anything else propagating from the service layer is a bug, not a handled case."""


class ValidationError(ApplicationError):
    """Cross-field domain invariants Pydantic's schema validation can't express."""


class UnknownStationError(ValidationError):
    def __init__(self, identifier: str) -> None:
        self.identifier = identifier
        super().__init__(f"Unknown station identifier: {identifier!r}")


class NonexistentLocalTimeError(ValidationError):
    """A wall-clock time that a DST spring-forward transition skips entirely."""

    def __init__(self, local_datetime_str: str, timezone_name: str) -> None:
        self.local_datetime_str = local_datetime_str
        self.timezone_name = timezone_name
        super().__init__(
            f"{local_datetime_str!r} does not exist in {timezone_name} "
            "(falls in a DST spring-forward gap)"
        )


class InvalidTimezoneError(ValidationError):
    def __init__(self, timezone_name: str) -> None:
        self.timezone_name = timezone_name
        super().__init__(f"Unknown timezone: {timezone_name!r}")


class AemetError(ApplicationError):
    """Base for failures originating from the AEMET integration."""


class AemetUnavailableError(AemetError):
    """Network/timeout/5xx/429 — retrying the same request later may succeed."""


class AemetAuthenticationError(AemetError):
    """AEMET rejected the API key (401/403) — a configuration problem, not an outage."""


class AemetResponseError(AemetError):
    """Malformed or unexpected payload shape — retrying would fail identically."""


class PersistenceError(ApplicationError):
    """The local SQLite cache could not be read from or written to."""
