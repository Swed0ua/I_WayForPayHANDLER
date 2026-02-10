from datetime import datetime, timedelta


def get_day_timestamp_range(days_ago: int = -1) -> tuple[int, int]:
    """
    Повертає (day_start_timestamp, day_end_timestamp) у Unix-секундах для вказаного дня.

    days_ago: -1 = вчора, -2 = два дні тому, 0 = сьогодні.
    day_start — 00:00:00 локального часу, day_end — 23:59:59 того ж дня.
    """
    today = datetime.now().date()
    target_date = today + timedelta(days=days_ago)
    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = day_start.replace(hour=23, minute=59, second=59, microsecond=999_999)
    return int(day_start.timestamp()), int(day_end.timestamp())

def format_timestamp_to_date(ts: int, fmt: str = "%d.%m.%Y") -> str:
    return datetime.fromtimestamp(ts).strftime(fmt)