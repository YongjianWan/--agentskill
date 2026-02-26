---
name: skill-manager
description: Manage OpenClaw skills - list, search, enable, disable, analyze, and organize skills. Use when you need to work with skills, manage skill collections, or optimize skill usage.
trigger: skill management, manage skills, list skills, enable skill, disable skill, skill analysis
---

# Skill Manager

A comprehensive skill management system for OpenClaw. This skill provides tools to manage, analyze, and optimize your skill collection.

## When to Use This Skill

Use this skill when you want to:
- See what skills are available
- Enable or disable specific skills
- Search for skills by functionality
- Analyze skill usage and quality
- Organize skills into logical groups
- Clean up unused or low-quality skills

## Core Functions

### 1. Skill Listing & Discovery
```
"List all available skills"
"Show me development skills"
"What skills do I have for document processing?"
```

### 2. Skill Search
```
"Search for skills related to code review"
"Find skills that can help with PDFs"
"Look for AI automation skills"
```

### 3. Skill Management
```
"Enable the frontend-design skill"
"Disable skills I don't use"
"Show me disabled skills"
```

### 4. Skill Analysis
```
"Analyze skill usage"
"Which skills are most effective?"
"Find skill conflicts or duplicates"
```

### 5. Skill Organization
```
"Create a development skill pack"
"Organize skills by category"
"Set up skill profiles for different tasks"
```

## Usage Examples

### Basic Management
```
User: "Show me all enabled skills"
Assistant: Lists currently enabled skills with descriptions

User: "Enable the article-extractor skill"
Assistant: Enables the skill and confirms

User: "Search for skills about security"
Assistant: Shows security-related skills
```

### Advanced Analysis
```
User: "Analyze my skill usage"
Assistant: Provides usage statistics, most used skills, recommendations

User: "Find duplicate functionality"
Assistant: Identifies skills with overlapping capabilities

User: "Optimize my skill collection"
Assistant: Suggests skills to disable based on usage patterns
```

### Organization
```
User: "Create a web development skill pack"
Assistant: Creates a pack with frontend-design, typescript-lsp, etc.

User: "Switch to documentation mode"
Assistant: Enables doc-related skills, disables others
```

## Implementation Details

This skill uses an integrated management system that provides:

### Core Management Functions
- **Direct skill operations** - Enable/disable/list/search via integrated script
- **JSON API** - Clean programmatic interface for all operations
- **Real-time updates** - Changes take effect immediately

### Integration with Existing Tools
- `scripts/skill-manager.sh` - Basic skill operations (fallback)
- `scripts/skill-analyzer.sh` - Usage and quality analysis
- `scripts/skill-packs.sh` - Skill grouping and profiles
- `skills/SKILLS-INDEX.md` - Skill catalog and documentation

### Technical Architecture
```
User Request → Skill Manager Skill → Integrated Manager Script → JSON Response
      ↓
  Skill State Updated
      ↓
  Next OpenClaw Session Loads Updated Skills
```

## Skill Categories

The system recognizes these categories:
- **Development** - Coding, review, git, testing
- **Design** - UI, frontend, visualization
- **Documentation** - Writing, Office docs, extraction
- **AI & Automation** - Self-improvement, automation
- **Tools & Utilities** - System tools, integrations
- **Language Support** - LSP servers, language tools

## Best Practices

1. **Start Small** - Enable only skills you need for current task
2. **Use Profiles** - Create skill packs for common workflows
3. **Regular Review** - Periodically analyze and clean up skills
4. **Quality Over Quantity** - Focus on high-quality, well-maintained skills
5. **Avoid Conflicts** - Be aware of overlapping functionality

## Troubleshooting

**Skill not working?**
- Check if skill is enabled
- Verify skill has proper SKILL.md file
- Look for error messages in skill directory

**Too many skills?**
- Use analysis to identify rarely used skills
- Create focused skill packs
- Disable skills not needed for current work

**Performance issues?**
- Reduce number of enabled skills
- Disable large or complex skills when not needed
- Use skill packs to load only necessary skills

## Integration with OpenClaw

This skill works with OpenClaw's skill loading system:
- Skills in `skills/` directory are automatically loaded
- Disabled skills (prefixed with `_`) are ignored
- Skill metadata is read from SKILL.md files
- Trigger conditions are based on skill descriptions

---

*Skill Manager v1.0 - Integrated skill management for OpenClaw*