# Manual Testing Guide - Teacher Availability APIs

This guide provides step-by-step instructions for manually testing the new teacher availability endpoints.

---

## Prerequisites

1. **Server Running**: Start the server with `python run.py`
2. **Admin Secret**: Have your `ADMIN_SECRET` env var ready
3. **API Client**: Use curl, Postman, or similar tool

---

## Test Scenario: Complete Flow

### Step 1: Create Teacher Account

First, create a teacher invite token (requires admin secret):

```bash
curl -X POST http://localhost:8000/api/admin/teacher-invites \
  -H "X-Admin-Secret: your-admin-secret-here" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testteacher@example.com",
    "expires_days": 7
  }'
```

**Expected Response**:
```json
{
  "email": "testteacher@example.com",
  "token": "long-random-token",
  "invite_url": "/teacher_register.html?token=...",
  "expires_at": "2024-01-22T10:00:00"
}
```

**Save the token** for the next step.

---

### Step 2: Register Teacher

Register the teacher using the invite token:

```bash
curl -X POST http://localhost:8000/api/auth/teacher/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Teacher",
    "email": "testteacher@example.com",
    "password": "SecurePassword123",
    "invite_token": "token-from-step-1"
  }'
```

**Expected Response**:
```json
{
  "token": "jwt-token-here",
  "student_id": 1,
  "name": "Test Teacher",
  "email": "testteacher@example.com",
  "role": "teacher"
}
```

**Save the JWT token** as `TEACHER_TOKEN`.

---

### Step 3: Add Teacher Availability

Add availability slots for the teacher:

```bash
curl -X POST http://localhost:8000/api/teacher/availability \
  -H "Authorization: Bearer TEACHER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_at": "2024-01-15T09:00:00",
    "end_at": "2024-01-15T17:00:00",
    "recurrence_rule": "RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR"
  }'
```

**Expected Response**:
```json
{
  "id": 1,
  "start_at": "2024-01-15T09:00:00",
  "end_at": "2024-01-15T17:00:00"
}
```

---

### Step 4: Register Student Account

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Student",
    "email": "teststudent@example.com",
    "password": "SecurePassword123",
    "age": 25
  }'
```

**Expected Response**:
```json
{
  "token": "jwt-token-here",
  "student_id": 2,
  "name": "Test Student",
  "email": "teststudent@example.com",
  "role": "student"
}
```

**Save the JWT token** as `STUDENT_TOKEN`.

---

### Step 5: List Teachers (Student)

**Test**: Student can see available teachers

```bash
curl -X GET http://localhost:8000/api/students/teachers \
  -H "Authorization: Bearer STUDENT_TOKEN"
```

**Expected Response**:
```json
{
  "teachers": [
    {
      "id": 1,
      "display_name": "Test Teacher"
    }
  ]
}
```

**Verify**:
- ✅ Returns list of teachers
- ✅ Only shows id and display_name
- ✅ No email or password exposed

---

### Step 6: Get Teacher Availability (Student)

**Test**: Student can view teacher's available time slots

```bash
curl -X GET "http://localhost:8000/api/students/teachers/1/availability?from_date=2024-01-15&to_date=2024-01-31" \
  -H "Authorization: Bearer STUDENT_TOKEN"
```

**Expected Response**:
```json
{
  "teacher_id": 1,
  "teacher_name": "Test Teacher",
  "windows": [
    {"date": "2024-01-15", "start_time": "09:00", "end_time": "17:00"},
    {"date": "2024-01-17", "start_time": "09:00", "end_time": "17:00"},
    {"date": "2024-01-19", "start_time": "09:00", "end_time": "17:00"},
    {"date": "2024-01-22", "start_time": "09:00", "end_time": "17:00"}
  ],
  "timezone_note": "All times are in server local time (ISO 8601 format without explicit timezone)"
}
```

**Verify**:
- ✅ Returns expanded time windows (not raw RRULE)
- ✅ Shows Monday, Wednesday, Friday slots only
- ✅ Within requested date range

---

### Step 7: Request Session WITH Teacher (Valid Time)

**Test**: Student can request session at valid time

```bash
curl -X POST http://localhost:8000/api/student/me/sessions/request \
  -H "Authorization: Bearer STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scheduled_at": "2024-01-15T10:00:00",
    "duration_min": 60,
    "notes": "Practice conversation",
    "teacher_id": 1
  }'
```

**Expected Response**:
```json
{
  "id": 1,
  "status": "requested",
  "scheduled_at": "2024-01-15T10:00:00",
  "duration_min": 60,
  "teacher_id": 1
}
```

**Verify**:
- ✅ Session created successfully
- ✅ teacher_id is set (pre-assigned)
- ✅ Status is "requested"

---

### Step 8: Request Session at INVALID Time

**Test**: Validation rejects booking outside availability

```bash
curl -X POST http://localhost:8000/api/student/me/sessions/request \
  -H "Authorization: Bearer STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scheduled_at": "2024-01-16T10:00:00",
    "duration_min": 60,
    "notes": "This is Tuesday (not available)",
    "teacher_id": 1
  }'
