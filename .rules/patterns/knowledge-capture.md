---
description: Knowledge capture and management philosophy for BTC algo trading
tags: [knowledge-management, philosophy, best-practices, trading]
last_updated: 2026-01-31
---

# Knowledge Capture & Management

Core philosophy and best practices for building and maintaining a personal knowledge system.

## The Garden Metaphor

**Why "knowledge garden"?** Because knowledge, like a garden:

- Grows organically from experience
- Needs regular tending to stay healthy
- Becomes more valuable over time
- Blooms when well-maintained
- Withers when neglected

## Core Principles

### 1. Capture While Fresh

Don't wait! Record insights when they're fresh.

- Record insights while they're relevant
- A note that exists is better than a perfect note that doesn't
- Every pattern captured makes future work easier
- Knowledge compounds over time

### 2. Keep It Concise

- Files under 400 lines (split if needed)
- One topic per file
- Show examples, not just prose
- Link to details instead of including everything

### 3. Link Everything

Build a knowledge graph:

- Add "Related" sections
- Reference other patterns
- Connect topics across domains
- Cross-reference projects, ideas, and learnings

### 4. Make It Discoverable

- Use clear file names
- Add descriptions
- Organize logically
- Keep structure shallow

## The Knowledge System

### Our Collaboration Framework

We work together through four interconnected systems:

```
CONSTITUTION.md    ->    VISION.md      ->    .rules/ + .claude/    ->    PLAN.md
Core Principles         The Dream            Long-term Memory          Working Memory
(Who we are)            (Where we're going)  (What we know)            (What we're doing)
```

Together, these form our **contracts for collaboration** - a shared understanding that helps us work as one unified force.

### Structure

```
.claude/              # AI workflows and commands
├── commands/         # /land, /query
└── scripts/          # Automation scripts

.rules/               # Technical documentation
├── architecture/     # System design
└── patterns/         # Reusable solutions
```

## Workflow

### During Work

**When you solve a problem**:
- Document the solution in `.rules/patterns/`
- Link to related patterns
- Knowledge syncs automatically via `/land`

**When you need guidance**:
- Query Cognee: `/query How do I...?`
- Check `.rules/` for technical patterns
- Review session history via Cognee

### After Completing Work

**Run `/land` to complete session**:
- Formats all changed markdown files
- Captures session to Cognee (searchable history)
- Syncs `.claude/` and `.rules/` if changed
- Updates `PLAN.md` with major milestones
- Writes `STICKYNOTE.md` for local handoff

### Regular Maintenance

**Knowledge garden health checks**:
- Files over 400 lines (split if needed)
- Outdated patterns (remove or update)
- Missing cross-links (add related sections)
- New patterns to document

**Note**: Syncing to Cognee happens automatically via `/land` - no manual steps required.

## Best Practices

### Capture Over Forget

- Record insights while they're fresh
- A note exists is better than a perfect note that doesn't
- Every pattern captured makes future work easier
- Knowledge compounds over time

### Clarity Over Complexity

- Write notes that future-you can understand
- Prefer simple organization over elaborate systems
- Name things clearly - files, headings, links
- Document the "why" not just the "what"

### Connection Over Isolation

- Link related notes together
- Build a knowledge graph, not a file dump
- Cross-reference projects, ideas, and learnings
- One insight often illuminates another

### Consistency Over Perfection

- Use established patterns
- Follow existing structure
- Small consistent efforts beat sporadic deep dives
- Regular tending keeps the garden healthy

### Action Over Accumulation

- Knowledge should inform decisions and work
- Review and apply what you capture
- Prune what's no longer useful
- Knowledge unused is knowledge lost

## Why This Matters

### For the Human

- **Memory**: Don't lose solutions when context switches
- **Consistency**: Same patterns applied everywhere
- **Speed**: Find answers quickly instead of rediscovering via Cognee

### For the Agent

- **Context**: Understand project conventions instantly via Cognee
- **Guidance**: Follow established patterns in `.rules/`
- **Continuity**: Pick up where previous sessions left off (STICKYNOTE.md + Cognee)

### For the Knowledge Base

- **Quality**: Consistent patterns = better notes
- **Maintainability**: Documented decisions are easier to revisit
- **Growth**: Nothing gets lost (Cognee searchable history)
- **Discovery**: Semantic search reveals connections

## Tools & Integration

### Cognee (AI Memory)

- Semantic search across `.claude/` and `.rules/`
- Session history from `/land` captures
- Knowledge graph visualization (Neo4j Browser)
- Automatic entity and relationship extraction
- **Auto-syncs**: `/land` syncs knowledge garden when files change

### Beads (Task Tracking)

- Git-native issue tracking
- Dependency management
- Kanban sync to Obsidian

### Commands

- `/land` - Complete session (formats, commits, syncs to Cognee, pushes)
- `/query` - Semantic search across knowledge garden

## The Garden Lifecycle

```
Experience -> Document -> /land -> Synced to Cognee -> Searchable Knowledge
    ^                                                         |
    |                                                         |
    +----------------- Query & Apply <-----------------------+
```

1. **Experience**: Work on projects, solve problems
2. **Document**: Create patterns in `.rules/`, capture insights
3. **Complete**: Run `/land` to format, commit, and sync
4. **Search**: Query Cognee for insights (`/query`)
5. **Apply**: Use knowledge in new work
6. **Repeat**: The cycle continues!

## Remember

> **The best time to plant a tree was 20 years ago. The second best time is now.**

Every pattern captured, every lesson learned, every insight recorded makes the garden more valuable. Start small, tend regularly, and watch it grow!

---

**Remember the hierarchy**:

```
CONSTITUTION (who we are)
    ↓
VISION (where we're going)
    ↓
.rules/ + Cognee (what we know)
    ↓
PLAN (what we're doing)
```

## Related Documentation

- [Cognee Integration](.rules/architecture/cognee-integration.md)
- [Beads Integration](.rules/patterns/beads-integration.md)
- [/land Command](.claude/commands/land.md)
- [/query Command](.claude/commands/query.md)
