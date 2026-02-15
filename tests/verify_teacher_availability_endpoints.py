"""
Quick verification script for teacher availability endpoints.
This script verifies that the new endpoints are registered and importable.

Run with: python tests/verify_teacher_availability_endpoints.py
"""

import sys
import os

# Add project to path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_dir)

print("=== Teacher Availability Endpoints Verification ===\n")

# 1. Verify imports
print("1. Verifying imports...")
try:
    from app.routes.scheduling import router
    from app.services.availability_validator import (
        parse_simple_rrule,
        expand_weekly_recurrence,
        is_booking_available,
        get_teacher_availability_windows
    )
    print("   [PASS] All imports successful")
except ImportError as e:
    print(f"   [FAIL] Import error: {e}")
    sys.exit(1)

# 2. Verify router has new endpoints
print("\n2. Verifying router endpoints...")
routes = [route.path for route in router.routes]
expected_routes = [
    "/api/students/teachers",
    "/api/students/teachers/{teacher_id}/availability",
    "/api/student/me/sessions/request"
]

for route in expected_routes:
    if any(route in r for r in routes):
        print(f"   [PASS] Route registered: {route}")
    else:
        print(f"   [FAIL] Route NOT found: {route}")
        print(f"   Available routes: {routes}")
        sys.exit(1)

# 3. Verify SessionRequest model has teacher_id field
print("\n3. Verifying SessionRequest model...")
try:
    from app.routes.scheduling import SessionRequest
    from pydantic import TypeAdapter

    # Test that teacher_id field is accepted
    test_data = {
        "scheduled_at": "2024-01-15T10:00:00",
        "duration_min": 60,
        "notes": "Test",
        "teacher_id": 1
    }
    request = SessionRequest(**test_data)
    assert request.teacher_id == 1
    print("   [PASS] SessionRequest accepts teacher_id field")

    # Test that teacher_id is optional
    test_data_no_teacher = {
        "scheduled_at": "2024-01-15T10:00:00",
        "duration_min": 60
    }
    request_no_teacher = SessionRequest(**test_data_no_teacher)
    assert request_no_teacher.teacher_id is None
    print("   [PASS] teacher_id is optional (backwards compatible)")

except Exception as e:
    print(f"   [FAIL] SessionRequest model error: {e}")
    sys.exit(1)

# 4. Verify availability validator functions work
print("\n4. Verifying availability validator functions...")
try:
    # Test RRULE parsing
    rrule = "RRULE:FREQ=WEEKLY;BYDAY=MO,WE"
    parsed = parse_simple_rrule(rrule)
    assert parsed["freq"] == "WEEKLY"
    assert "MO" in parsed["byday"]
    print("   [PASS] parse_simple_rrule works")

    # Test recurrence expansion (basic smoke test)
    from datetime import datetime
    windows = expand_weekly_recurrence(
        "2024-01-15T09:00:00",
        "2024-01-15T12:00:00",
        "RRULE:FREQ=WEEKLY;BYDAY=MO",
        datetime(2024, 1, 15),
        datetime(2024, 1, 22)
    )
    assert len(windows) > 0
    print("   [PASS] expand_weekly_recurrence works")

    # Test availability validation
    mock_slots = [{
        "start_at": "2024-01-15T09:00:00",
        "end_at": "2024-01-15T17:00:00",
        "recurrence_rule": None,
        "is_available": 1
    }]
    is_valid, _ = is_booking_available(
        mock_slots,
        datetime(2024, 1, 15, 10, 0),
        60
    )
    assert is_valid is True
    print("   [PASS] is_booking_available works")

except Exception as e:
    print(f"   [FAIL] Validator function error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 5. Verify no circular imports
print("\n5. Verifying no circular imports...")
try:
    from app.server import app
    print("   [PASS] Server imports successfully (no circular imports)")
except Exception as e:
    print(f"   [FAIL] Server import error: {e}")
    sys.exit(1)

print("\n=== All Verifications Passed ===")
print("\nNext steps:")
print("1. Start the server: python run.py")
print("2. Run full tests: python tests/test_teacher_availability.py")
print("3. Test endpoints with curl or Postman")
print("\nDocumentation: docs/TEACHER_AVAILABILITY_API.md")
