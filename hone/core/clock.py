from __future__ import annotations

from datetime import UTC, date, datetime

ISO_UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def to_iso_utc(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime(ISO_UTC_FORMAT)


def parse_iso_utc(text: str) -> datetime:
    return datetime.fromisoformat(text).astimezone(UTC)


def local_date_of(moment: datetime) -> date:
    return moment.astimezone().date()


def local_today() -> date:
    return local_date_of(utc_now())
