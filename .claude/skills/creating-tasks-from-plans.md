---
name: creating-tasks-from-plans
description: Creates beads tasks from implementation plans (.plan.md). Use when a .plan.md exists and you need trackable tasks, when asked to "create tasks from plan", "break down the plan into tasks", "generate beads issues", or "convert plan to tasks". This is Skill 3 in the BDD pipeline.
allowed-tools: Read, Bash, Glob
---

# Creating Tasks from Plans

Generate beads issues from `.plan.md` implementation plans.

## When to Use

- User says "create tasks from plan" or "break down the plan"
- A `.plan.md` exists and implementation is about to begin
- User asks "generate beads issues" or "convert this plan to tasks"
- Need to track implementation progress with dependencies

## Pipeline Position

```
beads issue -> .feature spec -> .plan.md -> tasks -> TDD implementation
                                            ^^^ YOU ARE HERE
```

## Input Location

`.plan.md` files are colocated with their `.feature` file:

```
features/<domain>/
├── <feature-name>.feature              <- Spec (Skill 1 output)
├── <feature-name>.plan.md              <- INPUT: Read this
└── test_<feature-name>.py
```

Created by the `planning-features` skill from a `.feature` file.

## Workflow

1. **Read the .plan.md** - Parse all phases and tasks
2. **Identify task boundaries** - Each task should be independently completable
3. **Determine dependencies** - Map task order and blockers
4. **Create beads issues** - Use `bd create` with proper metadata
5. **Link dependencies** - Use `bd dep add` to establish relationships
6. **Report created tasks** - Show IDs and dependency tree

## Task Extraction Rules

### From Implementation Plan Phases

Each checkbox item in the Implementation Plan becomes a task:

```markdown
### Phase 1: Order Book Pipeline

1. [ ] Create Bybit WebSocket client -> bd create task
2. [ ] Add L2 order book parser -> bd create task
```

### Task Naming Convention

- Use imperative mood: "Create X", "Add Y", "Implement Z"
- Be specific: "Implement reservation price formula" not "Do math"
- Include context: Reference the feature/strategy name

### Task Description Template

```
Implements: {plan-name} - Phase {N}

## What
{Brief description of what this task accomplishes}

## Acceptance Criteria
Scenarios pass green: {list specific .feature scenario names}

## Technical Notes
{Any relevant specs from .plan.md Technical Specifications}

## Files to Change
{Key files -- use full paths from repo root}

## Dependencies
{Reference parent epic and any blocking tasks}

## Testing
```bash
pytest features/<domain>/ -v
# Scenarios X, Y, Z pass green
```
```

### Priority Mapping

| Phase               | Priority    | Rationale                            |
| ------------------- | ----------- | ------------------------------------ |
| Phase 1             | P1 (high)   | Foundation work, unblocks everything |
| Phase 2             | P1-P2       | Core implementation                  |
| Phase 3+            | P2 (medium) | Dependent on earlier phases          |
| Polish/optimization | P3 (low)    | Nice-to-have improvements            |

### Dependency Rules

- **Tasks within a phase**: Usually independent (can run in parallel)
- **Tasks across phases**: Later phases depend on earlier phases completing
- **Link to parent epic**: If implementing from an epic, add dependency

## Commands

```bash
# Create a task
bd create --title="Task title" --type=task --priority=1 --description="..."

# Add dependency (task-b depends on task-a completing first)
bd dep add <task-b-id> <task-a-id>

# Link task to parent epic
bd dep add <task-id> <epic-id>

# View what was created
bd list --status=open
```

## Output Format

After creating tasks, report them with their dependencies visualized:

```
Created tasks for {plan-name}.plan.md:

{id}: {Task title} (P{priority})
{id}: {Task title} (P{priority})
  └── depends on: {blocker-id}
{id}: {Task title} (P{priority})
  └── depends on: {blocker-id-1}, {blocker-id-2}
```

## Example

