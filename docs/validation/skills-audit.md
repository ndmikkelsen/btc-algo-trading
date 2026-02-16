# Skills Audit: algo-imp vs compute-stack (Detailed Validation)

**Date**: 2026-02-09
**Auditor**: Validation Agent (deep comparison)
**Purpose**: Line-by-line comparison of all BDD/TDD skill files to find genuine gaps, missing content, and incomplete adaptations.

---

## Executive Summary

| Skill File | Gaps Found | Severity |
|------------|-----------|----------|
| creating-features-from-tasks | 4 gaps | 2 should-fix, 2 nice-to-have |
| planning-features | 1 gap | Nice-to-have |
| creating-tasks-from-plans | 1 gap | Nice-to-have |
| implementing-with-tdd | 1 gap | Should-fix |
| README.md | 2 gaps | Nice-to-have |

**Overall**: The algo-imp skills are well adapted. Infrastructure patterns were correctly replaced with trading-domain patterns. Most gaps are minor, but a few (missing `Edit` tool, missing shared step listing, missing Related Documentation links) should be addressed.

---

## 1. creating-features-from-tasks

### Sections Compared

| # | Section | compute-stack | algo-imp | Verdict |
|---|---------|--------------|----------|---------|
| 1 | Frontmatter `allowed-tools` | `Read, Write, Edit, Bash, Grep, Glob` | `Read, Write, Bash, Glob, Grep` | **GAP: Missing `Edit`** |
| 2 | When to Use | 4 bullets (infra-focused) | 3 bullets (trading-focused) | Adapted |
| 3 | Pipeline Position | Diagram | Diagram | Match |
| 4 | Workflow | 7 steps (app identification) | 7 steps (adds `/query`, domain research) | algo-imp better |
| 5 | Directory Naming Rules | 3 rules (lowercase, grouping, per-app) | Not present as section | **GAP** |
| 6 | Output Location / Structure | `apps/<app>/features/<domain>/` | `features/<domain>/` | Adapted |
| 7 | Domain Directory Mapping | Not present | 5-row table | algo-imp addition |
| 8 | Gherkin Conventions / Templates | 5 infrastructure templates | 5 trading templates | Adapted |
| 9 | Gherkin -> Trading Mapping | Not present | 7-row concept mapping table | algo-imp addition |
| 10 | Shared Step Definitions | **10 explicit steps listed** | Pattern described, no steps listed | **GAP** |
| 11 | Test Runner Pattern | `scenarios(".")` | `scenarios(".")` | Match |
| 12 | Feature File Structure | Inline in conventions | Separate section with Header/Background/Scenarios | algo-imp better |
| 13 | Step Expressions | Not present | parsers.parse example | algo-imp addition |
| 14 | Example | Sonarr -> .feature | Order book pipeline -> .feature | Adapted |
| 15 | After Creation | 4 steps | 4 steps (adds user review) | algo-imp better |
| 16 | Team Agent Usage | Not present | 5-step workflow | algo-imp addition |
| 17 | Anti-Patterns | 6 items | 8 items | See detailed comparison |
| 18 | Commands | Not present | 5 bash commands | algo-imp addition |

### GAP 1.1: Missing `Edit` in allowed-tools

**Severity**: Should fix

**compute-stack** frontmatter line 4:
```yaml
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
```

**algo-imp** frontmatter line 4:
```yaml
allowed-tools: Read, Write, Bash, Glob, Grep
```

**Impact**: Agents using this skill cannot modify existing `conftest.py` or `.feature` files -- they can only create new ones. The `Edit` tool is needed when adding shared steps to an existing conftest or updating an existing feature file.

### GAP 1.2: Missing "Directory Naming Rules" section

**Severity**: Nice-to-have

**compute-stack** lines 35-39:
```markdown
## Directory Naming Rules

- Use lowercase with hyphens: `apps/media-stack/features/sonarr/`, `apps/media-stack/features/arr-stack/`
- Group related services: `features/monitoring/` not `features/prometheus/` + `features/grafana/`
- Features live inside the app they belong to
```

**algo-imp** has no equivalent. While the "Domain Directory Mapping" table shows directory names, it doesn't state explicit naming conventions. An agent might create `features/OrderBook/` instead of `features/data/`.

**Recommendation**: Add rules like:
- Use lowercase with hyphens for directory names
- Group by trading domain, not by individual indicator
- Prefer broad categories (`trading/`, `data/`) over narrow ones (`spread-calc/`, `mid-price/`)

### GAP 1.3: Missing explicit shared step definitions listing

**Severity**: Should fix

