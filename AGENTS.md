# AGENTS.md

> AI Development Guide for Second Brain Knowledge System

**Last Updated**: 2026-01-25

## Overview

Personal knowledge management system using Obsidian with AI-powered semantic search (Cognee) and git-native issue tracking (Beads).

## Structure

```
second-brain/
├── notes/               # Obsidian vault notes
├── .rules/              # Technical documentation (architecture, patterns)
├── .claude/             # AI workflows (commands, scripts)
├── .beads/              # Issue tracking (bd commands)
├── to-do.md             # Obsidian kanban (synced from beads)
└── Core docs            # CONSTITUTION, VISION, PLAN, GARDENING
```

## Where to Look

| Task | Location | Notes |
|------|----------|-------|
| Architecture overview | `.rules/index.md` | System overview |
| Cognee integration | `.rules/architecture/cognee-integration.md` | AI memory layer |
| Issue tracking | `.rules/patterns/beads-integration.md` | Beads workflow |
| Session completion | `.claude/commands/land.md` | /land protocol |
| Search knowledge | `.claude/commands/query.md` | /query command |
| Paper trading | `.claude/commands/run-test.md` | /run-test skill |
| Live trading | `.claude/commands/run-live.md` | /run-live skill |
| Stop trading | `.claude/commands/stop.md` | /stop skill |

## Development Workflow

### BDD/TDD Pipeline (MANDATORY for features)

All new features follow this pipeline:

```
beads epic/task
    ↓  /creating-features-from-tasks
.feature file (Gherkin scenarios)
    ↓  /planning-features
.plan.md (implementation plan)
    ↓  /creating-tasks-from-plans
beads tasks (with dependencies)
    ↓  /implementing-with-tdd
test_*.py + production code (red-green-refactor)
```

### Red-Green-Refactor Protocol

| Phase | Action | Verification |
|-------|--------|-------------|
| RED | Write failing test | `pytest` fails for the right reason |
| GREEN | Write minimal code to pass | `pytest` passes |
| REFACTOR | Improve code quality | `pytest` still passes |

### AI Skills for BDD

| Skill | Purpose | Trigger |
|-------|---------|---------|
| `/creating-features-from-tasks` | Create `.feature` from beads task | "create feature file", "write scenarios" |
| `/planning-features` | Create `.plan.md` from `.feature` | "plan this feature" |
| `/planning-from-tasks` | Create `.plan.md` from beads epic (no BDD) | "plan this epic" |
| `/creating-tasks-from-plans` | Create beads tasks from `.plan.md` | "create tasks from plan" |
| `/implementing-with-tdd` | TDD implementation of beads tasks | "implement this task", "TDD this" |

### Trading Skills

| Skill | Purpose | Trigger |
|-------|---------|---------|
| `/run-test` | Paper trade with real market data (simulated fills) | "paper trade", "test trader", "dry run" |
| `/run-live` | Live trading with real orders on MEXC | "go live", "start live trading" |
| `/stop` | Gracefully stop any running trading process | "stop trading", "kill trader" |

#### Expected Workflow: Test Then Go Live

```
/run-test                    # 1. Paper trade — validate strategy with real market data
  (analyze results)          # 2. Review PnL, fill rates, spread capture
/run-test --gamma 0.001      # 3. Tune parameters, repeat
  (satisfied with results?)  # 4. Confirm strategy is profitable
/run-live                    # 5. Go live (requires explicit confirmation)
/stop                        # 6. Stop when done or if issues arise
```

#### `/run-test` — Paper Trading

Launches the GLFT market maker in dry-run mode. Uses real MEXC market data with simulated order fills locally. No real money at risk.

```bash
/run-test                                    # Default: BTCUSDT, GLFT model
/run-test --gamma 0.001 --order-size 0.005   # Custom risk aversion + size
/run-test --kappa constant --kappa-value 0.05 # Fixed kappa (skip live calibration)
/run-test --interval 3 --capital 5000         # Faster updates, more capital
/run-test --no-regime-filter                  # Disable ADX regime detection
```

