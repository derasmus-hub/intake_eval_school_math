"""
Unit tests for teacher availability and student booking features.
Run with: python tests/test_teacher_availability.py

Tests:
1. Student can list teachers
2. Student can fetch teacher availability
3. Invalid booking outside availability is rejected
4. Valid booking within availability is accepted
"""

import os
import sys
import asyncio
import aiosqlite
from datetime import datetime, timedelta

# Add project root to path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_dir)

from app.services.availability_validator import (
    expand_weekly_recurrence,
    is_booking_available,
    parse_simple_rrule
)

PASS = 0
FAIL = 0


def check(label, ok, detail=""):
    global PASS, FAIL
    tag = "[PASS]" if ok else "[FAIL]"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    extra = f"  ({detail})" if detail else ""
    print(f"  {tag} {label}{extra}")
    return ok


print("\n=== Teacher Availability & Booking Tests ===\n")

# ── 1. Test RRULE Parsing ────────────────────────────────────────────
print("=== 1. RRULE Parsing ===")

rrule1 = "RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR"
parsed1 = parse_simple_rrule(rrule1)
check("Parse valid RRULE", parsed1.get("freq") == "WEEKLY" and "MO" in parsed1.get("byday", []))

rrule2 = "INVALID"
parsed2 = parse_simple_rrule(rrule2)
check("Invalid RRULE returns empty dict", parsed2 == {})

rrule3 = None
parsed3 = parse_simple_rrule(rrule3)
check("None RRULE returns empty dict", parsed3 == {})


# ── 2. Test Recurrence Expansion ─────────────────────────────────────
print("\n=== 2. Weekly Recurrence Expansion ===")

# Test single slot (no recurrence)
start_single = "2024-01-15T09:00:00"
end_single = "2024-01-15T12:00:00"
from_date = datetime(2024, 1, 10)
to_date = datetime(2024, 1, 20)

windows_single = expand_weekly_recurrence(start_single, end_single, None, from_date, to_date)
check("Single slot (no recurrence) returns one window", len(windows_single) == 1)
check("Single slot date is correct", windows_single[0]["date"] == "2024-01-15" if windows_single else False)

# Test weekly recurrence on MO,WE,FR
start_weekly = "2024-01-15T09:00:00"  # This is a Monday
end_weekly = "2024-01-15T12:00:00"
rrule_weekly = "RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR"
from_date_weekly = datetime(2024, 1, 15)  # Monday Jan 15
to_date_weekly = datetime(2024, 1, 21)    # Sunday Jan 21

windows_weekly = expand_weekly_recurrence(start_weekly, end_weekly, rrule_weekly, from_date_weekly, to_date_weekly)
# Should have: Mon 15, Wed 17, Fri 19 = 3 windows
check("Weekly recurrence generates correct number of windows", len(windows_weekly) == 3, f"got {len(windows_weekly)}")
if len(windows_weekly) >= 3:
    check("First window is Monday", windows_weekly[0]["date"] == "2024-01-15")
    check("Second window is Wednesday", windows_weekly[1]["date"] == "2024-01-17")
    check("Third window is Friday", windows_weekly[2]["date"] == "2024-01-19")


# ── 3. Test Availability Validation ──────────────────────────────────
print("\n=== 3. Availability Validation ===")

# Mock availability slots
mock_slots = [
    {
        "start_at": "2024-01-15T09:00:00",
        "end_at": "2024-01-15T17:00:00",
        "recurrence_rule": "RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR",
        "is_available": 1
    }
]

# Test 1: Valid booking within availability (Monday 10am, 1 hour)
requested_valid = datetime(2024, 1, 15, 10, 0)  # Monday 10am
is_valid, error = is_booking_available(mock_slots, requested_valid, 60)
check("Valid booking (Mon 10am, 1hr) is accepted", is_valid, error if not is_valid else "")

# Test 2: Booking outside available hours (Monday 7am, before 9am start)
requested_too_early = datetime(2024, 1, 15, 7, 0)  # Monday 7am
is_valid_early, error_early = is_booking_available(mock_slots, requested_too_early, 60)
check("Booking before available hours is rejected", not is_valid_early, "Should be rejected")

