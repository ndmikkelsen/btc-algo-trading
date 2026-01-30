---
description: Git branching strategy, worktrees, and PR pipeline for second-brain knowledge base
tags: [git, workflow, branching, worktrees, knowledge-base]
last_updated: 2026-01-28
---

# Git Workflow

## 🚨 NON-NEGOTIABLE RULES

1. **NEVER commit directly to `main`**
2. **NEVER push directly to `main`**
3. **ALWAYS work on topic branches**
4. **ALWAYS use PR pipeline**: `topic-branch → dev → main`
5. **USE git worktrees for parallel work**

## Why Git Worktrees?

Git worktrees allow you to work on multiple branches simultaneously without stashing or switching:

- **Main worktree**: `second-brain/` - Your primary workspace (on `dev` branch)
- **Topic worktrees**: Separate directories for each topic branch
- **Benefits**:
  - No context switching between branches
  - Keep Obsidian open in main vault while working
  - Multiple content areas in progress without conflicts
  - Easy to compare branches side-by-side

## Mandatory Workflow

```
Main worktree: second-brain/ (on dev branch)
    ↓
Create topic branch from dev (manually via ocnew)
    ↓
Create worktree for topic branch (ocnew function)
    ↓
Work in worktree → commit changes
    ↓
/land: Push + Create PR to dev
    ↓
Review & merge PR: topic-branch → dev
    ↓
Clean up: Remove worktree (manual)
    ↓
(Periodic) User-driven merge: dev → main
```

## Branch Strategy

### Protected Branches

- **`main`** - Stable, polished knowledge (production)
  - Receives merges from `dev` after major milestones
  - User decides when to merge dev → main
  - Protected: No direct commits or pushes

- **`dev`** - Integration branch (primary workspace)
  - All topic branches merge here first
  - Main worktree stays on this branch
  - Protected: No direct commits, only via PR

### Branch Types

Knowledge base branches represent **content areas** or **workflow improvements**, not software features.

#### 1. Knowledge/Content Work: `<topic>/<date>`

**Purpose:** Capturing, organizing, and refining knowledge

**Naming Pattern:** `<topic>/<YYYY-MM-DD>`

**Examples:**
- `home-lab/2026-01-28` - Homelab documentation session
- `personal/2026-01-28` - Personal notes and planning
- `cognee/2026-01-26` - Cognee research and setup notes
- `work/2026-01-27` - Work-related knowledge capture

**When to use:**
- Adding notes from a work session
- Documenting homelab hardware/configuration
- Personal journaling or planning
- Organizing existing notes
- Capturing meeting notes or research

**Lifecycle:**
1. Create from dev: `ocnew home-lab/2026-01-28` (creates branch + worktree)
2. Work in worktree, commit changes
3. Run `/land` to push + create PR to dev
4. Review & merge PR
5. Clean up worktree (manual)

#### 2. Workflow/Infrastructure: `feat/<description>`

**Purpose:** Improving the knowledge system itself

**Naming Pattern:** `feat/<description>`, `fix/<description>`, `docs/<description>`, `chore/<description>`

**Examples:**
- `feat/cognee-integration` - Integrating Cognee AI memory
- `feat/beads-workflow` - Setting up Beads issue tracking
- `fix/sync-script-error` - Fixing broken sync script
- `docs/git-workflow-update` - Updating workflow documentation

**When to use:**
- Implementing new tools (Cognee, Beads)
- Creating/updating scripts
- Workflow improvements
- Documentation structure changes
- Git workflow updates

**Lifecycle:**
1. Create from dev: `ocnew feat/cognee-integration` (creates branch + worktree)
2. Work in worktree, commit and test changes
3. Run `/land` to push + create PR to dev
4. Review & merge PR
5. Clean up worktree (manual)

#### Deciding Branch Type

**Content/notes?** → `<topic>/<date>`  
**System/workflow improvement?** → `feat/`, `fix/`, `docs/`, `chore/`

## Git Worktree Workflow

