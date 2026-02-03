---
name: implementing-with-tdd
description: Implements beads tasks using strict TDD red-green-refactor workflow. Use when working on implementation tasks, when asked to "implement this task", "write the code for", or "TDD this feature". Ensures tests fail first, then pass, then refactor.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Implementing with TDD

Strict red-green-refactor implementation of beads tasks.

## When to Use

- User says "implement this task", "write the code for", or "TDD this feature"
- A beads issue is ready and you want to implement it safely
- You need to add behavior with tests-first discipline

## Pre-Implementation Checklist

Before writing ANY production code:

- [ ] Read the beads task: `bd show <task-id>`
- [ ] Read related .plan.md (if it exists)
- [ ] Identify one test to implement next (single increment)
- [ ] Claim the task: `bd update <task-id> --status in_progress`

## TDD Cycle (MANDATORY)

### RED Phase

1. Write a failing test first
2. Run `pytest` and confirm it FAILS
3. Confirm it fails for the right reason (not import/syntax error)
4. Do not proceed until the failure is correct

### GREEN Phase

1. Write the minimal code to make the test pass
2. Avoid extra features, abstractions, or cleanup
3. Run `pytest` and confirm it PASSES

### REFACTOR Phase

1. Improve structure/naming while keeping tests green
2. Run `pytest` frequently (ideally after each small refactor)
3. Stop and ask for approval before expanding scope beyond the original test

## Implementation Patterns

### Strategy Tests (strategies/test_*.py)

Test Freqtrade strategies with historical data:

```python
import pytest
from pandas import DataFrame
from strategies.BTCMomentumScalper import BTCMomentumScalper


@pytest.fixture
def strategy():
    return BTCMomentumScalper(config={})


@pytest.fixture
def sample_dataframe():
    """Create sample OHLCV data for testing."""
    return DataFrame({
        'open': [100, 101, 102, 103, 104],
        'high': [101, 102, 103, 104, 105],
        'low': [99, 100, 101, 102, 103],
        'close': [100.5, 101.5, 102.5, 103.5, 104.5],
        'volume': [1000, 1100, 1200, 1300, 1400],
    })


def test_populate_indicators_adds_rsi(strategy, sample_dataframe):
    """RED: this should fail until implementation exists."""
    result = strategy.populate_indicators(sample_dataframe, {})
    assert 'rsi' in result.columns
```

### Unit Tests (tests/test_*.py)

Test utility functions and helpers:

```python
import pytest
from utils.risk_calculator import calculate_position_size


def test_calculate_position_size_with_2_percent_risk():
    """RED: this should fail until implementation exists."""
    result = calculate_position_size(
        account_balance=10000,
        risk_percent=0.02,
        entry_price=50000,
        stop_loss_price=49000
    )
    assert result == 0.2  # 0.2 BTC position
```

### Indicator Tests

Test custom indicator calculations:

```python
import pytest
import numpy as np
from indicators.momentum import calculate_momentum_score


def test_momentum_score_bullish_trend():
    """Momentum score should be positive in uptrend."""
    prices = np.array([100, 102, 104, 106, 108])
    score = calculate_momentum_score(prices)
    assert score > 0
```

## Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_strategy.py

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "momentum"

# Run with coverage
pytest --cov=strategies --cov-report=term-missing

# Lint code
ruff check .

# Type check
mypy strategies/

# Task status
bd show <task-id>
bd update <task-id> --status in_progress
bd close <task-id> --reason "Implemented with TDD"
```

## Anti-Patterns (NEVER DO)

- Writing production code before the test
- Skipping the RED phase
- "Fixing" a failing test by weakening assertions
- Making broad refactors while tests are red
- Closing the beads task without green tests

## Completion Checklist

- [ ] All tests pass: `pytest`
- [ ] No lint errors: `ruff check .`
- [ ] No type errors: `mypy strategies/` (if configured)
- [ ] Close the beads task: `bd close <task-id> --reason "Implemented with TDD"`
