# BDD Test Infrastructure Audit

> Comparison of BDD test patterns between **compute-stack** and **algo-imp** repositories.
>
> **Date**: 2026-02-09
> **Auditor**: Validation Agent (validator)
> **Scope**: conftest patterns, test file patterns, feature files, pytest config, test execution

---

## Executive Summary

Both repositories use **pytest-bdd** with a consistent architectural pattern: shared steps in `conftest.py`, thin test runners using `scenarios(".")`, and Gherkin `.feature` files with `Background` sections. The pattern has been successfully adapted from infrastructure validation (compute-stack) to algorithmic trading domain logic (algo-imp), with appropriate domain-specific differences.

**Key findings:**
- 11/12 algo-imp tests pass (1 failure: `max_spread` clamping bug in model code)
- Core architectural patterns are consistent across both repos
- algo-imp introduces a `Context` class pattern not present in compute-stack
- Pytest config differs (pytest.ini vs pyproject.toml, missing `bdd_features_base_dir`)

---

## 1. conftest.py Patterns

### compute-stack (media-stack, llm-stack, pihole)

All three conftest.py files share a **nearly identical structure**:

```
conftest.py structure (compute-stack):
  - Utility functions (get_host_port)
  - Session-scoped fixtures (compose_config, all_services)
  - Given steps (the docker-compose.yml is loaded -> target_fixture="services")
  - Then steps organized by category (existence, ports, env, volumes, deps)
```

**Key characteristics:**
- Fixtures use `scope="session"` for expensive YAML parsing
- The `@given` step uses `target_fixture="services"` to inject fixture data into BDD step chain
- All `@then` steps accept `services` parameter directly from the `target_fixture`
- Steps are parameterized with `parsers.parse()` for dynamic values like `"{service}"`, `"{port}"`
- No `@when` steps at all -- tests go directly Given -> Then (validation-only pattern)
- Imports: `re`, `Path`, `pytest`, `yaml`, `pytest_bdd.{given, then, parsers}`

**Cross-file differences (compute-stack internal):**

| Step | media-stack | llm-stack | pihole |
|------|------------|-----------|--------|
| `get_host_port()` | Yes | Yes | Yes |
| `compose_config` fixture | Yes (session) | Yes (session) | Yes (session) |
| `all_services` fixture | Yes (session) | Yes (session) | Yes (session) |
| `@given docker-compose loaded` | Yes (target_fixture) | Yes (target_fixture) | Yes (target_fixture) |
| healthcheck step | Yes | Yes | No |
| env var step | `should set "{env_var}"` | No | `should set environment variable "{var}"` |
| password substitution | Yes | No | No |
| volume substitution | Yes | Yes | No |
| debrid/rshared mount | Yes | No | No |
| pg_isready step | Yes | No | No |
| NVIDIA GPU step | No | Yes | No |
| capability step | No | No | Yes |
| usenet mount step | Yes | No | No |

**Note:** pihole uses a different step text for env vars (`"should set environment variable"` vs `"should set"`). This is a minor inconsistency within compute-stack itself.

### algo-imp

```
conftest.py structure (algo-imp):
  - Domain fixtures (as_model, as_model_custom factory)
  - Data fixtures (sample_prices, stable_prices, trending_prices, sample_ohlcv)
  - NO Given/Then/When shared steps
  - NO target_fixture pattern
```

**Key characteristics:**
- Fixtures are **not** session-scoped (default function scope) -- appropriate since model creation is cheap
- Uses a **factory fixture** pattern (`as_model_custom`) not seen in compute-stack
- All step definitions live in the test file, not conftest
- No shared Given/Then steps at all -- each test file owns its complete step set
- Imports: `numpy`, `pandas`, `pytest`, domain model class

### Differences Summary

| Aspect | compute-stack | algo-imp |
|--------|--------------|----------|
| Fixture scope | `session` | `function` (default) |
| Shared Given steps | Yes (`target_fixture`) | No |
| Shared Then steps | Yes (15-20 reusable steps) | No |
| Factory fixtures | No | Yes (`as_model_custom`) |
| Data generation | YAML file loading | NumPy/Pandas random data |
| Step imports in conftest | `given`, `then`, `parsers` | None (no steps) |
| Utility functions | `get_host_port()` | None |

### Assessment

The difference is **appropriate by domain**. compute-stack validates the same kinds of properties (existence, ports, env vars) across many services, making shared steps valuable. algo-imp tests domain-specific behavior where each feature has unique steps. The conftest correctly provides only fixtures (model instances, data) that are reused across features.

**Potential issue:** As algo-imp grows more features, there may be benefit in moving common Given steps (e.g., "a BTC mid price of X", "a default model") to conftest.py using the `target_fixture` pattern. Currently this is fine at the single-feature stage.

---

## 2. Test File Patterns

### compute-stack