Key parameters:

| Flag | Default | Description |
|------|---------|-------------|
| `--gamma` | `0.005` | Risk aversion (1/$² units). Higher = tighter spreads with inventory |
| `--kappa` | `live` | Kappa mode: `live` (order book) or `constant` |
| `--order-size` | `0.003` | Order size in BTC |
| `--interval` | `5.0` | Quote update interval in seconds |
| `--min-spread` | `5.0` | Minimum spread in dollars |
| `--max-spread` | `100.0` | Maximum spread in dollars |
| `--capital` | `1000.0` | Initial capital in USDT |

#### `/run-live` — Live Trading

Launches the GLFT market maker with real orders on MEXC. **Requires explicit user confirmation** before placing any orders.

```bash
/run-live                       # Default settings (prompts for confirmation)
/run-live --gamma 0.01          # Conservative risk aversion
/run-live --dry-run             # Override: paper trade instead (no confirmation needed)
```

Requires `MEXC_API_KEY` and `MEXC_API_SECRET` in `.env`. Safety checks:
- Confirmation prompt before any live trading
- Warns if order size > 0.1 BTC or capital > $50,000
- All sessions logged to `logs/live-BTCUSDT-YYYYMMDD-HHMMSS.log`

#### `/stop` — Graceful Shutdown

Stops running trading processes by sending SIGINT, which triggers `trader.stop()` to cancel all open exchange orders and print a session summary.

```bash
/stop    # Finds and gracefully stops all running traders
```

Uses SIGINT (not SIGKILL) to ensure open orders are cancelled on the exchange. Never force-kills unless explicitly requested.

### Agent Conventions

Claude agent teams MUST follow these conventions:

1. **Use beads for ALL task tracking** - `bd create`, `bd update`, `bd close`
2. **Use cognee for knowledge queries** - `/query` before planning, after discovering patterns
3. **BDD for features** - All features start with `.feature` files
4. **TDD for implementation** - Red-green-refactor, no exceptions
5. **Complete sessions with /land** - Never skip the landing protocol

### Test File Locations

| Type | Location | Framework |
|------|----------|-----------|
| BDD feature tests | `features/<domain>/test_*.py` | pytest-bdd |
| Unit tests | `tests/unit/<module>/test_*.py` | pytest |
| Integration tests | `tests/integration/test_*.py` | pytest |

## Quick Commands

### Beads (Issue Tracking)

```bash
bd ready                              # Show unblocked issues
bd list --status=open                 # List all open issues
bd create "Title" -t task -p 1        # Create new issue
bd update <id> --status=in_progress   # Claim work
bd close <id> --reason "Done"         # Mark complete
bd dep add <issue> <depends-on>       # Add dependency
```

**IMPORTANT**: Use Beads for ALL task tracking. No markdown TODOs.

### Cognee (Semantic Search)

**Repository-Specific Instance:** Each repository has its own isolated Cognee stack.

```bash
# Start second-brain Cognee stack
.claude/scripts/cognee-local.sh up

# Check health
.claude/scripts/cognee-local.sh health

# Stop stack
.claude/scripts/cognee-local.sh down

# View logs
.claude/scripts/cognee-local.sh logs
```

**Location:** `.claude/docker/` (repository-specific)
**Containers:** `second-brain-cognee*` (isolated from other projects)
**Note**: Knowledge garden syncs automatically when you run `/land`.

### Development

```bash
# Sync beads to Obsidian kanban
node .claude/scripts/sync-beads-to-todo.js

# Query knowledge
/query How do I capture patterns?

# End session (auto-formats, commits, syncs to Cognee)
/land
```

## Git Workflow (Quick Reference)

**Main worktree:** Always on `dev` branch (your base camp)

### Branch Types

| Pattern | Purpose | Example |
|---------|---------|---------|
| `<topic>/<date>` | Knowledge/content work | `home-lab/2026-01-28` |
| `feat/<description>` | Workflow improvements | `feat/cognee-integration` |

### Workflow Pipeline

