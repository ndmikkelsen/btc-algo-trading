# Missed Files Audit: compute-stack -> algo-imp BDD/TDD Migration

**Date**: 2026-02-09
**Auditor**: Validation Agent
**Scope**: Comprehensive scan of compute-stack for BDD/TDD workflow files potentially missed in migration to algo-imp

## Executive Summary

The BDD/TDD migration from compute-stack to algo-imp is **substantially complete**. All 4 core skills, the BDD workflow pattern, beads integration, git workflow, and /land command have been migrated and properly adapted. A few items need attention.

**Verdict**: 0 MUST-HAVE gaps, 2 NICE-TO-HAVE items, rest NOT-APPLICABLE.

---

## 1. `.claude/` Directory Comparison

### 1a. `.claude/agents/`

| File | compute-stack | algo-imp | Status |
|------|--------------|----------|--------|
| `compute-stack-developer.md` | YES | NO (no agents/ dir) | **NOT-APPLICABLE** |

**Analysis**: compute-stack has `.claude/agents/compute-stack-developer.md` which defines a BDD-aware agent type for team spawning. algo-imp does NOT have an `agents/` directory.

**Priority**: **NICE-TO-HAVE** -- Creating an `algo-imp-developer.md` agent definition would enable better team agent workflows. The agent definition references the 4 skills, BDD pipeline, TDD discipline, and test runner patterns. algo-imp covers all of this in AGENTS.md already, but having a dedicated agent definition would allow `subagent_type` spawning with BDD awareness built in.

**Recommendation**: Consider creating `.claude/agents/algo-trader.md` that references algo-imp's trading domain, skills, and test patterns. Not blocking -- AGENTS.md serves the same purpose for manual reference.

### 1b. `.claude/commands/`

| File | compute-stack | algo-imp | Status |
|------|--------------|----------|--------|
| `land.md` | YES | YES | MIGRATED |
| `query.md` | N/A | YES | algo-imp only |

**Analysis**: `/land` command fully migrated and enhanced. algo-imp version has additional steps:
- Step 1: Beads-to-kanban sync (algo-imp specific)
- Step 4: Markdown formatting (algo-imp addition)
- Step 6.5: Auto PR creation to dev (algo-imp addition)
- Step 8b: Smart knowledge garden sync (algo-imp addition)

**Priority**: **COMPLETE** -- No gaps.

### 1c. `.claude/skills/`

| File | compute-stack | algo-imp | Status |
|------|--------------|----------|--------|
| `README.md` | YES | YES | MIGRATED |
| `creating-features-from-tasks.md` | YES | YES | MIGRATED |
| `planning-features.md` | YES | YES | MIGRATED |
| `creating-tasks-from-plans.md` | YES | YES | MIGRATED |
| `implementing-with-tdd.md` | YES | YES | MIGRATED |
| `planning-from-tasks.md` | NO | YES | algo-imp addition |
| `log-backtest.md` | NO | YES | algo-imp addition |

**Analysis**: All 4 compute-stack skills migrated. algo-imp adds 2 extras:
- `planning-from-tasks.md` (Skill 2b) -- Alternative path for non-BDD planning
- `log-backtest.md` -- Trading-specific skill

Each skill properly adapted:
- Docker/compose references replaced with trading/strategy references
- `apps/<app>/features/` paths replaced with `features/<domain>/`
- Gherkin templates use trading domain language
- Step definition examples use trading fixtures
- Quality gates use `ruff` and `mypy` instead of Docker compose validation

**Priority**: **COMPLETE** -- No gaps. algo-imp actually exceeds compute-stack.

### 1d. `.claude/scripts/` and `.claude/docker/`

| File | compute-stack | algo-imp | Status |
|------|--------------|----------|--------|
| `cognee-local.sh` | N/A | YES | algo-imp only |
| `format_markdown.py` | N/A | YES | algo-imp only |
| `sync-beads-to-todo.js` | N/A | YES | algo-imp only |
| `sync-to-cognee.sh` | N/A | YES | algo-imp only |
| `docker/docker-compose.yml` | N/A | YES | algo-imp only |
| `docker/.env.example` | N/A | YES | algo-imp only |

