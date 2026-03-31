# 🚀 AI Employee - Quick Commands Reference

## ⚡ First-Time Setup (5 Minutes)

```bash
# 1. Navigate to project
cd D:\Hackathon-0\ai-employee

# 2. Run setup (creates .env and directories)
python setup.py

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install browser
playwright install chromium

# 5. Edit credentials
notepad .env

# 6. Authenticate LinkedIn
python src/skills/linkedin_session_auth.py login

# 7. Start automation
python src/orchestration/orchestrator.py
```

---

## 🔐 LinkedIn Authentication

```bash
# Login (opens browser)
python src/skills/linkedin_session_auth.py login

# Test session
python src/skills/linkedin_session_auth.py test

# Check status
python src/skills/linkedin_session_auth.py status

# Logout
python src/skills/linkedin_session_auth.py logout
```

---

## 📝 Manual Posting

```bash
# Post immediately (bypasses approval)
python src/skills/linkedin_browser_post.py --content "Your post text here"

# Post from file
python src/skills/linkedin_browser_post.py --file path/to/post.md

# Test connection
python src/skills/linkedin_browser_post.py --test
```

---

## 🎯 Orchestrator Control

```bash
# Start (monitors every 30 seconds)
python src/orchestration/orchestrator.py

# Start with custom vault
python src/orchestration/orchestrator.py --vault "D:\Other\Vault"

# Stop
# Press Ctrl+C
```

---

## 📊 File Operations

```bash
# View pending posts
dir ..\AI_Employee_Vault\Pending_Approval\

# Approve post (move to Approved)
move ..\AI_Employee_Vault\Pending_Approval\LINKEDIN_xxx.md ..\AI_Employee_Vault\Approved\

# Retry failed post
move ..\AI_Employee_Vault\Failed\LINKEDIN_xxx.md ..\AI_Employee_Vault\Approved\

# View dashboard
type ..\AI_Employee_Vault\Dashboard.md

# View recent logs
Get-Content logs\orchestrator.log -Tail 50
```

---

## 🔧 Configuration

```bash
# Validate configuration
python src/config_loader.py

# Edit .env file
notepad .env

# Check git status (verify .env ignored)
git status
```

---

## 🐛 Troubleshooting

```bash
# Session expired - reauth
python src/skills/linkedin_session_auth.py logout
python src/skills/linkedin_session_auth.py login

# Browser issues - reinstall
playwright install chromium

# Missing dependencies
pip install -r requirements.txt

# Clear old logs
del logs\*.log
```

---

## 📁 Important Paths

| Path | Purpose |
|------|---------|
| `D:\Hackathon-0\ai-employee\.env` | ⚠️ Credentials (gitignored) |
| `D:\Hackathon-0\ai-employee\config\` | ⚠️ Sessions (gitignored) |
| `D:\Hackathon-0\ai-employee\logs\` | 📋 Logs (gitignored) |
| `D:\Hackathon-0\AI_Employee_Vault\Approved\` | ✅ Ready to post |
| `D:\Hackathon-0\AI_Employee_Vault\Pending_Approval\` | ⏳ Awaiting approval |
| `D:\Hackathon-0\AI_Employee_Vault\Done\` | ✅ Completed posts |

---

## 🔒 Security Checklist

Before GitHub upload:

```bash
# ✅ Verify .env is ignored
git status
# Should NOT see .env

# ✅ Verify .env.example exists
dir .env.example

# ✅ Clear credentials from .env
notepad .env
# Replace with placeholders
```

---

**Quick Start:** Run `python setup.py` then see README.md for details.
