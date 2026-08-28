import re
from datetime import datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.exceptions import InvalidTimezoneError, NonexistentLocalTimeError

OUTPUT_TIMEZONE = ZoneInfo("Europe/Madrid")

# The AEMET request format is documented as AAAA-MM-DDTHH:MM:SSUTC, a
# literal "UTC" suffix, not an ISO 8601 offset or "Z". Verified against a
# live AEMET response during integration testing; this is not an assumption.
AEMET_REQUEST_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SUTC"

# Matches a UTC offset like "+02:00" or "-05:30", per the challenge spec's
# alternative to naming a timezone. A fixed offset carries no DST rule at all
# it is not "Europe/Madrid in July", it is exactly this many hours
# from UTC on every date the caller supplies, which is a deliberate
# simplification the caller opts into by using this form instead of an
# IANA name.
_UTC_OFFSET_PATTERN = re.compile(r"^([+-])(\d{2}):(\d{2})$")


def resolve_timezone(name: str) -> tzinfo:
    offset_match = _UTC_OFFSET_PATTERN.match(name)
    if offset_match:
        sign, hours, minutes = offset_match.groups()
        delta = timedelta(hours=int(hours), minutes=int(minutes))
        return timezone(-delta if sign == "-" else delta)

    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise InvalidTimezoneError(name) from exc


def to_utc_instant(local_dt: datetime, tz: tzinfo) -> datetime:
    """Resolve naive wall-clock `local_dt` in `tz` to a UTC instant.

    Ambiguous (fall-back) times resolve to their first occurrence.
    Nonexistent (spring-forward) times raise NonexistentLocalTimeError.
    """
    if local_dt.tzinfo is not None:
        raise ValueError("to_utc_instant expects a naive datetime; tz is supplied separately")

    aware = local_dt.replace(tzinfo=tz, fold=0)

    # A nonexistent local time still constructs without error (Python does
    # not validate this), but converting to UTC and back reproduces a
    # different wall-clock time than what was given, because the offset
    # zoneinfo picks for a skipped hour belongs to the *following* period.
    round_tripped = aware.astimezone(ZoneInfo("UTC")).astimezone(tz)
    if round_tripped.replace(tzinfo=None) != local_dt:
        raise NonexistentLocalTimeError(local_dt.isoformat(), str(tz))

    return aware.astimezone(ZoneInfo("UTC"))


def to_output_representation(instant: datetime) -> datetime:
    """Convert a UTC (or any aware) instant to Europe/Madrid with explicit offset.

    The output requirement is unconditional: every returned datetime is
    Europe/Madrid, regardless of what timezone the request was made in.
    """
    if instant.tzinfo is None:
        raise ValueError("to_output_representation expects an aware datetime")
    return instant.astimezone(OUTPUT_TIMEZONE)


def format_for_aemet_request(instant_utc: datetime) -> str:
    if instant_utc.tzinfo is None:
        raise ValueError("format_for_aemet_request expects an aware datetime")
    return instant_utc.astimezone(ZoneInfo("UTC")).strftime(AEMET_REQUEST_DATETIME_FORMAT)
