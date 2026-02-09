---
name: creating-tasks-from-plans
description: Creates beads tasks from implementation plans (.plan.md). Use when a .plan.md exists and you need trackable tasks, when asked to "create tasks from plan", "break down the plan into tasks", "generate beads issues", or "convert plan to tasks".
allowed-tools: Read, Bash, Glob
---

# Creating Tasks from Plans

Generate beads issues from `.plan.md` implementation plans.

## When to Use

- User says "create tasks from plan" or "break down the plan"
- A `.plan.md` exists and implementation is about to begin
- User asks "generate beads issues" or "convert this plan to tasks"
- Need to track implementation progress with dependencies

## Input Location

`.plan.md` files can live in various locations:

```
docs/plans/
├── {feature-name}.plan.md    ← Implementation plans

strategies/
├── {strategy-name}.plan.md   ← Strategy implementation plans

backtests/
├── {analysis-name}.plan.md   ← Analysis plans
```

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
### Phase 1: Setup

1. [ ] Install Freqtrade dependencies → bd create task
2. [ ] Configure exchange API → bd create task
```

### Task Naming Convention

- Use imperative mood: "Create X", "Add Y", "Implement Z"
- Be specific: "Implement EMA crossover entry logic" not "Do entries"
- Include context: Reference the strategy or feature name

### Task Description Template

```
Implements: {feature-name} - Phase {N}

## What
{Brief description of what this task accomplishes}

## Acceptance Criteria
{From .plan.md Definition of Done, filtered to this task}

## Technical Notes
{Any relevant specs from .plan.md Technical Specifications}

## Dependencies
{Reference parent feature/epic and any blocking tasks}
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
- **Link to parent epic**: If implementing a feature from an epic, add dependency

## Commands

```bash
# Create a task
bd create --title="Task title" --type=task --priority=1 --description="..."

# Add dependency (task-b depends on task-a completing first)
bd dep add <task-b-id> <task-a-id>

# Link task to parent epic/feature
bd dep add <task-id> <epic-id>

# View what was created
bd list --status=open
```

## Output Format

After creating tasks, report them with their dependencies visualized:

```
Created tasks for {feature-name}.plan.md:

{id}: {Task title} (P{priority})
{id}: {Task title} (P{priority})
  └── depends on: {blocker-id}
{id}: {Task title} (P{priority})
  └── depends on: {blocker-id-1}, {blocker-id-2}
```

## Example

Given `docs/plans/momentum-strategy.plan.md` with:

```markdown
## Implementation Plan

### Phase 1: Data Infrastructure

1. [ ] Set up historical data download pipeline
2. [ ] Validate OHLCV data integrity

### Phase 2: Strategy Implementation

1. [ ] Implement EMA crossover signals
2. [ ] Add RSI confirmation filter
```

Create tasks:

```bash
bd create --title="Set up historical data download pipeline" --type=task --priority=1 \
  --description="Implements: momentum-strategy - Phase 1..."

bd create --title="Validate OHLCV data integrity" --type=task --priority=1 \
  --description="Implements: momentum-strategy - Phase 1..."

# Phase 2 tasks depend on Phase 1
bd create --title="Implement EMA crossover signals" --type=task --priority=1 \
  --description="Implements: momentum-strategy - Phase 2..."

bd dep add <ema-task-id> <data-pipeline-task-id>
```

Output:

```
Created tasks for momentum-strategy.plan.md:

btc-algo-abc: Set up historical data download pipeline (P1)
btc-algo-def: Validate OHLCV data integrity (P1)
btc-algo-ghi: Implement EMA crossover signals (P1)
  └── depends on: btc-algo-abc
btc-algo-jkl: Add RSI confirmation filter (P1)
  └── depends on: btc-algo-abc, btc-algo-ghi
```

## Integration with BDD Workflow

When creating tasks from a `.plan.md` that was generated from a `.feature` file:

1. Reference the `.feature` file in task descriptions
2. Each task's acceptance criteria should map to specific Gherkin scenarios
3. Implementation tasks should follow `/implementing-with-tdd` (red-green-refactor)

```
.feature → .plan.md → bd tasks (THIS SKILL) → /implementing-with-tdd
```

## After Task Creation

1. Run `bd ready` to see which tasks are unblocked
2. Claim a task: `bd update <id> --status in_progress`
3. Implement using TDD (red-green-refactor): `/implementing-with-tdd`
4. Close when done: `bd close <id>`