# Test 3: Booking on unavailable day (Tuesday)
requested_wrong_day = datetime(2024, 1, 16, 10, 0)  # Tuesday 10am
is_valid_day, error_day = is_booking_available(mock_slots, requested_wrong_day, 60)
check("Booking on unavailable day is rejected", not is_valid_day, "Should be rejected")

# Test 4: Booking that extends past available hours (Wed 4:30pm, 1hr = ends at 5:30pm, but slot ends at 5pm)
requested_too_long = datetime(2024, 1, 17, 16, 30)  # Wed 4:30pm
is_valid_long, error_long = is_booking_available(mock_slots, requested_too_long, 60)
check("Booking extending past available hours is rejected", not is_valid_long, "Should be rejected")

# Test 5: No availability slots configured
is_valid_none, error_none = is_booking_available([], requested_valid, 60)
check("No availability slots returns error", not is_valid_none and "no availability" in error_none.lower())


# ── 4. Integration Test: Database Operations ─────────────────────────
print("\n=== 4. Database Integration ===")

async def test_database_operations():
    """Test creating teacher, availability, and querying."""
    # Create in-memory database
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row

    try:
        # Create schema
        await db.execute("""
            CREATE TABLE students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT,
                role TEXT NOT NULL DEFAULT 'student',
                filler TEXT DEFAULT 'student',
                current_level TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE teacher_availability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL,
                start_at TEXT NOT NULL,
                end_at TEXT NOT NULL,
                recurrence_rule TEXT,
                is_available INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES students(id)
            )
        """)
        await db.commit()

        # Insert test teacher
        cur = await db.execute(
            "INSERT INTO students (name, email, role, filler) VALUES (?, ?, 'teacher', 'teacher')",
            ("Test Teacher", "teacher@test.com")
        )
        await db.commit()
        teacher_id = cur.lastrowid
        check("Teacher created in database", teacher_id > 0)

        # Insert availability slot
        cur = await db.execute(
            """INSERT INTO teacher_availability (teacher_id, start_at, end_at, recurrence_rule)
               VALUES (?, ?, ?, ?)""",
            (teacher_id, "2024-01-15T09:00:00", "2024-01-15T17:00:00", "RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR")
        )
        await db.commit()
        slot_id = cur.lastrowid
        check("Availability slot created", slot_id > 0)

        # Query teacher by role
        cur = await db.execute("SELECT id, name FROM students WHERE role = 'teacher'")
        teachers = await cur.fetchall()
        check("Can query teachers by role", len(teachers) == 1 and teachers[0]["name"] == "Test Teacher")

        # Query availability slots
        cur = await db.execute(
            "SELECT * FROM teacher_availability WHERE teacher_id = ? AND is_available = 1",
            (teacher_id,)
        )
        slots = await cur.fetchall()
        check("Can query teacher availability", len(slots) == 1)

        # Test expanded availability using service function
        from app.services.availability_validator import get_teacher_availability_windows
        windows = await get_teacher_availability_windows(
            db,
            teacher_id,
            datetime(2024, 1, 15),
            datetime(2024, 1, 19)
        )
        check("Availability windows expansion works", len(windows) >= 2, f"got {len(windows)} windows")

    finally:
        await db.close()

# Run async test
asyncio.run(test_database_operations())


# ── 5. Edge Cases ────────────────────────────────────────────────────
print("\n=== 5. Edge Cases ===")

# Test invalid ISO datetime
windows_invalid = expand_weekly_recurrence("invalid-date", "2024-01-15T12:00:00", None, from_date, to_date)
check("Invalid ISO datetime returns empty list", len(windows_invalid) == 0)

# Test booking with 0 duration
is_valid_zero, _ = is_booking_available(mock_slots, requested_valid, 0)
check("Zero duration booking is technically valid (edge case)", is_valid_zero)

# Test booking with very long duration
is_valid_toolong, _ = is_booking_available(mock_slots, datetime(2024, 1, 15, 9, 0), 600)  # 10 hours
check("Very long booking extending past window is rejected", not is_valid_toolong)


# ── Summary ──────────────────────────────────────────────────────────
print(f"\n=== Summary ===")
print(f"Total: {PASS + FAIL} tests")
print(f"Passed: {PASS}")
print(f"Failed: {FAIL}")

if FAIL > 0:
    sys.exit(1)
else:
    print("\nAll tests passed!")
    sys.exit(0)