All 4 test files follow an **identical minimal pattern**:

```python
"""BDD test runner for <name> feature files."""
from pytest_bdd import scenarios

scenarios(".")
```

- No step definitions in test files
- No Context class
- No additional imports
- Docstring describes the file purpose
- **Every** test file is exactly 3-5 lines of code

### algo-imp

`test_market_making.py` is substantially more complex (220 lines):

```python
from pytest_bdd import scenarios, given, when, then, parsers
scenarios(".")

class QuoteContext:
    """Mutable container for passing data between steps."""
    mid_price, model, inventory, volatility, time_remaining, ...

@pytest.fixture
def ctx():
    return QuoteContext()

# Given steps (8 step definitions)
# When steps (5 step definitions)
# Then steps (12 step definitions)
```

**Key patterns:**
- `scenarios(".")` -- matches compute-stack convention exactly
- `QuoteContext` class as a mutable container for inter-step state
- `ctx` fixture injected into every step via function parameter
- Steps organized in sections with comments: `# --- Given steps ---`, `# --- When steps ---`, `# --- Then steps ---`
- Uses `parsers.parse()` with typed parameters: `{inventory:d}`, `{volatility:g}`, `{time_remaining:g}`
- Uses all three step types (Given/When/Then) unlike compute-stack's Given/Then-only pattern

### Context Class Pattern

This is the most significant architectural difference. compute-stack doesn't need it because:
- `target_fixture="services"` provides a single shared data dict
- Steps only read from the compose config, never building intermediate state

algo-imp needs `QuoteContext` because:
- Steps build up state incrementally (set price, set model, set inventory, calculate, assert)
- Multiple intermediate results need to be compared (spread_1 vs spread_2, neutral vs inventory quotes)
- The pattern avoids excessive fixture chaining

### Assessment

The `QuoteContext` pattern is a **sound approach** for stateful BDD scenarios. compute-stack's minimal test files work because conftest.py carries all the step definitions. algo-imp's approach of co-locating steps with `scenarios(".")` is also valid and arguably better for domain-specific features.

---

## 3. Feature File Patterns

### Gherkin Conventions

| Convention | compute-stack | algo-imp |
|-----------|--------------|----------|
| Feature description | 3-line (As a / I want / So that) | 3-line (As a / I want / So that) |
| Background section | Yes (always) | Yes |
| Scenario keyword | `Scenario` and `Scenario Outline` | `Scenario` only |
| Examples keyword | Yes (with `Scenario Outline`) | No |
| Example tags | Yes (`@media_automation`, etc.) | No |
| Feature-level tags | Some (`@llm_inference`, `@dns_filtering`) | No |
| Comment sections | Yes (`# --- Category ---`) | Yes (`# --- Category ---`) |
| Step parameter syntax | `"<service>"` (outline) / `"{service}"` (inline) | Natural language only |

### Background Usage

**compute-stack:**
```gherkin
Background:
  Given the docker-compose.yml is loaded
```
- Every feature file has exactly this one Background step
- Consistent across all stacks

**algo-imp:**
```gherkin
Background:
  Given a BTC mid price of 50000
  And a default Avellaneda-Stoikov model
```
- More complex Background with 2 steps
- Domain-specific setup shared by all scenarios

### Scenario Outline with Examples

**compute-stack uses this extensively:**
```gherkin
Scenario Outline: Required service exists
  Then the "<service>" service should exist

  @media_automation
  Examples: Media Automation
    | service          |
    | zurg             |
    | riven            |
```

**algo-imp does NOT use Scenario Outline at all.** Each scenario is fully written out. This is because:
- Trading scenarios have unique Given/When/Then step combinations
- Unlike infrastructure checks where the same assertion applies to many services
- Each scenario tests a different behavior, not the same behavior across entities

### Assessment

Both approaches are **correct for their domains**:
- compute-stack's heavy use of `Scenario Outline + Examples` is ideal for repetitive validation across many services
- algo-imp's individual scenarios are better for behavior-driven testing where each scenario has unique logic

**The comment style (`# --- Category ---`) is consistent across both repos**, which is a good convention.

---

## 4. Pytest Configuration

### compute-stack (pyproject.toml)

All three apps use the same pytest config pattern in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests", "features"]
addopts = "-v --tb=short"
bdd_features_base_dir = "features/"
markers = [...]  # optional, domain-specific
```

### algo-imp (pytest.ini)

```ini
[pytest]
testpaths = tests features
python_files = test_*.py
addopts = -v --tb=short
markers =
    unit: Unit tests
    integration: Integration tests
    bdd: BDD feature tests
