---
name: linkedin-post
description: |
  Create and publish LinkedIn posts for business content. Supports multiple
  post templates (milestone, product_launch, thought_leadership, client_success,
  weekly_update). Includes approval workflow and scheduling capabilities.
---

# LinkedIn Post Skill

Automated LinkedIn posting for business content generation.

## When to Use

- Share business updates on LinkedIn
- Post milestones and achievements
- Publish thought leadership content
- Announce product launches
- Share client success stories

## CLI Usage

```bash
# Generate weekly update post
python ai-employee/src/skills/linkedin_post.py \
  --generate weekly_update \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Generate milestone post
python ai-employee/src/skills/linkedin_post.py \
  --generate milestone \
  --vault "D:\Hackathon-0\AI_Employee_Vault" \
  --title "Q1 Revenue Target Achieved" \
  --content "We've exceeded our Q1 revenue goal by 15%" \
  --achievement "$15,000 revenue in Q1"

# Generate thought leadership post
python ai-employee/src/skills/linkedin_post.py \
  --generate thought_leadership \
  --vault "D:\Hackathon-0\AI_Employee_Vault" \
  --title "AI in Business Automation" \
  --content "The future of business lies in intelligent automation..." \
  --insight "Companies using AI see 40% productivity gain"

# Test authentication
python ai-employee/src/skills/linkedin_post.py \
  --auth \
  --email "your@email.com"
```

## Post Templates

### Milestone Post

```
🎉 Business Update: {title}

{content}

Key Achievement: {achievement}

#BusinessGrowth #Milestone #Success
```

### Product Launch

```
🚀 Exciting News: {title}

{content}

What this means for you: {benefit}

Learn more: {link}

#ProductLaunch #Innovation #Business
```

### Thought Leadership

```
💡 Industry Insight: {title}

{content}

Key takeaway: {insight}

What's your perspective on this?

#ThoughtLeadership #Industry #Insights
```

### Client Success

```
⭐ Client Success Story: {title}

{content}

Results achieved: {results}

Ready to achieve similar results?

#ClientSuccess #CaseStudy #Results
```

### Weekly Update

```
📊 Weekly Business Update

{content}

Highlights:
- {highlight_1}
- {highlight_2}

Looking ahead: {outlook}

#WeeklyUpdate #Business #Progress
```

## Post Generation Flow

```
┌─────────────────────┐
│  Read Business Data │
│  (Goals, Dashboard) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Select Template    │
│  (based on content) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Generate Content   │
│  (fill template)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Add Hashtags       │
│  (3-5 relevant)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Create Approval    │
│  Request File       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Move to            │
│  Pending_Approval   │
└─────────────────────┘
```

## Approval File Format

Creates in `/Pending_Approval/`:

```markdown
---
type: approval_request
action: linkedin_post
post_type: milestone
title: Q1 Revenue Target Achieved
created: 2026-03-29T10:30:00Z
expires: 2026-03-30T10:30:00Z
status: pending
platform: LinkedIn
---

# LinkedIn Post Approval Request

## Post Content

🎉 Business Update: Q1 Revenue Target Achieved

We've exceeded our Q1 revenue goal by 15%...

Key Achievement: $15,000 revenue in Q1

#BusinessGrowth #Milestone #Success

---

## To Approve
Move this file to: `/Approved/`

## To Reject
Move this file to: `/Rejected/`
```

## Content Sources

### Business_Goals.md

```markdown
## Q1 2026 Objectives

### Revenue Target
- Monthly goal: $10,000
- Current MTD: $4,500

### Active Projects
1. Project Alpha - Due Jan 15
2. Project Beta - Due Jan 30
```

### Dashboard.md

```markdown
## Recent Activity
- Client A invoice paid
- Project Alpha milestone delivered
- New partnership signed
```

## Python API Usage

```python
from skills.linkedin_post import LinkedInPostSkill

# Initialize
linkedin = LinkedInPostSkill(
    vault_path="D:\\Hackathon-0\\AI_Employee_Vault"
)

# Generate post content
post = linkedin.generate_post(
    post_type="milestone",
    title="Q1 Target Achieved",
    content="We exceeded our goal by 15%",
    achievement="$15,000 revenue"
)

# Create approval request
result = linkedin.create_approval_request(
    post_content=post,
    vault_path="D:\\Hackathon-0\\AI_Employee_Vault"
)

print(f"Approval file created: {result['file_path']}")
```

## Integration

### Called By

- **Orchestrator**: Scheduled posting
- **Scheduler**: Regular posting times
- **Approval Workflow**: Execute approved posts

### Calls

- [`create_approval_request`](../create-approval-request/SKILL.md) - Request approval
- [`linkedin_browser_post`](../linkedin-browser-post/SKILL.md) - Publish via browser
- [`log_action`](../log-action/SKILL.md) - Log post creation

## Error Handling

| Error | Behavior | Recovery |
|-------|----------|----------|
| No content source | Returns error | Add data to Business_Goals |
| Template not found | Uses generic template | Use valid template name |
| Character limit exceeded | Truncates content | Edit content to fit |
| Auth failed | Returns error | Re-authenticate LinkedIn |

## Troubleshooting

### Post content empty

**Check:** Business_Goals.md has content

**Fix:**
```markdown
# Add to Business_Goals.md
## Recent Achievements
- Completed Project Alpha
- Signed Client ABC
```

### Approval not created

**Check:** Vault path is correct

**Fix:**
```bash
dir "D:\Hackathon-0\AI_Employee_Vault\Pending_Approval"
```

## Related Skills

- [`linkedin_auth`](../linkedin-auth/SKILL.md) - Authentication
- [`linkedin_browser_post`](../linkedin-browser-post/SKILL.md) - Browser-based posting
- [`approval_workflow`](../approval-workflow/SKILL.md) - Manage approvals

## Version

1.0.0 (Silver Tier)
