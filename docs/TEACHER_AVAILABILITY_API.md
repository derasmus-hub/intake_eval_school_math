# Teacher Availability API - Implementation Documentation

## Overview

This document describes the backend implementation for student-facing teacher availability and booking validation features.

**Status**: ✅ Implemented and tested
**Date**: 2024-01-15
**Breaking Changes**: None - all changes are backwards compatible

---

## 🎯 What Was Added

### A. Teacher Directory Endpoint

**Endpoint**: `GET /api/students/teachers`
**Auth**: Requires student role (JWT token)
**Purpose**: Allow students to see which teachers are available for booking

**Response**:
```json
{
  "teachers": [
    {"id": 1, "display_name": "John Doe"},
    {"id": 2, "display_name": "Jane Smith"}
  ]
}
```

**Security**: Only exposes teacher ID and name - no email, password, or private data.

---

### B. Teacher Availability Endpoint

**Endpoint**: `GET /api/students/teachers/{teacher_id}/availability`
**Auth**: Requires student role
**Query Params**:
- `from_date` (optional): Start date in YYYY-MM-DD format (default: today)
- `to_date` (optional): End date in YYYY-MM-DD format (default: 30 days from now)

**Purpose**: Fetch expanded availability windows for a specific teacher

**Response**:
```json
{
  "teacher_id": 1,
  "teacher_name": "John Doe",
  "windows": [
    {"date": "2024-01-15", "start_time": "09:00", "end_time": "12:00"},
    {"date": "2024-01-15", "start_time": "14:00", "end_time": "17:00"},
    {"date": "2024-01-17", "start_time": "09:00", "end_time": "12:00"}
  ],
  "timezone_note": "All times are in server local time (ISO 8601 format without explicit timezone)"
}
```

**Features**:
- Automatically expands weekly recurring availability (RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR)
- Returns concrete time windows per day (no need for frontend to parse recurrence rules)
- Filters by date range
- Only returns available slots (is_available=1)

---

### C. Session Request Validation

**Enhanced Endpoint**: `POST /api/student/me/sessions/request`
**Changes**:
1. Added optional `teacher_id` field to request body
2. If `teacher_id` provided, validates booking against teacher availability
3. If `teacher_id` not provided, preserves old behavior (marketplace flow)

**Request Body** (updated):
```json
{
  "scheduled_at": "2024-01-15T10:00:00",
  "duration_min": 60,
  "notes": "Practice speaking",
  "teacher_id": 1  // NEW: Optional field
}
```

**Validation Logic**:
- Verifies teacher exists and has role='teacher'
- Checks that requested datetime is in the future
- Fetches teacher's availability slots
- Validates that the entire booking window falls within an available time slot
- Returns 400 error with clear message if validation fails

**Error Responses**:
```json
// Teacher not found
{"detail": "Teacher not found"}

// Time not available
{"detail": "Requested time does not fall within teacher's available hours"}

// No availability configured
{"detail": "Teacher has no availability configured"}
```

---

## 📦 New Files Created

### 1. `app/services/availability_validator.py`

**Purpose**: Shared service for availability validation logic

**Functions**:
- `parse_simple_rrule(rrule: str)` - Parse RRULE strings (WEEKLY only)
- `expand_weekly_recurrence(...)` - Expand recurring slots into concrete date/time windows
- `is_booking_available(...)` - Validate if a booking request fits within availability
- `get_teacher_availability_windows(...)` - Database query + expansion helper

**Recurrence Support**:
- ✅ Single slots (no recurrence)
- ✅ Weekly recurrence with BYDAY (e.g., "RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR")
- ❌ Other recurrence types (DAILY, MONTHLY, etc.) - falls back to single occurrence

**Edge Cases Handled**:
- Invalid ISO datetime strings → returns empty list
- Missing recurrence_rule → treats as single occurrence
- Unparseable RRULE → treats as single occurrence
- Zero or very long durations → validated correctly

### 2. `tests/test_teacher_availability.py`

**Purpose**: Comprehensive unit tests for new features

**Test Coverage**:
- ✅ RRULE parsing (valid, invalid, null)
- ✅ Weekly recurrence expansion
- ✅ Availability validation (valid/invalid bookings)
- ✅ Database integration tests
- ✅ Edge cases (invalid dates, zero duration, etc.)

**Results**: 22/22 tests passing

---

## 🔄 Modified Files

### 1. `app/routes/scheduling.py`

**Changes**:
1. Added imports for datetime and availability_validator
2. Updated `SessionRequest` model to include optional `teacher_id` field
3. Enhanced `student_request_session` endpoint with validation logic
4. Added `list_teachers_for_students` endpoint
5. Added `get_teacher_availability_for_students` endpoint

**Backwards Compatibility**: ✅
- Old session requests without `teacher_id` still work (marketplace flow)
- Existing endpoints unchanged
- No schema changes required

---

## 🗄️ Database Schema

**No schema changes required!**

Existing tables already support this feature:
- `students` table has `role` column ('student' or 'teacher')
- `teacher_availability` table has all needed fields
- `sessions` table has `teacher_id` column (nullable)

