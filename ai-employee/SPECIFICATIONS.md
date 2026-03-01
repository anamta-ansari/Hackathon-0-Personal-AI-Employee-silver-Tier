# AI Employee Bronze Tier - Technical Specifications

**Version:** 1.0.0  
**Target:** Bronze Tier Deliverables  
**AI Engine:** Qwen Code  
**Knowledge Base:** Obsidian  

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Specifications](#component-specifications)
3. [Interface Definitions](#interface-definitions)
4. [Data Schemas](#data-schemas)
5. [Success Criteria](#success-criteria)

---

## System Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL SOURCES                         │
│         Gmail │ WhatsApp │ Bank APIs │ File System          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   PERCEPTION LAYER                          │
│              ┌─────────────────────┐                        │
│              │   Gmail Watcher     │                        │
│              │   (Python Script)   │                        │
│              └──────────┬──────────┘                        │
└─────────────────────────┼───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  OBSIDIAN VAULT (Local)                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  /Needs_Action  /Plans  /Done  /Logs  /Pending_...   │  │
│  │  Dashboard.md  Company_Handbook.md  Business_Goals.md│  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   REASONING LAYER                           │
│              ┌─────────────────────┐                        │
│              │     QWEN CODE       │                        │
│              │  Read → Think →     │                        │
│              │   Plan → Write      │                        │
│              └─────────────────────┘                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                ORCHESTRATION LAYER                          │
│              ┌─────────────────────┐                        │
│              │  orchestrator.py    │                        │
│              │  - Scheduling       │                        │
│              │  - Process Mgmt     │                        │
│              └─────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

### Bronze Tier Scope

| Component | Status | Priority |
|-----------|--------|----------|
| Gmail Watcher | Required | P0 |
| WhatsApp Watcher | Optional | P2 |
| File System Watcher | Optional | P2 |
| Qwen Code Integration | Required | P0 |
| MCP Email Server | Optional | P2 |
| Human-in-the-Loop | Required | P0 |
| Orchestrator | Required | P0 |

---

## Component Specifications

### 1. Gmail Watcher (`gmail_watcher.py`)

#### Specification: GMAIL-WATCHER-001

**Purpose:** Monitor Gmail for new unread important emails and create action files in Obsidian vault.

**Functional Requirements:**

| ID | Requirement | Priority |
|----|-------------|----------|
| GW-001 | Poll Gmail API every 120 seconds | P0 |
| GW-002 | Filter for unread AND important messages | P0 |
| GW-003 | Track processed message IDs to avoid duplicates | P0 |
| GW-004 | Create Markdown file in `/Needs_Action` for each new email | P0 |
| GW-005 | Log all operations to console and file | P1 |
| GW-006 | Handle API errors gracefully with retry logic | P1 |
| GW-007 | Support dry-run mode for testing | P2 |

**Technical Specifications:**

- **Input:** Gmail API credentials (OAuth 2.0)
- **Output:** Markdown files in `D:\Hackathon-0\AI_Employee_Vault\Needs_Action\`
- **Polling Interval:** 120 seconds (configurable)
- **Error Handling:** Exponential backoff, max 3 retries
- **Process Management:** Must support PM2/supervisord

**Interface:**

```python
class GmailWatcher(BaseWatcher):
    def __init__(self, vault_path: str, credentials_path: str)
    def check_for_updates(self) -> list[dict]
    def create_action_file(self, message: dict) -> Path
    def run(self) -> None  # Infinite loop
```

**Success Criteria:**
- [ ] New email arrives → `.md` file created within 130 seconds
- [ ] No duplicate files for same email
- [ ] Files follow specified Markdown schema
- [ ] Script runs continuously without crashing

---

### 2. Base Watcher (`base_watcher.py`)

#### Specification: BASE-WATCHER-001

**Purpose:** Provide abstract base class for all watcher implementations.

**Functional Requirements:**

| ID | Requirement | Priority |
|----|-------------|----------|
| BW-001 | Define abstract methods for all watchers | P0 |
| BW-002 | Provide common logging infrastructure | P1 |
| BW-003 | Implement main run loop with error handling | P0 |
| BW-004 | Support configurable check intervals | P1 |

**Technical Specifications:**

```python
from abc import ABC, abstractmethod
from pathlib import Path
import logging

class BaseWatcher(ABC):
    """
    Abstract base class for all watcher implementations.
    
    Attributes:
        vault_path (Path): Path to Obsidian vault root
        needs_action (Path): Path to Needs_Action folder
        check_interval (int): Seconds between checks
        logger (logging.Logger): Instance logger
        processed_ids (set): Track processed item IDs
    """
    
    @abstractmethod
    def check_for_updates(self) -> list:
        """Return list of new items to process"""
        pass
    
    @abstractmethod
    def create_action_file(self, item: any) -> Path:
        """Create .md file in Needs_Action folder"""
        pass
    
    def run(self) -> None:
        """Main infinite loop with error handling"""
        pass
```

**Success Criteria:**
- [ ] All abstract methods defined
- [ ] Concrete implementations can inherit cleanly
- [ ] Error handling prevents watcher death

---

### 3. Obsidian Vault Structure

#### Specification: VAULT-STRUCTURE-001

**Purpose:** Define folder structure and core files for AI Employee memory.

**Folder Structure:**

```
AI_Employee_Vault/
├── Inbox/                      # Raw incoming items (optional staging)
├── Needs_Action/               # Items requiring AI processing
├── Plans/                      # AI-generated action plans
├── Done/                       # Completed items (archive)
├── Pending_Approval/           # Awaiting human decision
├── Approved/                   # Approved for action
├── Rejected/                   # Rejected by human
├── Logs/                       # System audit logs
├── Briefings/                  # CEO briefings/reports
├── Accounting/                 # Financial records
├── Dashboard.md                # Real-time status
├── Company_Handbook.md         # Rules of engagement
└── Business_Goals.md           # Objectives and metrics
```

**Core File Specifications:**

#### Dashboard.md (`DASHBOARD-001`)

**Schema:**
```markdown
# Dashboard

## Last Updated
{ISO 8601 timestamp}

## Quick Stats
| Metric | Value |
|--------|-------|
| Pending Items | {count in /Needs_Action} |
| Pending Approval | {count in /Pending_Approval} |
| Completed Today | {count in /Done today} |

## Active Projects
{List from Business_Goals.md}

## Recent Activity
{Last 10 actions from Logs}

## Alerts
{Any items requiring immediate attention}
```

#### Company_Handbook.md (`HANDBOOK-001`)

**Schema:**
```markdown
# Company Handbook

## Rules of Engagement

### Communication Rules
1. Always be polite and professional
2. Response time target: < 24 hours
3. Escalate emotional/conflict messages to human

### Financial Rules
1. Flag any payment over $500 for approval
2. Never auto-approve new payees
3. Log all transactions

### Privacy Rules
1. Never share credentials
2. Redact sensitive info in logs
3. Minimum data collection
```

#### Business_Goals.md (`GOALS-001`)

**Schema:**
```markdown
# Business Goals

## Q1 2026 Objectives

### Revenue Target
- Monthly goal: ${amount}
- Current MTD: ${amount}

### Key Metrics
| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| {metric} | {target} | {threshold} |

### Active Projects
1. {Project Name} - Due {date} - Budget ${amount}
```

**Success Criteria:**
- [ ] All 10 folders exist
- [ ] All 3 core files created with proper schema
- [ ] Qwen Code can read/write all files

---

### 4. Qwen Code Integration

#### Specification: QWEN-INTEGRATION-001

**Purpose:** Enable Qwen Code to read, reason, and write to Obsidian vault.

**Functional Requirements:**

| ID | Requirement | Priority |
|----|-------------|----------|
| QI-001 | Qwen can read all vault files | P0 |
| QI-002 | Qwen can create/update Markdown files | P0 |
| QI-003 | Qwen creates Plan.md for each Needs_Action item | P0 |
| QI-004 | Qwen moves files to appropriate folders | P0 |
| QI-005 | Qwen logs all actions | P1 |
| QI-006 | Agent Skills implemented for common tasks | P0 |

**MCP Configuration:**

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "D:\\Hackathon-0\\AI_Employee_Vault"]
    }
  }
}
```

**Agent Skills Required:**

| Skill | Purpose | Input | Output |
|-------|---------|-------|--------|
| `process_email` | Process email action files | Path to .md file | Plan.md created |
| `create_approval_request` | Generate approval file | Action details | File in /Pending_Approval |
| `update_dashboard` | Refresh Dashboard.md | Vault state | Updated Dashboard.md |
| `log_action` | Write to audit log | Action details | Entry in Logs/ |

**Success Criteria:**
- [ ] Qwen reads vault files without errors
- [ ] Qwen creates properly formatted Plan.md files
- [ ] Agent Skills execute correctly
- [ ] File movements work as expected

---

### 5. Orchestrator (`orchestrator.py`)

#### Specification: ORCHESTRATOR-001

**Purpose:** Master process for scheduling, triggering Qwen, and managing watchers.

**Functional Requirements:**

| ID | Requirement | Priority |
|----|-------------|----------|
| OR-001 | Start all configured watchers | P0 |
| OR-002 | Monitor /Needs_Action for new files | P0 |
| OR-003 | Trigger Qwen Code when new items detected | P0 |
| OR-004 | Monitor /Approved for actions to execute | P1 |
| OR-005 | Update Dashboard.md periodically | P1 |
| OR-006 | Log all orchestration events | P1 |
| OR-007 | Support graceful shutdown | P2 |

**Technical Specifications:**

- **Check Interval:** 30 seconds for Needs_Action folder
- **Dashboard Update:** Every 5 minutes
- **Process Management:** PM2 compatible
- **Logging:** JSON format to `/Logs/orchestrator_{date}.json`

**Interface:**

```python
class Orchestrator:
    def __init__(self, vault_path: str, config: dict)
    def start_watchers(self) -> None
    def check_needs_action(self) -> list[Path]
    def trigger_qwen(self, items: list[Path]) -> None
    def process_approvals(self) -> None
    def update_dashboard(self) -> None
    def run(self) -> None  # Main loop
```

**Success Criteria:**
- [ ] Watchers start successfully
- [ ] Qwen triggered within 35 seconds of new file
- [ ] Dashboard updates every 5 minutes
- [ ] Clean shutdown on SIGINT/SIGTERM

---

### 6. Agent Skills (`src/skills/`)

#### Specification: AGENT-SKILLS-001

**Purpose:** Modular skills for Qwen Code to execute specific tasks.

**Required Skills for Bronze Tier:**

#### Skill: process_email

**Specification:**
```python
"""
Skill: process_email

Purpose: Process an email action file and create a plan

Input: 
    - file_path: Path to email .md file in /Needs_Action
    
Output:
    - Creates Plan.md in /Plans/
    - Updates original file status
    
Behavior:
    1. Read email content
    2. Analyze sender, subject, urgency
    3. Generate suggested actions
    4. Create Plan.md with checkboxes
    5. If action requires approval, create file in /Pending_Approval/
"""
```

#### Skill: update_dashboard

**Specification:**
```python
"""
Skill: update_dashboard

Purpose: Refresh Dashboard.md with current vault state

Input: None (reads vault state)

Output:
    - Updated Dashboard.md
    
Behavior:
    1. Count files in each folder
    2. Read recent logs
    3. Update timestamp
    4. Write new Dashboard.md
"""
```

#### Skill: log_action

**Specification:**
```python
"""
Skill: log_action

Purpose: Write action to audit log

Input:
    - action_type: str
    - actor: str (qwen_code/watcher/orchestrator)
    - target: str
    - parameters: dict
    - result: str (success/failure/pending)
    
Output:
    - JSON entry in /Logs/{date}.json
    
Schema:
{
    "timestamp": "ISO8601",
    "action_type": "string",
    "actor": "string",
    "target": "string",
    "parameters": {},
    "approval_status": "string",
    "approved_by": "string|null",
    "result": "string"
}
"""
```

**Success Criteria:**
- [ ] All 3 skills implemented
- [ ] Skills can be invoked by Qwen
- [ ] Skills produce expected outputs

---

## Interface Definitions

### Watcher → Vault Interface

```
Watcher creates file:
  Location: {vault_path}/Needs_Action/{TYPE}_{id}_{timestamp}.md
  Format: Markdown with YAML frontmatter
  Permissions: Read/Write for Qwen, Read for Orchestrator
```

### Orchestrator → Qwen Interface

```
Trigger mechanism:
  1. Orchestrator detects new file in /Needs_Action
  2. Creates state file in /Plans/PROCESSING_{filename}.md
  3. Invokes Qwen with prompt template
  4. Qwen processes and updates files
  5. Orchestrator verifies completion
```

### Qwen → MCP Interface

```
MCP calls available:
  - filesystem.read_file(path: str) -> str
  - filesystem.write_file(path: str, content: str) -> bool
  - filesystem.list_directory(path: str) -> list[str]
  - filesystem.move_file(src: str, dst: str) -> bool
```

---

## Data Schemas

### Email Action File Schema

```yaml
---
type: email
from: string (email address or name)
subject: string
received: ISO8601 timestamp
priority: low|medium|high
status: pending|processing|completed|requires_approval
---
```

### Plan File Schema

```yaml
---
type: plan
created: ISO8601 timestamp
status: pending|in_progress|completed|blocked
requires_approval: boolean
---
```

### Approval Request Schema

```yaml
---
type: approval_request
action: string (email_send|payment|etc)
created: ISO8601 timestamp
expires: ISO8601 timestamp (optional)
status: pending|approved|rejected
---
```

### Log Entry Schema

```json
{
  "timestamp": "2026-02-28T10:30:00Z",
  "action_type": "email_processed",
  "actor": "qwen_code",
  "target": "EMAIL_abc123.md",
  "parameters": {"sender": "client@example.com"},
  "approval_status": "not_required",
  "approved_by": null,
  "result": "success"
}
```

---

## Success Criteria

### Bronze Tier Completion Checklist

| # | Deliverable | Verification Method | Status |
|---|-------------|---------------------|--------|
| 1 | Obsidian vault with folder structure | `ls AI_Employee_Vault/` shows 10 folders | ☐ |
| 2 | Dashboard.md exists with proper schema | File contains required sections | ☐ |
| 3 | Company_Handbook.md exists | File contains 5+ rules | ☐ |
| 4 | Business_Goals.md exists | File contains Q1 objectives | ☐ |
| 5 | Gmail Watcher implemented | `gmail_watcher.py` exists and runs | ☐ |
| 6 | Watcher creates action files | Test email → file in /Needs_Action | ☐ |
| 7 | Qwen Code integration works | Qwen reads/writes vault files | ☐ |
| 8 | Agent Skills implemented | 3 skills in `/src/skills/` | ☐ |
| 9 | Orchestrator runs continuously | `orchestrator.py` stays alive | ☐ |
| 10 | End-to-end flow works | Email → File → Plan → Dashboard | ☐ |
| 11 | Audit logging functional | Logs appear in /Logs/ | ☐ |
| 12 | Documentation complete | README.md with setup instructions | ☐ |

### Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| Email detection latency | < 130 seconds | Time from email arrival to file creation |
| Qwen trigger latency | < 35 seconds | Time from file creation to Qwen invocation |
| Dashboard update frequency | Every 5 minutes | Timestamp freshness |
| System uptime | > 99% (Bronze: > 95%) | Orchestrator/Watcher alive time |
| Error rate | < 1% of operations | Failed vs total operations |

### Security Requirements

| Requirement | Verification |
|-------------|--------------|
| No credentials in code | Grep for patterns, review .env |
| .env in .gitignore | Check .gitignore file |
| Audit logs created | Verify log file entries |
| HITL for sensitive actions | Approval files required |

---

## Testing Strategy

### Unit Tests

| Component | Test Cases |
|-----------|------------|
| GmailWatcher | check_for_updates returns list, create_action_file creates valid markdown |
| BaseWatcher | Abstract methods enforced, run loop handles errors |
| Orchestrator | start_watchers, check_needs_action, trigger_qwen |
| Agent Skills | process_email, update_dashboard, log_action |

### Integration Tests

1. **Email Flow Test:** Send test email → Verify file created → Verify Qwen processes → Verify Dashboard updated
2. **Approval Flow Test:** Create approval request → Move to Approved → Verify action executed
3. **Error Recovery Test:** Kill watcher → Verify Orchestrator detects → Verify restart

### Acceptance Criteria

All 12 Bronze Tier deliverables must pass verification with documented evidence (screenshots, logs, or demo video).

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-02-28 | AI Employee Team | Initial specification |

---

*This specification document serves as the single source of truth for Bronze Tier implementation.*
