---
description: Constitution framework integration with Cognee semantic search
tags: [cognee, constitution, knowledge-graph, semantic-search, architecture]
created: 2026-01-26
status: implemented
---

# Constitution + Cognee Integration

**Status**: Implemented
**Created**: 2026-01-26

## Overview

Integration of the Constitution framework (CONSTITUTION.md, VISION.md, PLAN.md) with Cognee's semantic search to create constitution-aware knowledge retrieval.

## Architecture Decision

**Decision**: INTEGRATE (not refactor)

The Constitution framework and Cognee serve complementary purposes:
- **Constitution Framework** - Defines WHO WE ARE (values, principles, vision)
- **Cognee** - Enables HOW WE FIND (semantic search, knowledge retrieval)

Integrating them creates a knowledge system that:
1. Retrieves information semantically (Cognee)
2. Filters/contextualizes results through constitutional values (Constitution)
3. Provides answers aligned with core principles

## The Hierarchy

```
CONSTITUTION (who we are)
    ↓
VISION (where we're going)
    ↓
.rules/ (what we know) ← Cognee indexes this
    ↓
PLAN (what we're doing)
```

Cognee indexes the knowledge layer (`.rules/`, `.claude/`) while respecting the constitutional layer above it.

## Integration Components

### 1. Constitution Dataset in Cognee

**Dataset**: `btc-constitution`

Contains:
- `CONSTITUTION.md` - Core values and principles
- `VISION.md` - Long-term vision
- `PLAN.md` - Working memory (updated regularly)

**Purpose**: Make constitutional principles searchable and retrievable.

### 2. Constitution-Aware Query Enhancement

When `/query` is invoked, optionally enhance queries with constitutional context:

```
User query: "How should I organize my notes?"
↓
Enhanced query: "How should I organize my notes? (Context: Our values prioritize clarity over complexity, connection over isolation)"
↓
Cognee search (retrieves from all datasets)
↓
Response filtered/contextualized by constitutional values
```

### 3. Automatic Constitution Sync

Add constitution files to `/land` Step 8b sync logic:

```bash
# Sync constitution files if changed
CONSTITUTION_CHANGED=$(git diff --name-only main...HEAD | grep '^\(CONSTITUTION\|VISION\|PLAN\)\.md$' || echo "")

if [ -n "$CONSTITUTION_CHANGED" ]; then
  # Upload to btc-constitution dataset
  for file in CONSTITUTION.md VISION.md PLAN.md; do
    curl -X POST https://btc-algo-trading-cognee.apps.compute.lan/api/v1/add \
      -F "data=@${file}" \
      -F "datasetName=btc-constitution"
  done
  
  # Cognify
  curl -X POST https://btc-algo-trading-cognee.apps.compute.lan/api/v1/cognify \
    -H "Content-Type: application/json" \
    -d '{"datasets": ["btc-constitution"]}'
fi
```

## Datasets

| Dataset | Content | Purpose |
|---------|---------|---------|
| `btc-constitution` | CONSTITUTION.md, VISION.md, PLAN.md | Core principles, vision, working memory |
| `knowledge-garden` | `.claude/` files | Commands, patterns, quick references |
| `btc-patterns` | `.rules/` files | Architecture, technical patterns |
| `btc-sessions` | Session summaries | Work history, decisions, solutions |

## Query Flow

### Standard Query (No Constitution Context)

```
/query How do I capture patterns?
  ↓
Search datasets: [knowledge-garden, btc-patterns, btc-sessions]
  ↓
Return: Direct answer from .claude/commands/remember.md
```

### Constitution-Aware Query

```
/query --with-values How should I organize notes?
  ↓
1. Retrieve constitutional values from btc-constitution
2. Enhance query with relevant values
3. Search all datasets
4. Filter/prioritize results aligned with values
  ↓
Return: Answer contextualized by "Clarity over complexity, Connection over isolation"
```

## Implementation Strategy

