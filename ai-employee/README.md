# 🤖 AI Employee - Secure Automation System

> Intelligent LinkedIn posting and Gmail management with human-in-the-loop approval workflow.
> **Now with enhanced security using environment variables.**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-1.40.0-green.svg)](https://playwright.dev/)
[![Security](https://img.shields.io/badge/security-environment%20variables-brightgreen)]()

---

## 🔐 Security First

**IMPORTANT:** This project uses environment variables (`.env` file) to protect sensitive credentials.

**Before GitHub upload:**
1. ✅ All credentials moved to `.env` file
2. ✅ `.env` is in `.gitignore` (won't be committed)
3. ✅ `.env.example` template is safe to commit
4. ✅ Code reads from environment variables via `config_loader.py`

---

## 📖 Table of Contents

- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Commands Reference](#-commands-reference)
- [Project Structure](#-project-structure)
- [Security](#-security)
- [Troubleshooting](#-troubleshooting)

---

## 🚀 Quick Start

### 5-Minute Setup

```bash
# 1. Clone and enter directory
cd D:\Hackathon-0\ai-employee

# 2. Run setup script (creates .env and directories)
python setup.py

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install chromium

# 5. Edit .env file with your credentials
notepad .env

# 6. Authenticate LinkedIn
python src/skills/linkedin_session_auth.py login

# 7. Start automation
python src/orchestration/orchestrator.py
```

---

## 📦 Installation

### Step 1: Clone Repository

```bash
cd D:\Hackathon-0
git clone <repository-url> ai-employee
cd ai-employee
```

### Step 2: Run Setup Script

```bash
python setup.py
```

**What it does:**
- Creates `.env` file from `.env.example` template
- Creates vault directories (`Needs_Action/`, `Approved/`, `Done/`, etc.)
- Creates `config/` and `logs/` directories
- Verifies Python dependencies

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies:**
- `playwright` - Browser automation
- `playwright-stealth` - Avoid bot detection
- `python-dotenv` - Load `.env` files (CRITICAL for security)
- `PyYAML` - Parse YAML frontmatter
- `google-api-python-client` - Gmail integration
- `watchdog` - File system monitoring

### Step 4: Install Playwright Browsers

```bash
playwright install chromium
```

**Size:** ~300MB download

### Step 5: (Optional) Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## ⚙️ Configuration

### Step 1: Edit .env File

```bash
# Open .env in your editor
notepad .env          # Windows
nano .env             # macOS/Linux
code .env             # VS Code
```

### Required Credentials

#### LinkedIn Session Token

**Get it automatically (recommended):**
```bash
python src/skills/linkedin_session_auth.py login
```
This opens a browser, you login manually, and saves the session.

**Get it manually:**
1. Login to LinkedIn in Chrome
2. Press F12 (DevTools)
3. Go to **Application** → **Cookies** → `https://www.linkedin.com`
4. Find cookie named `li_at`
5. Copy its value
6. Paste into `.env`:
```env
LINKEDIN_SESSION_TOKEN=paste_your_li_at_cookie_here
```

#### Gmail OAuth Credentials

1. **Create Google Cloud Project:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Click "Create Project" → Name: "AI Employee"

2. **Enable Gmail API:**
   - APIs & Services → Enable APIs and Services
   - Search "Gmail API" → Enable

3. **Create OAuth Credentials:**
   - Credentials → Create Credentials → OAuth client ID
   - Application type: "Desktop app"
   - Download JSON file

4. **Add to .env:**
```env
GMAIL_CLIENT_ID=123456.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=ABCDEF-xyz123
GMAIL_PROJECT_ID=my-project-12345
```

### Step 2: Verify Configuration

```bash
python src/config_loader.py
```

**Expected output:**
```
✓ Loaded environment from: D:\Hackathon-0\ai-employee\.env
✅ All configuration valid!
📁 Vault path: D:\Hackathon-0\AI_Employee_Vault
🔧 Debug mode: False
⏱️  Cycle interval: 30s
```

---

## 🚀 Usage

### Start the Orchestrator

```bash
cd D:\Hackathon-0\ai-employee
python src/orchestration/orchestrator.py
```

**What it does:**
- Monitors folders every 30 seconds
- Processes approved LinkedIn posts
- Updates dashboard
- Logs all activities

**Stop with:** `Ctrl+C`

### Create LinkedIn Post

#### Step 1: Create Post File

Create file: `D:\Hackathon-0\AI_Employee_Vault\Pending_Approval\LINKEDIN_test_post.md`

```markdown
---
type: linkedin_post
post_type: thought_leadership
category: social_media
status: awaiting_approval
created: 2026-04-01T10:00:00
---

## Post Content

🚀 Just built an AI automation system!

Key takeaways:
✅ Start small
✅ Iterate quickly
✅ Monitor everything

#AI #Automation #Innovation
```

#### Step 2: Approve Post

Move file to Approved folder:
```bash
move D:\Hackathon-0\AI_Employee_Vault\Pending_Approval\LINKEDIN_test_post.md D:\Hackathon-0\AI_Employee_Vault\Approved\
```

#### Step 3: Watch It Post

Within 30 seconds, orchestrator will:
1. Detect file in `Approved/`
2. Launch browser
3. Login to LinkedIn
4. Create post
5. Publish content
6. Move file to `Done/`

---

## 📚 Commands Reference

### LinkedIn Session Management

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `python src/skills/linkedin_session_auth.py login` | Authenticate with LinkedIn | First-time setup or session expired |
| `python src/skills/linkedin_session_auth.py test` | Verify session is valid | Troubleshooting login issues |
| `python src/skills/linkedin_session_auth.py status` | Show session details | Check session age and validity |
| `python src/skills/linkedin_session_auth.py logout` | Clear saved session | Security or switching accounts |

### Manual Testing

```bash
# Test post to LinkedIn (bypasses approval)
python src/skills/linkedin_browser_post.py --content "Test post from AI Employee!"

# Test with file
python src/skills/linkedin_browser_post.py --file path/to/post.md

# Test connection only
python src/skills/linkedin_browser_post.py --test
```

### Configuration Management

```bash
# Validate configuration
python src/config_loader.py

# Run setup script
python setup.py
```

### File Operations

```bash
# View pending posts
dir ..\AI_Employee_Vault\Pending_Approval\

# Approve post
move ..\AI_Employee_Vault\Pending_Approval\LINKEDIN_xxx.md ..\AI_Employee_Vault\Approved\

# Retry failed post
move ..\AI_Employee_Vault\Failed\LINKEDIN_xxx.md ..\AI_Employee_Vault\Approved\

# View dashboard
type ..\AI_Employee_Vault\Dashboard.md
```

### View Logs

```bash
# Orchestrator log
type logs\orchestrator.log

# Last 50 lines
Get-Content logs\orchestrator.log -Tail 50

# LinkedIn posting log
type logs\linkedin_browser_post.log
```

---

## 📁 Project Structure

```
ai-employee/
│
├── .env                            # ⚠️  SECRETS (gitignored)
├── .env.example                    # Template for .env (safe to commit)
├── .gitignore                      # Git exclusions
├── README.md                       # This file
├── requirements.txt                # Python dependencies
├── setup.py                        # First-time setup script
│
├── src/
│   ├── config_loader.py            # Load .env variables (CRITICAL)
│   │
│   ├── orchestration/
│   │   └── orchestrator.py         # Main loop (monitors folders)
│   │
│   └── skills/
│       ├── linkedin_session_auth.py    # LinkedIn login
│       ├── linkedin_browser_post.py    # Post to LinkedIn
│       ├── linkedin_mcp_server.py      # MCP integration
│       └── gmail_reader.py             # Gmail processing
│
├── config/                         # ⚠️  Credentials (gitignored)
│   ├── linkedin_session.json       # LinkedIn cookies
│   ├── gmail_credentials.json      # Gmail OAuth
│   └── token.json                  # Gmail token
│
└── logs/                           # Logs (gitignored)
    ├── orchestrator.log            # Main log
    └── linkedin_browser_post.log   # LinkedIn log

../AI_Employee_Vault/               # Task management (outside project)
├── Needs_Action/                   # Incoming tasks
├── Plans/                          # Planned tasks
├── Pending_Approval/               # Posts awaiting approval
├── Approved/                       # Ready to publish
├── Done/                           # Published posts
├── Failed/                         # Failed posts (retry)
├── Rejected/                       # Rejected content
└── Dashboard.md                    # Real-time stats
```

---

## 🔐 Security

### Credential Protection

**Never commit these files:**

| File | Contains | Protection |
|------|----------|------------|
| `.env` | All secrets | In `.gitignore` |
| `config/linkedin_session.json` | LinkedIn cookies | In `.gitignore` |
| `config/gmail_credentials.json` | Gmail OAuth | In `.gitignore` |
| `config/token.json` | Gmail token | In `.gitignore` |
| `logs/*.log` | May contain sensitive data | In `.gitignore` |

**Safe to commit:**

| File | Purpose |
|------|---------|
| `.env.example` | Template (no secrets) |
| `src/*.py` | Source code |
| `requirements.txt` | Dependencies |
| `README.md` | Documentation |

### How Credentials Are Protected

1. **Environment Variables (`.env` file)**
   - Not tracked by git (`.gitignore`)
   - Read by `python-dotenv`
   - Never hardcoded in code

2. **Gitignore Rules**
   ```gitignore
   .env                    # Blocked
   config/*.json          # Blocked
   logs/*.log             # Blocked
   ```

3. **Config Loader**
   ```python
   from src.config_loader import Config
   
   # Reads from .env automatically
   token = Config.LINKEDIN_SESSION_TOKEN
   ```

### Before GitHub Upload

```bash
# Verify no secrets in git
git status

# Should NOT see:
# - .env
# - config/*.json
# - logs/*.log

# Should see:
# - .env.example
# - src/*.py
# - README.md

# Safe to push
git add .
git commit -m "Initial commit"
git push origin main
```

---

## 🐛 Troubleshooting

### LinkedIn Session Expired

**Symptom:**
```
Session expired or invalid
```

**Solution:**
```bash
# Clear old session
python src/skills/linkedin_session_auth.py logout

# Re-authenticate
python src/skills/linkedin_session_auth.py login
```

**Why it happens:** LinkedIn sessions expire after ~30-90 days.

---

### Configuration Errors

**Symptom:**
```
❌ LINKEDIN_SESSION_TOKEN not set in .env
```

**Solution:**
```bash
# Check .env file exists
dir .env

# Verify contents
type .env

# Run validation
python src/config_loader.py
```

---

### Post Not Publishing

**Check 1: Session valid?**
```bash
python src/skills/linkedin_session_auth.py test
```

**Check 2: File in Approved?**
```bash
dir ..\AI_Employee_Vault\Approved\
```

**Check 3: Orchestrator running?**
Should see output every 30 seconds.

**Check 4: Check logs**
```bash
type logs\linkedin_browser_post.log
```

---

### Browser Not Opening

**Symptom:**
```
Browser not found
```

**Solution:**
```bash
# Reinstall Playwright browsers
playwright install chromium
```

---

### Gmail Authentication Error

**Symptom:**
```
OAuth error: invalid_grant
```

**Solution:**
```bash
# Delete old token
del config\token.json

# Restart orchestrator (will re-authenticate)
python src/orchestration/orchestrator.py
```

---

## 🤝 Contributing

Contributions welcome!

1. Fork repository
2. Create feature branch: `git checkout -b feature/amazing`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push branch: `git push origin feature/amazing`
5. Open Pull Request

---

## 📄 License

MIT License - See LICENSE file

---

## 🙏 Acknowledgments

- [Playwright](https://playwright.dev/) - Browser automation
- [Google APIs](https://developers.google.com/) - Gmail integration
- [Python](https://python.org/) - Programming language

---

## 📞 Support

**Issues?** Check:
1. Troubleshooting section above
2. Log files in `logs/`
3. Dashboard at `AI_Employee_Vault/Dashboard.md`
4. GitHub Issues

---

**Made with ❤️ for secure automation**
