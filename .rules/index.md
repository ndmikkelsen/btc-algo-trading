# Second Brain Rules & Patterns

> Technical documentation, architecture patterns, and development guidelines

## Purpose

This directory contains technical documentation for AI agents and developers working on the second-brain knowledge system. These rules are referenced by `.claude/` workflows and indexed by Cognee for semantic search.

## Structure

### Architecture (`architecture/`)

System design, component relationships, and integration patterns:

- `knowledge-system.md` - Overall knowledge garden architecture
- `obsidian-integration.md` - Obsidian vault structure and conventions
- `cognee-integration.md` - AI memory layer integration
- `constitution-cognee-integration.md` - Constitution framework + Cognee integration

### Patterns (`patterns/`)

Reusable solutions and workflows:

- `beads-integration.md` - Issue tracking with Beads
- `git-workflow.md` - Git branching and commit conventions
- `knowledge-capture.md` - How to capture and organize knowledge

## Usage

### For AI Agents

Read relevant rules before implementing features:

```bash
# Before working on knowledge capture
Read .rules/patterns/knowledge-capture.md

# Before creating issues
Read .rules/patterns/beads-integration.md

# Before working with Obsidian
Read .rules/architecture/obsidian-integration.md
```

### For Cognee

These docs are indexed in Cognee datasets:

- `second-brain-constitution` - CONSTITUTION.md, VISION.md, PLAN.md
- `second-brain-patterns` - .rules/ pattern docs
- `knowledge-garden` - .claude/ workflow docs
- `second-brain-sessions` - Session history

Query Cognee for context:

```bash
# Standard query
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "How should I capture new patterns?"}'

# Constitution-aware query (via /query --with-values)
/query --with-values How should I organize my knowledge system?
```

## Maintenance

- Keep docs under 400 lines (split if needed)
- Use semantic Markdown (H1/H2/H3 hierarchy)
- Include metadata frontmatter
- Update when architecture changes
- Remove obsolete patterns

## Related Documentation

- [CONSTITUTION.md](../CONSTITUTION.md) - Core values and principles
- [VISION.md](../VISION.md) - Long-term vision
- [AGENTS.md](../AGENTS.md) - Quick reference for AI agents
- [.claude/INDEX.md](../.claude/INDEX.md) - Knowledge garden index

---

**Last Updated**: 2026-01-26
