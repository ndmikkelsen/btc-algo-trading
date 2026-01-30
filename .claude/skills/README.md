# Skills

Skills are reusable workflows for common knowledge management tasks. They provide structured approaches to formatting, organizing, and maintaining the knowledge system.

## Available Skills

### 1. formatting-notes

**Purpose**: Format markdown notes with consistent structure, fix links, and validate URLs

**When to use**:
- Cleaning up documentation
- Validating links in knowledge garden
- Before committing markdown changes
- After creating or updating multiple notes

**Input**: Files or directories to format  
**Output**: Formatted markdown with validated links

**Triggers**: "format notes", "fix markdown", "validate links", "clean up documentation"

---

## Workflow Example

```bash
# 1. Create or update notes
# ... work on documentation ...

# 2. Format and validate
# Use: formatting-notes skill
python3 .claude/scripts/format_markdown.py --dry-run .rules/

# 3. Review changes, apply if approved
python3 .claude/scripts/format_markdown.py .rules/

# 4. Commit formatted notes
git add .rules/
git commit -m "docs(rules): format and validate links"
```

## Integration with Knowledge System

### Before Syncing to Cognee

Formatting happens automatically via `/land`:

```bash
# /land automatically:
# 1. Formats all changed markdown files (Step 4)
# 2. Commits changes
# 3. Syncs to Cognee if .claude/ or .rules/ changed (Step 8)
```

### Manual Formatting (if needed)

```bash
# Format specific files
python3 .claude/scripts/format_markdown.py --yes file.md

# Preview changes
python3 .claude/scripts/format_markdown.py --dry-run .rules/
git commit -m "docs: format markdown files"
```

## Skill Development

Skills are tailored for second-brain's knowledge management focus:

- **second-brain**: Markdown formatting, link validation, Obsidian compatibility
- **media-stack**: Infrastructure planning, task breakdown, test-first development

Different repositories have different skills based on their primary use case.

## Related Documentation

- [Knowledge Capture](.rules/patterns/knowledge-capture.md)
- [Git Workflow](.rules/patterns/git-workflow.md)
- [/land Command](.claude/commands/land.md)
- [CONSTITUTION.md](../../CONSTITUTION.md)
- [VISION.md](../../VISION.md)
