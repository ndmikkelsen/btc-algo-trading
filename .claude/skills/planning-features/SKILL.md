---
name: planning-features
description: Creates implementation plans (.plan.md) from Gherkin feature files. Use when starting a new feature, when asked to plan a feature, or when a .feature file exists without a .plan.md. Triggers on phrases like "plan this feature", "create implementation plan", "how should we implement".
allowed-tools: Read, Write, Grep, Glob, Bash
---

# Planning Features

Create comprehensive implementation plans from Gherkin `.feature` files.

## When to Use

- User says "plan this feature" or "create implementation plan"
- A `.feature` file exists without a corresponding `.plan.md`
- Starting work on a new feature
- User asks "how should we implement [feature]?"

## Workflow

1. **Read the .feature file** - Understand all scenarios and acceptance criteria
2. **Query knowledge**: `/query` for relevant patterns, architecture decisions, prior art
3. **Analyze requirements** - Identify technical needs, dependencies, constraints
4. **Research codebase** - Find similar patterns, existing utilities, conventions
5. **Draft the plan** - Use template from `features/README.md`
6. **Review with user** - Confirm design decisions before finalizing

## Template Location

The complete `.plan.md` template is in [features/README.md](../../../features/README.md).

## Key Sections to Address

### Goals

- Extract from Feature description and scenario names
- Identify primary and secondary objectives

### User Stories

- Convert scenarios to "As a [role], I want [capability] so that [benefit]"

### Design Decisions

For each significant choice:

- **Context**: Why this decision is needed
- **Options Considered**: What alternatives exist
- **Decision**: What we chose and why
- **Consequences**: Trade-offs and implications

### Implementation Plan

- Break into phases
- Create actionable tasks with clear descriptions
- Order by dependencies
- Each task should be atomic and testable

### Technical Specifications

Based on scenarios, identify:

- **Indicators**: Which technical indicators and parameters
- **Entry/Exit Logic**: Conditions in plain language
- **Risk Parameters**: Stoploss, ROI targets, position sizing
- **Timeframes**: What timeframes the strategy uses
- **Data Requirements**: Historical data sources and format

### Constraints

- Performance requirements (latency, throughput)
- Exchange-specific limitations
- Capital constraints
- Risk limits

### Dependencies

- External libraries (TA-Lib, pandas, numpy)
- Internal modules (strategies/, config/)
- Blockers from other features/tasks

### Definition of Done

- Map directly to scenarios in .feature file
- Add technical criteria (tests, linting, types)

## Output

Create `{feature-name}.plan.md` in the same directory as the `.feature` file.

```
features/
├── {domain}/
│   ├── {feature-name}.feature     ← Input
│   ├── {feature-name}.plan.md     ← CREATE THIS
│   └── test_{feature-name}.py     ← Created during implementation
```

## Example

For `features/trading/regime-detection.feature`:

```markdown
# Regime Detection Implementation Plan

**Feature**: features/trading/regime-detection.feature
**Created**: 2026-02-09
**Status**: Draft

## Overview

Add market regime detection using ADX to the Avellaneda-Stoikov strategy,
enabling dynamic parameter adjustment based on whether the market is
trending or ranging.

## Goals

### Primary
- Classify market as trending or ranging in real-time

### Secondary
- Adjust spread and position sizing per regime
- Reduce adverse selection in trending markets

## Design Decisions

### ADX vs Other Regime Indicators

**Context**: Need a reliable regime classification method

**Options Considered**:
1. ADX - Well-established, single threshold
2. Bollinger Band width - Volatility-based
3. Hurst exponent - Statistically rigorous but computationally expensive

**Decision**: ADX with configurable threshold (default 25)

**Consequences**: Simple to implement, well-tested, but may lag regime changes

## Implementation Plan

### Phase 1: ADX Calculation
1. [ ] Implement ADX indicator calculation
2. [ ] Add regime classification function

### Phase 2: Parameter Adjustment
1. [ ] Adjust spread based on regime
2. [ ] Scale position size in trending markets

### Phase 3: Integration
1. [ ] Wire regime detection into live trading loop
2. [ ] Add regime to metrics/logging

## Definition of Done

- [ ] All scenarios in regime-detection.feature pass
- [ ] All existing tests still pass
- [ ] No lint errors: `ruff check .`
```

## After Planning

Once the `.plan.md` is approved:

1. **Create tasks**: Run `/creating-tasks-from-plans` to generate beads issues
2. **Implement with TDD**: Run `/implementing-with-tdd` for each task

## Commands

```bash
# View the beads epic
bd show <epic-id>

# Query domain knowledge
/query What regime detection approaches work for crypto market making?

# Find similar implementations
ls strategies/
grep -r "regime" strategies/
```