**compute-stack** lines 117-132 explicitly enumerates every shared step:
```markdown
## Shared Step Definitions

Each app has its own `features/conftest.py` with shared step definitions. Common steps include:

- `Given the docker-compose.yml is loaded`
- `Then the "{service}" service should exist`
- `Then the "{service}" service should have a container_name`
- `Then the "{service}" service should have a restart policy`
- `Then the "{service}" service should have a healthcheck`
- `Then the "{service}" service should expose host port "{port}"`
- `Then the "{service}" service should set "{env_var}"`
- `Then the "{service}" service should depend on "{dependency}"`
- `Then the "{service}" service should use variable substitution for config volumes`
- `Then there should be no duplicate host port bindings`
```

**algo-imp** "Step Definition Architecture" section (lines 78-88) describes the pattern (shared vs feature-specific, fixtures) but does NOT list what steps actually exist. An agent creating a new feature file won't know what Given/When/Then steps are already available without reading conftest.py first.

**Recommendation**: Add listing of existing shared steps, e.g.:
- `Given a BTC mid price of {price}`
- `Given a default Avellaneda-Stoikov model`
- Fixture: `as_model`, `as_model_custom`, `sample_prices`, etc.

### GAP 1.4: Missing anti-pattern from compute-stack

**Severity**: Nice-to-have

**compute-stack** anti-pattern (line 188):
```
- Creating `.feature` files that can't be executed by pytest-bdd
```

This is NOT in algo-imp's anti-patterns list. It's a useful quality gate -- ensuring features are syntactically valid for the test runner.

### Anti-Pattern Comparison (Full)

| Anti-Pattern | compute-stack | algo-imp |
|-------------|:---:|:---:|
| Writing implementation before `.feature` file | Y | N (different wording: "Proceeding to implementation without .plan.md") |
| Creating `.feature` files that can't be executed by pytest-bdd | Y | **MISSING** |
| Skipping the Background step | Y | N (infrastructure-specific) |
| Writing vague scenarios | Y | N (similar: "Using technical jargon instead of domain language") |
| Duplicating existing scenarios | Y | N |
| Using explicit file paths in `scenarios()` | Y | Y |
| Writing implementation-specific steps | N | Y |
| Combining multiple behaviors in one scenario | N | Y |
| Skipping error/edge case scenarios | N | Y |
| Using technical jargon instead of domain language | N | Y |
| Creating .feature without user review | N | Y |
| Proceeding to implementation without .plan.md | N | Y |
| Creating steps in test files that belong in conftest | N | Y |

---

## 2. planning-features

### Sections Compared

| # | Section | compute-stack | algo-imp | Verdict |
|---|---------|--------------|----------|---------|
| 1 | Frontmatter | Match | Match | Match |
| 2 | When to Use | 4 bullets | 4 bullets | Match (adapted "infrastructure" -> "trading strategy") |
| 3 | Pipeline Position | Diagram | Diagram | Match |
| 4 | Key Difference from Generic Planning | 4 bullets | 4 bullets | Match |
| 5 | Workflow | 6 steps (app identification) | 6 steps (domain identification) | Adapted |
| 6 | Plan Template | Full template | Full template | Match (paths adapted) |
| 7 | Technical Specifications | Docker Changes + Configuration | Trading Parameters + Data Requirements + Configuration | Adapted |
| 8 | Testing Strategy | BDD + Baseline Tests (REQUIRED_SERVICES, EXPECTED_PORTS) | BDD + Unit Tests | Adapted |
| 9 | Output Location | `apps/<app>/features/<domain>/` tree | `features/<domain>/` tree | Adapted |
| 10 | After Planning | 3 steps | 3 steps | Match |
| 11 | Team Agent Usage | Not present | 5 steps | algo-imp addition |
| 12 | Anti-Patterns | 5 items | 5 items | Match |
| 13 | Commands | Not present | 4 bash examples | algo-imp addition |

### GAP 2.1: No "Related Documentation" cross-links

**Severity**: Nice-to-have

compute-stack doesn't have this either in the planning-features skill, but the implementing-with-tdd skill (Skill 4) does. For consistency, algo-imp's planning-features should link to:
- `.rules/patterns/bdd-workflow.md`
- Other skills in the pipeline

### Overall Verdict

**No significant gaps.** algo-imp is a complete, well-adapted version with useful additions (Team Agent Usage, Commands).

---

## 3. creating-tasks-from-plans

### Sections Compared

