# BTC Algo Trading Rules & Patterns

> Technical documentation, architecture patterns, and development guidelines for the btc-algo-trading project.

## Purpose

This directory contains technical documentation for AI agents and developers working on Bitcoin algorithmic trading strategies. These rules are referenced by `.claude/` workflows and indexed by Cognee for semantic search.

## Structure

### Reference (`reference/`)

Strategy and tooling catalogs for research and implementation:

- `strategies-catalog.md` - Comprehensive strategy catalog with BTC applicability ratings
- `libraries-reference.md` - Python libraries organized by function (backtesting, data, ML, etc.)

### Architecture (`architecture/`)

System design, component relationships, and integration patterns:

- `cognee-integration.md` - AI memory layer integration
- `constitution-cognee-integration.md` - Constitution framework + Cognee integration

### Patterns (`patterns/`)

Reusable solutions and workflows:

- `bdd-workflow.md` - BDD pipeline and Gherkin conventions
- `beads-integration.md` - Issue tracking with Beads
- `git-workflow.md` - Git branching and commit conventions
- `knowledge-capture.md` - How to capture and organize knowledge
- `mrbb-parameter-research.md` - Literature findings for BB mean reversion parameters
- `mrbb-validation-results.md` - **NO-GO** validation results (Feb 2026) — strategy shelved

## Usage

### For AI Agents

Read relevant rules before implementing features:

```bash
# Before creating features (BDD pipeline)
Read .rules/patterns/bdd-workflow.md

# Before creating issues
Read .rules/patterns/beads-integration.md

# Before committing/pushing
Read .rules/patterns/git-workflow.md

# Before working with knowledge system
Read .rules/architecture/cognee-integration.md
```

### For Team Agents

When working as a team agent, read:

1. `.rules/patterns/bdd-workflow.md` - Understand the BDD pipeline
2. `.rules/patterns/beads-integration.md` - How to track work
3. `.claude/skills/` - The 4-skill workflow
4. `AGENTS.md` - Agent conventions

### For Cognee

These docs are indexed in Cognee datasets:

- `btc-patterns` - Pattern docs
- `btc-sessions` - Session history

Query Cognee for context:

```bash
/query How does the A-S model handle inventory risk?
```

## Maintenance

- Keep docs under 400 lines (split if needed)
- Use semantic Markdown (H1/H2/H3 hierarchy)
- Include metadata frontmatter
- Update when architecture changes
- Remove obsolete patterns

---

**Last Updated**: 2026-02-21
