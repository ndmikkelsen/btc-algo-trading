---
name: creating-features-from-tasks
description: Creates Gherkin .feature files from beads tasks or epics. Use when a beads issue describes a feature but no .feature file exists, when asked to "create feature file from task", "write scenarios for", or "convert this epic to BDD". This is Skill 1 in the BDD pipeline.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Creating Features from Tasks

Generate Gherkin `.feature` files from beads task/epic descriptions. Features are the entry point to the BDD pipeline -- every new capability starts here.

## When to Use

- User says "create feature file from task", "write scenarios for", or "convert this epic to BDD"
- A beads issue describes a feature but no `.feature` file exists
- Starting the BDD cycle for a new capability

## Pipeline Position

```
beads issue -> .feature spec -> .plan.md -> tasks -> TDD implementation
^^^ YOU ARE HERE
```

## Workflow

1. **Read the beads issue**: `bd show <task-id>`
2. **Query knowledge**: `/query` relevant domain concepts (trading strategies, indicators, order books, etc.)
3. **Analyze requirements**: Extract user stories, acceptance criteria, edge cases
4. **Research codebase**: Find similar features, understand patterns (`features/<domain>/`)
5. **Write .feature file**: Follow Gherkin best practices (see below)
6. **Create test runner**: `test_<feature-name>.py` with `scenarios(".")`
7. **Review with user**: Confirm scenarios before proceeding to `.plan.md`

## Output Location

Features are organized by domain:

```
features/
├── conftest.py                        # SHARED steps (fixtures + Given/When/Then)
├── <domain>/
│   ├── <feature-name>.feature         ← CREATE THIS
│   ├── <feature-name>.plan.md         ← Next step: /planning-features
│   └── test_<feature-name>.py         ← CREATE THIS (scenarios(".") only)
```

Domain is derived from:

1. Beads task title/description keywords
2. Existing feature directories (e.g., `trading/`, `backtesting/`, `risk/`)
3. Ask user if unclear

### Domain Directory Mapping

| Domain | Directory | Examples |
|--------|-----------|----------|
| Market making / quoting | `trading/` | Spread calc, inventory mgmt, order placement |
| Backtesting / simulation | `backtesting/` | Fill models, walk-forward, Monte Carlo |
| Risk management | `risk/` | Position sizing, stop-loss, drawdown limits |
| Data pipeline | `data/` | Order book capture, multi-exchange, validation |
| Infrastructure | `infra/` | Exchange connectivity, monitoring, alerts |

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

## Step Definition Architecture

**Shared steps** (`features/conftest.py`):
- Model fixtures (`as_model`, `as_model_custom`)
- Price data fixtures (`sample_prices`, `trending_prices`, `stable_prices`)
- Generic `Given` steps for market state setup
- Generic `Then` steps for common assertions

### Available Shared Fixtures

Before writing new steps, check what's already in `features/conftest.py`:

| Fixture | Purpose | Returns |
|---------|---------|---------|
| `as_model` | Default A-S model instance | `AvellanedaStoikov()` |
| `as_model_custom` | Factory for custom params | `_create(risk_aversion, order_book_liquidity, ...)` |
| `sample_prices` | 100 random BTC prices (seed=42) | `pd.Series` |
| `stable_prices` | Low-volatility price series | `pd.Series` |
| `trending_prices` | Upward-trending price series | `pd.Series` |
| `sample_ohlcv` | 200-row OHLCV DataFrame | `pd.DataFrame` |

**Feature-specific steps** (`test_<domain>.py`):
- Steps unique to that feature domain
- `scenarios(".")` call to register the `.feature` file

**IMPORTANT**: Always use `scenarios(".")` (not explicit file paths) for portability.

## Feature File Structure

### Feature Header

```gherkin
Feature: {Feature Name}
  As a {role}
  I want {capability}
  So that {benefit}
```

### Background (optional)

Use for common setup shared by all scenarios:

```gherkin
Background:
  Given a BTC mid price of 50000
  And a default Avellaneda-Stoikov model
```

