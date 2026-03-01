# AI Employee - Bronze Tier

**Your Personal AI Employee powered by Qwen Code**

A local-first, agent-driven automation system that manages your personal and business affairs 24/7 using Qwen Code as the reasoning engine and Obsidian as the knowledge base.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Bronze Tier Deliverables](#bronze-tier-deliverables)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

---

## Overview

The AI Employee is an autonomous agent system that:

1. **Perceives** - Monitors Gmail, file systems, and other inputs via "Watcher" scripts
2. **Reasons** - Uses Qwen Code to analyze, plan, and make decisions
3. **Acts** - Executes actions through MCP servers and file operations
4. **Remembers** - Stores everything in Obsidian for transparency and audit

### Bronze Tier Scope

The Bronze Tier provides the foundation:
- ✅ File system monitoring for task inputs
- ✅ Qwen Code integration for reasoning
- ✅ Obsidian vault as knowledge base
- ✅ Agent Skills for common tasks
- ✅ Human-in-the-loop approval workflow
- ✅ Audit logging for all actions

---

## Features

### Core Features

| Feature | Description | Status |
|---------|-------------|--------|
| File System Watcher | Monitor folder for new files | ✅ Complete |
| Email Processing | Process email action files | ✅ Complete |
| Plan Generation | Auto-create action plans | ✅ Complete |
| Approval Workflow | Human-in-the-loop for sensitive actions | ✅ Complete |
| Dashboard | Real-time system status | ✅ Complete |
| Audit Logging | Complete action history | ✅ Complete |
| Agent Skills | Modular task execution | ✅ Complete |

### Agent Skills

| Skill | Purpose |
|-------|---------|
| `process_email` | Process email files and create plans |
| `update_dashboard` | Refresh Dashboard.md with current state |
| `log_action` | Write actions to audit log |
| `create_approval_request` | Generate approval request files |
| `move_to_done` | Archive completed items |

---

## Architecture

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
│              │   Filesystem Watcher│                        │
│              └──────────┬──────────┘                        │
└─────────────────────────┼───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  OBSIDIAN VAULT (Local)                     │
│  /Needs_Action  /Plans  /Done  /Logs  /Pending_Approval     │
│  Dashboard.md  Company_Handbook.md  Business_Goals.md       │
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

---

## Quick Start

### Windows

```batch
cd ai-employee
start.bat
```

### Manual Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
copy .env.example .env   # Windows
cp .env.example .env     # Linux/Mac

# Edit .env with your settings
# Then start the orchestrator
python src/orchestration/orchestrator.py --dry-run
```

---

## Installation

### Prerequisites

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.13+ | Runtime |
| Obsidian | 1.10.6+ | Knowledge base |
| Git | Latest | Version control |
| Qwen Code | Latest | AI reasoning |

### Step-by-Step Installation

#### 1. Clone or Download

```bash
cd D:\Hackathon-0\ai-employee
```

#### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Setup Environment

```bash
cp .env.example .env
```

Edit `.env` with your settings (see [Configuration](#configuration)).

#### 5. Verify Installation

```bash
python -c "from watchers import FilesystemWatcher; print('OK')"
```

---

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Vault Configuration
OBSIDIAN_VAULT_PATH=D:\Hackathon-0\AI_Employee_Vault

# Watcher Settings
ENABLE_GMAIL_WATCHER=false          # Set true for Gmail monitoring
ENABLE_FILESYSTEM_WATCHER=true      # File drop monitoring

# Orchestrator Settings
ORCHESTRATOR_CHECK_INTERVAL=30      # Seconds between checks
DASHBOARD_UPDATE_INTERVAL=300       # Seconds between dashboard updates

# Development
DRY_RUN=false                       # Set true for testing
LOG_LEVEL=INFO                      # DEBUG, INFO, WARNING, ERROR
```

### Gmail Setup (Optional for Silver Tier)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Download `credentials.json` to project root
6. Set `ENABLE_GMAIL_WATCHER=true` in `.env`

---

## Usage

### Starting the System

```bash
# Dry run mode (no side effects)
python src/orchestration/orchestrator.py --dry-run

# Production mode
python src/orchestration/orchestrator.py
```

### Testing File Drop

1. Start the orchestrator
2. Drop a file into `AI_Employee_Vault/Inbox/`
3. Watcher detects the file
4. Action file created in `Needs_Action/`
5. Qwen processes and creates plan in `Plans/`
6. Dashboard updates automatically

### Manual Processing

```bash
# Process a specific email file
python src/skills/process_email.py \
  "D:\Hackathon-0\AI_Employee_Vault\Needs_Action\EMAIL_test.md" \
  "D:\Hackathon-0\AI_Employee_Vault"

# Update dashboard
python src/skills/update_dashboard.py \
  "D:\Hackathon-0\AI_Employee_Vault"

# Log an action
python src/skills/log_action.py \
  "D:\Hackathon-0\AI_Employee_Vault" \
  "test_action" "user" "test_target"
```

---

## Bronze Tier Deliverables

### ✅ Completed Deliverables

| # | Deliverable | Location | Status |
|---|-------------|----------|--------|
| 1 | Obsidian Vault | `AI_Employee_Vault/` | ✅ Complete |
| 2 | Dashboard.md | `AI_Employee_Vault/Dashboard.md` | ✅ Complete |
| 3 | Company Handbook | `AI_Employee_Vault/Company_Handbook.md` | ✅ Complete |
| 4 | Business Goals | `AI_Employee_Vault/Business_Goals.md` | ✅ Complete |
| 5 | Gmail Watcher | `src/watchers/gmail_watcher.py` | ✅ Complete |
| 6 | Filesystem Watcher | `src/watchers/filesystem_watcher.py` | ✅ Complete |
| 7 | Base Watcher | `src/watchers/base_watcher.py` | ✅ Complete |
| 8 | Agent Skills (5) | `src/skills/` | ✅ Complete |
| 9 | Orchestrator | `src/orchestration/orchestrator.py` | ✅ Complete |
| 10 | Test Suite | `tests/test_ai_employee.py` | ✅ Complete |
| 11 | Specifications | `SPECIFICATIONS.md` | ✅ Complete |
| 12 | Documentation | `README.md` | ✅ Complete |

### Folder Structure Verification

```bash
AI_Employee_Vault/
├── Inbox/                 ✅
├── Needs_Action/          ✅
├── Plans/                 ✅
├── Done/                  ✅
├── Pending_Approval/      ✅
├── Approved/              ✅
├── Rejected/              ✅
├── Logs/                  ✅
├── Briefings/             ✅
├── Accounting/            ✅
├── Dashboard.md           ✅
├── Company_Handbook.md    ✅
└── Business_Goals.md      ✅
```

---

## Project Structure

```
ai-employee/
├── src/
│   ├── watchers/
│   │   ├── __init__.py
│   │   ├── base_watcher.py       # Abstract base class
│   │   ├── gmail_watcher.py      # Gmail monitoring
│   │   └── filesystem_watcher.py # File drop monitoring
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── process_email.py      # Email processing skill
│   │   ├── update_dashboard.py   # Dashboard update skill
│   │   ├── log_action.py         # Audit logging skill
│   │   ├── create_approval_request.py  # Approval requests
│   │   └── move_to_done.py       # Archive completed items
│   └── orchestration/
│       ├── __init__.py
│       └── orchestrator.py       # Main orchestrator
├── tests/
│   ├── __init__.py
│   └── test_ai_employee.py       # Test suite
├── configs/
├── docs/
├── AI_Employee_Vault/            # Obsidian vault
│   ├── Inbox/
│   ├── Needs_Action/
│   ├── Plans/
│   ├── Done/
│   ├── Pending_Approval/
│   ├── Approved/
│   ├── Rejected/
│   ├── Logs/
│   ├── Briefings/
│   ├── Accounting/
│   ├── Dashboard.md
│   ├── Company_Handbook.md
│   └── Business_Goals.md
├── .env.example                  # Environment template
├── .gitignore
├── requirements.txt              # Python dependencies
├── pytest.ini                    # Pytest configuration
├── start.bat                     # Windows quick start
├── SPECIFICATIONS.md             # Technical specifications
└── README.md                     # This file
```

---

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Class

```bash
pytest tests/test_ai_employee.py::TestFilesystemWatcher -v
```

### Run with Coverage

```bash
pytest tests/ -v --cov=src --cov-report=html
```

### Test Categories

| Category | Command | Description |
|----------|---------|-------------|
| Unit Tests | `pytest tests/ -m unit` | Test individual components |
| Integration | `pytest tests/ -m integration` | Test component interaction |
| All Tests | `pytest tests/ -v` | Run complete test suite |

---

## Troubleshooting

### Common Issues

#### Python Not Found

```bash
# Check Python installation
python --version

# If not found, install from https://python.org
# Ensure "Add to PATH" is checked during installation
```

#### Module Not Found

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### Vault Not Found

```bash
# Verify vault path in .env
# Check that AI_Employee_Vault folder exists
dir D:\Hackathon-0\AI_Employee_Vault
```

#### Watcher Not Detecting Files

```bash
# Check if folder exists
dir AI_Employee_Vault\Inbox

# Verify file age (files must be > 5 seconds old)
# Check orchestrator logs in AI_Employee_Vault/Logs/
```

### Logs

Logs are stored in:
- Orchestrator: `AI_Employee_Vault/Logs/orchestrator_YYYY-MM-DD.log`
- Audit: `AI_Employee_Vault/Logs/YYYY-MM-DD.json`

### Getting Help

1. Check logs in `AI_Employee_Vault/Logs/`
2. Run with `--dry-run` for safe testing
3. Review `SPECIFICATIONS.md` for detailed requirements
4. Run test suite to verify installation

---

## Next Steps

### Silver Tier Upgrades

After completing Bronze Tier, consider adding:

1. **Gmail Integration** - Enable `ENABLE_GMAIL_WATCHER=true`
2. **MCP Servers** - Add email sending capabilities
3. **Scheduled Operations** - Add cron/Task Scheduler integration
4. **WhatsApp Watcher** - Monitor WhatsApp Web
5. **Enhanced Approval Workflow** - Add email/SMS notifications

### Learning Resources

- [Qwen Code Documentation](https://agentfactory.panaversity.org/docs/AI-Tool-Landscape/claude-code-features-and-workflows)
- [Obsidian Help](https://help.obsidian.md/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Python Watchdog Docs](https://python-watchdog.readthedocs.io/)

---

## Security Notes

⚠️ **Important Security Practices:**

1. **Never commit `.env`** - Contains sensitive configuration
2. **Never commit credentials** - Keep `credentials.json` out of version control
3. **Review approval requests** - Always verify before approving actions
4. **Monitor logs** - Check `AI_Employee_Vault/Logs/` regularly
5. **Use dry-run mode** - Test new configurations with `DRY_RUN=true`

---

## License

This project is part of the Personal AI Employee Hackathon 0.

---

## Credits

Built for the Personal AI Employee Hackathon 0: Building Autonomous FTEs in 2026

**Tech Stack:**
- Qwen Code - AI Reasoning Engine
- Obsidian - Knowledge Base
- Python - Implementation Language
- Model Context Protocol - External Integrations

---

*AI Employee v1.0.0 (Bronze Tier) - Built with Qwen Code*
