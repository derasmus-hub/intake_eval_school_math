# Frontend Testing Guide - Teacher Availability UI

This guide helps you test the new teacher availability UI on the student dashboard.

---

## Prerequisites

1. **Server Running**: `python run.py`
2. **Teacher Account**: Create at least one teacher with availability slots
3. **Student Account**: Have a student account to log in

---

## Setup Test Data

### Step 1: Create Teacher Account

```bash
# Create teacher invite
curl -X POST http://localhost:8000/api/admin/teacher-invites \
  -H "X-Admin-Secret: your-admin-secret" \
  -H "Content-Type: application/json" \
  -d '{"email": "testteacher@example.com", "expires_days": 7}'

# Register teacher (use token from above)
curl -X POST http://localhost:8000/api/auth/teacher/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Teacher",
    "email": "testteacher@example.com",
    "password": "password123",
    "invite_token": "TOKEN_FROM_ABOVE"
  }'
```

Save the JWT token returned.

### Step 2: Add Teacher Availability

```bash
# Add Monday, Wednesday, Friday 9am-5pm availability
curl -X POST http://localhost:8000/api/teacher/availability \
  -H "Authorization: Bearer TEACHER_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_at": "2024-01-15T09:00:00",
    "end_at": "2024-01-15T17:00:00",
    "recurrence_rule": "RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR"
  }'
```

### Step 3: Create Student Account

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Student",
    "email": "teststudent@example.com",
    "password": "password123",
    "age": 25
  }'
```

---

## UI Testing Steps

### 1. Access Student Dashboard

1. Open browser: `http://localhost:8000/student_dashboard.html`
2. Log in with student credentials
3. Dashboard should load successfully

### 2. Open Session Request Form

1. Click "Request / Poproś" button
2. Form should expand
3. **Verify**: Teacher dropdown appears at top of form

### 3. Check Teacher Dropdown

**Expected Behavior**:
- Dropdown shows "Loading teachers..." initially
- After loading, shows "Test Teacher" (or your teacher name)
- Dropdown is populated with teacher names
- First teacher is selected by default

**Verify**:
- ✅ Dropdown is visible
- ✅ Teacher name appears in dropdown
- ✅ No error message below dropdown

### 4. Check Availability Display

**Expected Behavior** (once teacher loads):
- "Available Times / Dostepne terminy" section appears
- Shows "Loading availability..." initially
- After loading, displays next 14 days
- Each day shows:
  - Date (e.g., "Mon, Jan 15 (2024-01-15)")
  - Available time windows (e.g., "09:00–17:00")
  - OR "Not available / Niedostepny" if no slots

**Verify**:
- ✅ Availability section is visible
- ✅ Shows 14 days in a scrollable list
- ✅ Monday, Wednesday, Friday show "09:00–17:00"
- ✅ Tuesday, Thursday show "Not available"
- ✅ Time windows displayed in green badges

### 5. Test Teacher Change

1. Create a second teacher with different availability
2. Change teacher in dropdown
3. **Expected**: Availability list refreshes with new teacher's schedule
4. **Verify**: Loading indicator appears, then new schedule loads

### 6. Test Valid Booking

1. Select teacher with availability
2. Pick a Monday (available day)
3. Select time: 10:00 AM
4. Duration: 60 min
5. Add notes (optional)
6. Click "Send Request"

**Expected**:
- ✅ No validation errors
- ✅ Form submits successfully
- ✅ Success banner appears
- ✅ Session appears in "My Requests & History" section with teacher name

### 7. Test Invalid Booking - Wrong Day

1. Select teacher
2. Pick a Tuesday (not available)
3. Select time: 10:00 AM
4. Duration: 60 min

**Expected**:
- ✅ Red error message appears below date/time field
- ✅ Error says "Teacher not available on this date"
- ✅ Submit button still enabled but validation fails

### 8. Test Invalid Booking - Wrong Time

1. Select teacher
2. Pick a Monday (available day)
3. Select time: 7:00 AM (before 9am availability)
4. Duration: 60 min

**Expected**:
- ✅ Red error message appears
- ✅ Error says "Selected time not available"

### 9. Test Invalid Booking - Extends Past Window

1. Select teacher
2. Pick a Monday
3. Select time: 4:30 PM (16:30)
4. Duration: 90 min (ends at 6:00 PM, past 5:00 PM availability)

**Expected**:
- ✅ Red error message appears
- ✅ Error says "Selected time not available"

### 10. Test Real-Time Validation

1. Select a valid time (Mon 10am)
2. **Verify**: No error message
3. Change to invalid time (Tue 10am)
4. **Verify**: Error appears immediately
5. Change back to valid time
6. **Verify**: Error disappears

---

## Visual Verification Checklist