```

**Expected Response** (HTTP 400):
```json
{
  "detail": "Requested time does not fall within teacher's available hours"
}
```

**Verify**:
- ✅ Request rejected (HTTP 400)
- ✅ Clear error message
- ✅ Tuesday is not available (only MO/WE/FR)

---

### Step 9: Request Session WITHOUT Teacher (Old Flow)

**Test**: Old marketplace flow still works

```bash
curl -X POST http://localhost:8000/api/student/me/sessions/request \
  -H "Authorization: Bearer STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scheduled_at": "2024-01-20T14:00:00",
    "duration_min": 90,
    "notes": "No teacher specified"
  }'
```

**Expected Response**:
```json
{
  "id": 2,
  "status": "requested",
  "scheduled_at": "2024-01-20T14:00:00",
  "duration_min": 90,
  "teacher_id": null
}
```

**Verify**:
- ✅ Session created successfully
- ✅ teacher_id is null (marketplace flow)
- ✅ No validation performed (any time accepted)
- ✅ Backwards compatible with old behavior

---

### Step 10: Teacher Confirms Session

**Test**: Teacher can confirm a requested session

```bash
curl -X POST http://localhost:8000/api/teacher/sessions/1/confirm \
  -H "Authorization: Bearer TEACHER_TOKEN"
```

**Expected Response**:
```json
{
  "id": 1,
  "status": "confirmed",
  "teacher_id": 1
}
```

---

### Step 11: Student Views Sessions

**Test**: Student can see confirmed sessions with teacher name

```bash
curl -X GET http://localhost:8000/api/student/me/sessions \
  -H "Authorization: Bearer STUDENT_TOKEN"
```

**Expected Response**:
```json
{
  "sessions": [
    {
      "id": 1,
      "scheduled_at": "2024-01-15T10:00:00",
      "duration_min": 60,
      "status": "confirmed",
      "notes": "Practice conversation",
      "homework": null,
      "session_summary": null,
      "teacher_name": "Test Teacher"
    },
    {
      "id": 2,
      "scheduled_at": "2024-01-20T14:00:00",
      "duration_min": 90,
      "status": "requested",
      "notes": "No teacher specified",
      "homework": null,
      "session_summary": null,
      "teacher_name": null
    }
  ]
}
```

---

## Edge Cases to Test

### Test: Booking Too Early
```bash
curl -X POST http://localhost:8000/api/student/me/sessions/request \
  -H "Authorization: Bearer STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scheduled_at": "2024-01-15T08:00:00",
    "duration_min": 60,
    "teacher_id": 1
  }'
```

**Expected**: HTTP 400, "Requested time does not fall within teacher's available hours"
(Availability starts at 09:00, not 08:00)

---

### Test: Booking Too Late
```bash
curl -X POST http://localhost:8000/api/student/me/sessions/request \
  -H "Authorization: Bearer STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scheduled_at": "2024-01-15T16:30:00",
    "duration_min": 90,
    "teacher_id": 1
  }'
```

**Expected**: HTTP 400
(Booking would end at 18:00, but availability ends at 17:00)

---

### Test: Invalid Teacher ID
```bash
curl -X POST http://localhost:8000/api/student/me/sessions/request \
  -H "Authorization: Bearer STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scheduled_at": "2024-01-15T10:00:00",
    "duration_min": 60,
    "teacher_id": 999
  }'
```

**Expected**: HTTP 404, "Teacher not found"

---

### Test: Teacher Without Availability
Create a second teacher without adding availability, then try to book:

**Expected**: HTTP 400, "Teacher has no availability configured"

---

### Test: Student Tries to Access Teacher Endpoint
```bash
curl -X GET http://localhost:8000/api/teacher/sessions \
  -H "Authorization: Bearer STUDENT_TOKEN"
```

**Expected**: HTTP 403, "Teachers only"

---

### Test: Teacher Tries to Access Student Teacher List
```bash
curl -X GET http://localhost:8000/api/students/teachers \
  -H "Authorization: Bearer TEACHER_TOKEN"
```

**Expected**: HTTP 403, "Students only"

---

## Troubleshooting

### Issue: "Teacher not found"
- Check teacher exists: `SELECT * FROM students WHERE id=X AND role='teacher'`
- Verify teacher_id in request matches database

### Issue: No availability windows returned
- Check availability slots exist: `SELECT * FROM teacher_availability WHERE teacher_id=X`
- Verify `is_available=1`
- Check date range includes slot dates

### Issue: Validation fails unexpectedly
- Verify datetime format: `YYYY-MM-DDTHH:MM:SS` (no Z or timezone)
- Check time is in future
- Ensure entire booking window (start + duration) fits within available slot

### Issue: "Invalid token"
- Token may be expired (72 hour expiry)
- Re-login to get fresh token

---

## Success Criteria

✅ All test cases pass
✅ Student can list teachers
✅ Student can view teacher availability
✅ Valid bookings are accepted
✅ Invalid bookings are rejected with clear errors
✅ Old flow (no teacher_id) still works
✅ Role-based access control enforced
✅ No private data exposed

---

## Automated Test

Run the automated test suite:
```bash
python tests/test_teacher_availability.py
```

Should output:
```
Total: 22 tests
Passed: 22
Failed: 0

All tests passed!
```
