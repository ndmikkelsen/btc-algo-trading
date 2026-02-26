---
triggers: ['/query', 'search knowledge', 'ask cognee']
description: Query the knowledge garden using Cognee semantic search
---

# /query — Semantic Search

Query your knowledge garden using Cognee's semantic search capabilities.

**Last Updated**: 2026-02-26

## Usage

```
/query <your question>
/query --with-values <your question>  # Constitution-aware query
```

## Examples

```
# Standard queries
/query How do I capture new patterns?
/query What's the git workflow?
/query How does beads integration work?
/query What commands are available?

# Constitution-aware queries (value-aligned answers)
/query --with-values How should I organize my notes?
/query --with-values What should I focus on next?
/query --with-values Should I create separate files or combine them?
```

## How It Works

### Standard Query

1. **Submits query to Cognee** - Uses semantic search across:
    - `.claude/` - Commands, patterns, quick-references
    - `.rules/` - Architecture and technical patterns
    - Session history (if captured via `/land`)

2. **Receives contextualized answer** - Cognee returns:
    - Direct answer to your question
    - Relevant snippets from documentation
    - Related documents and patterns

3. **Displays results** - Shows:
    - The answer
    - Source documents referenced
    - Confidence scores

### Constitution-Aware Query (`--with-values`)

1. **Retrieves constitutional context** - Fetches from:
    - `CONSTITUTION.md` - Core values and principles
    - `VISION.md` - Long-term direction and goals

2. **Enhances query with values** - Adds relevant context:
    - Example: "How should I organize notes?" becomes
    - "How should I organize notes? (Consider: Clarity over complexity, Connection over isolation)"

3. **Searches with context** - Cognee searches all datasets with constitutional framing

4. **Returns value-aligned answer** - Results filtered/prioritized by constitutional principles

## Requirements

Cognee runs on the compute server — no local Docker needed:

```bash
# Check Cognee is reachable
curl http://btc-cognee.apps.compute.lan/health

# Knowledge garden syncs automatically via /land
```

## Implementation

When user invokes `/query <question>`:

1. **Check Cognee availability**:
   ```bash
   curl -s http://btc-cognee.apps.compute.lan/health
   ```

   If not available, report that the compute server may be down.

2. **Submit search query**:
   ```bash
   curl -X POST http://btc-cognee.apps.compute.lan/api/v1/search \
     -H "Content-Type: application/json" \
     -d "{\"query\": \"<question>\"}"
   ```

3. **Parse and display results**:
    - Show the answer
    - List source documents
    - Include relevant snippets
    - Suggest related queries

4. **Optionally refine**:
    - If answer is unclear, ask follow-up questions
    - If results seem stale, remind user to run `/land` to sync latest changes

## Datasets Searched

By default, searches across all datasets:

- `btc-knowledge-garden` - .claude/ files (commands, patterns, templates)
- `btc-patterns` - .rules/ files (architecture, technical patterns)
- `btc-sessions` - Session history from `/land`
- `btc-constitution` - CONSTITUTION.md, VISION.md, PLAN.md (used with `--with-values`)

To search specific dataset:

```bash
curl -X POST http://btc-cognee.apps.compute.lan/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "your question",
    "dataset_name": "btc-knowledge-garden"
  }'
```

## When to Use

**Use `/query` when:**
- Looking for how to do something
- Can't remember where documentation is
- Want to find related patterns
- Exploring the knowledge base

**Use `/query --with-values` when:**
- Making organizational decisions
- Choosing between approaches
- Seeking value-aligned guidance
- Questions starting with "should I" or "how do I decide"

**Don't use `/query` when:**
- You know exactly which file to read (just read it)
- Cognee isn't reachable (check compute server)
- Knowledge hasn't been synced yet (run `/land` to sync)

## Syncing Knowledge

**Automatic sync** via `/land`:
- Session summaries captured automatically
- Knowledge garden (`.claude/` and `.rules/`) syncs when changed
- Knowledge graph updated with each session

**No manual sync required** - `/land` handles all syncing automatically.

## Troubleshooting

**Cognee not responding:**
```bash
# Check reachability
curl http://btc-cognee.apps.compute.lan/health

# API docs
open http://btc-cognee.apps.compute.lan/docs
```

**Stale results:**
- Run `/land` to ensure latest changes are synced
- Wait a few moments for Cognee to process updates

**No results found:**
- Check if knowledge has been synced
- Try rephrasing your question
- Search specific dataset
- Verify Cognee is processing correctly

## Related Commands

- `/remember` - Capture new patterns to knowledge garden
- `/learn` - Extract lessons from work
- `/cultivate` - Maintain and organize knowledge garden
- `/land` - Save session and sync to Cognee

## Related Documentation

- [Cognee Integration](.rules/architecture/cognee-integration.md)
- [Knowledge Garden](../GARDENING.md)
