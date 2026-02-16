---
description: Git branching strategy and PR pipeline for btc-algo-trading
tags: [git, workflow, branching]
last_updated: 2026-02-09
---

# Git Workflow

## NON-NEGOTIABLE RULES

1. **NEVER commit directly to `main`**
2. **NEVER push directly to `main`**
3. **ALWAYS work on feature/topic branches**
4. **ALWAYS use PR pipeline**: `feature → dev → main`

## Mandatory Workflow

```
Local: feature-branch (commit, test)
    ↓
Remote: origin/feature-branch (push)
    ↓
PR: feature-branch → dev (review, merge)
    ↓
PR: dev → main (review, merge)
```

## Branch Strategy

### Protected Branches

- **`main`** - Production-ready strategies, stable releases
- **`dev`** - Integration branch, tested features

**Protection**: No direct commits or pushes allowed.

### Feature Branches

- **Naming**: `feat/description`, `fix/description`, `docs/description`
- **Lifecycle**: Create → Work → Push → PR → Merge → Delete
- **Scope**: One feature/fix per branch

## Step-by-Step Workflow

### 1. Create Feature Branch

```bash
# From dev branch
git checkout dev
git pull origin dev

# Create feature branch
git checkout -b feat/order-book-pipeline
```

### 2. Work on Feature

```bash
# Follow BDD/TDD pipeline
# Make changes, test locally
pytest features/ -v
pytest tests/ -v

# Commit with conventional commits
git add <files>
git commit -m "feat(data): add Bybit WebSocket order book client"
```

### 3. Push to Remote

```bash
git push -u origin feat/order-book-pipeline
```

### 4. Create PR to dev

```bash
gh pr create --base dev --title "feat: Add order book pipeline" --body "..."
```

### 5. Merge to dev

```bash
# After review and approval
gh pr merge <pr-number> --squash
```

### 6. Create PR to main (periodic)

```bash
gh pr create --base main --title "release: Order book pipeline + formula fixes" --body "..."
```

### 7. Clean Up

```bash
git branch -D feat/order-book-pipeline
git push origin --delete feat/order-book-pipeline
```

## Conventional Commits

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Purpose | Example |
|------|---------|---------|
| `feat` | New feature | `feat(data): add Bybit order book stream` |
| `fix` | Bug fix | `fix(model): correct reservation price formula` |
| `docs` | Documentation | `docs(rules): add BDD workflow reference` |
| `refactor` | Code restructuring | `refactor(model): extract spread calculation` |
| `test` | Test changes | `test(trading): add fill model BDD scenarios` |
| `chore` | Maintenance | `chore(deps): update dependencies` |
| `perf` | Performance | `perf(simulator): optimize tick processing` |

### Scopes

| Scope | Component |
|-------|-----------|
| `model` | A-S model (reservation price, spread, quotes) |
| `data` | Order book pipeline, exchange data, validation |
| `risk` | Risk management, position sizing, stop-loss |
| `sim` | Backtesting, simulator, fill model |
| `live` | Live/paper trading, Bybit client |
| `config` | Configuration, parameters |
| `beads` | Issue tracking |
| `rules` | Documentation patterns |

### Examples

```bash
# Strategy fix
git commit -m "fix(model): use S - adj instead of S*(1-adj) for reservation price"

# New feature
git commit -m "feat(data): add L2 order book parser with kappa estimation"

# BDD feature
git commit -m "test(trading): add order book pipeline BDD scenarios"

# Documentation
git commit -m "docs(rules): add BDD workflow pattern reference"

# Maintenance
git commit -m "chore(beads): close completed A-S overhaul tasks"
```

## Merge Conflicts

### Prevention

- Pull `dev` frequently
- Keep feature branches short-lived
- Communicate with team about overlapping work

### Resolution

```bash
git checkout feat/your-feature
git fetch origin
git merge origin/dev

# Resolve conflicts, test
pytest
git add <resolved-files>
git commit -m "chore: resolve merge conflicts with dev"
git push origin feat/your-feature
```

## Emergency Fixes

If you accidentally commit to `main` or `dev`:

1. **STOP** - Do not push
2. **Check current branch**: `git branch --show-current`
3. **If on protected branch**:
   ```bash
   git reset --soft HEAD~1
   git checkout -b fix/accidental-commit
   git commit
   git push origin fix/accidental-commit
   gh pr create --base dev ...
   ```

## AI Agent Boundaries

### What AI Can Do

- Commit to current feature branch
- Push to remote feature branch
- Create PRs to dev (via `/land` command)
- Delete feature branches after merge

### What AI Cannot Do

- Create branches (user manages branches)
- Commit directly to `main` or `dev`
- Push directly to `main` or `dev`
- Force push to any branch
- Bypass PR pipeline

## Git Commands Reference

### Branch Management

```bash
git branch -a                          # List branches
git checkout -b feat/new-feature       # Create branch
git checkout dev                       # Switch branch
git branch -D feat/old-feature         # Delete local branch
git push origin --delete feat/old      # Delete remote branch
```

### Commit Management

```bash
git add <files>                        # Stage changes
git commit -m "feat(scope): desc"      # Commit
git log --oneline --graph              # View history
```

### Remote Management

```bash
git push -u origin feat/your-feature   # Push with tracking
git pull origin dev                    # Pull from remote
git fetch --all --prune                # Fetch all branches
```

## Related Documentation

- [Beads Integration](beads-integration.md)
- [BDD Workflow](bdd-workflow.md)
