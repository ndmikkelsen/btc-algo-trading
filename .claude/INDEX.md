# BTC Algo Trading - Knowledge System

> AI Development Guide and Knowledge Index

**Last Updated**: 2026-01-31

---

## Structure

```
btc-algo-trading/
├── .rules/              # Technical documentation (architecture, patterns)
├── .claude/             # AI workflow (commands, scripts)
├── .beads/              # Issue tracking (bd commands)
├── strategies/          # Freqtrade strategy implementations
├── backtests/           # Backtest results and analysis
├── config/              # Freqtrade configuration
└── Core docs            # AGENTS.md, CONSTITUTION.md, VISION.md, PLAN.md
```

## Where to Look

| Task | Location | Notes |
|------|----------|-------|
| Quick reference | `AGENTS.md` | Start here |
| Architecture | `.rules/architecture/` | System design |
| Patterns | `.rules/patterns/` | Technical workflows |
| Issue tracking | `.rules/patterns/beads-integration.md` | Beads workflow |
| Session completion | `.claude/commands/land.md` | /land protocol |
| Cognee integration | `.rules/architecture/cognee-integration.md` | AI memory layer |

---

## Commands

### `/land` - End Session

Complete session landing protocol:
- Sync beads to kanban
- Commit and push changes
- Write STICKYNOTE.md for handoff
- Capture session to Cognee
- Display clipboard-ready summary

See [commands/land.md](commands/land.md)

### `/query` - Search Knowledge

Semantic search using Cognee:
- Query across `.rules/` and session history
- Get contextualized answers
- Discover related patterns

See [commands/query.md](commands/query.md)

---

## Scripts

### Beads Integration

```bash
# Sync beads to Obsidian kanban
node .claude/scripts/sync-beads-to-todo.js
```

### Cognee Integration

```bash
# Start Cognee stack
.claude/scripts/cognee-local.sh up

# Check health
.claude/scripts/cognee-local.sh health

# Knowledge syncs automatically via /land
```

---

## Beads (Issue Tracking)

**IMPORTANT**: Use Beads for ALL task tracking. No markdown TODOs.

```bash
bd ready                              # Show unblocked issues
bd create "Title" -t task -p 1        # Create issue
bd update <id> --status in_progress   # Claim work
bd close <id> --reason "Done"         # Complete work
bd dep add <blocked> <blocker>        # Add dependency
```

See [.rules/patterns/beads-integration.md](.rules/patterns/beads-integration.md)

---

## Cognee (AI Memory)

Semantic search over knowledge garden and session history.

### Quick Start

```bash
# Start Cognee stack (requires Docker)
.claude/scripts/cognee-local.sh up

# Query knowledge
/query How do I use beads?

# Knowledge syncs automatically when you run /land
```

### Datasets

| Dataset | Content |
|---------|---------|
| `btc-knowledge-garden` | `.claude/` files |
| `btc-patterns` | `.rules/` files |
| `btc-sessions` | Session history from `/land` |
| `btc-strategies` | `strategies/` code and docs |
| `btc-backtests` | `backtests/` results |

See [.rules/architecture/cognee-integration.md](.rules/architecture/cognee-integration.md)

---

## The Hierarchy

```
CONSTITUTION (who we are)
    ↓
VISION (where we're going)
    ↓
.rules/ (what we know)
    ↓
PLAN (what we're doing)
```

---

## Session Workflow

1. **Check for work**: `bd ready`
2. **Claim issue**: `bd update <id> --status in_progress`
3. **Do the work**: Implement, test, document
4. **Query knowledge**: `/query <question>` if needed
5. **Complete**: `bd close <id> --reason "Done"`
6. **Land**: `/land` to finish session

---

## Related Documents

- **[AGENTS.md](../AGENTS.md)** - Quick reference guide
- **[CONSTITUTION.md](../CONSTITUTION.md)** - Core values and principles
- **[VISION.md](../VISION.md)** - Long-term vision
- **[PLAN.md](../PLAN.md)** - Working memory (major milestones only)
- **[GARDENING.md](../GARDENING.md)** - Knowledge system philosophy

---

**This is your knowledge system.** Use Cognee to search it. Use Beads to track work. Use `/land` to save sessions.