Given `features/data/order-book-pipeline.plan.md` with:

```markdown
## Implementation Plan

### Phase 1: WebSocket Infrastructure

1. [ ] Create Bybit WebSocket client
2. [ ] Add L2 order book parser

### Phase 2: Data Processing

1. [ ] Implement mid-price calculation
2. [ ] Add liquidity (kappa) estimation
```

Create tasks:

```bash
# Phase 1 tasks (P1, no dependencies)
bd create --title="Create Bybit WebSocket client" --type=task --priority=1 \
  --description="Implements: order-book-pipeline - Phase 1

## What
WebSocket client for Bybit L2 order book stream with reconnection logic.

## Acceptance Criteria
- Connect to Bybit order book stream scenario passes
- Handle WebSocket disconnection scenario passes

## Files to Change
- strategies/avellaneda_stoikov/bybit_ws.py (create)
- config/ (add WebSocket settings)

## Testing
pytest features/data/ -v"

bd create --title="Add L2 order book parser" --type=task --priority=1 \
  --description="Implements: order-book-pipeline - Phase 1

## What
Parse L2 order book snapshots into bid/ask arrays.

## Acceptance Criteria
- Each snapshot should have bids and asks scenario passes

## Files to Change
- strategies/avellaneda_stoikov/order_book.py (create)

## Testing
pytest features/data/ -v"

# Phase 2 tasks (P1, depend on Phase 1)
bd create --title="Implement mid-price calculation from order book" --type=task --priority=1 \
  --description="Implements: order-book-pipeline - Phase 2

## What
Calculate mid price from best bid/ask in real order book data.

## Acceptance Criteria
- Calculate mid price from order book scenario passes

## Dependencies
- Bybit WebSocket client and L2 parser must be complete

## Testing
pytest features/data/ -v"

# Add dependencies (Phase 2 depends on Phase 1)
bd dep add <mid-price-task-id> <ws-client-task-id>
bd dep add <kappa-task-id> <parser-task-id>
```

Output:

```
Created tasks for order-book-pipeline.plan.md:

algo-imp-abc: Create Bybit WebSocket client (P1)
algo-imp-def: Add L2 order book parser (P1)
algo-imp-ghi: Implement mid-price calculation from order book (P1)
  └── depends on: algo-imp-abc
algo-imp-jkl: Add liquidity (kappa) estimation (P1)
  └── depends on: algo-imp-def
```

## After Task Creation

1. **Verify dependencies**: `bd dep tree <task-id>`
2. **Check ready work**: `bd ready` to see which tasks are unblocked
3. **Claim a task**: `bd update <id> --status in_progress`
4. **Implement**: Use `implementing-with-tdd` skill
5. **Close when done**: `bd close <id> --reason "Completed"`

## Team Agent Usage

When working as a team agent creating tasks:

1. **Create all tasks for a plan** in one pass
2. **Set up dependencies** between phases
3. **Report the task tree** to team lead for assignment
4. Team lead assigns tasks to agents via TaskUpdate

## Anti-Patterns (NEVER DO)

- Creating tasks without reading the full plan
- Skipping dependency links between phases
- Making tasks too large (should be completable in one session)
- Creating tasks without clear acceptance criteria
- Forgetting to link to parent epic
- Using `bd update --deps` instead of `bd dep add`

## Commands Reference

```bash
# View the plan
cat features/<domain>/<feature-name>.plan.md

# Create task with full description
bd create --title="Task title" \
  --type=task \
  --priority=1 \
  --description="$(cat <<EOF
Implements: plan-name - Phase N

## What
Description

## Acceptance Criteria
- Criterion 1
- Criterion 2

## Files to Change
- strategies/file1.py
- features/domain/file2.feature

## Testing
How to verify
EOF
)"

# Add dependency
bd dep add <dependent-task-id> <blocker-task-id>

# View dependency tree
bd dep tree <task-id>

# Check ready work
bd ready
```