### 1. List Existing Worktrees

```bash
# See all worktrees
git worktree list

# Example output:
# /path/to/second-brain                     991eb21 [main]
# /path/to/feat-cognee.worktree.20260125    d04b50a [feat/cognee-integration]
```

### 2. Create Topic Worktree

```bash
# From main repository (on dev branch)
cd ~/path/to/second-brain
git checkout dev && git pull

# Use ocnew function to create branch + worktree
# This is a custom zsh function that automates worktree creation
ocnew home-lab/2026-01-28

# ocnew automatically:
# - Creates branch from current branch (dev)
# - Creates matching worktree with correct naming
# - Changes directory to new worktree
```

**Naming Convention**:

Worktree name MUST match branch name (replace `/` with `.`):

```
Branch: home-lab/2026-01-28
Worktree: second-brain.worktree.home-lab.2026-01-28

Branch: feat/cognee-integration
Worktree: second-brain.worktree.feat-cognee-integration
```

**Pattern:** `second-brain.worktree.<topic>.<description>`

**Note:** The `ocnew` zsh function handles this naming automatically.

### 3. Work in Topic Worktree

```bash
# Navigate to worktree (if not already there from ocnew)
cd ../second-brain.worktree.home-lab.2026-01-28

# Verify you're on the right branch
git branch --show-current
# Should show: home-lab/2026-01-28

# Make changes, commit with conventional commits
git add <files>
git commit -m "docs(home-lab): document NAS cable requirements"
```

### 4. Push Topic Branch (Automated by /land)

```bash
# The /land command handles pushing automatically
/land

# Manual push (if needed):
git push -u origin home-lab/2026-01-28
```

### 5. Create Pull Request (Automated by /land)

The `/land` command automatically creates PRs to `dev`:

```bash
# /land handles:
# - Pushing changes
# - Creating PR to dev (not main)
# - Including Beads references
# - Syncing to Cognee

# Manual PR creation (if needed):
gh pr create --base dev --title "docs(home-lab): 2026-01-28 session" --body "..."
```

**Important:** All PRs target `dev`, not `main`.

### 6. After Merge

```bash
# Navigate to main worktree
cd ~/path/to/second-brain

# Pull latest changes into dev
git checkout dev
git pull origin dev

# Remove topic worktree (manual cleanup)
git worktree remove ../second-brain.worktree.home-lab.2026-01-28

# Optional: Delete local branch
git branch -D home-lab/2026-01-28

# Optional: Delete remote branch (if not auto-deleted by GitHub)
git push origin --delete home-lab/2026-01-28

# Prune worktree references
git worktree prune
```

## Common Worktree Operations

### List All Worktrees

```bash
git worktree list

# With paths and branches
git worktree list --porcelain
```

### Remove Worktree

```bash
# Remove worktree (must not have uncommitted changes)
git worktree remove path/to/worktree

# Force remove (even with uncommitted changes)
git worktree remove --force path/to/worktree
```

### Move Worktree

```bash
# Move worktree to new location
git worktree move old/path new/path
```

### Lock/Unlock Worktree

```bash
# Lock worktree (prevents removal)
git worktree lock path/to/worktree

# Unlock worktree
git worktree unlock path/to/worktree
```

### Prune Stale Worktrees

```bash
# Remove worktree references for deleted directories
git worktree prune

# Dry run to see what would be pruned
git worktree prune --dry-run
```

## Worktree Best Practices

### Naming Convention

> ⚠️ **IMPORTANT:** Worktree name MUST match branch name (replace `/` with `.`)

```bash
# Knowledge work
Branch: home-lab/2026-01-28
Worktree: second-brain.worktree.home-lab.2026-01-28

Branch: personal/2026-01-28
Worktree: second-brain.worktree.personal.2026-01-28

# Workflow work
Branch: feat/cognee-integration
Worktree: second-brain.worktree.feat-cognee-integration

Branch: fix/sync-script
Worktree: second-brain.worktree.fix-sync-script
```

