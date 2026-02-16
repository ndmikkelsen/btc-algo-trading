# Knowledge Base Constitution

> Our guiding principles for building and maintaining a personal knowledge system together

**This document defines WHO WE ARE.** For where we're going, see [VISION.md](./VISION.md).

## Core Values

### 1. Capture Over Forget

- Record insights while they're fresh
- A note exists is better than a perfect note that doesn't
- Every pattern captured makes future work easier
- Knowledge compounds over time

### 2. Clarity Over Complexity

- Write notes that future-you can understand
- Prefer simple organization over elaborate systems
- Name things clearly - files, headings, links
- Document the "why" not just the "what"

### 3. Connection Over Isolation

- Link related notes together
- Build a knowledge graph, not a file dump
- Cross-reference projects, ideas, and learnings
- One insight often illuminates another

### 4. Consistency Over Perfection

- Use templates for common note types
- Follow established patterns
- Small consistent efforts beat sporadic deep dives
- Regular tending keeps the garden healthy

### 5. Action Over Accumulation

- Notes should inform decisions and work
- Review and apply what you capture
- Prune what's no longer useful
- Knowledge unused is knowledge lost

### 6. BDD-First Feature Development

All new features MUST follow the BDD workflow:

1. **Start with .feature** - Write Gherkin scenarios BEFORE any code
2. **Create .plan.md** - Document design decisions, implementation plan, and done criteria
3. **Generate tasks** - Create beads issues from the plan with dependencies
4. **Red-Green-Refactor** - Follow strict TDD for each scenario

### 7. TDD Red-Green-Refactor Protocol

| Phase | Action | Verification |
|-------|--------|-------------|
| RED | Write a failing test | `pytest` fails for the right reason |
| GREEN | Write minimal code to pass | `pytest` passes |
| REFACTOR | Improve code quality | `pytest` still passes |

**CRITICAL**:
- NEVER skip RED phase
- NEVER write production code without a failing test first
- NEVER refactor while tests are failing

### 8. Tool Discipline

- **Beads** for ALL task tracking - No markdown TODOs, no ad-hoc tracking
- **Cognee** for knowledge queries - Query before planning, capture learnings after
- **pytest-bdd** for feature tests - Gherkin scenarios drive acceptance criteria
- **pytest** for unit tests - Red-green-refactor, no exceptions

## Structure Principles

### Organization

- `personal/` - Personal projects and notes
- `work/` - Work-related documentation
- `templates/` - Consistent starting points
- `.claude/` - Knowledge garden for Claude collaboration

### Note Hygiene

- One topic per note (split if needed)
- Keep notes under 400 lines
- Use clear, descriptive filenames
- Add frontmatter for metadata

### Linking Strategy

- Use wiki-links: `[[path/to/note]]`
- Create hub notes for major topics
- Link freely - connections reveal value
- Use kanbans for project tracking

## Collaboration Principles

### Human + Agent Partnership

- **We're a team**: Building knowledge together
- **Ask when uncertain**: Clarify before assuming
- **Capture together**: Agent helps identify patterns
- **Learn together**: Update garden as we discover

### Communication Style

- **Be direct**: Get to the point
- **Use examples**: Show, don't just tell
- **Stay organized**: Use structure to aid understanding

## The Hierarchy

```
CONSTITUTION (who we are)
    |
VISION (where we're going)
    |
GARDEN (what we know)
    |
PLAN (what we're doing)
```

**This document anchors everything.** Our vision grows from our values. Our knowledge reflects our principles. Our plans execute our vision.

---

**Last Updated**: 2025-12-27

> "Knowledge is only potential power. It becomes power only when organized and applied."
