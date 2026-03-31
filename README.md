# AI Employee - Personal AI FTE (Full-Time Equivalent)

**Your 24/7 Autonomous AI Employee powered by Qwen Code**

A local-first, agent-driven automation system that manages your personal and business affairs using Qwen Code as the reasoning engine and Obsidian as the knowledge base.

![Status](https://img.shields.io/badge/status-production--ready-green)
![Tier](https://img.shields.io/badge/tier-silver-blue)
![Python](https://img.shields.io/badge/python-3.13+-blue)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Folder Structure](#folder-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Agent Skills](#agent-skills)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Overview

The AI Employee is an autonomous agent system that operates 24/7 to:

1. **Perceive** - Monitor Gmail, WhatsApp, file systems, and other inputs via "Watcher" scripts
2. **Reason** - Use Qwen Code to analyze, plan, and make decisions
3. **Act** - Execute actions through MCP servers and file operations
4. **Remember** - Store everything in Obsidian for transparency and audit

### What It Can Do

| Category | Capabilities |
|----------|-------------|
| **Email** | Monitor Gmail, process emails, send responses (with approval) |
| **Social Media** | Auto-post to LinkedIn with generated content |
| **Messaging** | Monitor WhatsApp for urgent messages |
| **Workflow** | Human-in-the-loop approval for sensitive actions |
| **Scheduling** | Run tasks on schedule (daily briefings, weekly audits) |
| **Audit** | Complete logging of all actions for compliance |

---

## Features

### Core Features

| Feature | Description | Status |
|---------|-------------|--------|
| Gmail Watcher | Monitor Gmail for new emails | ✅ Complete |
| WhatsApp Watcher | Monitor WhatsApp Web for keywords | ✅ Complete |
| File System Watcher | Monitor folders for new files | ✅ Complete |
| LinkedIn Auto-Posting | Generate and post business content | ✅ Complete |
| Approval Workflow | Human-in-the-loop for sensitive actions | ✅ Complete |
| Agent Skills | Modular task execution | ✅ Complete |
| Audit Logging | Complete action history | ✅ Complete |
| Scheduling | Recurring tasks via cron/Task Scheduler | ✅ Complete |

### Human-in-the-Loop Safety

All sensitive actions require human approval before execution:

- ✉️ **Email sending** - Review before sending
- 💼 **LinkedIn posts** - Approve content before posting
- 💰 **Payments** - Verify before executing (Gold tier)
- 📝 **File operations** - Confirm deletions

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL SOURCES                         │
│         Gmail │ WhatsApp │ LinkedIn │ File System           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   PERCEPTION LAYER                          │
│              ┌─────────────────────┐                        │
│              │   Gmail Watcher     │                        │
│              │   WhatsApp Watcher  │                        │
│              │   Filesystem Watcher│                        │
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
│                   ACTION LAYER                              │
│              ┌─────────────────────┐                        │
│              │   MCP Servers       │                        │
│              │   - Email           │                        │
│              │   - LinkedIn        │                        │
│              │   - Browser         │                        │
│              └─────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
D:\Hackathon-0\
├── ai-employee/                 # Main application code
│   ├── src/
│   │   ├── orchestration/       # Main orchestrator
│   │   ├── skills/              # Agent Skills (modular tasks)
│   │   └── watchers/            # Watcher scripts (Gmail, WhatsApp, etc.)
│   ├── tests/                   # Test files
│   └── README.md                # Technical documentation
│
├── AI_Employee_Vault/           # Obsidian vault (knowledge base)
│   ├── Inbox/                   # New files dropped here
│   ├── Needs_Action/            # Items awaiting processing
│   ├── Plans/                   # Action plans
│   ├── Pending_Approval/        # Awaiting human approval
│   ├── Approved/                # Approved, ready for execution
│   ├── Failed/                  # Failed actions (review & retry)
│   ├── Done/                    # Completed items
│   ├── Logs/                    # Audit logs
│   ├── Dashboard.md             # Real-time status
│   ├── Company_Handbook.md      # Rules of engagement
│   └── Business_Goals.md        # Objectives and metrics
│
├── .qwen/skills/                # Qwen Code Agent Skills
│   ├── process-email/
│   ├── update-dashboard/
│   ├── linkedin-post/
│   └── ... (19 skills total)
│
├── config/                      # Configuration files
│   └── linkedin_session.json    # LinkedIn session (auto-generated)
│
├── .env                         # Environment variables (SENSITIVE - never commit)
├── .env.example                 # Environment template (safe to commit)
├── .gitignore                   # Git ignore rules
├── credentials.json             # OAuth credentials (SENSITIVE - never commit)
└── README.md                    # This file
```

---

## Prerequisites

### Required Software

| Software | Version | Purpose | Download |
|----------|---------|---------|----------|
| Python | 3.13+ | Runtime | [python.org](https://python.org) |
| Obsidian | 1.10.6+ | Knowledge base | [obsidian.md](https://obsidian.md) |
| Git | Latest | Version control | [git-scm.com](https://git-scm.com) |
| Qwen Code | Latest | AI reasoning | See setup guide |

### Hardware Requirements

- **Minimum:** 8GB RAM, 4-core CPU, 20GB free disk
- **Recommended:** 16GB RAM, 8-core CPU, SSD storage
- **For 24/7 operation:** Consider cloud VM (Oracle Cloud Free Tier, AWS, etc.)

---

## Installation

### Step 1: Clone the Repository

```bash
cd D:\Hackathon-0
git clone <repository-url> .
```

### Step 2: Install Python Dependencies

```bash
cd ai-employee
pip install -r requirements.txt
```

### Step 3: Install Playwright (for WhatsApp & LinkedIn)

```bash
pip install playwright
playwright install chromium
```

### Step 4: Set Up Environment

```bash
# Copy environment template
copy .env.example .env   # Windows
cp .env.example .env     # Linux/Mac

# Edit .env with your settings
notepad .env  # Windows
nano .env     # Linux/Mac
```

### Step 5: Set Up OAuth Credentials (Optional)

#### For Gmail Integration:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download `credentials.json` to project root
6. Set `ENABLE_GMAIL_WATCHER=true` in `.env`

#### For LinkedIn Integration:

Add your credentials to `.env`:
```bash
LINKEDIN_EMAIL=your.email@example.com
LINKEDIN_PASSWORD=your_password
```

⚠️ **Note:** Review LinkedIn Terms of Service before using automation.

### Step 6: Verify Installation

```bash
# Test Python imports
python -c "from src.watchers import FilesystemWatcher; print('OK')"

# Test vault structure
python ai-employee/verify_setup.py
```

---

## Configuration

### Environment Variables (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `VAULT_PATH` | `D:/Hackathon-0/AI_Employee_Vault` | Path to Obsidian vault |
| `ENABLE_GMAIL_WATCHER` | `false` | Enable Gmail monitoring |
| `ENABLE_FILESYSTEM_WATCHER` | `true` | Enable file drop monitoring |
| `ORCHESTRATOR_CHECK_INTERVAL` | `30` | Seconds between checks |
| `DASHBOARD_UPDATE_INTERVAL` | `300` | Seconds between dashboard updates |
| `DRY_RUN` | `false` | Test mode (no side effects) |
| `LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR |

### Sensitive Data

**NEVER commit these files:**
- `.env` - Contains credentials
- `credentials.json` - OAuth credentials
- `token.json` - Session tokens
- `config/*_session.json` - Browser sessions

These are already in `.gitignore`.

---

## Usage

### Starting the Orchestrator

```bash
cd D:\Hackathon-0\ai-employee

# Dry run mode (safe testing - no side effects)
python src/orchestration/orchestrator.py --dry-run

# Production mode
python src/orchestration/orchestrator.py
```

### Running as Background Service (Windows)

```batch
# Create start.bat
@echo off
cd /d D:\Hackathon-0\ai-employee
python src/orchestration/orchestrator.py
```

### Manual Skill Execution

```bash
# Process a specific email
python src/skills/process_email.py \
  "D:\Hackathon-0\AI_Employee_Vault\Needs_Action\EMAIL_123.md" \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Update dashboard
python src/skills/update_dashboard.py \
  "D:\Hackathon-0\AI_Employee_Vault"

# Test LinkedIn connection
python src/skills/linkedin_browser_post.py --test
```

### Workflow Example: Email Processing

1. **Gmail Watcher** detects new email → Creates file in `Needs_Action/`
2. **Orchestrator** processes file → Creates plan in `Plans/`
3. **Approval Request** created → File moved to `Pending_Approval/`
4. **Human reviews** → Moves file to `Approved/`
5. **Orchestrator executes** → Sends email via MCP
6. **File archived** → Moved to `Done/`

### Workflow Example: LinkedIn Posting

1. **Content generated** from `Business_Goals.md` or `Dashboard.md`
2. **Approval file created** in `Pending_Approval/`
3. **Human approves** → Moves to `Approved/`
4. **Orchestrator posts** via browser automation
5. **Success** → File moved to `Done/`
6. **Failure** → File moved to `Failed/` with error details

---

## Automation Commands

### Gmail Automation

#### Setup & Authentication

```bash
cd D:\Hackathon-0\ai-employee

# Authenticate Gmail (first-time setup)
python src/skills/gmail-auth.py auth

# Verify authentication status
python src/skills/gmail-auth.py status

# Refresh tokens (if expired)
python src/skills/gmail-auth.py refresh
```

#### Running Gmail Watcher

```bash
# Start Gmail Watcher (monitors for new emails)
python src/watchers/gmail_watcher.py

# Start with custom check interval (every 60 seconds)
python src/watchers/gmail_watcher.py --interval 60

# Test mode (check once and exit)
python src/watchers/gmail_watcher.py --test

# Enable in orchestrator (add to .env)
echo ENABLE_GMAIL_WATCHER=true >> .env
```

#### Processing Emails

```bash
# Process all emails in Needs_Action folder
python src/skills/process-email.py

# Process specific email file
python src/skills/process-email.py "D:\Hackathon-0\AI_Employee_Vault\Needs_Action\EMAIL_123.md"

# Process with custom vault path
python src/skills/process-email.py --vault "D:\Hackathon-0\AI_Employee_Vault"
```

#### Sending Emails

```bash
# Send email via MCP server
python src/skills/send-email.py \
  --to "client@example.com" \
  --subject "Invoice #123" \
  --body "Please find attached your invoice."

# Send with attachment
python src/skills/send-email.py \
  --to "client@example.com" \
  --subject "Invoice #123" \
  --body "Please find attached your invoice." \
  --attachment "D:\Hackathon-0\AI_Employee_Vault\Invoices\2026-03_Client.pdf"

# Dry run (preview without sending)
python src/skills/send-email.py --dry-run \
  --to "client@example.com" \
  --subject "Test" \
  --body "Test email"
```

#### Gmail MCP Server

```bash
# Start Gmail MCP server (for Qwen Code integration)
npx -y @modelcontextprotocol/server-gmail

# Or run locally
python src/mcp/email_mcp_server.py
```

---

### LinkedIn Automation

#### Setup & Authentication

```bash
cd D:\Hackathon-0\ai-employee

# Authenticate LinkedIn (first-time setup)
python src/skills/linkedin-auth.py login

# Verify session status
python src/skills/linkedin-auth.py status

# Clear session (if issues)
python src/skills/linkedin-auth.py logout
```

#### Running LinkedIn Content Generator

```bash
# Generate post content from Business_Goals.md
python src/skills/linkedin-content-generator.py

# Generate with custom topic
python src/skills/linkedin-content-generator.py --topic "Q1 2026 Achievements"

# Generate multiple post options
python src/skills/linkedin-content-generator.py --count 3

# Preview generated content (without creating approval)
python src/skills/linkedin-content-generator.py --preview
```

#### Creating & Posting to LinkedIn

```bash
# Create LinkedIn post (creates approval request)
python src/skills/linkedin-post.py \
  --content "Excited to share our Q1 results! Revenue up 45%."

# Post with hashtags
python src/skills/linkedin-post.py \
  --content "Just launched our new AI Employee feature!" \
  --hashtags "#AI #Automation #Productivity"

# Direct post (bypass approval - use with caution)
python src/skills/linkedin-post.py \
  --content "Quick update from our team" \
  --force-post

# Test LinkedIn connection
python src/skills/linkedin-browser-post.py --test
```

#### Browser-Based Posting (Playwright)

```bash
# Start LinkedIn browser automation
python src/skills/linkedin-browser-post.py \
  --content "Your post content here"

# Headless mode (no browser UI)
python src/skills/linkedin-browser-post.py \
  --content "Your post content here" \
  --headless

# With screenshot confirmation
python src/skills/linkedin-browser-post.py \
  --content "Your post content here" \
  --screenshot "D:\Hackathon-0\screenshot.png"
```

#### LinkedIn MCP Server

```bash
# Start LinkedIn MCP server (for Qwen Code integration)
python src/mcp/linkedin_mcp_server.py

# With custom session path
python src/mcp/linkedin_mcp_server.py \
  --session "D:\Hackathon-0\config\linkedin_session.json"
```

#### Scheduling LinkedIn Posts

```bash
# Schedule a post for later
python src/skills/scheduler.py \
  --action "linkedin_post" \
  --content "Scheduled post content" \
  --schedule "2026-03-31T18:00:00"

# View scheduled tasks
python src/skills/scheduler.py --list

# Cancel scheduled task
python src/skills/scheduler.py --cancel <task_id>
```

---

### Combined Workflows

#### Full Email-to-LinkedIn Workflow

```bash
# 1. Start Gmail watcher (background)
start python src/watchers/gmail_watcher.py

# 2. Start orchestrator (processes all inputs)
python src/orchestration/orchestrator.py

# 3. Generate LinkedIn content from business updates
python src/skills/linkedin-content-generator.py --auto

# 4. Review and approve pending actions
# Check: D:\Hackathon-0\AI_Employee_Vault\Pending_Approval\
```

#### Daily Automation Routine

```batch
@echo off
REM daily_automation.bat - Morning routine

cd D:\Hackathon-0\ai-employee

REM Start all watchers
start python src/watchers/gmail_watcher.py
start python src/watchers/filesystem_watcher.py

REM Run orchestrator
python src/orchestration/orchestrator.py

REM Generate daily briefing
python src/skills/update-dashboard.py --briefing
```

#### Weekly LinkedIn Posting Schedule (Windows Task Scheduler)

```batch
REM Create scheduled task for LinkedIn posts
schtasks /Create /TN "AI_Employee_LinkedIn" /TR "python D:\Hackathon-0\ai-employee\src\skills\linkedin-content-generator.py --auto" /SC WEEKLY /D MON /ST 09:00
```

---

## Agent Skills

The project uses **19 Agent Skills** for modular task execution:

### Bronze Tier (5 Skills)

| Skill | Purpose |
|-------|---------|
| `process-email` | Process email action files |
| `update-dashboard` | Refresh Dashboard.md |
| `log-action` | Audit logging |
| `create-approval-request` | Create approval files |
| `move-to-done` | Archive completed items |

### Silver Tier (14 Skills)

| Skill | Purpose |
|-------|---------|
| `gmail-auth` | Gmail OAuth authentication |
| `gmail-watcher` | Monitor Gmail |
| `whatsapp-watcher` | Monitor WhatsApp Web |
| `send-email` | Send emails via Gmail API |
| `create-plan` | Generate action plans |
| `approval-workflow` | Manage approvals |
| `email-mcp-server` | MCP server for email |
| `scheduler` | Task scheduling |
| `linkedin-post` | Create LinkedIn posts |
| `linkedin-auth` | LinkedIn authentication |
| `linkedin-browser-post` | Browser-based posting |
| `linkedin-content-generator` | Generate post content |
| `linkedin-mcp-server` | MCP server for LinkedIn |
| `browsing-with-playwright` | Browser automation |

Full documentation: [`.qwen/skills/README.md`](.qwen/skills/README.md)

---

## Security

### Best Practices

1. **Never commit sensitive files**
   ```bash
   git status  # Verify .env, credentials.json not staged
   ```

2. **Use environment variables**
   - Store credentials in `.env`
   - Use secrets manager for production

3. **Review approval requests**
   - Always verify before approving actions
   - Check `/Logs/` regularly

4. **Use dry-run mode for testing**
   ```bash
   python src/orchestration/orchestrator.py --dry-run
   ```

5. **Rotate credentials regularly**
   - Gmail OAuth: Every 30 days
   - LinkedIn: Every 60 days

### Audit Logging

All actions logged to:
- `/Vault/Logs/YYYY-MM-DD.json`
- `/Vault/Logs/actions.json`

Log entry format:
```json
{
  "timestamp": "2026-03-31T10:30:00Z",
  "action_type": "email_send",
  "actor": "orchestrator",
  "target": "client@example.com",
  "parameters": {"subject": "Invoice #123"},
  "approval_status": "approved",
  "approved_by": "human",
  "result": "success"
}
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| **Python not found** | Install Python 3.13+, add to PATH |
| **Module not found** | `pip install -r requirements.txt --force-reinstall` |
| **Gmail API error** | Re-authenticate: `python src/skills/gmail_auth.py auth` |
| **LinkedIn session expired** | Re-login: `python src/skills/linkedin_session_auth.py login` |
| **Playwright error** | `playwright install chromium` |
| **Vault not found** | Check `VAULT_PATH` in `.env` |

### LinkedIn Automation Troubleshooting

#### "Session expired or invalid" Error

**Symptom:** Logs show `Session expired or invalid` or posts fail with browser automation errors.

**Solution:**
```bash
cd D:\Hackathon-0\ai-employee

# Step 1: Clear expired session
python src/skills/linkedin_session_auth.py logout

# Step 2: Re-authenticate (browser will open)
python src/skills/linkedin_session_auth.py login

# Step 3: Verify session
python src/skills/linkedin_session_auth.py status
```

**Why it happens:** LinkedIn sessions expire after ~30-90 days, or if you change password, clear cookies, or LinkedIn detects automation.

#### "Page.goto: Timeout 60000ms exceeded" Error

**Symptom:** Browser opens but navigation to LinkedIn times out.

**Solutions:**
1. **Check internet connection** - Slow/intermittent connection causes timeouts
2. **Close other browser instances** - Multiple Chrome instances can conflict
3. **Increase timeout** - Edit `linkedin_mcp_server.py`, change timeout from 60000 to 120000
4. **Disable VPN/proxy** - These can interfere with Playwright

```bash
# Test LinkedIn manually to verify connectivity
python src/skills/linkedin_browser_post.py --test
```

#### "Could not enter post content" Error

**Symptom:** Browser navigates successfully but fails when typing post content.

**Causes & Solutions:**
1. **LinkedIn UI changed** - Selectors may need updating
2. **Cookie consent popup** - Manually dismiss any cookie banners
3. **Account restriction** - Check if LinkedIn limited your account

**Debug steps:**
```bash
# Run in non-headless mode to see what's happening
python src/skills/linkedin_browser_post.py \
  --content "Test post" \
  --no-headless
```

#### "Not logged in" Error (MCP Server)

**Symptom:** MCP server reports not logged in even with valid session.

**Solution:**
```bash
# Restart MCP server with fresh session
# Kill existing server process first
taskkill /F /IM node.exe  # Windows

# Then restart orchestrator
python src/orchestration/orchestrator.py
```

### Gmail Automation Troubleshooting

#### "403 Forbidden" or "Invalid Credentials"

**Solution:**
```bash
# Re-authenticate Gmail
python src/skills/gmail-auth.py auth

# Or refresh existing tokens
python src/skills/gmail-auth.py refresh
```

#### "Gmail API not enabled"

**Solution:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Enable Gmail API
4. Download fresh `credentials.json`

### Getting Help

1. Check logs in `AI_Employee_Vault/Logs/`
2. Run with `--dry-run` for safe testing
3. Review technical docs in `ai-employee/README.md`
4. Check Agent Skills docs in `.qwen/skills/README.md`

---

## Contributing

### Project Structure for Contributors

```
ai-employee/
├── src/
│   ├── orchestration/    # Core orchestration logic
│   ├── skills/           # Agent Skills (add new skills here)
│   └── watchers/         # Watcher scripts (add new watchers here)
└── tests/                # Add tests for new features
```

### Adding New Skills

1. Create skill in `ai-employee/src/skills/my_new_skill.py`
2. Create SKILL.md in `.qwen/skills/my-new-skill/SKILL.md`
3. Add to `.qwen/skills/README.md` index
4. Write tests in `ai-employee/tests/`

### Code Style

- Follow PEP 8
- Use type hints
- Add docstrings
- Write tests

---

## License

Built for Personal AI Employee Hackathon 0.

---

## Credits

**Tech Stack:**
- Qwen Code - AI Reasoning Engine
- Obsidian - Knowledge Base
- Python - Implementation Language
- Playwright - Browser Automation
- Model Context Protocol - External Integrations

**Resources:**
- [Qwen Code Documentation](https://agentfactory.panaversity.org/docs/AI-Tool-Landscape/claude-code-features-and-workflows)
- [Obsidian Help](https://help.obsidian.md/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Agent Skills Documentation](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)

---

*AI Employee v1.0.0 (Silver Tier) - Built with Qwen Code*