### Teacher Dropdown
- [ ] Appears at top of form
- [ ] Has bilingual label "Choose Teacher / Wybierz nauczyciela"
- [ ] Populated with teacher names
- [ ] Required field (can't submit without selection)
- [ ] Matches existing form styling

### Availability Section
- [ ] Light gray background box
- [ ] Header with date range
- [ ] Scrollable list (max height 300px)
- [ ] Each day in white card
- [ ] Green time window badges
- [ ] Gray "Not available" text for unavailable days
- [ ] Consistent spacing and padding

### Validation Errors
- [ ] Red error box with left border
- [ ] Appears below date/time field
- [ ] Bilingual error messages
- [ ] Disappears when issue resolved

### Form Submission
- [ ] Includes teacher_id in payload
- [ ] Shows "Sending..." while submitting
- [ ] Success banner on successful submission
- [ ] Session shows teacher name in history
- [ ] Backend validation errors displayed clearly

---

## Error Scenarios

### No Teachers Available
**Simulate**: No teachers registered in system
**Expected**:
- Dropdown shows "No teachers available / Brak nauczycieli"
- Red error message appears
- Form cannot be submitted

### Teacher Without Availability
**Simulate**: Teacher exists but has no availability slots
**Expected**:
- Availability section shows all days as "Not available"
- Selecting any time shows validation error
- Clear message: "Teacher has no availability configured"

### API Failure
**Simulate**: Stop server while on page
**Expected**:
- Error message appears
- Form gracefully handles failure
- No JavaScript errors in console

---

## Browser Console Checks

Open browser console (F12) and verify:
- [ ] No JavaScript errors
- [ ] API calls to `/api/students/teachers` succeed
- [ ] API calls to `/api/students/teachers/{id}/availability` succeed
- [ ] POST to `/api/student/me/sessions/request` includes `teacher_id`

Expected console logs:
```
[loadTeachers] Success: loaded 1 teacher(s)
[loadTeacherAvailability] Success: loaded 21 window(s)
[validateAvailability] Valid booking
[submitSessionRequest] Success: session created
```

---

## Network Tab Verification

In browser DevTools Network tab:

### On Form Open:
1. **GET** `/api/students/teachers`
   - Status: 200
   - Response: `{"teachers": [{"id": 1, "display_name": "Test Teacher"}]}`

2. **GET** `/api/students/teachers/1/availability?from_date=...&to_date=...`
   - Status: 200
   - Response: Contains `windows` array with time slots

### On Form Submit:
3. **POST** `/api/student/me/sessions/request`
   - Status: 200
   - Request Body includes: `teacher_id`, `scheduled_at`, `duration_min`, `notes`
   - Response: `{"id": X, "status": "requested", "teacher_id": 1, ...}`

---

## Mobile/Responsive Testing

Test on smaller screen sizes (resize browser to < 600px):
- [ ] Teacher dropdown remains full width
- [ ] Availability section remains readable
- [ ] Time windows wrap properly
- [ ] Form remains usable
- [ ] No horizontal scrolling

---

## Accessibility Testing

- [ ] All form fields have labels
- [ ] Required fields marked with `required` attribute
- [ ] Error messages associated with fields
- [ ] Tab navigation works through all fields
- [ ] Enter key submits form

---

## Performance Checks

- [ ] Teachers load within 500ms
- [ ] Availability loads within 1 second
- [ ] Validation is instant (no lag)
- [ ] Form submission responds within 2 seconds
- [ ] No UI freezing or stuttering

---

## Success Criteria

All of the following must work:

✅ Teacher dropdown populates correctly
✅ Availability displays for next 14 days
✅ Available time windows shown as green badges
✅ Unavailable days show "Not available"
✅ Real-time validation works on date/time change
✅ Valid bookings submit successfully
✅ Invalid bookings show clear error messages
✅ Backend receives teacher_id in request
✅ Session history shows teacher name
✅ No JavaScript errors in console
✅ Bilingual labels throughout
✅ Consistent design with existing dashboard

---

## Troubleshooting

### Issue: Teachers don't load
- Check: Teacher exists in database with role='teacher'
- Check: Student is logged in (JWT token valid)
- Check: Network tab shows 200 response
- Check: Console for errors

### Issue: Availability shows all "Not available"
- Check: Teacher has slots in `teacher_availability` table
- Check: Slots have `is_available=1`
- Check: Date range covers slot dates
- Check: Recurrence rule is valid WEEKLY format

### Issue: Validation always fails
- Check: Selected date matches availability date format
- Check: Time format is HH:MM
- Check: Duration doesn't extend past window end
- Check: teacherAvailability variable is populated

### Issue: Form won't submit
- Check: Teacher selected
- Check: Date/time selected
- Check: Validation passes
- Check: Console for JavaScript errors

---

## Automated Test Command

Run backend tests:
```bash
python tests/test_teacher_availability.py
```

Should show:
```
Total: 22 tests
Passed: 22
Failed: 0
```
