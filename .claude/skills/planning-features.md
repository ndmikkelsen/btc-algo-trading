---
name: planning-features
description: Creates implementation plans (.plan.md) driven by .feature file scenarios. Use when a .feature spec exists and you need an implementation plan, when asked to "plan this feature", "create implementation plan from feature", or "how should we implement this spec". This is Skill 2 in the BDD pipeline.
allowed-tools: Read, Write, Bash, Grep, Glob
---

# Planning Features

Create implementation plans driven by `.feature` file scenarios. Plans are DRIVEN BY the spec -- every scenario maps to implementation work, and the Definition of Done is all scenarios passing green.

## When to Use

- A `.feature` file exists and needs an implementation plan
- User says "plan this feature", "create implementation plan", "how should we implement"
- After the `creating-features-from-tasks` skill has produced a `.feature` file
- Starting significant trading strategy or infrastructure work

## Pipeline Position

```
beads issue -> .feature spec -> .plan.md -> tasks -> TDD implementation
                                ^^^ YOU ARE HERE
```

## Key Difference from Generic Planning

Plans are **scenario-driven**:
- Every scenario in the `.feature` file maps to at least one implementation task
- The "Feature Scenarios" section explicitly links scenarios -> phases -> tasks
- Definition of Done = all `.feature` scenarios pass green
- User Stories are extracted from the Feature description (As a / I want / So that)

## Workflow

1. **Read the `.feature` file**: Parse all scenarios and understand the spec
2. **Read the beads issue**: `bd show <task-id>` for additional context
3. **Identify the domain**: Which `features/<domain>/` does this belong to?
4. **Research codebase**: Find similar patterns, existing utilities, conventions
5. **Draft the plan**: Use template below -- scenarios drive the structure
6. **Review with user**: Confirm design decisions before finalizing

## Plan Template

Create the plan as `features/<domain>/<feature-name>.plan.md` (colocated with the feature):

```markdown
# {Feature Title} - Implementation Plan

**Beads Issue**: {task-id}
**Feature Spec**: `features/<domain>/<feature-name>.feature`
**Created**: {DATE}
**Status**: Draft | Approved | In Progress | Complete

## User Stories

> As a {role}
> I want {capability}
> So that {benefit}

(Extracted from the Feature description)

## Feature Scenarios

Maps scenarios to implementation phases and tasks:

| Scenario | Phase | Tasks |
|----------|-------|-------|
| {Scenario name} | Phase {N} | {What to do} |
| {Scenario name} | Phase {N} | {What to do} |

### Definition of Done
All scenarios in `features/<domain>/<feature-name>.feature` pass green:
```bash
pytest features/<domain>/ -v
```

## Design Decisions

### Decision 1: {Title}

**Context**: {Why this decision is needed}

**Options Considered**:
1. {Option A}: {pros/cons}
2. {Option B}: {pros/cons}

**Decision**: {What we chose}

**Rationale**: {Why we chose it}

## Implementation Plan

### Phase 1: {Foundation}

1. [ ] {Task -- linked to scenario(s)}
   - **Scenarios**: {Which .feature scenarios this satisfies}
   - **Files**: {Key files to create/modify}

### Phase 2: {Core Implementation}

1. [ ] {Task -- linked to scenario(s)}

### Phase 3: {Integration/Verification}

1. [ ] {Task -- verify all scenarios pass}

## Technical Specifications

### Trading Parameters
- {Model parameters, formulas, constants}
- {Exchange-specific settings}

### Data Requirements
- {Data sources, formats, timeframes}
- {Order book depth, tick data, OHLCV}

### Configuration
- {Environment variables}
- {Config files}

## Testing Strategy

### BDD Scenarios (Primary)
- Feature file: `features/<domain>/<feature-name>.feature`
- Run: `pytest features/<domain>/ -v`

### Unit Tests (If Applicable)
- Update `tests/unit/` with component tests
- Run: `pytest tests/ -v`

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| {Risk} | {Impact} | {Mitigation} |
```

## Output Location

Plans are colocated with their feature:

```
features/<domain>/
├── <feature-name>.feature       <- Spec (Skill 1 output)
├── <feature-name>.plan.md       <- Plan (THIS skill output)
└── test_<feature-name>.py       <- Test runner
```

## After Planning

Once the `.plan.md` is approved:

1. **Create beads tasks**: Use `creating-tasks-from-plans` skill
2. **Begin implementation**: Use `implementing-with-tdd` skill
3. **Verify**: All `.feature` scenarios pass green

## Team Agent Usage

When working as a team agent creating plans:

1. **Read the .feature file** assigned to you
2. **Create the Feature Scenarios mapping table** -- every scenario must map to a phase
3. **Draft the plan** with all sections
4. **Report to team lead** for review before task creation
5. Team lead approves plan before proceeding to task breakdown

## Anti-Patterns (NEVER DO)

- Creating a plan without reading the `.feature` file first
- Plans that don't reference specific scenarios
- Definition of Done that doesn't include "all scenarios pass green"
- Skipping the Feature Scenarios mapping table
- Planning work not covered by any scenario

## Commands

```bash
# View the beads epic
bd show <epic-id>

# Query domain knowledge
/query What regime detection approaches work for crypto market making?

# Find similar implementations
ls strategies/
grep -r "def calculate" strategies/

# Verify feature parses
pytest features/<domain>/ --collect-only
```
