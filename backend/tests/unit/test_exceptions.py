import pytest

from app.core.exceptions import (
    AemetError,
    AemetResponseError,
    AemetUnavailableError,
    ApplicationError,
    PersistenceError,
    UnknownStationError,
    ValidationError,
)


@pytest.mark.parametrize(
    ("exception_type", "base_type"),
    [
        (ValidationError, ApplicationError),
        (UnknownStationError, ValidationError),
        (AemetError, ApplicationError),
        (AemetUnavailableError, AemetError),
        (AemetResponseError, AemetError),
        (PersistenceError, ApplicationError),
    ],
)
def test_exception_hierarchy(
    exception_type: type[Exception], base_type: type[Exception]
) -> None:
    assert issubclass(exception_type, base_type)


def test_unknown_station_error_carries_identifier() -> None:
    error = UnknownStationError("99999")

    assert error.identifier == "99999"
    assert "99999" in str(error)


def test_aemet_subclasses_are_distinguishable() -> None:
    # A caller catching AemetUnavailableError specifically (e.g. to decide
    # whether a retry is worthwhile) must not also catch AemetResponseError.
    with pytest.raises(AemetError):
        try:
            raise AemetResponseError("malformed payload")
        except AemetUnavailableError:
            pytest.fail("AemetResponseError must not be caught as AemetUnavailableError")