```
dev (main worktree)
  ↓
Create topic branch (ocnew <branch-name>)
  ↓
Work in worktree, commit changes
  ↓
/land (push + create PR to dev + sync to Cognee)
  ↓
Review & merge PR to dev
  ↓
Clean up worktree (manual)
  ↓
(User-driven) Merge dev → main
```

### Creating Branches

**Using `ocnew` function:**
```bash
# Knowledge work (today's date)
ocnew home-lab/2026-01-28

# Workflow improvement
ocnew feat/cognee-query-command
```

The `ocnew` function automatically:
- Creates branch from current branch (dev)
- Creates matching worktree with correct naming
- Changes directory to new worktree

### Ending Sessions

```bash
# In worktree, after committing work
/land

# /land handles:
# - Push to remote
# - Create PR to dev
# - Sync to Cognee
# - Write STICKYNOTE.md
# - Generate clipboard handoff
```

### Merging to Main

**User decides** when to merge `dev` → `main` (not automated).

**Triggers:**
- Major milestones completed
- Content review/polish complete
- Workflow features fully tested
- Periodic consolidation

See [.rules/patterns/git-workflow.md](.rules/patterns/git-workflow.md) for complete workflow guide.

## Issue Types

| Type | Purpose | Example |
|------|---------|---------|
| `bug` | Something broken | "Wiki link navigation broken" |
| `feature` | New functionality | "Add semantic search to vault" |
| `task` | Work item | "Document cognee integration" |
| `epic` | Large feature with subtasks | "Cognee Integration" |
| `chore` | Maintenance | "Update vault structure" |

## Priorities

| Priority | Meaning | When to Use |
|----------|---------|-------------|
| `0` | Critical | Broken workflows, data loss |
| `1` | High | Major features, important improvements |
| `2` | Medium | Default priority, nice-to-have |
| `3` | Low | Polish, optimization |
| `4` | Backlog | Future ideas |

See [.rules/patterns/beads-integration.md](.rules/patterns/beads-integration.md) for complete guide.

## Cognee (AI Memory)

Semantic search over knowledge garden (`.rules/`, `.claude/`) and session history.

### Datasets

| Dataset | Content |
|---------|---------|
| `knowledge-garden` | `.claude/` files |
| `btc-patterns` | `.rules/` files (architecture, patterns) |
| `btc-sessions` | Session history from `/land` |
| `btc-constitution` | CONSTITUTION.md, VISION.md, PLAN.md |
| `btc-strategies` | Homelab builds (NAS, AI server, network, hardware) |

### Search Knowledge

```bash
# Standard search
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "How does beads integration work?"}'

# Or use the /query command
/query How does beads integration work?

# Constitution-aware search (value-aligned answers)
/query --with-values How should I organize my notes?

# Homelab queries (hardware, builds, network)
/query What cables do I need for my SAS drives?
/query What hardware is still needed for my NAS build?
/query Which PCIe slots should I use for my LSI HBA?
```

### Sync to Cognee

**Manual Sync (Current):**
```bash
# Sync all datasets
.claude/scripts/sync-to-cognee.sh

# Sync all datasets (clear and fresh upload)
.claude/scripts/sync-to-cognee.sh --clear

# Sync specific dataset
.claude/scripts/sync-to-cognee.sh knowledge-garden
.claude/scripts/sync-to-cognee.sh patterns
.claude/scripts/sync-to-cognee.sh constitution
.claude/scripts/sync-to-cognee.sh homelab

# Clear and sync specific dataset
.claude/scripts/sync-to-cognee.sh --clear homelab
```

**Auto-Sync (Planned):**
Future integration with `/land` command to automatically detect and sync changes to:
- `.claude/` → `knowledge-garden` dataset
- `.rules/` → `btc-patterns` dataset
- `CONSTITUTION.md`, `VISION.md`, `PLAN.md` → `btc-constitution` dataset
- Session history → `btc-sessions` dataset

## Conventions

### Commit Messages

Use conventional commits:

