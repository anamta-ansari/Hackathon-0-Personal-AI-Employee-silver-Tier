# Single-File Lifecycle Implementation

## Problem Statement

**BEFORE:** System created 3 separate files for ONE task:
- 1 file in `Needs_Action/` (EMAIL_*.md)
- 1 file in `Plans/` (PLAN_*.md)  
- 1 file in `Pending_Approval/` (APPROVAL_*.md)

This caused:
- Clutter across multiple folders
- Confusion about which files belong together
- Complex tracking logic
- Difficult to see task history

## Solution: Single-File Lifecycle

**AFTER:** ONE file moves through folders as it progresses:

```
Needs_Action/TASK_12345.md
    ↓ (Plan created)
Plans/TASK_12345.md            ← Same file, updated with Action Plan
    ↓ (Approval needed)
Pending_Approval/TASK_12345.md ← Same file, updated with Approval section
    ↓ (Approved)
Approved/TASK_12345.md         ← Same file
    ↓ (Executed)
Done/TASK_12345.md             ← Same file, updated with Execution Result
```

## File Evolution Example

### Stage 1: Email Detected (`Needs_Action/TASK_12345.md`)

```markdown
---
task_id: TASK_12345
type: email
from: client@example.com
subject: Invoice Request
received: 2026-03-05T14:00:00
status: pending
---

## Email Content

Hi, can you send me the invoice for January?

Thanks,
Client
```

### Stage 2: Plan Created (`Plans/TASK_12345.md`)

```markdown
---
task_id: TASK_12345
type: email
from: client@example.com
subject: Invoice Request
received: 2026-03-05T14:00:00
status: planned
plan_created: 2026-03-05T14:05:00
category: financial
priority: high
requires_approval: true
---

## Email Content

Hi, can you send me the invoice for January?

Thanks,
Client

## Action Plan
*Created: 2026-03-05T14:05:00*

- [ ] Review financial details
- [ ] Verify amount and vendor
- [ ] Draft response
- [ ] Archive after processing
```

### Stage 3: Approval Requested (`Pending_Approval/TASK_12345.md`)

```markdown
---
task_id: TASK_12345
type: email
from: client@example.com
subject: Invoice Request
received: 2026-03-05T14:00:00
status: awaiting_approval
plan_created: 2026-03-05T14:05:00
approval_requested: 2026-03-05T14:06:00
category: financial
priority: high
requires_approval: true
---

## Email Content

Hi, can you send me the invoice for January?

Thanks,
Client

## Action Plan
*Created: 2026-03-05T14:05:00*

- [ ] Review financial details
- [ ] Verify amount and vendor
- [ ] Draft response
- [ ] Archive after processing

## Approval Required
*Added: 2026-03-05T14:06:00*

🟡 **Action Type:** Email Response
**Priority:** High

**Draft Reply:**
**To:** client@example.com
**Subject:** Re: Invoice Request

```
Dear Client,

Thank you for your email regarding "Invoice Request".
I will review the financial details and get back to you within 24 hours.

Best regards
```

**Instructions:**
- Move this file to `/Approved/` to approve and send
- Move to `/Rejected/` to decline
```

### Stage 4: Approved (`Approved/TASK_12345.md`)

File moved by user from `Pending_Approval/` to `Approved/`.
Orchestrator detects file in `Approved/` and executes the action.

### Stage 5: Executed (`Done/TASK_12345.md`)

```markdown
---
task_id: TASK_12345
type: email
from: client@example.com
subject: Invoice Request
received: 2026-03-05T14:00:00
status: completed
plan_created: 2026-03-05T14:05:00
approval_requested: 2026-03-05T14:06:00
approved: 2026-03-05T14:10:00
executed: 2026-03-05T14:15:00
completed: 2026-03-05T14:15:00
execution_result: success
message_id: 19cbdf6ea4f0352c
---

## Email Content

Hi, can you send me the invoice for January?

Thanks,
Client

## Action Plan
*Created: 2026-03-05T14:05:00*

- [x] Review financial details
- [x] Verify amount and vendor
- [x] Draft response
- [x] Archive after processing

## Approval Required
*Added: 2026-03-05T14:06:00*

🟡 **Action Type:** Email Response
**Priority:** High

## Execution Result
*Added: 2026-03-05T14:15:00*

**Status:** ✅ Success
**Message ID:** 19cbdf6ea4f0352c
**Sent to:** client@example.com
```

## Implementation Changes

### 1. `src/skills/process_email.py`

**Key Changes:**
- Added `update_frontmatter()` function to modify existing metadata
- Added `add_action_plan()` function to append plan section
- Added `add_approval_section()` function to append approval section
- Modified `process_email()` to:
  - Update the same file instead of creating new PLAN_*.md
  - Move file from `Needs_Action/` → `Plans/` → `Pending_Approval/`
  - Return `current_file` and `previous_location` instead of `plan_file` and `approval_file`

### 2. `src/skills/create_approval_request.py`

**Key Changes:**
- Added `file_path` parameter for single-file mode
- Added `_update_existing_file()` function
- Modified `create_approval_request()` to:
  - Check if `file_path` is provided
  - If yes: Update existing file and move to `Pending_Approval/`
  - If no: Create new file (legacy mode for backward compatibility)

### 3. `src/orchestration/orchestrator.py`

**Key Changes:**
- Added `_read_frontmatter()` helper method
- Added `_update_frontmatter()` helper method
- Added `_check_and_request_approval_single_file()` method
- Modified `_process_email_file()` to use single-file lifecycle
- Modified `_process_generic_file()` to:
  - Update file in place instead of creating new PLAN_*.md
  - Move file instead of copying
- Added `_finalize_executed_action()` method to:
  - Update file with execution result
  - Move to `Done/` (no need to move multiple files)

### 4. `src/skills/move_to_done.py`

**Key Changes:**
- Added `preserve_filename` parameter (default: `True`)
- When `preserve_filename=True`: Keep original filename
- When `preserve_filename=False`: Add timestamp (legacy mode)
- Handle duplicate filenames by adding timestamp

## Benefits

| Benefit | Before | After |
|---------|--------|-------|
| Files per task | 3 separate files | 1 evolving file |
| Task history | Scattered across files | Complete in one file |
| File tracking | Complex (match IDs) | Simple (same filename) |
| Obsidian view | Multiple files | Single file lifecycle |
| Dashboard counts | Confusing | Accurate |
| Debugging | Hard to trace | Easy to trace |

## Testing

Run the test script to see the single-file lifecycle in action:

```bash
cd D:\Hackathon-0\ai-employee
python test_single_file_lifecycle.py
```

This will:
1. Create a test email in `Needs_Action/`
2. Process it (moves to `Plans/`, then `Pending_Approval/`)
3. Show the file location at each stage
4. Display the file content evolution
5. Offer to clean up test files

## Migration Notes

### Existing Files

The system maintains **backward compatibility**:
- Old multi-file tasks will continue to work
- New single-file tasks use the improved lifecycle
- Orchestrator handles both modes

### Cleanup

After testing, you may want to clean up old multi-file tasks:
- Files in `Plans/` named `PLAN_*.md`
- Files in `Pending_Approval/` named `APPROVAL_*.md`

These can be manually reviewed and moved to `Done/` or deleted.

## Next Steps

1. ✅ Test the single-file lifecycle
2. Run the orchestrator and process real emails
3. Verify file moves correctly through all stages
4. Check Dashboard.md shows accurate counts
5. Review completed files in `Done/` for complete history

---

*Implementation Date: 2026-03-05*
*Version: 1.0.0 (Single-File Lifecycle)*