**Analysis**: compute-stack has no scripts or docker directories in `.claude/`. These are algo-imp additions for Cognee integration. No migration needed.

**Priority**: **NOT-APPLICABLE**

---

## 2. `.rules/` Directory Comparison

### 2a. `.rules/patterns/`

| File | compute-stack | algo-imp | Status |
|------|--------------|----------|--------|
| `bdd-workflow.md` | YES | YES | MIGRATED |
| `beads-integration.md` | YES | YES | MIGRATED |
| `git-workflow.md` | YES | YES | MIGRATED (different content) |
| `knowledge-capture.md` | N/A | YES | algo-imp only |

**Analysis**:

- **bdd-workflow.md**: Fully migrated. compute-stack uses `apps/<app>/features/` structure with Docker compose testing. algo-imp uses `features/<domain>/` with trading-specific patterns. Both reference the same 5-stage pipeline and `scenarios(".")` convention.

- **beads-integration.md**: Fully migrated. Issue prefix changed from `compute-stack` to `algo-imp`. Examples changed from Docker services to trading concepts (reservation price formula, order book pipeline).

- **git-workflow.md**: **Different content but intentional.** compute-stack uses feature->dev->main PR pipeline with no worktrees. algo-imp uses git worktrees with ocnew function, topic branches, and a more elaborate workflow inherited from second-brain. Both serve the same purpose (git discipline) but are adapted to their respective workflows.

- **knowledge-capture.md**: algo-imp only addition. Documents the knowledge garden philosophy. Not in compute-stack.

**Priority**: **COMPLETE** -- No gaps.

### 2b. `.rules/architecture/`

| File | compute-stack | algo-imp | Status |
|------|--------------|----------|--------|
| `stack-overview.md` | YES | NO | **NOT-APPLICABLE** |
| `mount-structure.md` | YES | NO | **NOT-APPLICABLE** |
| `cognee-integration.md` | N/A | YES | algo-imp only |
| `constitution-cognee-integration.md` | N/A | YES | algo-imp only |

**Analysis**: compute-stack architecture docs describe media stack Docker services, NFS mounts, and infrastructure. These are 100% compute-stack specific and have zero relevance to BDD/TDD workflow. algo-imp has its own architecture docs for Cognee integration.

**Priority**: **NOT-APPLICABLE** -- These are domain-specific, not BDD/TDD related.

### 2c. `.rules/index.md`

| File | compute-stack | algo-imp | Status |
|------|--------------|----------|--------|
| `index.md` | YES | YES | MIGRATED |

**Analysis**: Both files serve as indexes to their respective `.rules/` directories. algo-imp version correctly references its own files and uses trading-appropriate Cognee dataset names. Both reference team agent workflow, Cognee integration, and maintenance guidelines.

**Priority**: **COMPLETE**

---

## 3. CONSTITUTION.md Comparison

### compute-stack CONSTITUTION.md
- Focused on reliability, code style, Docker deployment, TUI testing
- Has "Conventional Commits = Clear History" section
- **No BDD/TDD sections** -- BDD workflow is in `.rules/` not constitution

### algo-imp CONSTITUTION.md
- Focused on knowledge capture, clarity, connection
- **HAS BDD/TDD sections** (Sections 6, 7, 8):
  - "BDD-First Feature Development" -- mandates .feature -> .plan.md -> tasks -> TDD
  - "TDD Red-Green-Refactor Protocol" -- RED/GREEN/REFACTOR table with CRITICAL rules
  - "Tool Discipline" -- mandates Beads, Cognee, pytest-bdd, pytest

**Analysis**: algo-imp CONSTITUTION goes further than compute-stack by embedding BDD/TDD as a core constitutional value. compute-stack keeps BDD/TDD in `.rules/` only. This is an **improvement** in algo-imp -- the BDD/TDD discipline is elevated to a constitutional principle.

**Priority**: **COMPLETE** -- algo-imp exceeds compute-stack.

---

## 4. AGENTS.md Comparison