| # | Section | compute-stack | algo-imp | Verdict |
|---|---------|--------------|----------|---------|
| 1 | Frontmatter | No pipeline position | Adds "This is Skill 3 in the BDD pipeline" | algo-imp better |
| 2 | Pipeline Position | Not present | Present with diagram | algo-imp addition |
| 3 | When to Use | 4 bullets | 4 bullets | Match |
| 4 | Input Location | `apps/<app>/` + `plans/` legacy | `features/<domain>/` only | See GAP |
| 5 | Workflow | 6 steps | 6 steps | Match |
| 6 | Task Extraction Rules | Phase checkbox mapping | Phase checkbox mapping | Match (adapted example) |
| 7 | Task Naming Convention | 3 rules | 3 rules | Match |
| 8 | Task Description Template | Full template with `App: apps/{app}/` | Full template (no App field) | Adapted |
| 9 | Priority Mapping | 4-row table | 4-row table | Match |
| 10 | Dependency Rules | 3 rules | 3 rules | Match |
| 11 | Commands | `bd create "Title"` syntax | `bd create --title="Title"` syntax | Different style |
| 12 | Output Format | Tree visualization | Tree visualization | Match |
| 13 | Example | Cognee Docker services | Order book WebSocket pipeline | Adapted |
| 14 | After Task Creation | 5 steps | 5 steps | Match |
| 15 | Team Agent Usage | 4 steps | 4 steps | Match |
| 16 | Anti-Patterns | 5 items | 6 items (adds `bd update --deps`) | algo-imp better |
| 17 | Commands Reference | Full bash examples | Full bash examples | Match |

### GAP 3.1: Inconsistency with planning-from-tasks output locations

**Severity**: Nice-to-have

algo-imp's `planning-from-tasks` skill says plans can go to:
```
features/<domain>/
docs/plans/
strategies/
```

But `creating-tasks-from-plans` only shows `features/<domain>/` as input. Should mention `docs/plans/` and `strategies/` as alternative input locations for consistency.

### Overall Verdict

**No significant gaps.** Well adapted with consistent trading-domain examples.

---

## 4. implementing-with-tdd

### Sections Compared

| # | Section | compute-stack | algo-imp | Verdict |
|---|---------|--------------|----------|---------|
| 1 | Frontmatter | Present | Adds pipeline position to description | algo-imp better |
| 2 | When to Use | 4 bullets (infra-focused) | 3 bullets (trading-focused) | Adapted |
| 3 | Pipeline Position | Not present | Diagram | algo-imp addition |
| 4 | Pre-Implementation Checklist | 5 items | 6 items (adds `/query`, single increment) | algo-imp better |
| 5 | TDD Cycle (mandatory) | RED/GREEN/REFACTOR | RED/GREEN/REFACTOR | Match |
| 6 | Compose-Specific TDD Pattern | Full section (RED/GREEN/REFACTOR for Docker) | Not present | Correct omission (infra-specific) |
| 7 | BDD TDD Pattern | 3-phase pattern for `.feature` work | 7-step pattern + code example | algo-imp better |
| 8 | Implementation Patterns | Not present as section | 4 patterns: BDD, Strategy Tests, Order Book, Data | algo-imp addition |
| 9 | Quality Gates | `pytest` + `py_compile` + `docker compose config` | `pytest` + `ruff check` + `mypy` | Adapted |
| 10 | Commands | 10 bash commands | 12 bash commands (adds coverage, collect-only) | algo-imp better |
| 11 | Example Workflow | Sonarr to media stack (bash walkthrough) | Not present as named section | Inline in patterns |
| 12 | Team Agent Usage | 5 steps | 5 steps | Match |
| 13 | Anti-Patterns | 7 items | 8 items (adds trading-specific) | algo-imp better |
| 14 | Completion Checklist | Not present | 5-item checklist | algo-imp addition |
| 15 | **Related Documentation** | **4 links** | **Not present** | **GAP** |

### GAP 4.1: Missing "Related Documentation" section

**Severity**: Should fix

**compute-stack** lines 212-217:
```markdown
## Related Documentation

- [BDD Workflow](.rules/patterns/bdd-workflow.md)
- [Beads Integration](.rules/patterns/beads-integration.md)
- [Git Workflow](.rules/patterns/git-workflow.md)
- [/land Command](.claude/commands/land.md)
```

**algo-imp** has no equivalent section in implementing-with-tdd. These cross-references help agents discover related workflow documentation. The algo-imp README.md has Related Documentation links, but the individual skill file should too -- especially since implementing-with-tdd is the most frequently used skill.

### Trading-Specific Anti-Patterns (algo-imp additions, well done)

These are in algo-imp but NOT in compute-stack:
- `Using look-ahead bias in test data (e.g., using future prices)`
- `Testing against overfit parameters`
- `Ignoring fill assumption realism in backtest tests`

These are excellent domain-specific additions that prevent common quant trading mistakes.

### Overall Verdict

**One gap** (missing Related Documentation links). Otherwise, algo-imp exceeds compute-stack with better patterns and trading-specific quality gates.

---

## 5. README.md

### Sections Compared

