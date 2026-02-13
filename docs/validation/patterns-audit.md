# Patterns Documentation Audit

> Comparing compute-stack (source) against algo-imp (target) for gaps, leaks, and incomplete adaptations.
>
> **Date**: 2026-02-09

---

## Summary

| Category | Issues Found |
|----------|-------------|
| Missing sections | 3 |
| Incomplete adaptations | 4 |
| Leaked compute-stack references | 2 |
| Missing cross-references | 3 |
| Missing files from compute-stack | 2 (architecture docs, not applicable) |

**Overall assessment**: The adaptation is solid. Most domain-specific content has been properly translated from infrastructure/Docker to trading/algorithmic domains. The issues below are minor-to-moderate.

---

## 1. BDD Workflow (`bdd-workflow.md`)

### 1.1 Sections Present in Both

| Section | compute-stack | algo-imp | Status |
|---------|:---:|:---:|--------|
| Pipeline table | Y | Y | Identical (good) |
| Repository Structure | Y | Y | Properly adapted |
| Gherkin mapping table | Y | Y | Properly adapted to trading domain |
| Step Definition Architecture | Y | Y | Properly adapted |
| Worked Example | Y | Y | Properly adapted (Radarr -> Order Book Pipeline) |
| tests/ vs features/ table | Y | Y | Properly adapted |
| Commands section | Y | Y | Properly adapted |
| Feature Domain Guide | N | Y | **algo-imp adds this** (good addition) |
| Related Documentation | Y | Y | Present in both |

### 1.2 Gaps Found

**NONE** - This file is well-adapted. algo-imp actually adds a useful "Feature Domain Guide" section that compute-stack lacks.

### 1.3 Minor Observations

- compute-stack has `## Monorepo Structure` heading; algo-imp correctly uses `## Repository Structure` -- good adaptation.
- compute-stack references `apps/<app>/features/conftest.py`; algo-imp correctly uses `features/conftest.py` -- good adaptation.
- algo-imp adds a `--cov` example in Commands section -- useful addition for a code-heavy project.
- algo-imp cross-references link to `.rules/patterns/` using full relative paths from repo root, but the file itself is inside `.rules/patterns/`. The links `[Beads Integration](.rules/patterns/beads-integration.md)` would resolve correctly only from repo root, not from the file's location.

### 1.4 Cross-Reference Issue

**algo-imp line 210-212**: The "Related Documentation" links use paths relative to repo root:
```markdown
- [Beads Integration](.rules/patterns/beads-integration.md)
- [Git Workflow](.rules/patterns/git-workflow.md)
- [Skills README](.claude/skills/README.md)
```

These should be relative to the file's location inside `.rules/patterns/`:
```markdown
- [Beads Integration](beads-integration.md)
- [Git Workflow](git-workflow.md)
- [Skills README](../../.claude/skills/README.md)
```

