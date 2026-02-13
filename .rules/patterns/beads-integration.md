---
description: Issue tracking with Beads (bd) for btc-algo-trading
tags: [beads, issue-tracking, workflow, git-integration]
last_updated: 2026-02-09
---

# Beads Issue Tracking

This project uses [Beads (bd)](https://github.com/steveyegge/beads) for ALL issue tracking.

## Core Rules

- **Track ALL work in bd** - Never use markdown TODOs or comment-based task lists
- **Use `bd ready`** to find available work
- **Use `bd create`** to track new issues/tasks/bugs
- **Use `bd sync`** at end of session to sync with git remote
- **Git hooks auto-sync** on commit/merge

## Quick Reference

```bash
bd ready                              # Show issues ready to work (no blockers)
bd list --status=open                 # List all open issues
bd create --title="Title" --type=task --priority=1  # Create new issue
bd update <id> --status=in_progress   # Claim work
bd close <id> --reason "Done"         # Mark complete
bd dep add <issue> <depends-on>       # Add dependency
bd sync                               # Sync with git remote
```

## Workflow

1. **Check for ready work**: `bd ready`
2. **Claim an issue**: `bd update <id> --status=in_progress`
3. **Do the work**: Implement, test, document
4. **Mark complete**: `bd close <id> --reason "Completed"`
5. **Sync**: `bd sync` (or let git hooks handle it)

## Issue Types

| Type | Purpose | Example |
|------|---------|---------|
| `bug` | Something broken | "Reservation price formula uses wrong scaling" |
| `feature` | New functionality | "Add order book data pipeline from Bybit" |
| `task` | Work item | "Implement kappa estimation from order book" |
| `epic` | Large feature with subtasks | "A-S Strategy Overhaul" |
| `chore` | Maintenance | "Update Python dependencies" |

## Priorities

| Priority | Meaning | When to Use |
|----------|---------|-------------|
| `0` | Critical | Strategy bugs causing losses, data corruption, broken builds |
| `1` | High | Major features, important bugs, blocking issues |
| `2` | Medium | Default priority, nice-to-have features |
| `3` | Low | Polish, optimization, minor improvements |
| `4` | Backlog | Future ideas, deferred work |

## Managing Dependencies

Dependencies can be added at creation time or to existing issues.

### At Creation Time

```bash
# Child depends on parent
bd create --title="Child task" \
  --description="Details" \
  --priority=1 \
  --deps algo-imp-parent

# Task blocked by multiple issues
bd create --title="Blocked task" \
  --description="Details" \
  --deps algo-imp-blocker1,algo-imp-blocker2
```

### Add to Existing Issues

Use `bd dep`, NOT `bd update --deps`:

```bash
# Make algo-imp-abc depend on algo-imp-xyz
bd dep add algo-imp-abc algo-imp-xyz

# Same thing using --blocks syntax
bd dep algo-imp-xyz --blocks algo-imp-abc

# Check dependencies
bd dep list algo-imp-abc

# Show full dependency tree
bd dep tree algo-imp-abc
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
bd close algo-imp-abc --reason "Done"
# (Auto-exports to .beads/issues.jsonl after 5s)

# Commit the JSONL file
git add .beads/issues.jsonl
git commit -m "chore(beads): close algo-imp-abc"

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
bd create --title="Implement GLFT 2012 spread formula" \
  --description="Replace current A-S formula with Guéant-Lehalle-Fernandez-Tapia extension" \
  --type=feature --priority=1

# 2. Query Cognee for related context
/query What do we know about GLFT spread formulas?
```

## Integration with Team Agents

When working with Claude team agents:

1. **Team lead** uses `bd ready` to find available work
2. **Lead assigns tasks** to agents based on expertise
3. **Agents claim work**: `bd update <id> --status in_progress`
4. **Agents complete work**: `bd close <id> --reason "Completed"`
5. **Lead verifies**: Run quality gates and review changes
6. **Sync at session end**: `bd sync --from-main`

## Common Patterns

### Epic with Subtasks

```bash
# Create parent epic
bd create --title="A-S Strategy Overhaul" \
  --description="Fix formula, add order book data, build tick simulator" \
  --type=epic --priority=1

# Create subtasks
bd create --title="Fix reservation price formula" \
  --description="Use S - adj instead of S*(1-adj)" \
  --type=task --priority=0 \
  --deps algo-imp-overhaul

bd create --title="Build order book pipeline" \
  --description="Bybit WebSocket L2 book capture" \
  --type=task --priority=1 \
  --deps algo-imp-overhaul
```

### Bug Discovered During Feature Work

```bash
# Working on algo-imp-feature-x
bd update algo-imp-feature-x --status in_progress

# Discover a bug
bd create --title="Fill model assumes 100% fill at price touch" \
  --description="Found during feature-x testing. Need probabilistic fill model." \
  --type=bug --priority=0
```

### Blocked Work

```bash
# Can't test live until order book pipeline is ready
bd create --title="Run Bybit testnet shadow trading" \
  --description="Shadow trade with real order book data" \
  --type=task --priority=1 \
  --deps algo-imp-order-book-pipeline

# Check what's ready (testnet won't show up)
bd ready
# (algo-imp-testnet is blocked)

# Once pipeline is done
bd close algo-imp-order-book-pipeline --reason "Completed"

# Now testnet is ready!
bd ready
# Shows: algo-imp-testnet
```

## Important Rules

- **Use Beads for ALL task tracking** - No markdown TODOs or external trackers
- **Link discovered work** with `discovered-from` dependencies
- **Check `bd ready`** before asking "what should I work on?"
- **Commit `.beads/issues.jsonl`** - Share issues with team/sessions
- **Do NOT create markdown TODO lists** - Use Beads instead
- **Do NOT use external issue trackers** - Beads is the single source of truth
- **Do NOT use `bd update --deps`** - Use `bd dep add` instead

## Related Documentation

- [BDD Workflow](bdd-workflow.md)
- [Git Workflow](git-workflow.md)
