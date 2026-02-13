# Skills

Skills are reusable workflows for common tasks. They provide structured approaches to development, testing, and maintaining the trading system.

## BDD/TDD Pipeline

These skills form a complete behavior-driven development cycle:

```
beads epic/task
    ↓  /creating-features-from-tasks          (Skill 1: Specify)
.feature file (Gherkin scenarios)
    ↓  /planning-features                     (Skill 2: Plan)
.plan.md (implementation plan)
    ↓  /creating-tasks-from-plans             (Skill 3: Break)
beads tasks (with dependencies)
    ↓  /implementing-with-tdd                 (Skill 4: Build)
test_*.py + production code (red-green-refactor)
```

**Alternative path** (for tasks without BDD):

```
beads epic → /planning-from-tasks → .plan.md → /creating-tasks-from-plans → /implementing-with-tdd
```

## Available Skills

### Skill 1: creating-features-from-tasks

**Purpose**: Create Gherkin `.feature` files from beads tasks/epics

**When to use**:
- Starting the BDD cycle for a new feature
- A beads issue describes behavior but no `.feature` file exists

**Input**: Beads task/epic ID
**Output**: `features/<domain>/<feature-name>.feature` + `test_<feature-name>.py`

**Triggers**: "create feature file", "write scenarios for", "convert this epic to BDD"

### Skill 2: planning-features

**Purpose**: Create scenario-driven implementation plans from `.feature` files

**When to use**:
- A `.feature` file exists and needs an implementation plan
- Starting work on a feature with Gherkin scenarios

**Input**: `.feature` file
**Output**: `features/<domain>/<feature-name>.plan.md`

**Triggers**: "plan this feature", "create implementation plan", "how should we implement"

### Skill 2b: planning-from-tasks

**Purpose**: Create implementation plans directly from beads epics (without BDD)

**When to use**:
- No `.feature` file exists yet
- Planning infrastructure/tooling work (not behavior-driven)

**Input**: Beads epic ID
**Output**: `.plan.md` file

**Triggers**: "plan this epic", "create implementation plan"

### Skill 3: creating-tasks-from-plans

**Purpose**: Generate beads tasks with dependencies from `.plan.md` files

**When to use**:
- A `.plan.md` exists and is approved
- Need trackable tasks with dependencies
- Ready to start implementation

**Input**: `.plan.md` file
**Output**: Beads tasks with dependency tree

**Triggers**: "create tasks from plan", "break down the plan", "generate beads issues"

### Skill 4: implementing-with-tdd

**Purpose**: Implement tasks using strict TDD red-green-refactor

**When to use**:
- Working on any implementation task
- Adding new features or fixing bugs
- Want test-first discipline

**Input**: Beads task ID
**Output**: Tested, working code with all quality gates passing

**Triggers**: "implement this task", "TDD this feature", "write the code for"

### log-backtest

**Purpose**: Log backtest results to Cognee for future querying

**When to use**: After completing a significant backtest analysis

**Triggers**: "log this backtest", "save these results"

## Team Agent Workflow

When working with Claude team agents:

```
1. Team lead runs `bd ready` to find available work
2. Lead assigns tasks to agents based on expertise
3. Agents claim work: `bd update <id> --status in_progress`
4. Agents follow BDD pipeline for their assigned tasks
5. Agents run quality gates before completing
6. Agents close work: `bd close <id> --reason "Completed"`
7. Lead verifies: runs full test suite
8. Lead syncs: `bd sync` at session end
```

### Agent Task Assignment

| Agent Type | Skills | Tasks |
|------------|--------|-------|
| Spec Writer | Skill 1 | Create .feature files from epics |
| Planner | Skill 2/2b | Create .plan.md from features |
| Task Creator | Skill 3 | Break plans into beads tasks |
| Implementer | Skill 4 | TDD implementation of tasks |
| Researcher | -- | Data analysis, strategy research |

## Workflow Examples

### Complete Feature Development (BDD Pipeline)

```bash
# 1. Create epic in beads
bd create --title="Order book data pipeline" --type=feature --priority=1

# 2. Create .feature file (/creating-features-from-tasks)
# Creates: features/data/order-book-pipeline.feature

# 3. Plan the feature (/planning-features)
# Creates: features/data/order-book-pipeline.plan.md

# 4. Create tasks from plan (/creating-tasks-from-plans)
# Creates beads tasks with dependencies

# 5. Implement with TDD (/implementing-with-tdd)
bd ready                           # Find available work
bd update <task-id> --status in_progress
pytest features/data/ -v           # RED: failing scenarios
# ... implement ...
pytest features/data/ -v           # GREEN: scenarios pass
bd close <task-id>                 # Complete task
```

### Quick Bug Fix

```bash
# 1. Create task
bd create --title="Fix reservation price formula" --type=bug --priority=0

# 2. Implement with TDD
bd update <task-id> --status in_progress
pytest tests/unit/avellaneda_stoikov/ -v   # RED
# ... fix bug ...
pytest tests/unit/avellaneda_stoikov/ -v   # GREEN
bd close <task-id>
```

## Related Documentation

- [BDD Workflow](.rules/patterns/bdd-workflow.md) - Full BDD pipeline reference
- [Beads Integration](.rules/patterns/beads-integration.md) - Issue tracking
- [AGENTS.md](../../AGENTS.md) - AI development guide
- [CONSTITUTION.md](../../CONSTITUTION.md) - Core values
