# Gmail System Email Filtering

## Overview

The Gmail Watcher Skill now automatically filters out bounce emails and system notifications to prevent them from creating unnecessary tasks in your AI Employee vault.

## Problem Solved

Previously, bounce emails from `mailer-daemon@googlemail.com` and other system addresses were creating tasks like any other email, cluttering your Needs_Action folder with items that require no human action.

## Solution

The Gmail watcher now checks each incoming email against patterns for:
1. **System sender addresses** (e.g., mailer-daemon@, postmaster@, no-reply@)
2. **Bounce subject lines** (e.g., "Undeliverable", "Delivery Failed")

Emails matching these patterns are automatically filtered out and logged.

## Filtered Email Types

### Bounce/Non-Delivery Notifications
- `mailer-daemon@*`
- `postmaster@*`
- `daemon@*`
- `bounce@*`

### No-Reply/Automated Emails
- `no-reply@*`
- `noreply@*`
- `do-not-reply@*`
- `donotreply@*`
- `automated@*`
- `automation@*`

### System Addresses
- `system@*`
- `admin@*`
- `administrator@*`
- `webmaster@*`
- `hostmaster@*`

### Google System Emails
- `*@googlemail.com`
- `notifications@google.com`
- `accounts@google.com`

### Marketing/Promotional
- `newsletter@*`
- `marketing@*`
- `promo@*`
- `offers@*`

### Notification Services
- `notification@*.com`
- `notifications@*.com`
- `updates@*.com`
- `alerts@*.com`

### Bounce Subject Patterns
Emails with subjects containing:
- "Undeliverable"
- "Delivery Failed"
- "Mail Delivery Failed"
- "Returned Mail"
- "Undelivered Mail"
- "Delivery Status Notification"
- "Non-Delivery Report"
- "Bounce Notification"
- "Message Could Not Be Delivered"
- "Address Not Found"
- "User Unknown"
- "Mailbox Not Found"
- "Invalid Recipient"
- "Delivery Error"

## How It Works

### Filtering Process

1. **Email Received**: Gmail API returns new unread messages
2. **Header Check**: Fetch From and Subject headers for each message
3. **Pattern Match**: Check against sender and subject patterns
4. **Filter Decision**:
   - Match → Log and skip (mark as processed)
   - No Match → Create action file in Needs_Action/

### Code Example

```python
# In check_for_updates() method
from_email = headers.get('From', '')
subject = headers.get('Subject', '')

# Check if this is a system/bounce email
if self._is_system_email(from_email, subject):
    filtered_count += 1
    logger.info(f"Filtered out system email: {from_email} - {subject[:50]}")
    self.processed_ids.add(msg_id)  # Don't re-check
    continue

# Normal email - create action file
new_messages.append(message)
```

## Logging

Filtered emails are logged at INFO level:

```
2026-03-06 18:00:00 - skills.gmail_watcher_skill - INFO - Filtered out system email: mailer-daemon@googlemail.com - Undeliverable: Test Message
2026-03-06 18:00:00 - skills.gmail_watcher_skill - INFO - Filtered 1 system email(s), 0 new message(s) to process
```

## Configuration

No configuration needed - filtering is automatic.

To customize patterns, edit `src/skills/gmail_watcher_skill.py`:

```python
# Add custom patterns
SYSTEM_SENDER_PATTERNS = [
    # ... existing patterns ...
    r'your-custom-pattern@',  # Add your pattern here
]

BOUNCE_SUBJECT_PATTERNS = [
    # ... existing patterns ...
    r'your-custom-subject-pattern',
]
```

## Testing

Run the test script to verify filtering:

```bash
cd D:\Hackathon-0\ai-employee
python test_gmail_filtering.py
```

Expected output:
```
============================================================
Testing Gmail System Email Filtering
============================================================

Running 24 test cases...

PASS | mailer-daemon@googlemail.com             | Mail Delivery Failed           | Expected: True, Got: True
...
============================================================
Results: 24 passed, 0 failed out of 24 tests
============================================================

[PASS] All tests passed!
```

## What Still Gets Through

The following emails will **NOT** be filtered and will create tasks:

- Personal emails from individuals
- Business emails from colleagues/clients
- Urgent messages (even if automated-looking)
- Meeting invitations
- Project updates
- Support tickets (unless from filtered addresses)

## False Positives

If a legitimate email is filtered:

1. Check the logs to see which pattern matched
2. Add an exception in the code, or
3. Contact the sender to use a different email address

## Future Enhancements

Potential improvements:

1. **Whitelist**: Allow specific addresses to bypass filtering
2. **Separate Folder**: Move filtered emails to `/Inbox/System/` instead of deleting
3. **User Configuration**: YAML config file for custom patterns
4. **Machine Learning**: Learn from user behavior to improve filtering

## Related Files

- `src/skills/gmail_watcher_skill.py` - Main implementation
- `test_gmail_filtering.py` - Test script
- `docs/GMAIL_FILTERING.md` - This documentation

---

**Implementation Date**: 2026-03-06  
**Version**: 1.0.0  
**Status**: Production Ready