**Severity**: Low (doesn't affect functionality, only markdown link resolution in some renderers)

---

## 2. Beads Integration (`beads-integration.md`)

### 2.1 Sections Present in Both

| Section | compute-stack | algo-imp | Status |
|---------|:---:|:---:|--------|
| Core Rules | Y | Y | Identical |
| Quick Reference | Y | Y | Adapted (`bd create` syntax differs slightly) |
| Workflow | Y | Y | Identical |
| Issue Types | Y | Y | **Properly adapted** examples |
| Priorities | Y | Y | **Properly adapted** P0 example |
| Managing Dependencies | Y | Y | Properly adapted (compute-stack -> algo-imp prefixes) |
| Auto-Sync | Y | Y | Properly adapted |
| Integration with Cognee | Y | Y | **Partially adapted** (see below) |
| Integration with Team Agents | Y | Y | Identical |
| Common Patterns | Y | Y | **Properly adapted** to trading domain |
| Important Rules | Y | Y | Identical |
| Related Documentation | Y | Y | Present in both |

### 2.2 Gaps Found

#### Gap 1: Cognee Integration Section is Simplified

**compute-stack** (lines 129-160) has a full `curl` example showing how to POST to Cognee API and cognify:
```bash
cat > cognee-plex-sync-issue.txt << 'EOF'
Issue: compute-stack-plex-sync
...
EOF
curl -X POST http://localhost:8000/api/v1/add ...
curl -X POST http://localhost:8000/api/v1/cognify ...
```

**algo-imp** (lines 129-140) replaces this with just:
```bash
# 2. Sync to Cognee
.claude/scripts/sync-to-cognee.sh
```

**Assessment**: This is actually a *good* simplification IF `sync-to-cognee.sh` exists. However, this script does not appear to exist in the repo (no file found at `.claude/scripts/sync-to-cognee.sh`). This is a **dangling reference** to a non-existent script.

**Severity**: Medium -- references a script that doesn't exist.

**Recommendation**: Either create the script or replace with actual Cognee integration steps, or use the `/query` command pattern that exists in algo-imp.

### 2.3 Leaked Compute-Stack References

**NONE found** - All `compute-stack-*` issue ID prefixes have been properly replaced with `algo-imp-*`. Examples have been well-adapted to trading domain (e.g., "Riven queue stalls" -> "Fill model assumes 100% fill at price touch").

### 2.4 Minor: `bd create` Syntax Inconsistency

- **compute-stack Quick Reference** (line 24): `bd create "Title" -t task -p 1` (short flags, positional title)
- **algo-imp Quick Reference** (line 24): `bd create --title="Title" --type=task --priority=1` (long flags)
- **algo-imp examples throughout**: Use `--title=`, `--type=`, `--priority=` consistently

The algo-imp version is more explicit, which is good. But the Quick Reference and the body examples should use the same syntax. compute-stack uses short flags in Quick Reference and long flags in examples -- algo-imp is more consistent.

**Severity**: Cosmetic -- no functional impact.

### 2.5 Cross-Reference Issue

Same pattern as bdd-workflow.md -- "Related Documentation" links use repo-root-relative paths instead of file-relative paths.

---

## 3. Rules Index (`index.md`)

### 3.1 Sections Present in Both

| Section | compute-stack | algo-imp | Status |
|---------|:---:|:---:|--------|
| Purpose | Y | Y | Properly adapted |
| Architecture section | Y | Y | Different contents (correctly) |
| Patterns section | Y | Y | Properly adapted |
| For AI Agents | Y | Y | Adapted to trading context |
| For Team Agents | Y | Y | **Partially adapted** (see below) |
| For Cognee | Y | Y | Adapted to trading datasets |
| Maintenance | Y | Y | Identical |

### 3.2 Gaps Found

#### Gap 1: Team Agents Section - Leaked Reference Pattern

**compute-stack** (line 57): References `.claude/agents/compute-stack-developer.md`
**algo-imp** (line 53): References `AGENTS.md`

This is properly adapted -- good.

#### Gap 2: Architecture Docs Differ Appropriately

**compute-stack** has:
- `stack-overview.md` - Media stack architecture
- `mount-structure.md` - Volume mount/NFS patterns

**algo-imp** has:
- `cognee-integration.md` - AI memory layer
- `constitution-cognee-integration.md` - Constitution framework + Cognee

These are correctly different -- the architecture docs should be project-specific.

#### Gap 3: algo-imp Adds Extra Pattern

algo-imp has `knowledge-capture.md` in patterns, which compute-stack does not. This is a good addition specific to the algo-imp project's knowledge management philosophy.

### 3.3 Leaked Compute-Stack References

**NONE** - All references properly adapted.

### 3.4 Cognee Section Differs Appropriately

- **compute-stack**: Uses `curl` API calls, datasets named `compute-stack-architecture`, `compute-stack-patterns`
- **algo-imp**: Uses `/query` command, datasets named `btc-patterns`, `btc-sessions`

Good adaptation.

---

## 4. Files in compute-stack `.rules/` Not Present in algo-imp

### 4.1 Architecture Files

| File | In compute-stack | In algo-imp | Assessment |
|------|:---:|:---:|-----------|
| `architecture/stack-overview.md` | Y | N | **Not applicable** - Docker/media-specific |
| `architecture/mount-structure.md` | Y | N | **Not applicable** - NFS/FUSE-specific |
| `architecture/cognee-integration.md` | N | Y | **algo-imp only** - good |
| `architecture/constitution-cognee-integration.md` | N | Y | **algo-imp only** - good |

**Assessment**: The missing architecture files are infrastructure-specific (media stack, NFS mounts) and have no equivalent in a trading project. No gap here.

### 4.2 Pattern Files

| File | In compute-stack | In algo-imp | Assessment |
|------|:---:|:---:|-----------|
| `patterns/bdd-workflow.md` | Y | Y | Both present |
| `patterns/beads-integration.md` | Y | Y | Both present |
| `patterns/git-workflow.md` | Y | Y | Both present (see section 5) |
| `patterns/knowledge-capture.md` | N | Y | **algo-imp only** - good addition |

**Assessment**: All relevant patterns are present. algo-imp adds `knowledge-capture.md` which is appropriate.

---

## 5. Git Workflow (`git-workflow.md`)

### 5.1 Major Structural Difference

These files are **very different** in scope and content:

- **compute-stack**: 275 lines, standard feature branch workflow with `dev` and `main` protection, PR pipeline, conventional commits with infrastructure scopes (`tui`, `api`, `docker`, `monitoring`)
- **algo-imp**: 598 lines, extensive git worktrees workflow with `ocnew` function, Obsidian integration, knowledge-base-focused scopes (`home-lab`, `personal`, `work`, `cognee`)

### 5.2 Leaked Content

**algo-imp git-workflow.md contains content that appears to be from a *third* repo (second-brain/knowledge base), NOT from compute-stack:**

- Line 3: "Git branching strategy, worktrees, and PR pipeline for **second-brain knowledge base**"
- Line 19: "Main worktree: `second-brain/`"
- Line 27: "Keep Obsidian open in main vault while working"
- Lines 88-117: Knowledge-focused branch naming (`home-lab/2026-01-28`, `personal/2026-01-28`)
- Lines 154-164: `second-brain.worktree.*` naming convention
- Lines 329-336: Obsidian Considerations section
- Lines 339-405: Commit types for "Knowledge Work" (80% `docs`, scopes like `home-lab`, `personal`, `work`)
- Lines 503-586: Examples reference `~/Documents/second-brain`

**Severity**: HIGH -- This is not adapted from compute-stack at all. It appears to be a wholesale copy from a knowledge-base/second-brain repository. The git workflow for an algorithmic trading project should have:
- Trading-relevant scopes (`strategy`, `backtest`, `data`, `risk`)
- No references to Obsidian, second-brain, or knowledge work
- No `ocnew` function (unless it exists for algo-imp)
- Trading-relevant branch examples (`feat/order-book-pipeline`, `fix/reservation-price-formula`)

**Recommendation**: Rewrite this file for the algo-imp trading context. Use compute-stack's simpler structure as a base, but with trading-specific scopes and examples.

---

## 6. Features README Comparison

### 6.1 compute-stack (`apps/media-stack/features/README.md`)

- 151 lines
- Infrastructure-focused (Docker compose validation)
- Lists shared step definitions for compose services
- Includes `.plan.md` template with Feature Scenarios mapping
- Has "Gherkin Conventions for Infrastructure" with code examples

### 6.2 algo-imp (`features/README.md`)

- 114 lines
- Trading-focused (market making, backtesting, risk, data)
- Lists shared steps for model fixtures and price data
- Includes "Writing Good Scenarios" section (Do/Don't guidance)
- Has Feature Domains table

### 6.3 Gaps

#### Gap 1: Missing `.plan.md` Template

**compute-stack** (lines 121-138) includes a `.plan.md` template showing how to map scenarios to implementation phases:
```markdown
## Feature Scenarios
Maps scenarios to implementation phases:
| Scenario | Phase | Tasks |
...
### Definition of Done
All `.feature` scenarios pass green.
```

**algo-imp** does NOT include this template.

**Severity**: Medium -- This template is useful for the planning skill and should be included.

**Recommendation**: Add a `.plan.md` template section to algo-imp's `features/README.md` adapted for trading (e.g., mapping A-S model scenarios to phases).

#### Gap 2: Missing Gherkin Convention Examples

**compute-stack** (lines 57-99) provides Gherkin code examples for common patterns:
- Service existence
- Port configuration
- Volume configuration
- Environment variables

**algo-imp** has a "Writing Good Scenarios" section with Do/Don't lists but NO Gherkin code examples for trading patterns.

**Severity**: Medium -- Trading-specific Gherkin examples would help agents write consistent scenarios.

**Recommendation**: Add Gherkin code examples for common trading patterns, e.g.:
- Spread calculation scenario
- Inventory management scenario
- Fill model validation scenario

#### Gap 3: algo-imp Has Better "Writing Good Scenarios" Section

algo-imp adds Do/Don't guidance that compute-stack lacks. This is a good addition.

---

## 7. Conftest Patterns

### 7.1 compute-stack conftest (`features/conftest.py`)

- 260 lines of shared step definitions
- Infrastructure-focused: compose loading, service validation, port checks, volume propagation
- Sophisticated pattern matching for Docker port mappings, env var substitution, rshared propagation

### 7.2 algo-imp conftest

- Exists at `features/conftest.py` (not read in detail for this audit)
- Should contain trading-focused fixtures: model instances, price data, market state
- Referenced in README as having `as_model`, `as_model_custom`, `sample_prices` fixtures

**Assessment**: These are correctly different. No adaptation needed -- the conftest files should be completely domain-specific.

---

## 8. Action Items

### High Priority

| # | Issue | File | Action |
|---|-------|------|--------|
| 1 | **Git workflow is from wrong repo** | `.rules/patterns/git-workflow.md` | Rewrite for trading context; remove all second-brain/Obsidian/knowledge-base references |

### Medium Priority

| # | Issue | File | Action |
|---|-------|------|--------|
| 2 | Dangling `sync-to-cognee.sh` reference | `.rules/patterns/beads-integration.md` | Create script or replace with actual Cognee steps |
| 3 | Missing `.plan.md` template | `features/README.md` | Add template section adapted for trading |
| 4 | Missing Gherkin convention examples | `features/README.md` | Add trading-specific Gherkin examples |

### Low Priority

| # | Issue | File | Action |
|---|-------|------|--------|
| 5 | Cross-reference paths use repo root | `bdd-workflow.md`, `beads-integration.md` | Change to file-relative paths |
| 6 | Minor syntax inconsistency in `bd create` | `beads-integration.md` | Cosmetic, no action needed |

---

## 9. What Was Done Well

- **Domain translation**: Infrastructure concepts (Docker services, ports, volumes) properly mapped to trading concepts (strategies, market data, risk management) across bdd-workflow.md and beads-integration.md
- **Issue type examples**: Properly adapted (e.g., "Riven queue stalls" -> "Reservation price formula uses wrong scaling")
- **Beads ID prefixes**: All `compute-stack-*` properly replaced with `algo-imp-*`
- **Feature domains**: Well-organized for trading (Trading, Backtesting, Risk, Data, Infrastructure)
- **Additional content**: algo-imp adds Feature Domain Guide table and knowledge-capture.md pattern
- **Metadata frontmatter**: Properly added to all algo-imp files
- **Writing Good Scenarios**: Do/Don't section in features/README.md is a useful addition