| # | Section | compute-stack | algo-imp | Verdict |
|---|---------|--------------|----------|---------|
| 1 | Pipeline Overview | Single-path diagram | BDD path + alternative non-BDD path | algo-imp better |
| 2 | Available Skills | 4 skills | 6 skills (adds planning-from-tasks, log-backtest) | algo-imp better |
| 3 | Skill descriptions | Triggers + Input/Output | Triggers + Input/Output | Match |
| 4 | Integration with Knowledge System | Per-app directory tree | Not present | **GAP** (minor) |
| 5 | Current Apps/Domains with BDD | 4 apps listed | Not present | **GAP** (minor) |
| 6 | Workflow Example | 1 example (single walkthrough) | 2 examples (full feature + quick bug fix) | algo-imp better |
| 7 | Team Agent Workflow | 7-step text | 8-step process + Agent Task Assignment table | algo-imp better |
| 8 | Skill Development | muninn attribution, tech comparison | Not present | **GAP** (minor) |
| 9 | Related Documentation | 4 links (patterns, commands) | 4 links (patterns, AGENTS.md, CONSTITUTION.md) | Match (different targets) |

### GAP 5.1: Missing "Skill Development" provenance section

**Severity**: Nice-to-have

**compute-stack** lines 146-149:
```markdown
## Skill Development

Skills are adapted from [muninn](https://github.com/bldx/muninn) with modifications for compute-stack's multi-app monorepo:

- **muninn**: TypeScript, BDD/Gherkin, API development
- **compute-stack**: Python, infrastructure, Docker, monitoring, BDD/Gherkin, multi-app monorepo
```

**algo-imp** doesn't document where these skills came from. Not functionally critical, but good for maintainability and understanding the adaptation chain.

### GAP 5.2: Missing feature directory structure / "current BDD domains" section

**Severity**: Nice-to-have

**compute-stack** has "Integration with Knowledge System" (lines 104-131) showing:
- Full directory tree of `apps/<app>/features/`
- List of apps with BDD support and their descriptions

**algo-imp** doesn't have an equivalent section showing which domains currently have features/ directories. This context helps agents understand what's already been specified vs. what's new.

### Overall Verdict

**Two minor gaps.** algo-imp README is more comprehensive overall with better workflow examples and agent task assignment.

---

## 6. Additional File: planning-from-tasks (algo-imp Only)

algo-imp has a 5th skill `planning-from-tasks.md` that compute-stack does NOT have. This provides an alternative non-BDD planning path for infrastructure/tooling work.

**Assessment**: Well-designed addition. No gaps (nothing to compare against).

---

## 7. Cross-Cutting Observations

### Consistent Improvements in algo-imp

These patterns appear across all algo-imp skill files but NOT in compute-stack:

| Pattern | Skills | Value |
|---------|--------|-------|
| Pipeline Position diagrams | All 4 skills | Clear context of where each skill fits |
| Team Agent Usage sections | Skills 1, 2, 3, 4 | Structured multi-agent workflow |
| Commands sections | Skills 1, 2, 3, 4 | Quick reference for common operations |
| `/query` knowledge step | Skills 1, 4 | Cognee integration |
| Completion Checklist | Skill 4 | Explicit "done" criteria |

### Properly Omitted compute-stack Content

These compute-stack sections were correctly NOT migrated:

| Section | Reason |
|---------|--------|
| Compose-Specific TDD Pattern (Skill 4) | Infrastructure-specific, not relevant to trading |
| REQUIRED_SERVICES / EXPECTED_PORTS patterns | Docker compose testing, not applicable |
| `docker compose config --quiet` quality gate | No Docker in algo-imp |
| `python3 -m py_compile` syntax check | Replaced by `ruff check .` |
| Per-app monorepo structure | algo-imp is single-project |
| Baseline compose tests (Skill 4) | Docker-specific |

---

## Recommendations

### Priority 1: Should Fix

| # | Gap | Skill | Action |
|---|-----|-------|--------|
| 1 | Missing `Edit` in allowed-tools | creating-features-from-tasks | Add `Edit` to frontmatter `allowed-tools` |
| 2 | No shared step definitions listing | creating-features-from-tasks | Enumerate existing conftest.py steps |
| 3 | Missing "Related Documentation" section | implementing-with-tdd | Add links to bdd-workflow.md, beads-integration.md, etc. |

### Priority 2: Nice-to-Have

| # | Gap | Skill | Action |
|---|-----|-------|--------|
| 4 | No "Directory Naming Rules" | creating-features-from-tasks | Add naming conventions for feature directories |
| 5 | Missing anti-pattern about pytest-bdd execution | creating-features-from-tasks | Add "Creating .feature files that can't be executed by pytest-bdd" |
| 6 | No "Skill Development" provenance | README.md | Document muninn -> compute-stack -> algo-imp chain |
| 7 | No "current BDD domains" listing | README.md | List which feature domains exist |
| 8 | Input location inconsistency | creating-tasks-from-plans | Add `docs/plans/` as alternative input (matches planning-from-tasks output) |
