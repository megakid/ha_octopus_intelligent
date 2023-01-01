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


def merge_and_sort_time_ranges(date_ranges: list) -> list:
    # Sort the time ranges by start time
    date_ranges.sort(key=lambda r: r["start"])
    
    # initialize the list of merged date ranges
    merged_date_ranges = []
    
    # initialize the current date range with the first date range in the list
    current_date_range = date_ranges[0]
    
    # iterate through the rest of the date ranges
    for i in range(1, len(date_ranges)):
        # if the current date range overlaps with the next date range, update the end date of the current date range
        if current_date_range["end"] >= date_ranges[i]["start"]:
            current_date_range["end"] = max(current_date_range["end"], date_ranges[i]["end"])
        # if the current date range does not overlap with the next date range, add the current date range to the list of merged date ranges and update the current date range
        else:
            merged_date_ranges.append(current_date_range)
            current_date_range = date_ranges[i]
    
    # add the final date range to the list of merged date ranges
    merged_date_ranges.append(current_date_range)
    return merged_date_ranges
