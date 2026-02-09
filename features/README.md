# Features (BDD)

Gherkin `.feature` files and their implementation plans for behavior-driven development.

## Directory Structure

```
features/
├── README.md              ← This file (workflow docs + .plan.md template)
├── conftest.py            ← Shared BDD fixtures
├── trading/               ← Trading strategy features
│   ├── market-making.feature
│   ├── test_market_making.py
│   └── ...
├── backtesting/           ← Backtesting pipeline features
│   └── ...
└── risk/                  ← Risk management features
    └── ...
```

## BDD Workflow

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

## File Conventions

| File | Purpose | Created By |
|------|---------|------------|
| `{name}.feature` | Gherkin scenarios | `/creating-features-from-tasks` |
| `{name}.plan.md` | Implementation plan | `/planning-features` |
| `test_{name}.py` | pytest-bdd step implementations | `/implementing-with-tdd` |

## Running BDD Tests

```bash
# All tests (unit + BDD)
pytest

# BDD tests only
pytest features/

# Specific feature domain
pytest features/trading/

# Specific feature
pytest features/trading/test_market_making.py
```

## .plan.md Template

Use this template when creating implementation plans with `/planning-features`:

```markdown
# {Feature Name} Implementation Plan

**Feature**: features/{domain}/{feature-name}.feature
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

**Consequences**: {Trade-offs and implications}

## Technical Specifications

### Indicators
- {Technical indicators and parameters}

### Entry/Exit Logic
- {Conditions in plain language}

### Risk Parameters
- {Stoploss, ROI targets, position sizing}

### Data Requirements
- {Data sources, timeframes, format}

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

## Constraints

- {Performance requirements}
- {Exchange limitations}
- {Capital constraints}

## Dependencies

- {External libraries}
- {Internal modules}
- {Blocking tasks}

## Definition of Done

- [ ] All scenarios in {feature-name}.feature pass
- [ ] All existing tests still pass (`pytest`)
- [ ] No lint errors (`ruff check .`)
- [ ] No type errors (`mypy strategies/`)
- [ ] Documentation updated
- [ ] Backtest results validated (if applicable)

## Open Questions

- {Question 1}
- {Question 2}
```

## Writing Good Scenarios

### Do

- Focus on behavior, not implementation
- Use domain language (spread, inventory, volatility)
- One behavior per scenario
- Include edge cases (zero inventory, extreme volatility)
- Keep scenarios independent

### Don't

- Reference implementation details (function names, classes)
- Combine multiple behaviors
- Skip error scenarios
- Use technical jargon over domain language
