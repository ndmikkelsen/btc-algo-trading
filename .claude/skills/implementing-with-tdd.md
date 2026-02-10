---
name: implementing-with-tdd
description: Implements beads tasks using strict TDD red-green-refactor workflow. Use when working on implementation tasks, when asked to "implement this task", "write the code for", or "TDD this feature". Ensures tests fail first, then pass, then refactor. This is Skill 4 in the BDD pipeline.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Implementing with TDD

Strict red-green-refactor implementation of beads tasks. Every line of production code is justified by a failing test.

## When to Use

- User says "implement this task", "write the code for", or "TDD this feature"
- A beads issue is ready and you want to implement it safely
- You need to add behavior with tests-first discipline

## Pipeline Position

```
beads issue -> .feature spec -> .plan.md -> tasks -> TDD implementation
                                                     ^^^ YOU ARE HERE
```

## Pre-Implementation Checklist

Before writing ANY production code:

- [ ] Read the beads task: `bd show <task-id>`
- [ ] Read related .feature file (if BDD workflow)
- [ ] Read related .plan.md (if it exists)
- [ ] Query knowledge: `/query` for relevant domain context
- [ ] Identify one test/scenario to implement next (single increment)
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

### BDD TDD Pattern (features/test_*.py)

When implementing BDD scenarios with TDD:

```
1. Run pytest features/<domain>/ -v          # See failing scenarios
2. Pick ONE scenario                         # Single increment
3. Write/update step definitions             # RED: test fails
4. Implement production code                 # GREEN: test passes
5. Refactor if needed                        # REFACTOR: clean up
6. Run pytest features/<domain>/ -v          # Verify
7. Repeat for next scenario
```

### BDD Scenarios (features/test_*.py)

Implement step definitions for pytest-bdd scenarios:

```python
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from strategies.avellaneda_stoikov.model import AvellanedaStoikov

# Load scenarios from .feature file -- ALWAYS use scenarios(".")
scenarios(".")


class Context:
    """Mutable container for passing data between steps."""
    def __init__(self):
        self.model = None
        self.result = None


@pytest.fixture
def ctx():
    return Context()


@given("a default Avellaneda-Stoikov model")
def given_default_model(ctx):
    ctx.model = AvellanedaStoikov()


@when(parsers.parse("I calculate the spread with volatility {vol:g}"))
def when_calculate_spread(ctx, vol):
    ctx.result = ctx.model.calculate_optimal_spread(vol, 0.5)


@then("the spread should be positive")
def then_spread_positive(ctx):
    assert ctx.result > 0
```

### Strategy Tests (tests/unit/)

Test trading strategy components:

```python
import pytest
import numpy as np
from strategies.avellaneda_stoikov.model import AvellanedaStoikov


def test_reservation_price_shifts_with_inventory():
    """RED: this should fail until implementation exists."""
    model = AvellanedaStoikov()
    r_long = model.calculate_reservation_price(50000, 5, 0.02, 0.5)
    r_neutral = model.calculate_reservation_price(50000, 0, 0.02, 0.5)
    assert r_long < r_neutral  # Long inventory pushes price down
```

### Order Book / Data Pipeline Tests

Test exchange connectivity and data processing:

```python
import pytest
from strategies.avellaneda_stoikov.order_book import OrderBook


def test_mid_price_from_order_book():
    """Mid price should be average of best bid and ask."""
    book = OrderBook()
    book.update(bids=[(50000, 1.0)], asks=[(50001, 1.0)])
    assert book.mid_price == pytest.approx(50000.5)
```

## Quality Gates

Before marking a task complete, ALL must pass:

```bash
# 1. All tests pass
pytest

# 2. BDD scenarios pass (if applicable)
pytest features/<domain>/ -v

# 3. No lint errors
ruff check .

# 4. No type errors (if configured)
mypy strategies/
```

## Commands

```bash
# Run all tests
pytest

# Run specific feature domain
pytest features/trading/ -v

# Run specific test file
pytest tests/unit/avellaneda_stoikov/test_model.py -v

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "reservation_price"

# Run with coverage
pytest --cov=strategies --cov-report=term-missing

# Collect without running (verify parsing)
pytest features/ --collect-only

# Task status
bd show <task-id>
bd update <task-id> --status in_progress
bd close <task-id> --reason "Implemented with TDD"
```

## Team Agent Usage

When working as a team agent implementing tasks:

1. **Claim the task**: `bd update <id> --status in_progress`
2. **Follow TDD strictly**: RED -> GREEN -> REFACTOR for each scenario
3. **Run quality gates** before marking complete
4. **Close the task**: `bd close <id> --reason "Implemented with TDD"`
5. **Report to team lead** with test results summary

## Anti-Patterns (NEVER DO)

- Writing production code before the test
- Skipping the RED phase
- "Fixing" a failing test by weakening assertions
- Making broad refactors while tests are red
- Closing the beads task without green tests
- Using look-ahead bias in test data (e.g., using future prices)
- Testing against overfit parameters
- Ignoring fill assumption realism in backtest tests

## Completion Checklist

- [ ] All tests pass: `pytest`
- [ ] BDD scenarios pass: `pytest features/<domain>/ -v`
- [ ] No lint errors: `ruff check .`
- [ ] No type errors: `mypy strategies/` (if configured)
- [ ] Close the beads task: `bd close <task-id> --reason "Implemented with TDD"`

## Related Documentation

- [BDD Workflow](../../.rules/patterns/bdd-workflow.md) - Full BDD pipeline reference
- [Beads Integration](../../.rules/patterns/beads-integration.md) - Issue tracking
- [Git Workflow](../../.rules/patterns/git-workflow.md) - Branching and commits
- [Features README](../../features/README.md) - Feature directory conventions