### Phase 1: Constitution Dataset (Completed)
- [x] Create `btc-constitution` dataset
- [x] Add CONSTITUTION.md, VISION.md, PLAN.md to dataset
- [x] Update `/land` Step 8b to auto-sync constitution files

### Phase 2: Enhanced Query Command
- [x] Add optional `--with-values` flag to `/query`
- [x] Implement constitution context injection
- [x] Test with sample queries

### Phase 3: Documentation
- [x] Document integration in `.rules/architecture/`
- [x] Update AGENTS.md with new capabilities
- [x] Update `/query` command documentation

## Use Cases

### 1. Value-Aligned Decision Making

```bash
/query --with-values Should I create separate notes for each small idea?
```

Response incorporates "Capture over forget" and "Clarity over complexity" to recommend simple capture approach.

### 2. Vision-Driven Planning

```bash
/query --with-values What should I focus on next for the knowledge system?
```

Response prioritizes work aligned with VISION.md goals.

### 3. Principle-Based Problem Solving

```bash
/query --with-values How do I handle conflicting organization strategies?
```

Response references CONSTITUTION.md principles to guide decision.

## Benefits

### For Knowledge Retrieval
- **Contextual answers**: Results aligned with personal values
- **Priority filtering**: Favor approaches matching constitutional principles
- **Consistency**: Recommendations follow established values

### For System Evolution
- **Guided growth**: System evolves along constitutional lines
- **Value preservation**: Changes respect core principles
- **Vision alignment**: Features support long-term vision

### For Collaboration
- **Agent alignment**: AI understands user values
- **Consistent guidance**: Recommendations match personal philosophy
- **Context awareness**: Answers consider both knowledge AND values

## Configuration

### Enable Constitution-Aware Queries (Default: Optional)

Constitution context is opt-in via `--with-values` flag:

```bash
# Standard query (no constitution context)
/query How do I use beads?

# Constitution-aware query
/query --with-values How should I organize my knowledge system?
```

### Auto-Enable for Specific Query Types

Could auto-enable constitution context for questions about:
- Organization strategy
- Decision making
- System design
- Workflow choices

Detection keywords: "should I", "how do I decide", "what's the best way"

## Future Enhancements

- [ ] Auto-detect queries that need constitutional context
- [ ] Constitution change alerts (notify when values updated)
- [ ] Value alignment scoring (rate how well results match values)
- [ ] Vision progress tracking (show alignment with VISION.md goals)
- [ ] PLAN.md intelligence (suggest tasks aligned with current focus)

## Related Documentation

- [Cognee Integration](.rules/architecture/cognee-integration.md)
- [/query Command](.claude/commands/query.md)
- [/land Command](.claude/commands/land.md)
- [CONSTITUTION.md](../../CONSTITUTION.md)
- [VISION.md](../../VISION.md)

## Maintenance

### Syncing Constitution to Cognee

Constitution files sync automatically via `/land`:
1. Change CONSTITUTION.md, VISION.md, or PLAN.md
2. Run `/land` at end of session
3. Step 8b detects changes and syncs to Cognee
4. Constitution dataset updated automatically

### Verifying Constitution Dataset

```bash
# Check if constitution dataset exists
curl -X GET https://btc-algo-trading-cognee.apps.compute.lan/api/v1/datasets | grep constitution

# Query constitution directly
/query --with-values What are our core values?
```

## Troubleshooting

**Constitution not in search results:**
- Verify dataset exists: `curl https://btc-algo-trading-cognee.apps.compute.lan/api/v1/datasets`
- Ensure `/land` was run after constitution changes
- Check Cognee logs: `docker logs cognee | tail -50`

**Stale constitution values:**
- Run `/land` to sync latest changes
- Wait for Cognee to process updates (~30 seconds)

**Query timeout:**
- Cognee searches can take 1-3 seconds for large datasets
- This is normal behavior

---

**Integration Complete**: Constitution framework now enhances Cognee knowledge retrieval with value-aligned, vision-driven answers.
