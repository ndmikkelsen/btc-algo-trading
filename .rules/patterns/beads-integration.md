---
description: Issue tracking with Beads (bd) for second-brain
tags: [beads, issue-tracking, workflow, git-integration]
last_updated: 2026-01-28
---

# Beads Issue Tracking

This project uses [Beads (bd)](https://github.com/steveyegge/beads) for ALL issue tracking.

## Core Rules

- **Track ALL work in bd** - Never use markdown TODOs or comment-based task lists
- **Use `bd ready`** to find available work
- **Use `bd create`** to track new issues/tasks/bugs
- **Sync with kanban** using `node .claude/scripts/sync-beads-to-todo.js`
- **Git hooks auto-sync** on commit/merge

## Quick Reference

```bash
bd ready                              # Show issues ready to work (no blockers)
bd list --status=open                 # List all open issues
bd create "Title" -t task -p 1        # Create new issue
bd update <id> --status=in_progress   # Claim work
bd close <id> --reason "Done"         # Mark complete
bd dep add <issue> <depends-on>       # Add dependency
```

## Workflow

1. **Check for ready work**: `bd ready`
2. **Claim an issue**: `bd update <id> --status=in_progress`
3. **Do the work**: Implement, test, document
4. **Mark complete**: `bd close <id> --reason "Completed"`
5. **Sync to kanban**: `node .claude/scripts/sync-beads-to-todo.js`

## Issue Types

| Type | Purpose | Example |
|------|---------|---------|
| `bug` | Something broken | "Wiki link navigation broken in neovim" |
| `feature` | New functionality | "Add semantic search to knowledge garden" |
| `task` | Work item | "Document cognee integration workflow" |
| `epic` | Large feature with subtasks | "Cognee Integration" |
| `chore` | Maintenance | "Update knowledge garden INDEX.md" |

## Priorities

| Priority | Meaning | When to Use |
|----------|---------|-------------|
| `0` | Critical | Broken workflows, data loss, blocked work |
| `1` | High | Major features, important improvements |
| `2` | Medium | Default priority, nice-to-have features |
| `3` | Low | Polish, optimization, minor improvements |
| `4` | Backlog | Future ideas, deferred work |

## Managing Dependencies

Dependencies can be added at creation time or to existing issues.

### At Creation Time

```bash
# Child depends on parent
bd create "Child task" \
  --description="Details" \
  -p 1 \
  --deps SB-parent

# Task blocked by multiple issues
bd create "Blocked task" \
  --description="Details" \
  --deps SB-blocker1,SB-blocker2
```

### Add to Existing Issues

Use `bd dep`, NOT `bd update --deps`:

```bash
# Make SB-abc depend on SB-xyz
bd dep add SB-abc SB-xyz

# Same thing using --blocks syntax
bd dep SB-xyz --blocks SB-abc

# Check dependencies
bd dep list SB-abc

# Show full dependency tree
bd dep tree SB-abc
```

**Known issue**: `bd dep` with `--json` flag may cause a panic. Omit `--json` for dep commands.

## Auto-Sync

Beads automatically syncs with git:

- **Exports** to `.beads/issues.jsonl` after changes (5s debounce)
- **Imports** from JSONL when newer (e.g., after `git pull`)
- **No manual export/import needed!**

### Sync Workflow

```bash
# After closing issues or making changes
bd close SB-abc --reason "Done"
# (Auto-exports to .beads/issues.jsonl after 5s)

# Sync to Obsidian kanban
node .claude/scripts/sync-beads-to-todo.js

# Commit the JSONL file
git add .beads/issues.jsonl to-do.md
git commit -m "chore(beads): close SB-abc and sync kanban"

# Push to share with team/other sessions
git push origin feature/your-branch

# On another machine or after git pull
git pull origin feature/your-branch
# (Auto-imports from .beads/issues.jsonl)

bd list
# Shows updated issues!
```

## Integration with Cognee

Document important issues in Cognee for searchability:

```bash
# 1. Create issue in Beads
bd create "Add semantic search to knowledge garden" \
  --description="Implement semantic search using Cognee API" \
  -t feature -p 1

# 2. Document the issue context in Cognee
cat > /tmp/cognee-search-issue.txt << 'EOF'
Issue: SB-search
Title: Add semantic search to knowledge garden
Priority: High
Type: Feature

Goal: Add semantic search capabilities to knowledge garden using Cognee.

Implementation Plan:
- Create search command in .claude/commands/
- Integrate with Cognee API
- Add search UI to Obsidian
EOF

curl -X POST http://localhost:8000/api/v1/add \
  -F "data=@/tmp/cognee-search-issue.txt" \
  -F "datasetName=second-brain-issues"

curl -X POST http://localhost:8000/api/v1/cognify \
  -H "Content-Type: application/json" \
  -d '{"datasets": ["second-brain-issues"]}'
```

## Common Patterns

### Epic with Subtasks

```bash
# Create parent epic
bd create "Cognee Integration" \
  --description="Integrate Cognee AI memory layer" \
  -t epic -p 1

# Create subtasks
bd create "Environment Configuration" \
  --description="Set up cognee docker compose" \
  -t task -p 1 \
  --deps SB-cognee

bd create "Documentation" \
  --description="Document Cognee workflows and patterns" \
  -t task -p 2 \
  --deps SB-cognee
```

### Bug Discovered During Feature Work

```bash
# Working on SB-feature-x
bd update SB-feature-x --status in_progress

# Discover a bug
bd create "Format command breaks on long files" \
  --description="Found during feature-x testing" \
  -t bug -p 0 \
  --deps discovered-from:SB-feature-x
```

### Blocked Work

```bash
# Can't implement search until Cognee is integrated
bd create "Add search command" \
  --description="Semantic search using Cognee API" \
  -t feature -p 1 \
  --deps SB-cognee

# Check what's ready (search won't show up)
bd ready
# (SB-search is blocked)

# Once Cognee is done
bd close SB-cognee --reason "Completed"

# Now search is ready!
bd ready
# Shows: SB-search
```

## Beads + Git Branch Integration

When creating Beads issues during a session, include the current branch name for tracking and context.

### During /land Command (Automatic)

The `/land` command (Step 2: File Remaining Work) automatically includes branch references when creating issues:

```bash
# Get current branch for reference
CURRENT_BRANCH=$(git branch --show-current)

# Create issue with branch reference
bd create "Complete TODO: <description>" \
  --description="Branch: $CURRENT_BRANCH

Found in <file>:<line>

[Additional context]" \
  -t task -p 2
```

### Manual Issue Creation During Session

When creating issues manually during a session:

```bash
# Get current branch
CURRENT_BRANCH=$(git branch --show-current)

# Create issue with branch context
bd create "Implement query caching" \
  --description="Branch: $CURRENT_BRANCH

Found during Cognee integration work. Need to add Redis caching layer for query results.

File: .claude/scripts/query-cognee.sh:45" \
  -t task -p 2
```

### Examples

**Knowledge work branch:**
```bash
# On branch: home-lab/2026-01-28
bd create "Source SAS cables for HGST drives" \
  --description="Branch: home-lab/2026-01-28

While documenting NAS build, identified need for 2x SFF-8087 to 4x SATA cables.

Related: NAS build documentation session" \
  -t task -p 1
```

**Workflow branch:**
```bash
# On branch: feat/cognee-integration
bd create "Add error handling to Cognee sync" \
  --description="Branch: feat/cognee-integration

Cognee sync fails silently when API is down. Need to add proper error handling and retry logic.

File: .claude/scripts/sync-to-cognee.sh:120" \
  -t bug -p 1
```

### Benefits

- **Traceability:** Know which branch/session an issue originated from
- **Context:** Easy to find related commits and PRs
- **Searchability:** Query Cognee for "issues from home-lab sessions"
- **Workflow insight:** See which branches generate the most follow-up work

## Integration with /land Command

The `/land` command automatically:

1. Syncs beads to kanban: `node .claude/scripts/sync-beads-to-todo.js`
2. Commits changes including `.beads/issues.jsonl` and `to-do.md`
3. Pushes to remote

See `.claude/commands/land.md` for details.

## Important Rules

- ✅ **Use Beads for ALL task tracking** - No markdown TODOs or external trackers
- ✅ **Always use `--json` flag** for programmatic use (except `bd dep`)
- ✅ **Link discovered work** with `discovered-from` dependencies
- ✅ **Check `bd ready`** before asking "what should I work on?"
- ✅ **Commit `.beads/issues.jsonl`** - Share issues with team/sessions
- ✅ **Sync to kanban** - Keep `to-do.md` in sync with beads
- ❌ **Do NOT create markdown TODO lists** - Use Beads instead
- ❌ **Do NOT use external issue trackers** - Beads is the single source of truth
- ❌ **Do NOT use `bd update --deps`** - Use `bd dep add` instead

## Related Documentation

- [Git Workflow](.rules/patterns/git-workflow.md)
- [Knowledge Capture](.rules/patterns/knowledge-capture.md)
- [/land Command](.claude/commands/land.md)