---

## 🔐 Security & Role-Based Access

### Student Role (`role='student'`):
- ✅ Can list teachers (public info only)
- ✅ Can view teacher availability
- ✅ Can request sessions with or without teacher_id
- ❌ Cannot access teacher-only endpoints
- ❌ Cannot see teacher email, password, or private notes

### Teacher Role (`role='teacher'`):
- ✅ All previous teacher permissions unchanged
- ✅ Can still view/confirm/cancel sessions
- ✅ Can still manage own availability

### Public Access:
- Existing `/api/booking/slots` endpoint still public (unchanged)

---

## 🌐 Timezone Handling

**Current Implementation**: "Server Local Time"

All datetimes are stored and returned as ISO 8601 strings **without explicit timezone**.

Example: `"2024-01-15T10:00:00"` (no Z suffix, no +00:00 offset)

**Documentation**:
- API response includes: `"timezone_note": "All times are in server local time (ISO 8601 format without explicit timezone)"`
- Frontend should use native `datetime-local` input (browser's local timezone)
- Backend validation uses `datetime.now()` (server's local timezone)

**Future Enhancement**: Add explicit timezone field to teacher_availability table and convert times appropriately.

---

## 🧪 Testing

### Run Tests:
```bash
python tests/test_teacher_availability.py
```

### Test Scenarios Covered:
1. ✅ Student lists all teachers
2. ✅ Student fetches teacher availability
3. ✅ Booking within availability is accepted
4. ✅ Booking outside availability is rejected
5. ✅ Booking on wrong day is rejected
6. ✅ Booking extending past available hours is rejected
7. ✅ Teacher with no availability configured returns error
8. ✅ Invalid datetime formats handled gracefully
9. ✅ Weekly recurrence expansion works correctly
10. ✅ Database integration works end-to-end

---

## 🚀 Deployment

### Docker:
No changes required! All code works in existing Docker environment.

### Environment Variables:
No new environment variables needed.

### Database Migrations:
No migrations required - existing schema is sufficient.

---

## 📋 API Usage Examples

### 1. Student Lists Teachers
```bash
curl -X GET http://localhost:8000/api/students/teachers \
  -H "Authorization: Bearer <student_token>"
```

### 2. Student Fetches Availability
```bash
curl -X GET "http://localhost:8000/api/students/teachers/1/availability?from_date=2024-01-15&to_date=2024-01-31" \
  -H "Authorization: Bearer <student_token>"
```

### 3. Student Requests Session with Teacher
```bash
curl -X POST http://localhost:8000/api/student/me/sessions/request \
  -H "Authorization: Bearer <student_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "scheduled_at": "2024-01-15T10:00:00",
    "duration_min": 60,
    "notes": "Practice conversation",
    "teacher_id": 1
  }'
```

### 4. Old Flow Still Works (No Teacher ID)
```bash
curl -X POST http://localhost:8000/api/student/me/sessions/request \
  -H "Authorization: Bearer <student_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "scheduled_at": "2024-01-15T10:00:00",
    "duration_min": 60,
    "notes": "Practice conversation"
  }'
```

---

## 🐛 Known Limitations

1. **Recurrence Types**: Only WEEKLY recurrence supported. DAILY, MONTHLY, YEARLY fall back to single occurrence.

2. **Timezone**: No explicit timezone handling. Assumes server and clients are in same timezone or manually handle conversion.

3. **Conflict Detection**: Does not check for overlapping session bookings (multiple students booking same teacher at same time). This should be added in future enhancement.

4. **Booking Window**: Default availability fetch is 30 days. Frontend should handle pagination or date range selection for longer ranges.

---

## ✅ Verification Checklist

Before deploying:

- [x] All imports work correctly
- [x] Tests pass (22/22)
- [x] No breaking changes to existing endpoints
- [x] Backwards compatible (old session requests still work)
- [x] Role-based access enforced
- [x] No private teacher data exposed to students
- [x] Database schema unchanged
- [x] Works in Docker environment
- [x] Documentation complete

---

## 📚 Next Steps for Frontend

To integrate these APIs, the frontend needs:

1. **Teacher Selection UI**:
   - Add dropdown/select input to session request form
   - Fetch teachers via `GET /api/students/teachers`
   - Populate options with teacher names

2. **Availability Display** (optional but recommended):
   - Fetch availability via `GET /api/students/teachers/{id}/availability`
   - Show available time slots for selected teacher
   - Disable/highlight unavailable times in datetime picker

3. **Validation Feedback**:
   - Handle 400 errors from session request endpoint
   - Display error message if booking is outside availability
   - Guide student to select valid times

4. **Updated Request Payload**:
   - Include `teacher_id` in session request body
   - Keep `teacher_id: null` as fallback for marketplace flow

---

## 📞 Support

If you encounter issues:
1. Check that teacher has role='teacher' in database
2. Verify teacher has availability slots configured
3. Ensure datetime format is ISO 8601 (YYYY-MM-DDTHH:MM:SS)
4. Run tests: `python tests/test_teacher_availability.py`
5. Check server logs for detailed error messages