### Scenarios

Each scenario tests one specific behavior:

```gherkin
Scenario: {Descriptive name}
  Given {precondition}
  When {action}
  Then {expected outcome}
```

## Scenario Templates

### Strategy Calculation

```gherkin
Scenario: Calculate {indicator/signal} under {condition}
  Given {market conditions}
  And {model parameters}
  When I calculate the {indicator}
  Then the result should {expected behavior}
```

### Risk Management

```gherkin
Scenario: {Risk rule} triggers under {condition}
  Given {position/exposure state}
  When {market event occurs}
  Then {risk action should be taken}
  And the position should {expected state}
```

### Order Execution

```gherkin
Scenario: Place {order type} when {condition}
  Given {market state}
  And {strategy parameters}
  When the strategy evaluates the market
  Then a {order type} order should be placed at {price level}
```

### Fill Model Validation

```gherkin
Scenario: {Fill condition} under {market condition}
  Given {order book state}
  And {order placement}
  When {time passes / price moves}
  Then the fill probability should be {expectation}
```

### Error Handling

```gherkin
Scenario: Handle {error condition}
  Given {setup for error}
  When {action that may fail}
  Then {graceful handling}
  And {system remains stable}
```

## Step Expressions

Use parameterized steps for reusability with `pytest_bdd.parsers`:

```python
from pytest_bdd import parsers

@given(parsers.parse("a volatility of {volatility:g}"))
def given_volatility(ctx, volatility):
    ctx.volatility = volatility
```

## Example: Beads Task to .feature

### Input: Beads Task

```
Title: Implement order book data pipeline for Bybit
Description: Build WebSocket-based L2 order book capture from Bybit
for real-time bid/ask data and liquidity measurement.
```

### Output: .feature File

Create `features/data/order-book-pipeline.feature`:

```gherkin
Feature: Order book data pipeline
  As a market maker
  I want real-time order book data from Bybit
  So that I can measure liquidity and place informed quotes

  Background:
    Given a Bybit WebSocket connection configuration

  Scenario: Connect to Bybit order book stream
    When I subscribe to BTC/USDT L2 order book
    Then I should receive order book snapshots
    And each snapshot should have bids and asks

  Scenario: Calculate mid price from order book
    Given an order book with best bid 50000 and best ask 50001
    When I calculate the mid price
    Then the mid price should be 50000.50

  Scenario: Measure order book liquidity (kappa)
    Given an order book with known depth
    When I estimate the liquidity parameter
    Then kappa should be a positive number
    And kappa should reflect the book depth

  Scenario: Handle WebSocket disconnection
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

## After Creation

1. **Review .feature with user** - Confirm scenarios capture requirements
2. **Create implementation plan** - Run `/planning-features` to generate `.plan.md`
3. **Create tasks** - Run `/creating-tasks-from-plans` to generate beads tasks
4. **Implement with TDD** - Run `/implementing-with-tdd` for each task

## Team Agent Usage

When working as a team agent creating features:

1. **Read the beads task** assigned to you
2. **Create .feature file** following conventions above
3. **Create test runner** with `scenarios(".")`
4. **Report to team lead** with file paths and scenario count
5. Team lead reviews and approves before planning phase

## Anti-Patterns (NEVER DO)

- Writing implementation-specific steps ("call function X", "query database")
- Combining multiple behaviors in one scenario
- Skipping error/edge case scenarios
- Using technical jargon instead of domain language
- Creating .feature without user review
- Proceeding to implementation without .plan.md
- Using explicit file paths instead of `scenarios(".")`
- Creating steps in test files that belong in shared conftest.py

## Commands

```bash
# View the beads task
bd show <task-id>

# Query domain knowledge
/query How does the Avellaneda-Stoikov model handle inventory risk?

# List existing feature directories
ls features/

# Find similar features
grep -r "Feature:" features/

# Verify feature parses
pytest features/<domain>/ --collect-only
```
