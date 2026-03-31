---
name: linkedin-mcp-server
description: |
  Model Context Protocol (MCP) server for LinkedIn operations. Provides
  post, schedule, analyze, and profile tools for LinkedIn integration.
  Enables Qwen Code to interact with LinkedIn via standardized MCP interface.
---

# LinkedIn MCP Server Skill

MCP server for LinkedIn operations and posting.

## When to Use

- Post to LinkedIn via MCP protocol
- Schedule LinkedIn posts
- Analyze post performance
- Manage LinkedIn profile

## CLI Usage

```bash
# Show server status
python ai-employee/src/skills/linkedin_mcp_server.py \
  --status \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Test post (browser automation)
python ai-employee/src/skills/linkedin_mcp_server.py \
  --post \
  --content "Test post from MCP server" \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Schedule post
python ai-employee/src/skills/linkedin_mcp_server.py \
  --schedule \
  --content "Scheduled content" \
  --time "2026-04-01T10:00:00" \
  --vault "D:\Hackathon-0\AI_Employee_Vault"
```

## MCP Tools

The LinkedIn MCP Server provides these tools:

### post_to_linkedin

Publish a post to LinkedIn.

```json
{
  "name": "post_to_linkedin",
  "arguments": {
    "content": "Excited to announce our Q1 results! 📊",
    "image_path": "D:\\Images\\results.jpg",
    "schedule_time": null
  }
}
```

### schedule_post

Schedule a post for future publishing.

```json
{
  "name": "schedule_post",
  "arguments": {
    "content": "Weekly update content...",
    "schedule_time": "2026-04-01T10:00:00Z",
    "timezone": "UTC"
  }
}
```

### get_profile

Get LinkedIn profile information.

```json
{
  "name": "get_profile",
  "arguments": {}
}
```

### analyze_post

Analyze post content for engagement potential.

```json
{
  "name": "analyze_post",
  "arguments": {
    "content": "Post content to analyze..."
  }
}
```

### get_analytics

Get post analytics and performance metrics.

```json
{
  "name": "get_analytics",
  "arguments": {
    "post_id": "urn:li:share:123456789",
    "time_range": "7d"
  }
}
```

## Server Configuration

### MCP Server Setup

Add to Qwen Code MCP configuration:

```json
{
  "servers": {
    "linkedin": {
      "command": "python",
      "args": ["ai-employee/src/skills/linkedin_mcp_server.py", "--serve"],
      "env": {
        "VAULT_PATH": "D:/Hackathon-0/AI_Employee_Vault",
        "LINKEDIN_EMAIL": "your.email@example.com",
        "LINKEDIN_PASSWORD": "your_password"
      }
    }
  }
}
```

## Integration

### Called By

- **Qwen Code**: Via MCP protocol
- **Orchestrator**: Direct skill calls
- **Approval Workflow**: Execute approved posts

### Calls

- [`linkedin_auth`](../linkedin-auth/SKILL.md) - Authentication
- [`linkedin_browser_post`](../linkedin-browser-post/SKILL.md) - Browser posting
- [`linkedin_content_generator`](../linkedin-content-generator/SKILL.md) - Content creation
- [`log_action`](../log-action/SKILL.md) - Log operations

## Error Handling

| Error | Behavior | Recovery |
|-------|----------|----------|
| Auth failed | Returns error | Re-authenticate |
| Post failed | Logs error | Check content/format |
| Session expired | Attempts refresh | Manual login if needed |
| Rate limited | Waits and retries | Wait for limit reset |

## Troubleshooting

### Server not starting

**Check:** Python path and file exist

**Fix:**
```bash
python ai-employee/src/skills/linkedin_mcp_server.py --status
```

### Authentication error

**Check:** Credentials in .env are valid

**Fix:**
```bash
python ai-employee/src/skills/linkedin_auth.py auth
```

### MCP tools not available

**Check:** Server registered in MCP config

**Fix:** Add server to MCP configuration file

## Related Skills

- [`linkedin_post`](../linkedin-post/SKILL.md) - Direct posting
- [`linkedin_auth`](../linkedin-auth/SKILL.md) - Authentication
- [`linkedin_browser_post`](../linkedin-browser-post/SKILL.md) - Browser posting

## Version

1.0.0 (Silver Tier)
