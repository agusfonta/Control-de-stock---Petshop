"""Funciones de fecha/hora del dominio.

La base actual guarda DateTime sin zona. Para no cambiar el esquema todavía,
stored UTC se mantiene como datetime naive y las entradas del usuario se
interpretan en la zona configurada y se convierten a UTC naive.
"""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.config import settings

LOCAL_TZ = ZoneInfo(settings.app_timezone)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def local_today() -> date:
    return datetime.now(LOCAL_TZ).date()


def local_day_bounds_utc(day: date) -> tuple[datetime, datetime]:
    start_local = datetime.combine(day, datetime.min.time(), tzinfo=LOCAL_TZ)
    end_local = start_local + timedelta(days=1)
    return (
        start_local.astimezone(timezone.utc).replace(tzinfo=None),
        end_local.astimezone(timezone.utc).replace(tzinfo=None),
    )


def local_datetime_to_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=LOCAL_TZ)
    return value.astimezone(timezone.utc).replace(tzinfo=None)
