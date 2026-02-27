# CLAUDE.md

> Quick reference for AI agents working with this project.

**For complete guidance, see [AGENTS.md](./AGENTS.md)**

## The Hierarchy

```
CONSTITUTION (who we are)
    ↓
VISION (where we're going)
    ↓
WORKFLOW (how we operate)
    ↓
.rules/ (what we know)
    ↓
PLAN (what we're doing)
```

## Quick Links

- **[AGENTS.md](./AGENTS.md)** - Complete AI development guide
- **[CONSTITUTION.md](./CONSTITUTION.md)** - Core values and principles
- **[VISION.md](./VISION.md)** - Long-term vision
- **[WORKFLOW.md](./WORKFLOW.md)** - Strategy development pipeline
- **[PLAN.md](./PLAN.md)** - Working memory (current milestones)
- **[.rules/index.md](.rules/index.md)** - Technical documentation

## Project Context

This is a **Bitcoin algorithmic trading** project. Key areas:

- **strategies/** - Freqtrade strategy implementations
- **data/** - Historical OHLCV data (gitignored)
- **backtests/** - Backtest results and analysis
- **config/** - Freqtrade configuration

## Repository Structure

```
btc-algo-trading/
├── AGENTS.md           # AI development guide
├── CONSTITUTION.md     # Core values
├── VISION.md          # Long-term direction
├── PLAN.md            # Working memory
│
├── strategies/        # Freqtrade strategies
├── data/              # Historical data (gitignored)
├── backtests/         # Results and analysis
├── config/            # Freqtrade config
│
├── .claude/           # AI workflows
│   ├── commands/      # /land, /query, /run-test, /run-live, /stop
│   └── scripts/       # Automation
│
├── .rules/            # Technical docs
└── .beads/            # Issue tracking
```

## Essential Commands

```bash
# Issue tracking
bd ready                              # Find work
bd create "Title" -t task -p 1        # Create issue
bd close <id> --reason "Done"         # Complete work

# Market making (recommended workflow: test first, then go live)
/run-test                             # Paper trade with real market data
/run-test --gamma 0.001 --interval 3  # Custom params
/run-live                             # Live trading (requires confirmation)
/run-live --dry-run                   # Override to paper trade mode
/stop                                 # Gracefully stop any running trader

# Cognee integration
.claude/scripts/cognee-local.sh up    # Start Cognee
/query <question>                      # Search knowledge

# End session
/land                                  # Complete landing protocol
```

## NON-NEGOTIABLE: Kamal Deploy

**ALWAYS use `-c <config-file>`. NEVER use `-d <destination>`.**

```bash
# ✅ Correct
kamal setup -c config/deploy.cognee.yml
kamal deploy -c config/deploy.cognee.yml
kamal setup -c config/deploy.dolt.yml
kamal deploy -c config/deploy.dolt.yml

# ❌ NEVER DO THIS — merges configs, causes invisible drift
kamal deploy -d cognee
kamal deploy -d dolt
```

Each service config (`config/deploy.cognee.yml`, `config/deploy.dolt.yml`) is fully self-contained.
Secrets live in a single `.kamal/secrets` file (see `.kamal/secrets.example`).

## Core Principles

1. **Use Beads for ALL task tracking** - No markdown TODOs
2. **Backtest before live trading** - Data-driven decisions only
3. **Complete sessions with /land** - NEVER skip this
4. **Document findings** - Capture learnings in .rules/

---

**This is a pointer document.** For detailed guidance, see [AGENTS.md](./AGENTS.md).
