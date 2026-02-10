---
description: BDD/TDD workflow for the btc-algo-trading repository
tags: [bdd, tdd, workflow, testing, trading]
last_updated: 2026-02-09
---

# BDD Workflow

Technical reference for the Behavior-Driven Development pattern used in btc-algo-trading.

## Pipeline

```
beads issue -> .feature spec -> .plan.md -> tasks -> TDD implementation
   (Define)     (Specify)      (Plan)    (Break)    (Build)
```

| Stage | Skill | Input | Output |
|-------|-------|-------|--------|
| Define | `bd create` | Problem/need | Beads issue |
| Specify | `creating-features-from-tasks` | Beads issue | `.feature` file |
| Plan | `planning-features` | `.feature` file | `.plan.md` |
| Break | `creating-tasks-from-plans` | `.plan.md` | Beads tasks |
| Build | `implementing-with-tdd` | Beads task | Code + passing tests |

## Repository Structure

```
btc-algo-trading/
├── features/
│   ├── conftest.py                    # SHARED steps (fixtures + Given/When/Then)
│   ├── trading/
│   │   ├── market-making.feature      # A-S market making scenarios
│   │   ├── market-making.plan.md      # Implementation plan
│   │   └── test_market_making.py      # scenarios(".") + domain steps
│   ├── backtesting/
│   │   ├── fill-model.feature
│   │   └── test_fill_model.py
│   ├── data/
│   │   ├── order-book-pipeline.feature
│   │   └── test_order_book_pipeline.py
│   └── risk/
│       ├── position-management.feature
│       └── test_position_management.py
├── tests/
│   └── unit/                          # Traditional unit tests
│       └── avellaneda_stoikov/
├── strategies/                        # Production code
└── scripts/                           # Utilities
```

## Gherkin -> Trading Mapping

| Gherkin Concept | Trading Equivalent |
|-----------------|-------------------|
| Feature | A trading capability (e.g., "Optimal spread calculation") |
| Background | Common setup -- model config, market state |
| Scenario | A single testable assertion about behavior |
| Scenario Outline | Parametrized test across market conditions |
| Examples | Data table of prices, volatilities, inventories |
| Given | Precondition -- market state, model config |
| When | Action -- calculate, evaluate, execute |
| Then | Assertion -- price is correct, order is placed |
| And | Additional assertion in same scenario |

## Step Definition Architecture

**Shared steps** (`features/conftest.py`):
- Model fixtures (`as_model`, `as_model_custom`, `sample_prices`)
- `Given a BTC mid price of 50000` -> sets up market state
- `Given a default Avellaneda-Stoikov model` -> provides model instance
- Generic `Then` steps for common assertions (positive values, bounds checks)

**Feature-specific steps** (`test_<domain>.py`):
- Steps unique to that domain (e.g., custom spread validation)
- `scenarios(".")` call to register the `.feature` file

**IMPORTANT**: Always use `scenarios(".")` (not explicit paths) for portability.

## Worked Example: Adding Order Book Pipeline

### 1. Create beads issue

```bash
bd create --title="Implement order book data pipeline" --type=feature --priority=1
```

### 2. Specify behavior (Skill 1)

Create `features/data/order-book-pipeline.feature`:

```gherkin
Feature: Order book data pipeline
  As a market maker
  I want real-time order book data from Bybit
  So that I can measure liquidity and place informed quotes

  Background:
    Given a Bybit WebSocket connection configuration

  Scenario: Connect to order book stream
    When I subscribe to BTC/USDT L2 order book
    Then I should receive order book snapshots
    And each snapshot should have bids and asks

  Scenario: Calculate mid price from order book
    Given an order book with best bid 50000 and best ask 50001
    When I calculate the mid price
    Then the mid price should be 50000.50

  Scenario: Measure order book liquidity
    Given an order book with known depth
    When I estimate the liquidity parameter
    Then kappa should be a positive number

  Scenario: Handle connection failure
    Given an active order book stream
    When the WebSocket connection drops
    Then the system should attempt reconnection
    And stale data should be flagged
```

Create `features/data/test_order_book_pipeline.py`:

```python
from pytest_bdd import scenarios

scenarios(".")
```

Verify RED:

```bash
pytest features/data/ -v
# FAILS: Steps not implemented
```

### 3. Plan implementation (Skill 2)

Create `features/data/order-book-pipeline.plan.md` driven by the 4 scenarios above.

### 4. Create tasks (Skill 3)

```bash
bd create --title="Create Bybit WebSocket client" --type=task --priority=1
bd create --title="Add L2 order book parser" --type=task --priority=1
bd create --title="Implement kappa estimation" --type=task --priority=1
```

### 5. Implement with TDD (Skill 4)

RED -> write step definitions -> GREEN -> implement production code -> REFACTOR.

Verify GREEN:

```bash
pytest features/data/ -v
# PASSES: All 4 scenarios green

pytest
# PASSES: All tests green
```

## Relationship: tests/ vs features/

| Aspect | `tests/unit/` | `features/` |
|--------|---------------|-------------|
| Purpose | Component unit tests | BDD specifications |
| Style | Parametrized pytest | Gherkin Scenario Outlines |
| When to use | Testing internals | New feature work |
| Driven by | Implementation details | Beads issues |
| Fixtures | `tests/conftest.py` | `features/conftest.py` |

Both run together: `pytest`

## Commands

```bash
# Run all tests across the repo
pytest

# Run only BDD features
pytest features/ -v

# Run specific feature domain
pytest features/trading/ -v

# Run only unit tests
pytest tests/ -v

# Collect without running (verify parsing)
pytest features/ --collect-only

# Run with coverage
pytest --cov=strategies --cov-report=term-missing
```

## Feature Domain Guide

| Domain | Directory | What belongs here |
|--------|-----------|-------------------|
| Trading | `features/trading/` | Market making, quoting, spread calculation, inventory |
| Backtesting | `features/backtesting/` | Fill models, simulation, walk-forward, Monte Carlo |
| Risk | `features/risk/` | Position sizing, stop-loss, drawdown, exposure limits |
| Data | `features/data/` | Order book, exchange data, multi-source, validation |
| Infrastructure | `features/infra/` | Connectivity, monitoring, alerts, deployment |

## Related Documentation

- [Beads Integration](beads-integration.md)
- [Git Workflow](git-workflow.md)
- [Skills README](../../.claude/skills/README.md)