```bash
feat(cognee): add semantic search command
fix(beads): correct sync script path
docs(rules): add cognee architecture
chore(beads): close completed issues
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`

Scopes: `cognee`, `beads`, `obsidian`, `rules`, `garden`

### File Organization

- **`.rules/`** - Technical documentation, stable reference
- **`.claude/`** - AI workflows, commands, scripts
- **`.beads/`** - Issue tracking state
- **`notes/`** - Obsidian vault content

## Session Completion (Mandatory)

Work is **NOT complete** until `git push` succeeds:

```bash
/land  # Execute complete landing protocol
```

**Landing Protocol:**
1. Sync beads to kanban
2. File remaining work
3. Update issue status
4. Commit changes
5. Push to remote (MANDATORY)
6. Write STICKYNOTE.md
7. Capture session to Cognee
8. Display clipboard handoff
9. Update PLAN.md (if major milestone)
10. Verify clean state

**NEVER** leave work unpushed. **NEVER** say "ready to push when you are."

See [.claude/commands/land.md](.claude/commands/land.md) for complete protocol.

## Testing (Non-Negotiables)

- **BDD for features** - All features start with `.feature` files
- **TDD for implementation** - Red-green-refactor, no exceptions
- **.plan.md for complex features** - Design before code
- **Test files colocated** - BDD tests in `features/`, unit tests in `tests/`
- **Mock external services** - No real API calls in unit tests
- **Use pytest** for all testing
- **Test edge cases** - Errors, boundary conditions, empty states

## Anti-Patterns (NEVER)

| Rule | Why |
|------|-----|
| Markdown TODOs | Use Beads |
| Skip /land protocol | Work not complete |
| Unpushed commits | Session incomplete |
| Direct main/dev commits | Use topic branches + PR |
| Write code before tests | Use TDD red-green-refactor |
| Skip .feature files for features | Use BDD pipeline |
| Ad-hoc task tracking | Use Beads exclusively |

## Constitution + Cognee Integration

The Constitution framework (CONSTITUTION.md, VISION.md, PLAN.md) is integrated with Cognee to provide **value-aligned, vision-driven knowledge retrieval**.

### How It Works

- **Constitution Framework** defines WHO WE ARE (values, principles, vision)
- **Cognee** enables HOW WE FIND (semantic search, knowledge retrieval)
- Integration creates constitution-aware queries that return answers aligned with core values

### Constitution-Aware Queries

Use `/query --with-values` for value-aligned answers:

```bash
# Standard query (technical, factual)
/query How do I use beads?

# Constitution-aware query (value-aligned guidance)
/query --with-values How should I organize my knowledge system?
/query --with-values Should I create separate files or combine them?
/query --with-values What should I focus on next?
```

Constitution context automatically enhances queries with relevant values from CONSTITUTION.md and VISION.md.

See [.rules/architecture/constitution-cognee-integration.md](.rules/architecture/constitution-cognee-integration.md) for complete integration details.

## Cognee Integration

### Setup

Requires Docker and OpenAI API key:

```bash
# Copy docker-compose from media-stack or create custom
# Add .env with OPENAI_API_KEY

# Start stack
.claude/scripts/cognee-local.sh up

# Knowledge garden syncs automatically when you run /land
# To verify sync: /query "test query"
```

### Usage

```bash
# Search knowledge
/query <question>

# Complete session (auto-syncs to Cognee)
/land

# View in Neo4j Browser
open http://localhost:7474

# API docs
open http://localhost:8001/docs
```

See [.rules/architecture/cognee-integration.md](.rules/architecture/cognee-integration.md) for complete architecture.

## Resources

- **Technical Docs**: `.rules/` (architecture, patterns)
- **Constitution**: `CONSTITUTION.md` (core values)
- **Vision**: `VISION.md` (long-term direction)
- **Plan**: `PLAN.md` (working memory, major milestones only)
- **Gardening**: `GARDENING.md` (knowledge system philosophy)

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

**This document is your quick reference.** For deep technical details, see `.rules/` and query Cognee.

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
