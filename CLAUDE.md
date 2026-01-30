# CLAUDE.md

> Quick reference for AI agents working with this project.

**For complete guidance, see [AGENTS.md](./AGENTS.md)**

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

## Quick Links

- **[AGENTS.md](./AGENTS.md)** - Complete AI development guide
- **[CONSTITUTION.md](./CONSTITUTION.md)** - Core values and principles
- **[VISION.md](./VISION.md)** - Long-term vision
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
│   ├── commands/      # /land, /query
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

# Freqtrade
freqtrade download-data ...           # Get historical data
freqtrade backtesting ...             # Run backtest
freqtrade trade --dry-run             # Paper trading

# Cognee integration
.claude/scripts/cognee-local.sh up    # Start Cognee
/query <question>                      # Search knowledge

# End session
/land                                  # Complete landing protocol
```

## Core Principles

1. **Use Beads for ALL task tracking** - No markdown TODOs
2. **Backtest before live trading** - Data-driven decisions only
3. **Complete sessions with /land** - NEVER skip this
4. **Document findings** - Capture learnings in .rules/

---

**This is a pointer document.** For detailed guidance, see [AGENTS.md](./AGENTS.md).
