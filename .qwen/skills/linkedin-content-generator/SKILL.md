---
name: linkedin-content-generator
description: |
  Generate LinkedIn post content from business data in Vault. Reads
  Business_Goals.md, Dashboard.md, and completed tasks to create engaging
  post content with appropriate hashtags and formatting.
---

# LinkedIn Content Generator Skill

AI-powered content generation for LinkedIn posts.

## When to Use

- Need fresh post ideas from business data
- Convert achievements into posts
- Generate thought leadership content
- Create weekly update summaries

## CLI Usage

```bash
# Generate content from business goals
python ai-employee/src/skills/linkedin_content_generator.py \
  --source business_goals \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Generate from completed tasks
python ai-employee/src/skills/linkedin_content_generator.py \
  --source done_folder \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Generate thought leadership
python ai-employee/src/skills/linkedin_content_generator.py \
  --type thought_leadership \
  --topic "AI in Business" \
  --vault "D:\Hackathon-0\AI_Employee_Vault"

# Generate with custom data
python ai-employee/src/skills/linkedin_content_generator.py \
  --type milestone \
  --data "{\"title\": \"Q1 Target\", \"value\": \"$15,000\"}" \
  --vault "D:\Hackathon-0\AI_Employee_Vault"
```

## Content Sources

### Business_Goals.md

Reads objectives and metrics:

```markdown
## Q1 2026 Objectives

### Revenue Target
- Monthly goal: $10,000
- Current MTD: $4,500

### Active Projects
1. Project Alpha - Due Jan 15
2. Project Beta - Due Jan 30
```

**Generated Post:**
```
📊 Q1 Progress Update

We're making great strides toward our Q1 revenue target of $10,000!
Current MTD: $4,500 (45% achieved)

Active projects keeping us busy:
• Project Alpha (due Jan 15)
• Project Beta (due Jan 30)

#BusinessGrowth #Q1Goals #Progress
```

### Dashboard.md

Reads recent activity:

```markdown
## Recent Activity
- Client A invoice paid
- Project Alpha milestone delivered
- New partnership signed
```

**Generated Post:**
```
🎉 Great week for our team!

✓ Client A invoice paid - Thank you for your trust!
✓ Project Alpha milestone delivered - On track for completion
✓ New partnership signed - Exciting collaboration ahead

Grateful for our amazing clients and partners!

#ClientSuccess #Partnership #Milestone
```

### Done Folder

Analyzes completed tasks:

```
/Done/
├── EMAIL_client_invoice.md
├── PROJECT_alpha_phase1.md
└── MEETING_partnership_signing.md
```

**Generated Post:**
```
✨ This Week in Review

Successfully completed:
• Client invoicing and payment processing
• Project Alpha Phase 1 delivery
• Strategic partnership agreement

Productivity level: 100% 📈

#WeeklyReview #Productivity #Success
```

## Content Types

### Milestone Content

```python
{
    "type": "milestone",
    "template": "🎉 Business Update: {title}",
    "data_fields": ["title", "content", "achievement"],
    "hashtags": ["#BusinessGrowth", "#Milestone", "#Success"]
}
```

### Thought Leadership

```python
{
    "type": "thought_leadership",
    "template": "💡 Industry Insight: {title}",
    "data_fields": ["title", "content", "insight", "question"],
    "hashtags": ["#ThoughtLeadership", "#Industry", "#Insights"]
}
```

### Weekly Update

```python
{
    "type": "weekly_update",
    "template": "📊 Weekly Business Update",
    "data_fields": ["highlights", "metrics", "outlook"],
    "hashtags": ["#WeeklyUpdate", "#Business", "#Progress"]
}
```

## Python API Usage

```python
from skills.linkedin_content_generator import LinkedInContentGenerator

# Initialize
generator = LinkedInContentGenerator(
    vault_path="D:\\Hackathon-0\\AI_Employee_Vault"
)

# Generate from business goals
content = generator.generate_from_business_goals()
print(content)

# Generate from done folder
content = generator.generate_from_done_folder()
print(content)

# Generate custom thought leadership
content = generator.generate_thought_leadership(
    topic="AI Automation",
    key_points=["Productivity gains", "Cost reduction", "Future trends"]
)
print(content)
```

## Integration

### Called By

- [`linkedin_post`](../linkedin-post/SKILL.md) - Content source
- **Orchestrator** - Scheduled content generation
- **Scheduler** - Weekly auto-generation

### Calls

- **File System**: Read Business_Goals.md, Dashboard.md, Done folder
- [`log_action`](../log-action/SKILL.md) - Log generation

## Error Handling

| Error | Behavior | Recovery |
|-------|----------|----------|
| Source file missing | Returns error | Create source file |
| No data to generate from | Returns empty | Add business data |
| Invalid content type | Uses default | Use valid type |
| Template error | Logs error | Fix template |

## Troubleshooting

### No content generated

**Check:** Source files have content

**Fix:**
```markdown
# Add to Business_Goals.md
## Recent Achievements
- Completed Project X
- Signed Client Y
```

### Generated content too short

**Check:** More data in source files

**Fix:** Add detailed information to Business_Goals.md

## Related Skills

- [`linkedin_post`](../linkedin-post/SKILL.md) - Uses generated content
- [`update_dashboard`](../update-dashboard/SKILL.md) - Updates source data

## Version

1.0.0 (Silver Tier)
