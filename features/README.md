# Features (BDD)

Gherkin `.feature` files and their implementation plans for behavior-driven development of trading strategies.

## Directory Structure

```
features/
├── README.md              <- This file
├── conftest.py            <- SHARED fixtures (model instances, price data, Given/Then)
├── trading/               <- Market making and quoting
│   ├── market-making.feature
│   ├── market-making.plan.md
│   └── test_market_making.py    <- scenarios(".") + domain-specific steps
├── backtesting/           <- Fill models and simulation
│   └── ...
├── data/                  <- Order book and exchange data
│   └── ...
├── risk/                  <- Position management and risk
│   └── ...
└── infra/                 <- Connectivity and monitoring
    └── ...
```

## BDD Pipeline

```
beads issue -> .feature spec -> .plan.md -> tasks -> TDD implementation
   (Define)     (Specify)      (Plan)    (Break)    (Build)
```

| Stage | Skill | Input | Output |
|-------|-------|-------|--------|
| Define | `bd create` | Problem/need | Beads issue |
| Specify | `/creating-features-from-tasks` | Beads issue | `.feature` file |
| Plan | `/planning-features` | `.feature` file | `.plan.md` |
| Break | `/creating-tasks-from-plans` | `.plan.md` | Beads tasks |
| Build | `/implementing-with-tdd` | Beads task | Code + passing tests |

## File Conventions

| File | Purpose | Created By |
|------|---------|------------|
| `{name}.feature` | Gherkin scenarios | `/creating-features-from-tasks` |
| `{name}.plan.md` | Implementation plan | `/planning-features` |
| `test_{name}.py` | pytest-bdd step implementations | `/implementing-with-tdd` |

## Step Definition Architecture

**Shared steps** (`conftest.py`):
- Model fixtures (`as_model`, `as_model_custom`)
- Price data fixtures (`sample_prices`, `trending_prices`, `stable_prices`, `sample_ohlcv`)
- Common Given/When/Then steps used across multiple features

**Feature-specific steps** (`test_<name>.py`):
- Steps unique to that feature domain
- `scenarios(".")` call to register the `.feature` file
- Domain-specific Context class

**IMPORTANT**: Always use `scenarios(".")` (not explicit file paths) for portability.

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

# Collect without running (verify parsing)
pytest features/ --collect-only
```

## Feature Domains

| Domain | Directory | Examples |
|--------|-----------|---------|
| Trading | `trading/` | Spread calc, inventory mgmt, order placement |
| Backtesting | `backtesting/` | Fill models, walk-forward, Monte Carlo |
| Risk | `risk/` | Position sizing, stop-loss, drawdown limits |
| Data | `data/` | Order book capture, multi-exchange, validation |
| Infrastructure | `infra/` | Exchange connectivity, monitoring, alerts |

## .plan.md Template

When creating implementation plans with `/planning-features`, use this template:

```markdown
# {Feature Title} - Implementation Plan

**Beads Issue**: {task-id}
**Feature Spec**: `features/<domain>/<feature-name>.feature`
**Created**: {DATE}
**Status**: Draft | Approved | In Progress | Complete

## User Stories

> As a {role}
> I want {capability}
> So that {benefit}

## Feature Scenarios

Maps scenarios to implementation phases:

| Scenario | Phase | Tasks |
|----------|-------|-------|
| {Scenario name} | Phase {N} | {What to do} |

### Definition of Done
All scenarios in `features/<domain>/<feature-name>.feature` pass green:
pytest features/<domain>/ -v

## Design Decisions

### {Decision Title}
**Context**: {Why needed}
**Options**: 1. {A} 2. {B}
**Decision**: {Chosen}
**Rationale**: {Why}

## Implementation Plan

### Phase 1: {Foundation}
1. [ ] {Task -- linked to scenario(s)}

### Phase 2: {Core}
1. [ ] {Task -- linked to scenario(s)}

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
```

## Gherkin Conventions for Trading

### Spread Calculation

```gherkin
Scenario: Spread widens with higher volatility
  Given a BTC mid price of 50000
  And a default Avellaneda-Stoikov model
  And a volatility of 0.02
  And a time remaining of 0.5
  When I calculate the optimal spread at this volatility
  And I recalculate with a volatility of 0.05
  Then the second spread should be wider than the first
```

### Inventory Management

```gherkin
Scenario: Long inventory shifts quotes downward
  Given a BTC mid price of 50000
  And a default Avellaneda-Stoikov model
  And a volatility of 0.02
  And a time remaining of 0.5
  When I calculate quotes with inventory 0
  And I calculate quotes with inventory 5
  Then the long-inventory bid should be lower than the neutral bid
```

### Fill Model Validation

```gherkin
Scenario Outline: Fill probability decreases with distance from mid
  Given an order book with spread <spread>
  And an order placed <distance> from mid price
  When I estimate the fill probability
  Then the fill probability should be less than <max_prob>

  Examples:
    | spread | distance | max_prob |
    | 0.01%  | 0.005%   | 0.8      |
    | 0.01%  | 0.02%    | 0.3      |
    | 0.01%  | 0.05%    | 0.1      |
```

### Risk Management

```gherkin
Scenario: Stop-loss triggers at threshold
  Given a position of 1.0 BTC at entry price 50000
  And a stop-loss threshold of 2%
  When the price drops to 48900
  Then the stop-loss should trigger
  And the position should be closed
```

## Writing Good Scenarios

### Do

- Focus on behavior, not implementation
- Use domain language (spread, inventory, volatility, kappa)
- One behavior per scenario
- Include edge cases (zero inventory, extreme volatility)
- Keep scenarios independent
- Use Scenario Outline for parametrized tests

### Don't

- Reference implementation details (function names, classes)
- Combine multiple behaviors
- Skip error scenarios
- Use technical jargon over domain language
- Use explicit file paths in `scenarios()` calls

## Related Documentation

- [BDD Workflow](../.rules/patterns/bdd-workflow.md) - Full technical reference
- [Beads Integration](../.rules/patterns/beads-integration.md) - Issue tracking
- [Skills README](../.claude/skills/README.md) - Skill pipeline overview
