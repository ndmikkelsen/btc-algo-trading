---
name: creating-features-from-tasks
description: Creates Gherkin .feature files from beads tasks or epics. Use when a beads issue describes a feature but no .feature file exists, when asked to "create feature file from task", "write scenarios for", or "convert this epic to BDD".
allowed-tools: Read, Write, Bash, Glob, Grep
---

# Creating Features from Tasks

Generate Gherkin `.feature` files from beads task/epic descriptions.

## When to Use

- User says "create feature file from task", "write scenarios for", or "convert this epic to BDD"
- A beads issue describes a feature but no `.feature` file exists
- Starting the BDD cycle for a new capability

## Workflow

1. **Read the beads issue**: `bd show <task-id>`
2. **Query knowledge**: `/query` relevant domain concepts (trading strategies, indicators, etc.)
3. **Analyze requirements**: Extract user stories, acceptance criteria, edge cases
4. **Research codebase**: Find similar features, understand patterns (`features/<domain>/`)
5. **Write .feature file**: Follow Gherkin best practices (see below)
6. **Create directory**: `features/<domain>/<feature-name>.feature`
7. **Review with user**: Confirm scenarios before proceeding to `.plan.md`

## Output Location

```
features/
├── <domain>/
│   ├── <feature-name>.feature       ← CREATE THIS
│   ├── <feature-name>.plan.md       ← Next step: /planning-features
│   └── test_<feature-name>.py       ← Step implementations (pytest-bdd)
```

Domain is derived from:

1. Beads task title/description keywords
2. Existing feature directories (e.g., `trading/`, `backtesting/`)
3. Ask user if unclear

## Gherkin Syntax Reference

### Keywords

- **Feature**: High-level description of a software feature.
- **Scenario**: A specific business situation or path through a feature.
- **Given**: Describes the initial context (setup).
- **When**: Describes the event or action.
- **Then**: Describes the expected outcome (assertion).
- **And/But**: Extends the preceding keyword.
- **Background**: Common setup shared by all scenarios in a feature.

### Best Practices

- Focus on "what" the system does, not "how" it does it.
- Keep scenarios concise and focused on a single behavior.
- Use domain-specific language that stakeholders understand.
- One behavior per scenario.
- Use declarative style (what, not how).
- Avoid UI-specific language.
- Include happy path AND edge cases.

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
  And a default model configuration
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

### Strategy Calculation Scenario

```gherkin
Scenario: Calculate {indicator/signal} under {condition}
  Given {market conditions}
  And {model parameters}
  When I calculate the {indicator}
  Then the result should {expected behavior}
```

### Risk Management Scenario

```gherkin
Scenario: {Risk rule} triggers under {condition}
  Given {position/exposure state}
  When {market event occurs}
  Then {risk action should be taken}
  And the position should {expected state}
```

### Order Execution Scenario

```gherkin
Scenario: Place {order type} when {condition}
  Given {market state}
  And {strategy parameters}
  When the strategy evaluates the market
  Then a {order type} order should be placed at {price level}
```

### Error Handling Scenario

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
Title: Implement regime detection for A-S strategy
Description: Add market regime detection (trending vs ranging) to adjust
spread and inventory parameters dynamically.
```

### Output: .feature File

```gherkin
Feature: Market Regime Detection
  As a market maker
  I want to detect the current market regime
  So that I can adjust my quoting parameters for optimal performance

  Background:
    Given a default regime detector

  Scenario: Detect trending market from ADX
    Given a price series with strong directional movement
    When I calculate the ADX indicator
    Then the market regime should be "trending"

  Scenario: Detect ranging market from ADX
    Given a price series with sideways movement
    When I calculate the ADX indicator
    Then the market regime should be "ranging"

  Scenario: Widen spread in trending market
    Given the market regime is "trending"
    When I adjust the model parameters
    Then the spread should be wider than default

  Scenario: Reduce position size in trending market
    Given the market regime is "trending"
    When I calculate the position size
    Then the position should be scaled by the trend factor
```

## After Creation

1. **Review .feature with user** - Confirm scenarios capture requirements
2. **Create implementation plan** - Run `/planning-features` to generate `.plan.md`
3. **Create tasks** - Run `/creating-tasks-from-plans` to generate beads tasks
4. **Implement with TDD** - Run `/implementing-with-tdd` for each task

## Anti-Patterns (NEVER DO)

- Writing implementation-specific steps ("call function X", "query database")
- Combining multiple behaviors in one scenario
- Skipping error/edge case scenarios
- Using technical jargon instead of domain language
- Creating .feature without user review
- Proceeding to implementation without .plan.md

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
```
