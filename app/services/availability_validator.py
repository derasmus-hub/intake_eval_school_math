"""
Availability validation service for teacher scheduling.

Provides functions to:
- Expand recurring availability slots into concrete time windows
- Validate if a requested booking falls within teacher availability
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import re


def parse_simple_rrule(rrule: str) -> Dict[str, Any]:
    """Parse simple RRULE strings (WEEKLY recurrence only).

    Example: "RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR"
    Returns: {"freq": "WEEKLY", "byday": ["MO", "WE", "FR"]}

    Returns empty dict if unparseable.
    """
    if not rrule or not rrule.startswith("RRULE:"):
        return {}

    result = {}
    parts = rrule.replace("RRULE:", "").split(";")
    for part in parts:
        if "=" in part:
            key, value = part.split("=", 1)
            if key == "FREQ":
                result["freq"] = value
            elif key == "BYDAY":
                result["byday"] = value.split(",")

    return result


def expand_weekly_recurrence(
    start_at: str,
    end_at: str,
    recurrence_rule: Optional[str],
    from_date: datetime,
    to_date: datetime
) -> List[Dict[str, str]]:
    """Expand a weekly recurring slot into concrete occurrences within date range.

    Args:
        start_at: ISO datetime string (first occurrence)
        end_at: ISO datetime string (first occurrence)
        recurrence_rule: RRULE string or None
        from_date: Start of date range to expand
        to_date: End of date range to expand

    Returns:
        List of {"date": "YYYY-MM-DD", "start_time": "HH:MM", "end_time": "HH:MM"}
    """
    slots = []

    # Parse base slot
    try:
        start_dt = datetime.fromisoformat(start_at.replace("Z", "+00:00").replace("+00:00", ""))
        end_dt = datetime.fromisoformat(end_at.replace("Z", "+00:00").replace("+00:00", ""))
    except (ValueError, AttributeError):
        return []

    # If no recurrence, just return single slot if it's in range
    if not recurrence_rule:
        if from_date.date() <= start_dt.date() <= to_date.date():
            slots.append({
                "date": start_dt.date().isoformat(),
                "start_time": start_dt.strftime("%H:%M"),
                "end_time": end_dt.strftime("%H:%M"),
            })
        return slots

    # Parse recurrence rule
    rrule_data = parse_simple_rrule(recurrence_rule)
    if rrule_data.get("freq") != "WEEKLY":
        # Unsupported recurrence type, return single occurrence
        if from_date.date() <= start_dt.date() <= to_date.date():
            slots.append({
                "date": start_dt.date().isoformat(),
                "start_time": start_dt.strftime("%H:%M"),
                "end_time": end_dt.strftime("%H:%M"),
            })
        return slots

    # Map day codes to weekday numbers (0=Monday, 6=Sunday)
    day_map = {
        "MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6
    }

    # Get target weekdays
    target_days = [day_map[d] for d in rrule_data.get("byday", []) if d in day_map]
    if not target_days:
        # No valid days specified
        return slots

    # Calculate duration
    duration = end_dt - start_dt

    # Iterate through each day in range
    current_date = from_date.date()
    while current_date <= to_date.date():
        if current_date.weekday() in target_days:
            # Create slot for this day with same time as original slot
            slot_start = datetime.combine(current_date, start_dt.time())
            slot_end = slot_start + duration
            slots.append({
                "date": current_date.isoformat(),
                "start_time": slot_start.strftime("%H:%M"),
                "end_time": slot_end.strftime("%H:%M"),
            })
        current_date += timedelta(days=1)

    return slots


def is_booking_available(
    teacher_availability_slots: List[Dict[str, Any]],
    requested_datetime: datetime,
    duration_minutes: int
) -> tuple[bool, Optional[str]]:
    """Check if a booking request falls within teacher's available windows.

    Args:
        teacher_availability_slots: List of raw DB rows from teacher_availability table
            Each row has: start_at, end_at, recurrence_rule, is_available
        requested_datetime: Requested start datetime
        duration_minutes: Requested duration in minutes

    Returns:
        (is_available: bool, error_message: Optional[str])
    """
    if not teacher_availability_slots:
        return False, "Teacher has no availability configured"

    requested_end = requested_datetime + timedelta(minutes=duration_minutes)

    # Expand all slots into a date range covering the requested time
    # (we only need to check the specific requested date)
    from_date = requested_datetime - timedelta(days=1)
    to_date = requested_datetime + timedelta(days=1)

    available_windows = []
    for slot in teacher_availability_slots:
        if slot.get("is_available") != 1:
            continue

        expanded = expand_weekly_recurrence(
            start_at=slot["start_at"],
            end_at=slot["end_at"],
            recurrence_rule=slot.get("recurrence_rule"),
            from_date=from_date,
            to_date=to_date
        )
        available_windows.extend(expanded)

    # Check if requested time falls within any available window
    for window in available_windows:
        try:
            window_start = datetime.fromisoformat(f"{window['date']}T{window['start_time']}")
            window_end = datetime.fromisoformat(f"{window['date']}T{window['end_time']}")

            # Check if requested booking fits completely within this window
            if window_start <= requested_datetime and requested_end <= window_end:
                return True, None
        except (ValueError, KeyError):
            continue

    return False, f"Requested time does not fall within teacher's available hours"


async def get_teacher_availability_windows(
    db,
    teacher_id: int,
    from_date: datetime,
    to_date: datetime
) -> List[Dict[str, str]]:
    """Fetch and expand teacher availability into concrete time windows.

    Args:
        db: Database connection
        teacher_id: Teacher's ID
        from_date: Start date for expansion
        to_date: End date for expansion

    Returns:
        List of {"date": "YYYY-MM-DD", "start_time": "HH:MM", "end_time": "HH:MM"}
        sorted by date and time
    """
    cursor = await db.execute(
        """SELECT start_at, end_at, recurrence_rule, is_available
           FROM teacher_availability
           WHERE teacher_id = ? AND is_available = 1
           ORDER BY start_at""",
        (teacher_id,)
    )
    slots = await cursor.fetchall()

    all_windows = []
    for slot in slots:
        expanded = expand_weekly_recurrence(
            start_at=slot["start_at"],
            end_at=slot["end_at"],
            recurrence_rule=slot["recurrence_rule"],
            from_date=from_date,
            to_date=to_date
        )
        all_windows.extend(expanded)

    # Sort by date and start_time
    all_windows.sort(key=lambda w: (w["date"], w["start_time"]))

    return all_windows
