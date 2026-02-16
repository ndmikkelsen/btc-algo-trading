---
name: planning-from-tasks
description: Creates implementation plans (.plan.md) from beads epics or feature tasks. Use when starting a new feature, when asked to plan an epic, or when a beads issue needs detailed planning. Triggers on phrases like "plan this epic", "create implementation plan", "how should we implement". Alternative path for tasks without BDD.
allowed-tools: Read, Write, Grep, Glob, Bash
---

# Planning from Tasks

Create implementation plans directly from beads epics or feature tasks, bypassing the `.feature` file step. Use this for infrastructure, tooling, or research work that doesn't fit BDD.

## When to Use

- User says "plan this epic" or "create implementation plan"
- A beads epic/feature exists that needs detailed breakdown
- Planning infrastructure/tooling work (not behavior-driven)
- User asks "how should we implement [feature]?"
- **No `.feature` file exists** -- if one does, use `/planning-features` instead

## Pipeline Position (Alternative Path)

```
beads epic -> .plan.md -> tasks -> TDD implementation
              ^^^ YOU ARE HERE (skipping .feature)
```

## Workflow

1. **Read the beads issue** - `bd show <epic-id>` to understand scope
2. **Query knowledge** - `/query` for relevant patterns, prior art, architecture
3. **Check for .feature file** - If one exists, redirect to `/planning-features`
4. **Analyze requirements** - Identify technical needs, dependencies, constraints
5. **Research codebase** - Find similar patterns, existing utilities, conventions
6. **Draft the plan** - Use template below
7. **Review with user** - Confirm design decisions before finalizing

## Output Location

Place `.plan.md` files near related code:

```
features/<domain>/
├── <feature-name>.plan.md       <- If domain-specific

docs/plans/
├── <feature-name>.plan.md       <- General/cross-cutting plans

strategies/
├── <strategy-name>.plan.md      <- Strategy implementation plans
```

## Plan Template

```markdown
# {Feature Name} Implementation Plan

**Epic**: {beads-id}
**Created**: {date}
**Status**: Draft | In Review | Approved

## Overview

{1-2 paragraph summary of what this feature does and why it matters}

## Goals

### Primary
- {Main objective}

### Secondary
- {Supporting objectives}

## User Stories

- As a {role}, I want {capability} so that {benefit}

## Design Decisions

### {Decision 1 Title}

**Context**: {Why this decision is needed}

**Options Considered**:
1. {Option A} - {pros/cons}
2. {Option B} - {pros/cons}

**Decision**: {What we chose}

**Rationale**: {Why we chose it}

## Technical Specifications

### Data Requirements
- {Data sources needed}
- {Format/schema}

### Dependencies
- {External libraries}
- {Internal modules}

### Configuration
- {Config parameters}

## Implementation Plan

### Phase 1: {Foundation}

1. [ ] {Task 1}
2. [ ] {Task 2}

### Phase 2: {Core Implementation}

1. [ ] {Task 3}
2. [ ] {Task 4}

### Phase 3: {Integration & Testing}

1. [ ] {Task 5}
2. [ ] {Task 6}

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| {Risk 1} | Low/Med/High | Low/Med/High | {Strategy} |

## Definition of Done

- [ ] All tests pass
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] Backtest results validated (if applicable)

## Open Questions

- {Question 1}
- {Question 2}
```

## After Planning

1. **Review with user** - Confirm the plan captures requirements
2. **Create tasks** - Run `creating-tasks-from-plans` skill
3. **Start implementation** - Use `implementing-with-tdd` skill

## Team Agent Usage

When working as a team agent:

1. **Read the beads epic** assigned to you
2. **Draft the plan** with all sections
3. **Report to team lead** for review
4. Team lead approves plan before task creation

## Anti-Patterns (NEVER DO)

- Using this when a `.feature` file exists (use `/planning-features` instead)
- Creating a plan without reading the beads issue
- Plans without clear Definition of Done
- Skipping the Design Decisions section
- Tasks that are too large to complete in one session

## Commands

```bash
# View the beads epic
bd show <epic-id>

# List related issues
bd list

# Find similar implementations
ls strategies/
grep -r "def calculate" strategies/
```
