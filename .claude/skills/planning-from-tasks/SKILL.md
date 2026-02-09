---
name: planning-from-tasks
description: Creates implementation plans (.plan.md) from beads epics or feature tasks. Use when starting a new feature, when asked to plan an epic, or when a beads issue needs detailed planning. Triggers on phrases like "plan this epic", "create implementation plan", "how should we implement".
allowed-tools: Read, Write, Grep, Glob, Bash
---

# Planning from Tasks

Create comprehensive implementation plans from beads epics or feature tasks.

## When to Use

- User says "plan this epic" or "create implementation plan"
- A beads epic/feature exists that needs detailed breakdown
- Starting work on a new feature
- User asks "how should we implement [feature]?"

## Workflow

1. **Read the beads issue** - `bd show <epic-id>` to understand scope
2. **Query knowledge** - `/query` for relevant patterns, prior art, architecture
3. **Check for .feature file** - If a `.feature` file exists, use `/planning-features` instead
4. **Analyze requirements** - Identify technical needs, dependencies, constraints
5. **Research codebase** - Find similar patterns, existing utilities, conventions
6. **Draft the plan** - Use template below
7. **Review with user** - Confirm design decisions before finalizing

**Note**: For features that already have a `.feature` file, use the `/planning-features` skill instead. This skill is for planning directly from beads epics/tasks that don't yet have Gherkin scenarios.

## Output Location

Place `.plan.md` files near related code:

```
docs/plans/
├── {feature-name}.plan.md       ← General feature plans

strategies/
├── {strategy-name}.plan.md      ← Strategy implementation plans

backtests/
├── {analysis-name}.plan.md      ← Analysis/research plans
```

## Plan Template

```markdown
# {Feature Name} Implementation Plan

**Epic**: {beads-id}
**Created**: {date}
**Status**: Draft | In Review | Approved

## Overview

{1-2 paragraph summary of what this feature does and why it matters}

## Goals

### Primary
- {Main objective}

### Secondary
- {Supporting objectives}

## User Stories

- As a {role}, I want {capability} so that {benefit}

## Design Decisions

### {Decision 1 Title}

**Context**: {Why this decision is needed}

**Options Considered**:
1. {Option A} - {pros/cons}
2. {Option B} - {pros/cons}

**Decision**: {What we chose}

**Rationale**: {Why we chose it}

## Technical Specifications

### Data Requirements
- {Data sources needed}
- {Format/schema}

### Dependencies
- {External libraries}
- {Internal modules}

### Configuration
- {Config parameters}

## Implementation Plan

### Phase 1: {Foundation}

1. [ ] {Task 1}
2. [ ] {Task 2}

### Phase 2: {Core Implementation}

1. [ ] {Task 3}
2. [ ] {Task 4}

### Phase 3: {Integration & Testing}

1. [ ] {Task 5}
2. [ ] {Task 6}

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| {Risk 1} | Low/Med/High | Low/Med/High | {Strategy} |

## Definition of Done

- [ ] All tests pass
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] Backtest results validated (if applicable)

## Open Questions

- {Question 1}
- {Question 2}
```

## Key Sections Explained

### Goals

Extract from the beads epic description:
- What is the primary outcome?
- What secondary benefits do we get?

### Design Decisions

For each significant architectural choice:
- **Context**: Why we need to decide
- **Options**: What alternatives exist (with trade-offs)
- **Decision**: What we chose and why

### Implementation Plan

Break into phases:
- **Phase 1**: Foundation/setup (unblocks everything)
- **Phase 2**: Core functionality
- **Phase 3**: Polish, testing, documentation

Each task should be:
- Atomic (completable independently)
- Testable (clear success criteria)
- Sized for 1-4 hours of work

### Technical Specifications

For trading strategies, include:
- **Indicators**: Which technical indicators and parameters
- **Entry/Exit Logic**: Conditions in plain language
- **Risk Parameters**: Stoploss, ROI targets, position sizing
- **Timeframes**: What timeframes the strategy uses

## Example

For beads epic "Backtesting Pipeline Setup":

```markdown
# Backtesting Pipeline Implementation Plan

**Epic**: btc-algo-trading-bkg
**Created**: 2024-01-15
**Status**: Draft

## Overview

Set up a complete backtesting pipeline for BTC trading strategies using
Freqtrade. This enables data-driven strategy development and validation
before any live trading.

## Goals

### Primary
- Run backtests against 7+ years of BTC price history

### Secondary
- Establish reproducible testing methodology
- Create baseline performance metrics

## Design Decisions

### Data Source Selection

**Context**: Need reliable historical OHLCV data

**Options Considered**:
1. Binance only (2017-present) - Most liquid, but limited history
2. Bitstamp (2012-2017) + Binance (2017-present) - Full history, merge needed

**Decision**: Use both sources with merged dataset

**Rationale**: Extended history captures multiple market cycles

## Implementation Plan

### Phase 1: Environment Setup

1. [ ] Install Freqtrade
2. [ ] Configure exchange API
3. [ ] Verify backtesting works

### Phase 2: Data Acquisition

1. [ ] Download Binance data (2017-present)
2. [ ] Download Bitstamp data (2012-2017)
3. [ ] Validate data quality
4. [ ] Merge datasets

### Phase 3: Strategy Testing

1. [ ] Backtest BTCMomentumScalper
2. [ ] Analyze by market regime
3. [ ] Document findings
```

## After Planning

1. **Review with user** - Confirm the plan captures requirements
2. **Create tasks** - Run `creating-tasks-from-plans` skill
3. **Start implementation** - Use `implementing-with-tdd` skill

## Commands

```bash
# View the beads epic
bd show <epic-id>

# List related issues
bd list

# Find similar implementations
ls strategies/
grep -r "def populate_indicators" strategies/
```
