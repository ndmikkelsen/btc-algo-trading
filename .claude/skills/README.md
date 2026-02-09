# Skills

Skills are reusable workflows for common tasks. They provide structured approaches to development, formatting, and maintaining the knowledge system.

## Available Skills

### Development Workflow

These skills form a complete BDD/TDD development cycle:

```
beads epic/task
    ↓  /creating-features-from-tasks
.feature file (Gherkin scenarios)
    ↓  /planning-features
.plan.md (implementation plan)
    ↓  /creating-tasks-from-plans
beads tasks (with dependencies)
    ↓  /implementing-with-tdd
test_*.py + production code (red-green-refactor)
```

**Alternative path** (for tasks without BDD):

```
beads epic → /planning-from-tasks → .plan.md → /creating-tasks-from-plans → /implementing-with-tdd
```

#### 1. creating-features-from-tasks

**Purpose**: Create Gherkin `.feature` files from beads tasks/epics

**When to use**:

- Starting the BDD cycle for a new feature
- A beads issue describes behavior but no `.feature` file exists
- Want to define acceptance criteria as scenarios

**Input**: Beads task/epic ID
**Output**: `features/<domain>/<feature-name>.feature`

**Triggers**: "create feature file", "write scenarios for", "convert this epic to BDD"

#### 2. planning-features

**Purpose**: Create implementation plans from `.feature` files

**When to use**:

- A `.feature` file exists and needs an implementation plan
- Starting work on a feature with Gherkin scenarios
- Need to document design decisions before coding

**Input**: `.feature` file
**Output**: `{feature-name}.plan.md` alongside the `.feature` file

**Triggers**: "plan this feature", "create implementation plan", "how should we implement"

#### 2b. planning-from-tasks

**Purpose**: Create implementation plans directly from beads epics (without BDD)

**When to use**:

- No `.feature` file exists yet
- Planning infrastructure/tooling work (not behavior-driven)

**Input**: Beads epic ID
**Output**: `{feature}.plan.md` file

**Triggers**: "plan this epic", "create implementation plan"

#### 3. creating-tasks-from-plans

**Purpose**: Generate beads tasks from `.plan.md` files

**When to use**:

- A `.plan.md` exists and is approved
- Need trackable tasks with dependencies
- Ready to start implementation

**Input**: `.plan.md` file
**Output**: Beads tasks with dependencies

**Triggers**: "create tasks from plan", "break down the plan", "generate beads issues"

#### 4. implementing-with-tdd

**Purpose**: Implement tasks using strict TDD red-green-refactor

**When to use**:

- Working on any implementation task
- Adding new features or fixing bugs
- Want test-first discipline

**Input**: Beads task ID
**Output**: Tested, working code

**Triggers**: "implement this task", "TDD this feature", "write the code for"

---

### Knowledge Management

#### 4. formatting-notes

**Purpose**: Format markdown notes with consistent structure, fix links, and validate URLs

**When to use**:

- Cleaning up documentation
- Validating links in knowledge garden
- Before committing markdown changes

**Input**: Files or directories to format
**Output**: Formatted markdown with validated links

**Triggers**: "format notes", "fix markdown", "validate links"

---

## Workflow Examples

### Complete Feature Development (BDD Pipeline)

```bash
# 1. Create epic in beads
bd create --title="New Strategy Feature" --type=feature --priority=1

# 2. Create .feature file (/creating-features-from-tasks skill)
bd show <epic-id>
# Creates: features/trading/new-strategy.feature

# 3. Plan the feature (/planning-features skill)
# Creates: features/trading/new-strategy.plan.md

# 4. Create tasks from plan (/creating-tasks-from-plans skill)
# Creates beads tasks with dependencies

# 5. Implement with TDD (/implementing-with-tdd skill)
bd ready                           # Find available work
bd update <task-id> --status in_progress
pytest                             # RED: write failing test
# ... write code ...
pytest                             # GREEN: test passes
bd close <task-id>                 # Complete task
```

### Quick Bug Fix

```bash
# 1. Create task
bd create --title="Fix RSI calculation" --type=bug --priority=1

# 2. Implement with TDD
bd update <task-id> --status in_progress
pytest tests/test_indicators.py   # RED
# ... fix bug ...
pytest tests/test_indicators.py   # GREEN
bd close <task-id>
```

### Manual Formatting (if needed)

```bash
# Format specific files
python3 .claude/scripts/format_markdown.py --yes file.md

# Preview changes
python3 .claude/scripts/format_markdown.py --dry-run .rules/
git commit -m "docs: format markdown files"
```

## Skill Development

Skills are tailored for btc-algo-trading's development focus:

- **btc-algo-trading**: Trading strategy documentation, backtest analysis, Freqtrade workflows
- **knowledge-garden**: Markdown formatting, link validation, pattern documentation

Different repositories have different skills based on their primary use case.

## Related Documentation

- [AGENTS.md](../../AGENTS.md) - Complete AI development guide
- [CONSTITUTION.md](../../CONSTITUTION.md) - Core values
- [/land Command](.claude/commands/land.md) - Session completion