### compute-stack
- Has `agents.md` (lowercase) at root level
- Contains: Structure, NON-NEGOTIABLE GIT RULES, BDD skills reference, team agent workflow, quick commands
- References `.claude/agents/compute-stack-developer.md` for team spawning

### algo-imp
- Has `AGENTS.md` (uppercase) at root level
- Contains: Full BDD/TDD pipeline reference, Red-Green-Refactor protocol, AI Skills table, Agent conventions, Test file locations, Git workflow, Cognee integration, Constitution+Cognee integration
- Does NOT reference `.claude/agents/` (directory doesn't exist)

**Analysis**: algo-imp AGENTS.md is significantly more comprehensive than compute-stack's agents.md. It covers all BDD/TDD workflow content plus Cognee integration, knowledge garden, and constitution-aware queries. The only gap is the lack of a `.claude/agents/` agent definition file.

**Priority**: **COMPLETE** (NICE-TO-HAVE for agent definition file)

---

## 5. Test Configuration Comparison

### compute-stack: `pyproject.toml`
```toml
[tool.pytest.ini_options]
testpaths = ["apps/media-stack", "apps/llm-stack", "apps/pihole"]
addopts = "-v --tb=short --import-mode=importlib"
markers = ["media_automation", "content_discovery", "media_servers", ...]
```

Dependencies: `pytest`, `pytest-asyncio`, `pytest-bdd`, `pyyaml`

### algo-imp: `pytest.ini`
```ini
[pytest]
testpaths = tests features
python_files = test_*.py
addopts = -v --tb=short
markers = unit, integration, bdd
```

Dependencies (from requirements.txt): `pytest==9.0.2`, `pytest-bdd==8.1.0`, `pytest-cov==7.0.0`

**Analysis**:

Both have proper test configuration. Key differences:

1. **`--import-mode=importlib`**: compute-stack uses this to prevent conftest plugin collisions in the monorepo. algo-imp doesn't need it (single project, not monorepo). **NOT-APPLICABLE**.

2. **Test markers**: compute-stack uses domain-specific markers for Docker services. algo-imp uses `unit`, `integration`, `bdd` markers. **Properly adapted**.

3. **pytest-asyncio**: compute-stack has it; algo-imp doesn't. **NICE-TO-HAVE** if/when async exchange connectivity is implemented. Not needed for current BDD workflow.

4. **pyyaml**: compute-stack needs it for Docker compose YAML parsing in tests. algo-imp doesn't need it. **NOT-APPLICABLE**.

**Priority**: **COMPLETE** -- Test configuration properly adapted for algo-imp's structure.

---

## 6. BDD Test Infrastructure

### compute-stack
- `apps/<app>/features/conftest.py` -- Shared steps per app (compose loading, service assertions)
- `apps/<app>/tests/conftest.py` -- Baseline test fixtures (parametrized)
- `apps/<app>/features/<domain>/test_<domain>.py` -- `scenarios(".")`

### algo-imp
- `features/conftest.py` -- Shared fixtures (as_model, sample_prices, etc.) -- EXISTS, VERIFIED
- `tests/__init__.py` -- Test package marker -- EXISTS
- `tests/unit/` -- Unit test directory -- EXISTS
- `features/trading/test_market_making.py` -- BDD test runner -- EXISTS
- `features/trading/market-making.feature` -- Feature spec -- EXISTS

**Analysis**: BDD infrastructure is present and functional:
- Shared conftest.py with trading-appropriate fixtures
- Feature domain directories with correct file structure
- `scenarios(".")` pattern used correctly
- pytest.ini discovers both `tests/` and `features/`

**Priority**: **COMPLETE**

---

## 7. Files Found ONLY in compute-stack (Not in algo-imp)

| File | Relevance to BDD/TDD | Priority |
|------|----------------------|----------|
| `.claude/agents/compute-stack-developer.md` | Agent definition for team BDD work | NICE-TO-HAVE |
| `.rules/architecture/stack-overview.md` | Docker architecture (not BDD) | NOT-APPLICABLE |
| `.rules/architecture/mount-structure.md` | NFS/Docker mounts (not BDD) | NOT-APPLICABLE |
| `CODE_OF_CONDUCT.md` | Repo governance (not BDD) | NOT-APPLICABLE |
| `CONTRIBUTING.md` | Contribution guide (not BDD) | NOT-APPLICABLE |
| `SECURITY.md` | Security policy (not BDD) | NOT-APPLICABLE |
| `LICENSE` | License file (not BDD) | NOT-APPLICABLE |
| `pnpm-lock.yaml` | Node.js deps (not BDD) | NOT-APPLICABLE |
| `pnpm-workspace.yaml` | Monorepo config (not BDD) | NOT-APPLICABLE |
| `package.json` | Node.js config (not BDD) | NOT-APPLICABLE |
| `turbo.json` | Turborepo config (not BDD) | NOT-APPLICABLE |

---

## 8. Files Found ONLY in algo-imp (Additions beyond compute-stack)

| File | Purpose |
|------|---------|
| `.claude/skills/planning-from-tasks.md` | Skill 2b: Non-BDD planning path |
| `.claude/skills/log-backtest.md` | Backtest logging to Cognee |
| `.claude/commands/query.md` | Cognee semantic search command |
| `.claude/scripts/cognee-local.sh` | Cognee Docker management |
| `.claude/scripts/format_markdown.py` | Markdown formatting (used by /land) |
| `.claude/scripts/sync-beads-to-todo.js` | Beads-to-kanban sync |
| `.claude/scripts/sync-to-cognee.sh` | Knowledge garden sync |
| `.claude/docker/` | Cognee Docker compose |
| `.rules/patterns/knowledge-capture.md` | Knowledge philosophy |
| `.rules/architecture/cognee-integration.md` | Cognee architecture |
| `.rules/architecture/constitution-cognee-integration.md` | Constitution+Cognee |
| `features/README.md` | BDD features directory guide |
| `GETTING_STARTED.md` | Setup guide |

---

## 9. Summary Table

| Category | Status | Notes |
|----------|--------|-------|
| Skills (4 core + README) | COMPLETE | All migrated, properly adapted |
| Skills (extras) | EXCEEDS | algo-imp adds planning-from-tasks + log-backtest |
| BDD Workflow pattern | COMPLETE | Adapted for trading domain |
| Beads Integration pattern | COMPLETE | Examples use algo-imp prefix |
| Git Workflow pattern | COMPLETE | Different approach (worktrees) but serves same purpose |
| /land command | COMPLETE | Enhanced with formatting + auto-PR + smart sync |
| CONSTITUTION BDD/TDD | EXCEEDS | Elevated to constitutional principle |
| AGENTS.md | COMPLETE | More comprehensive than compute-stack |
| Agent definition file | NICE-TO-HAVE | No `.claude/agents/` directory |
| Test configuration | COMPLETE | pytest.ini properly configured |
| BDD infrastructure | COMPLETE | conftest.py, features/, scenarios(".") |
| Architecture docs | NOT-APPLICABLE | Domain-specific, not BDD related |
| Compute-stack specific files | NOT-APPLICABLE | Docker, Turbo, pnpm, etc. |

---

## 10. Recommendations

### NICE-TO-HAVE (Priority: Low)

1. **Create `.claude/agents/algo-trader.md`**: Agent definition file for team spawning. Would enable `subagent_type` BDD-aware agents. Model after compute-stack's `compute-stack-developer.md` but with trading domain context, referencing algo-imp's skills, features directory, pytest commands, and quality gates (`ruff check .`, `mypy strategies/`).

2. **Add `pytest-asyncio` to requirements.txt**: Not needed now, but will be needed when implementing Bybit WebSocket order book pipeline (async tests). Can be added when that feature work begins.

### NO ACTION NEEDED

Everything else in compute-stack is either:
- Already migrated and properly adapted
- Domain-specific to compute-stack (Docker, NFS, Turborepo)
- Not related to BDD/TDD workflow

---

**Conclusion**: The BDD/TDD migration is complete. algo-imp has all the workflow files it needs, properly adapted for the trading domain, and in several areas (CONSTITUTION BDD sections, extra skills, /land enhancements) exceeds what compute-stack provides.
