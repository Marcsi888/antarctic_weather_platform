from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.core.exceptions import InvalidTimezoneError, NonexistentLocalTimeError
from app.domain.time import (
    format_for_aemet_request,
    resolve_timezone,
    to_output_representation,
    to_utc_instant,
)

MADRID = ZoneInfo("Europe/Madrid")

# Verified empirically against Python's own zoneinfo (IANA tz database) for
# 2026, not assumed: spring-forward 2026-03-29 (02:00 skipped -> 03:00),
# fall-back 2026-10-25 (02:00-02:59 occurs twice).


def test_resolve_timezone_valid_name() -> None:
    tz = resolve_timezone("Europe/Madrid")

    assert str(tz) == "Europe/Madrid"


def test_resolve_timezone_invalid_name_raises() -> None:
    with pytest.raises(InvalidTimezoneError):
        resolve_timezone("Not/A_Real_Zone")


def test_resolve_timezone_positive_utc_offset() -> None:
    tz = resolve_timezone("+02:00")

    assert datetime(2026, 1, 1, tzinfo=tz).utcoffset() == timedelta(hours=2)


def test_resolve_timezone_negative_utc_offset() -> None:
    tz = resolve_timezone("-05:30")

    assert datetime(2026, 1, 1, tzinfo=tz).utcoffset() == timedelta(hours=-5, minutes=-30)


def test_resolve_timezone_fixed_offset_has_no_dst_regardless_of_date() -> None:
    # Unlike Europe/Madrid, a fixed offset is the same value in January
    # and July: this is the point of offering it as an alternative to an
    # IANA name, per the challenge spec.
    tz = resolve_timezone("+02:00")

    winter_offset = datetime(2026, 1, 15, tzinfo=tz).utcoffset()
    summer_offset = datetime(2026, 7, 15, tzinfo=tz).utcoffset()

    assert winter_offset == summer_offset == timedelta(hours=2)


def test_to_utc_instant_with_fixed_offset_timezone() -> None:
    tz = resolve_timezone("+02:00")
    local = datetime(2026, 1, 15, 14, 0, 0)

    instant = to_utc_instant(local, tz)

    assert instant == datetime(2026, 1, 15, 12, 0, 0, tzinfo=ZoneInfo("UTC"))


def test_to_utc_instant_ordinary_winter_time() -> None:
    # 2026-01-15 14:00 Madrid is winter (+01:00), per the brief's own example.
    local = datetime(2026, 1, 15, 14, 0, 0)

    instant = to_utc_instant(local, MADRID)

    assert instant == datetime(2026, 1, 15, 13, 0, 0, tzinfo=ZoneInfo("UTC"))


def test_to_utc_instant_ordinary_summer_time() -> None:
    # 2026-07-15 14:00 Madrid is summer (+02:00), per the brief's own example.
    local = datetime(2026, 7, 15, 14, 0, 0)

    instant = to_utc_instant(local, MADRID)

    assert instant == datetime(2026, 7, 15, 12, 0, 0, tzinfo=ZoneInfo("UTC"))


def test_to_utc_instant_rejects_aware_input() -> None:
    aware = datetime(2026, 1, 15, 14, 0, 0, tzinfo=MADRID)

    with pytest.raises(ValueError, match="naive"):
        to_utc_instant(aware, MADRID)


@pytest.mark.parametrize("skipped_minute", [0, 1, 30, 59])
def test_to_utc_instant_nonexistent_spring_forward_time_raises(skipped_minute: int) -> None:
    # 2026-03-29 02:00-02:59 does not exist on the Madrid wall clock.
    local = datetime(2026, 3, 29, 2, skipped_minute)

    with pytest.raises(NonexistentLocalTimeError):
        to_utc_instant(local, MADRID)


def test_to_utc_instant_just_before_spring_forward_gap_is_valid() -> None:
    local = datetime(2026, 3, 29, 1, 59, 0)

    instant = to_utc_instant(local, MADRID)

    assert instant == datetime(2026, 3, 29, 0, 59, 0, tzinfo=ZoneInfo("UTC"))


def test_to_utc_instant_just_after_spring_forward_gap_is_valid() -> None:
    local = datetime(2026, 3, 29, 3, 0, 0)

    instant = to_utc_instant(local, MADRID)

    assert instant == datetime(2026, 3, 29, 1, 0, 0, tzinfo=ZoneInfo("UTC"))


def test_to_utc_instant_ambiguous_fall_back_time_resolves_to_first_occurrence() -> None:
    # 2026-10-25 02:30 Madrid occurs twice: first at +02:00 (summer, still
    # DST), then again at +01:00 (winter). We document resolving to the
    # first (pre-transition) occurrence rather than relying on Python's
    # implicit fold=0 default.
    local = datetime(2026, 10, 25, 2, 30, 0)

    instant = to_utc_instant(local, MADRID)

    assert instant == datetime(2026, 10, 25, 0, 30, 0, tzinfo=ZoneInfo("UTC"))


def test_to_output_representation_winter_has_plus_one_offset() -> None:
    utc_instant = datetime(2026, 1, 15, 13, 0, 0, tzinfo=ZoneInfo("UTC"))

    result = to_output_representation(utc_instant)

    assert result.isoformat() == "2026-01-15T14:00:00+01:00"


def test_to_output_representation_summer_has_plus_two_offset() -> None:
    utc_instant = datetime(2026, 7, 15, 12, 0, 0, tzinfo=ZoneInfo("UTC"))

    result = to_output_representation(utc_instant)

    assert result.isoformat() == "2026-07-15T14:00:00+02:00"


def test_to_output_representation_rejects_naive_input() -> None:
    with pytest.raises(ValueError, match="aware"):
        to_output_representation(datetime(2026, 1, 15, 13, 0, 0))


def test_format_for_aemet_request_uses_documented_utc_suffix() -> None:
    utc_instant = datetime(2026, 1, 15, 13, 0, 0, tzinfo=ZoneInfo("UTC"))

    formatted = format_for_aemet_request(utc_instant)

    assert formatted == "2026-01-15T13:00:00UTC"


def test_format_for_aemet_request_converts_non_utc_input_to_utc_first() -> None:
    madrid_instant = datetime(2026, 1, 15, 14, 0, 0, tzinfo=MADRID)

    formatted = format_for_aemet_request(madrid_instant)

    assert formatted == "2026-01-15T13:00:00UTC"


def test_unspecified_timezone_default_matches_documented_spillover_example() -> None:
    # Regression test for the Phase 0 worked example: a user typing "all of
    # January 15th" with Europe/Madrid as the default input timezone should
    # see the full Madrid calendar day reflected in the output, not spill
    # into January 16th the way a UTC default would.
    start_local = datetime(2026, 1, 15, 0, 0, 0)
    end_local = datetime(2026, 1, 15, 23, 59, 59)

    start_instant = to_utc_instant(start_local, MADRID)
    end_instant = to_utc_instant(end_local, MADRID)

    start_output = to_output_representation(start_instant)
    end_output = to_output_representation(end_instant)

    assert start_output.date().isoformat() == "2026-01-15"
    assert end_output.date().isoformat() == "2026-01-15"