```

### Differences

| Setting | compute-stack | algo-imp | Impact |
|---------|--------------|----------|--------|
| Config file format | `pyproject.toml` | `pytest.ini` | Cosmetic (both work) |
| `bdd_features_base_dir` | Set to `"features/"` | **Missing** | Could cause path issues if scenarios() uses relative paths across directories |
| `python_files` | Not set (default) | `test_*.py` (explicit) | No functional difference (matches default) |
| Markers | Domain-specific | Generic (unit/integration/bdd) | compute-stack markers align with feature tags |
| `testpaths` format | TOML list | Space-separated | Cosmetic |

### Critical Difference: `bdd_features_base_dir`

compute-stack sets `bdd_features_base_dir = "features/"` which tells pytest-bdd where to resolve feature file paths relative to. algo-imp **does not set this**, relying on `scenarios(".")` to find `.feature` files relative to the test file's directory. This works currently because:
- The test file sits next to the feature file in `features/trading/`
- `scenarios(".")` resolves relative to the test file location

**Risk:** If a future test file is placed in a different directory structure, the missing `bdd_features_base_dir` could cause pytest-bdd to fail to locate `.feature` files.

---

## 5. Test Execution Results

### algo-imp Test Run

```
$ python3 -m pytest features/ -v

12 items collected
11 passed, 1 failed
```

| Test | Status |
|------|--------|
| Reservation price equals mid price with zero inventory | PASSED |
| Reservation price is below mid price with long inventory | PASSED |
| Reservation price is above mid price with short inventory | PASSED |
| Spread widens with higher volatility | PASSED |
| Spread respects minimum bound | PASSED |
| **Spread respects maximum bound** | **FAILED** |
| Bid is below ask | PASSED |
| Quotes straddle the reservation price | PASSED |
| Long inventory shifts quotes downward | PASSED |
| Short inventory shifts quotes upward | PASSED |
| Volatility calculated from price series | PASSED |
| Default volatility for insufficient data | PASSED |

### Failure Analysis

```
test_spread_respects_maximum_bound:
  assert ctx.spread <= ctx.model.max_spread
  AssertionError: assert 1.3907 <= 0.05
```

The `calculate_optimal_spread()` method returns a raw spread (1.39) that exceeds `max_spread` (0.05). The model's `calculate_optimal_spread` method does **not** clamp the result to `[min_spread, max_spread]`. This is a **bug in the model code**, not in the test infrastructure. The test is correctly written and correctly catching the bug.

---

## 6. Overall Comparison Matrix

| Pattern | compute-stack | algo-imp | Aligned? |
|---------|--------------|----------|----------|
| `scenarios(".")` in test files | Yes (all 4) | Yes | Yes |
| Shared steps in conftest.py | Yes (Given + Then) | Fixtures only | Intentionally different |
| `target_fixture` in Given | Yes | Yes | Yes |
| Context class | No | Yes (`QuoteContext`) | Domain-appropriate |
| Background in .feature | Yes (1 step) | Yes (2 steps) | Yes |
| Scenario Outline + Examples | Heavy use | Not used | Domain-appropriate |
| Feature-level tags | Some (@llm_inference) | None | Gap (could add @trading) |
| Comment sections in .feature | Yes | Yes | Yes |
| `parsers.parse()` for params | Yes (string only) | Yes (typed: :d, :g) | algo-imp is more advanced |
| pytest addopts | `-v --tb=short` | `-v --tb=short` | Yes |
| `bdd_features_base_dir` | Set | **Missing** | Gap |
| Tests passing | N/A (not run) | 11/12 | 1 model bug |

---

## 7. Recommendations

### Must Fix

1. **Add `bdd_features_base_dir`** to `pytest.ini`:
   ```ini
   bdd_features_base_dir = features/
   ```
   This matches compute-stack convention and prevents future path resolution issues.

2. **Fix max_spread clamping** in `AvellanedaStoikov.calculate_optimal_spread()`:
   The method should clamp output to `[min_spread, max_spread]`. The test correctly expects this behavior.

### Should Consider

3. **Add feature-level tags** to `market-making.feature`:
   ```gherkin
   @trading
   Feature: Avellaneda-Stoikov Market Making
   ```
   This matches compute-stack's convention (`@llm_inference`, `@dns_filtering`) and enables selective test execution.

4. **Add domain markers** to pytest config that match feature tags:
   ```ini
   markers =
       trading: Trading strategy tests
       backtesting: Backtest and simulation tests
   ```

### Nice to Have

5. **Promote common Given steps to conftest.py** as more features are added:
   - `"a BTC mid price of {price}"` will likely be reused across trading, backtesting, and risk features
   - Use `target_fixture` pattern from compute-stack

6. **Consider `@dataclass` for QuoteContext** to make attributes explicit and provide better IDE support.

---

**Overall Verdict**: BDD test infrastructure is complete, functional, and properly adapted from compute-stack's patterns. The architecture choices (function-scoped fixtures, domain-specific steps, Context class) are all correct for algo-imp's domain. The 1 test failure is a legitimate model bug correctly caught by the BDD test.
