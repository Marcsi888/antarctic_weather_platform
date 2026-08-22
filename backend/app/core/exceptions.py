class ApplicationError(Exception):
    """Anything else propagating from the service layer is a bug, not a handled case."""


class ValidationError(ApplicationError):
    """Cross-field domain invariants Pydantic's schema validation can't express."""


class UnknownStationError(ValidationError):
    def __init__(self, identifier: str) -> None:
        self.identifier = identifier
        super().__init__(f"Unknown station identifier: {identifier!r}")


class AemetError(ApplicationError):
    """Base for failures originating from the AEMET integration."""


class AemetUnavailableError(AemetError):
    """Network/timeout/5xx/429 — retrying the same request later may succeed."""


class AemetResponseError(AemetError):
    """Malformed or unexpected payload shape — retrying would fail identically."""


class PersistenceError(ApplicationError):
    """The local SQLite cache could not be read from or written to."""
