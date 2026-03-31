---
name: email-mcp-server
description: |
  Model Context Protocol (MCP) server for email operations. Provides send,
  draft, search, and read capabilities via Gmail API. Supports attachment
  handling and approval-based sending workflow.
---

# Email MCP Server Skill

MCP server for comprehensive email operations.

## When to Use

- Send emails via Gmail API
- Create and manage drafts
- Search and read emails
- Handle email attachments
- Implement approval-based sending

## CLI Usage

```bash
# Show server status
python ai-employee/src/skills/email_mcp_server.py \
  --status \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Send test email
python ai-employee/src/skills/email_mcp_server.py \
  --send \
  --to "test@example.com" \
  --subject "Test Email" \
  --body "This is a test email" \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Create draft
python ai-employee/src/skills/email_mcp_server.py \
  --draft \
  --to "client@example.com" \
  --subject "Invoice #123" \
  --body "Please find attached..." \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Search emails
python ai-employee/src/skills/email_mcp_server.py \
  --search "is:unread from:client" \
  --vault "D:\Hackathon-0\AI_Employee_Vault"
```

## MCP Tools

The Email MCP Server provides these tools:

### send_email

Send an email via Gmail API.

```json
{
  "name": "send_email",
  "arguments": {
    "to": "client@example.com",
    "subject": "Invoice #123",
    "body": "Email body content",
    "cc": ["manager@example.com"],
    "attachments": ["/path/to/file.pdf"]
  }
}
```

### create_draft

Create a draft email without sending.

```json
{
  "name": "create_draft",
  "arguments": {
    "to": "client@example.com",
    "subject": "Proposal",
    "body": "Draft content..."
  }
}
```

### search_emails

Search Gmail with query.

```json
{
  "name": "search_emails",
  "arguments": {
    "query": "is:unread from:client@example.com",
    "max_results": 10
  }
}
```

### read_email

Read a specific email by ID.

```json
{
  "name": "read_email",
  "arguments": {
    "email_id": "18e4f2a3b5c6d7e8"
  }
}
```

### delete_email

Move email to trash.

```json
{
  "name": "delete_email",
  "arguments": {
    "email_id": "18e4f2a3b5c6d7e8"
  }
}
```

## Server Configuration

### MCP Server Setup

Add to Qwen Code MCP configuration:

```json
{
  "servers": {
    "email": {
      "command": "python",
      "args": ["ai-employee/src/skills/email_mcp_server.py", "--serve"],
      "env": {
        "VAULT_PATH": "D:/Hackathon-0/AI_Employee_Vault",
        "CREDENTIALS_PATH": "D:/Hackathon-0/credentials.json"
      }
    }
  }
}
```

### Environment Variables

```bash
# In .env file
VAULT_PATH=D:/Hackathon-0/AI_Employee_Vault
CREDENTIALS_PATH=D:/Hackathon-0/credentials.json
TOKEN_PATH=D:/Hackathon-0/token.json
DRY_RUN=false
```

## Integration

### Called By

- **Qwen Code**: Via MCP protocol
- **Orchestrator**: Direct skill calls
- **Approval Workflow**: Execute approved emails

### Calls

- [`gmail_auth`](../gmail-auth/SKILL.md) - Gmail API authentication
- [`send_email`](../send-email/SKILL.md) - Direct email sending
- [`log_action`](../log-action/SKILL.md) - Log email operations

## Error Handling

| Error | Behavior | Recovery |
|-------|----------|----------|
| Auth failed | Returns error response | Re-authenticate |
| Invalid recipient | Returns error | Fix email address |
| Attachment missing | Logs warning, sends without | Verify file path |
| API quota exceeded | Waits, retries | Wait for reset |

## Troubleshooting

### Server not starting

**Check:** Python path and file exist

**Fix:**
```bash
python ai-employee/src/skills/email_mcp_server.py --status
```

### Authentication error

**Check:** Token is valid

**Fix:**
```bash
python ai-employee/src/skills/gmail_auth.py auth --force-refresh
```

### MCP tools not available

**Check:** Server is registered in MCP config

**Fix:** Add server to MCP configuration file

## Related Skills

- [`gmail_auth`](../gmail-auth/SKILL.md) - Authentication required
- [`send_email`](../send-email/SKILL.md) - Direct email sending
- [`gmail_watcher`](../gmail-watcher/SKILL.md) - Email monitoring

## Example: Using Email MCP

```python
# Via MCP client
from mcp_client import MCPClient

client = MCPClient("http://localhost:8808")

# Send email
result = client.call_tool("send_email", {
    "to": "client@example.com",
    "subject": "Invoice #123",
    "body": "Please find attached invoice...",
    "attachments": ["invoice.pdf"]
})

print(f"Email sent: {result['message_id']}")

# Search emails
results = client.call_tool("search_emails", {
    "query": "is:unread from:client"
})

for email in results:
    print(f"From: {email['from']}, Subject: {email['subject']}")
```

## Version

1.0.0 (Silver Tier)