**Note:** The `ocnew` function handles this naming automatically.

### Location

Keep worktrees at the same level as main repository:

```
~/Documents/
├── second-brain/                                           # Main worktree (dev branch)
├── second-brain.worktree.home-lab.2026-01-28/              # Knowledge worktree
└── second-brain.worktree.feat-cognee-integration/          # Workflow worktree
```

### Cleanup Regularly

Remove worktrees after merging:

```bash
# After PR is merged
git worktree remove path/to/worktree
git branch -D branch-name
git worktree prune
```

### Obsidian Considerations

When using worktrees with Obsidian:

- **Main vault**: Keep open in `second-brain/` (main branch)
- **Feature worktrees**: Open in separate Obsidian windows if needed
- **Plugins**: May need to reinstall in worktrees
- **.obsidian/**: Gitignored, so safe to work in multiple worktrees

## Conventional Commits for Knowledge Base

Knowledge base commits are primarily documentation-focused, with occasional workflow improvements.

### Types for Knowledge Work

| Type | Purpose | Usage Frequency | Example |
|------|---------|-----------------|---------|
| `docs` | Documentation/notes | ⭐ **Most common** (80%) | Adding homelab notes, personal planning |
| `feat` | New feature/workflow | Occasional (10%) | Implementing Cognee, new scripts |
| `fix` | Bug fix | Occasional (5%) | Fixing broken scripts, correcting information |
| `refactor` | Reorganization | Occasional (3%) | Restructuring notes, moving files |
| `chore` | Maintenance | Occasional (2%) | Beads cleanup, routine updates |
| `style` | Formatting | Rare (<1%) | Markdown formatting only |

### Scopes for Knowledge Work

| Scope | Content Area | Examples |
|-------|--------------|----------|
| `home-lab` | Homelab hardware, builds, network | NAS, servers, networking |
| `personal` | Personal notes, planning | Goals, journaling, life admin |
| `work` | Work-related notes | Projects, meetings, research |
| `cognee` | Cognee integration | Setup, queries, datasets |
| `beads` | Beads issue tracking | Issue creation, workflow |
| `scripts` | Automation scripts | Sync scripts, helpers |
| `workflow` | Git workflow, processes | Workflow docs, conventions |

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Examples: Knowledge Work

```bash
# Most common - adding notes
git commit -m "docs(home-lab): document NAS cable requirements"

# Personal planning
git commit -m "docs(personal): update 2026 Q1 goals"

# Work notes
git commit -m "docs(work): capture project kickoff meeting notes"

# Organizing content
git commit -m "refactor(home-lab): consolidate network documentation"
```

### Examples: Workflow Work

```bash
# Implementing new tool
git commit -m "feat(cognee): add docker-compose for local instance"

# Fixing script
git commit -m "fix(scripts): correct beads sync path in land command"

# Updating workflow
git commit -m "docs(workflow): update git branching strategy"

# Routine cleanup
git commit -m "chore(beads): close completed cognee integration issues"
```

### Multi-Paragraph Commits (for significant sessions)

```bash
git commit -m "docs(home-lab): NAS build session 2026-01-28

Documented:
- HGST drive cable requirements (SFF-8087 to SATA)
- LSI HBA PCIe slot placement (slot 3 recommended)
- Power distribution unit wiring diagram
- 10GbE SFP+ connection topology

References: SB-xxx (cable sourcing), SB-yyy (PCIe planning)
Branch: home-lab/2026-01-28"
```

### Commit Message Guidelines

**Good:**
- Descriptive: "docs(home-lab): document NAS cable requirements"
- Specific: "fix(scripts): correct beads sync script path"
- Actionable: "feat(cognee): add semantic search command"

**Avoid:**
- Vague: "docs: update files"
- Generic: "chore: misc changes"
- Missing scope: "docs: add notes"

## Merge Conflicts

### Prevention

- Pull `dev` frequently in main worktree
- Keep topic branches short-lived
- Sync worktrees with dev regularly

### Resolution in Worktree

```bash
# From topic worktree
cd path/to/worktree

# Update with latest dev
git fetch origin
git merge origin/dev

# Resolve conflicts
# Edit conflicted files
git add <resolved-files>
git commit -m "chore: resolve merge conflicts with dev"

# Push updated branch
git push origin home-lab/2026-01-28
```

## Emergency Fixes

If you accidentally commit to `main` or `dev`:

1. **STOP** - Do not push
2. **Check current branch**: `git branch --show-current`
3. **If on protected branch (main or dev)**:
   ```bash
   # Soft reset to previous commit
   git reset --soft HEAD~1

   # Create topic branch
   git checkout -b fix/accidental-commit

   # Commit again
   git commit

   # Follow normal PR workflow
   git push origin fix/accidental-commit
   gh pr create --base dev ...
   ```

## AI Agent Boundaries

### What AI Can Do

- ✅ Commit to current topic branch (in worktree)
- ✅ Push to remote topic branch
- ✅ Create PRs to dev (via `/land` command)
- ✅ Document workflow and provide examples

### What AI Cannot Do

- ❌ Create worktrees (user manages via `ocnew` function)
- ❌ Remove worktrees (user cleans up manually)
- ❌ Create or delete branches (user manages)
- ❌ Commit directly to `main` or `dev`
- ❌ Push directly to `main` or `dev`
- ❌ Merge dev to main (user decides timing)
- ❌ Force push to any branch
- ❌ Bypass PR pipeline

## Workflow Examples

### Example 1: Knowledge Work Session

```bash
# 1. In main worktree, ensure on dev
cd ~/Documents/second-brain
git checkout dev && git pull

# 2. Create branch + worktree using ocnew
ocnew home-lab/2026-01-28
# ocnew automatically creates branch and worktree, changes to worktree directory

# 3. Work in worktree
# ... add homelab notes ...
git add .
git commit -m "docs(home-lab): document NAS cable requirements"

# 4. End session with /land
/land
# /land handles: push, create PR to dev, sync to Cognee, write STICKYNOTE

# 5. After PR merges to dev, clean up
cd ~/Documents/second-brain
git checkout dev && git pull
git worktree remove ../second-brain.worktree.home-lab.2026-01-28
git worktree prune
```

### Example 2: Workflow Improvement

```bash
# 1. In main worktree, ensure on dev
cd ~/Documents/second-brain
git checkout dev && git pull

# 2. Create workflow branch + worktree
ocnew feat/cognee-query-cache

# 3. Work in worktree
# ... implement caching feature ...
git add .
git commit -m "feat(cognee): add Redis query caching"

# 4. End session with /land
/land
# PR created to dev automatically

# 5. After merge, clean up
cd ~/Documents/second-brain
git checkout dev && git pull
git worktree remove ../second-brain.worktree.feat-cognee-query-cache
git worktree prune
```

### Example 3: Multiple Parallel Work Areas

```bash
# Work on homelab notes in worktree 1
cd ~/Documents/second-brain.worktree.home-lab.2026-01-28

# Work on personal planning in worktree 2
cd ~/Documents/second-brain.worktree.personal.2026-01-28

# Main vault still open in Obsidian at ~/Documents/second-brain (on dev)
# No need to switch branches or stash changes!
```

### Example 4: Updating Topic Branch with Latest dev

```bash
# From topic worktree
cd ~/Documents/second-brain.worktree.home-lab.2026-01-28

# Update with latest dev
git fetch origin
git merge origin/dev

# Resolve any conflicts, test, commit
git add .
git commit -m "chore: merge latest dev"
git push origin home-lab/2026-01-28
```

## Related Documentation

- [Beads Integration](.rules/patterns/beads-integration.md)
- [Cognee Integration](.rules/architecture/cognee-integration.md)
- [/land Command](.claude/commands/land.md)

## Resources

- [Git Worktree Documentation](https://git-scm.com/docs/git-worktree)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub CLI](https://cli.github.com/)
