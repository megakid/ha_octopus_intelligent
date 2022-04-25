from datetime import timedelta

def to_timedelta(str_time: str) -> timedelta:
    """Convert a time string to a timedelta."""
    hours, minutes = str_time.split(":")
    return timedelta(hours=int(hours), minutes=int(minutes))

def to_time_string(td: timedelta) -> str:
    """Convert a timedelta to a HH:mm time string."""
    return f"{td.seconds // 3600:02}:{td.seconds // 60 % 60:02}"

def to_hours_after_midnight(str_time: str) -> float:
    td = to_timedelta(str_time)
    return td.seconds / 3600