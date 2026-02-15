# Teacher Invite System

Teachers can only be registered via invite tokens. Public registration always creates student accounts.

## Setup

Set the `ADMIN_SECRET` environment variable (minimum 16 characters):

**PowerShell:**
```powershell
$env:ADMIN_SECRET = "your-secure-admin-secret-here"
```

**Bash:**
```bash
export ADMIN_SECRET="your-secure-admin-secret-here"
```

Or add to `.env` file:
```
ADMIN_SECRET=your-secure-admin-secret-here
```

## Creating a Teacher Invite

**PowerShell:**
```powershell
$headers = @{
    "Content-Type" = "application/json"
    "X-Admin-Secret" = $env:ADMIN_SECRET
}
$body = @{
    email = "teacher@example.com"
    expires_days = 7
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/admin/teacher-invites" -Method POST -Headers $headers -Body $body
$response | ConvertTo-Json
```

**cURL:**
```bash
curl -X POST http://localhost:8000/api/admin/teacher-invites \
  -H "Content-Type: application/json" \
  -H "X-Admin-Secret: $ADMIN_SECRET" \
  -d '{"email": "teacher@example.com", "expires_days": 7}'
```

Response:
```json
{
  "email": "teacher@example.com",
  "token": "abc123...",
  "invite_url": "/teacher_register.html?token=abc123...&email=teacher@example.com",
  "expires_at": "2026-02-12T10:00:00"
}
```

## Registering as Teacher

1. Open the invite URL in browser: `http://localhost:8000/teacher_register.html?token=TOKEN&email=EMAIL`
2. The form pre-fills email and token from URL
3. Enter name and password (minimum 8 characters)
4. Submit to create teacher account
5. Redirected to teacher dashboard on success

## Listing All Invites

**PowerShell:**
```powershell
$headers = @{ "X-Admin-Secret" = $env:ADMIN_SECRET }
Invoke-RestMethod -Uri "http://localhost:8000/api/admin/teacher-invites" -Method GET -Headers $headers | ConvertTo-Json -Depth 3
```

**cURL:**
```bash
curl -H "X-Admin-Secret: $ADMIN_SECRET" http://localhost:8000/api/admin/teacher-invites
```

## Security Notes

- Invite tokens are single-use and expire after the specified days
- Email must match exactly (case-insensitive) when registering
- Public `/api/auth/register` always creates students, even if `role=teacher` is sent
- Admin endpoints require `X-Admin-Secret` header matching the `ADMIN_SECRET` env var
- Teacher emails are never exposed to students

example run that worked
(.venv) PS C:\Users\erasm\OneDrive\Documents\intake_eval_school>
(.venv) PS C:\Users\erasm\OneDrive\Documents\intake_eval_school> $response
(.venv) PS C:\Users\erasm\OneDrive\Documents\intake_eval_school> $headers = @{
>>   "Content-Type"   = "application/json"
>>   "X-Admin-Secret" = $env:ADMIN_SECRET
>> }
(.venv) PS C:\Users\erasm\OneDrive\Documents\intake_eval_school>
(.venv) PS C:\Users\erasm\OneDrive\Documents\intake_eval_school> $body = @{
>>   email = "teacher1@gmail.com"
>>   expires_days = 7
>> } | ConvertTo-Json
(.venv) PS C:\Users\erasm\OneDrive\Documents\intake_eval_school>
(.venv) PS C:\Users\erasm\OneDrive\Documents\intake_eval_school> $response = Invoke-RestMethod `
>>   -Uri "http://localhost:8000/api/admin/teacher-invites" `
>>   -Method POST `
>>   -Headers $headers `
>>   -Body $body
(.venv) PS C:\Users\erasm\OneDrive\Documents\intake_eval_school>
(.venv) PS C:\Users\erasm\OneDrive\Documents\intake_eval_school> $response

email              token                                       invite_url
-----              -----                                       ----------
teacher1@gmail.com _3zjue9PBn3mQ4_AbBw4bF5kZBS3zB3YhHkLFgO2mlY /teacher_register.html?token=_3zjue9PBn3mQ4_AbBw4bF5kZB…

(.venv) PS C:\Users\erasm\OneDrive\Documents\intake_eval_school> http://localhost:8000/teacher_register.html?token=XXX&email=teacher1@gmail.com

Id     Name            PSJobTypeName   State         HasMoreData     Location             Command
--     ----            -------------   -----         -----------     --------             -------
1      Job1            BackgroundJob   Running       True            localhost            http://localhost:8000/te…
email=teacher1@gmail.com: The term 'email=teacher1@gmail.com' is not recognized as a name of a cmdlet, function, script file, or executable program.
Check the spelling of the name, or if a path was included, verify that the path is correct and try again.

(.venv) PS C:\Users\erasm\OneDrive\Documents\intake_eval_school> $invitePath = $response.invite_url
(.venv) PS C:\Users\erasm\OneDrive\Documents\intake_eval_school> $fullUrl = "http://localhost:8000$invitePath"
(.venv) PS C:\Users\erasm\OneDrive\Documents\intake_eval_school> $fullUrl
http://localhost:8000/teacher_register.html?token=_3zjue9PBn3mQ4_AbBw4bF5kZBS3zB3YhHkLFgO2mlY&email=teacher1@gmail.com
(.venv) PS C:\Users\erasm\OneDrive\Documents\intake_eval_school>