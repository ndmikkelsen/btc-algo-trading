---
description: Cognee AI memory layer integration for second-brain knowledge system
tags: [cognee, architecture, knowledge-graph, semantic-search]
last_updated: 2026-01-25
---

# Cognee Integration Architecture

Cognee provides semantic search, knowledge graphs, and AI-powered insights over the second-brain knowledge system.

## Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Knowledge Garden                       │
│  (.claude/ + .rules/ + Session History)                 │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ /land (Step 8b - auto-sync)
                 ▼
┌─────────────────────────────────────────────────────────┐
│                    Cognee Stack                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  PostgreSQL  │  │    Redis     │  │    Neo4j     │  │
│  │  + pgvector  │  │   (Cache)    │  │   (Graph)    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         │                  │                 │          │
│         └──────────────────┴─────────────────┘          │
│                           │                             │
│                  ┌────────▼────────┐                    │
│                  │  Cognee API     │                    │
│                  │  (FastAPI)      │                    │
│                  └────────┬────────┘                    │
└───────────────────────────┼─────────────────────────────┘
                            │
                            │ HTTP API
                            ▼
┌─────────────────────────────────────────────────────────┐
│                      Consumers                           │
│  • /query command (semantic search)                     │
│  • /land command (session capture)                      │
│  • Claude agents (context retrieval)                    │
│  • Neo4j Browser (graph visualization)                  │
└─────────────────────────────────────────────────────────┘
```

## Components

### 1. Data Sources

**Knowledge Garden** (`.claude/`)
- Commands (`/remember`, `/learn`, `/cultivate`, etc.)
- Patterns (reusable solutions)
- Quick references (how-to guides)
- Templates (document templates)

**Technical Documentation** (`.rules/`)
- Architecture (system design)
- Patterns (technical solutions)

**Session History**
- Captured via `/land` command
- Work completed, decisions made, challenges solved
- Context for future sessions

### 2. Cognee Stack

**PostgreSQL + pgvector**
- Document storage and metadata
- Vector embeddings for semantic search
- Full-text search capabilities

**Redis**
- Response caching
- Async job queue
- Session storage

**Neo4j**
- Knowledge graph database
- Entity relationships
- Pattern connections
- Concept hierarchies

**Cognee API**
- REST API (FastAPI)
- Document ingestion and processing
- Semantic search
- Knowledge graph queries

## Data Flow

### Ingestion (Knowledge → Cognee)

```
1. User runs: /land (Step 8b auto-syncs when .claude/ or .rules/ changed)
   │
2. /land finds all .md files in .claude/ and .rules/
   │
3. For each file:
   │  ├─ Upload to Cognee API (POST /api/v1/add)
   │  ├─ Assign to dataset (knowledge-garden or second-brain-patterns)
   │  └─ Store metadata (file path, last modified, etc.)
   │
4. Cognee processes files:
   │  ├─ Chunk documents (semantic chunking)
   │  ├─ Generate embeddings (OpenAI text-embedding-3-small)
   │  ├─ Extract entities (LLM-based)
   │  ├─ Build knowledge graph (Neo4j)
   │  └─ Index for search (PostgreSQL + pgvector)
   │
5. Knowledge graph created and ready for queries
```

### Query (User → Cognee → Answer)

```
1. User runs: /query "How do I capture patterns?"
   │
2. Claude calls Cognee API:
   │  POST /api/v1/search
   │  { "query": "How do I capture patterns?" }
   │
3. Cognee processes query:
   │  ├─ Generate query embedding
   │  ├─ Vector similarity search (pgvector)
   │  ├─ Graph traversal (Neo4j) for related concepts
   │  ├─ LLM-based answer generation
   │  └─ Return answer + sources
   │
4. Claude displays:
   │  ├─ Answer to user's question
   │  ├─ Source documents referenced
   │  └─ Related patterns/commands
```

### Session Capture (/land → Cognee)

```
1. User runs: /land
   │
2. Create session summary:
   │  ├─ Date, branch, commit
   │  ├─ Work completed
   │  ├─ Beads closed
   │  ├─ Technical decisions
   │  └─ Challenges/solutions
   │
3. Upload to Cognee:
   │  ├─ POST /api/v1/add
   │  ├─ Dataset: second-brain-sessions
   │  └─ Cognify to update graph
   │
4. Session indexed and searchable:
   │  ├─ "What did we work on last week?"
   │  ├─ "How did we solve X problem?"
   │  └─ "What decisions were made about Y?"
```

## Datasets

| Dataset | Source | Purpose |
|---------|--------|---------|
| `knowledge-garden` | `.claude/` files | Commands, patterns, quick references |
| `second-brain-patterns` | `.rules/` files | Architecture, technical patterns |
| `second-brain-sessions` | Session summaries | Work history, decisions, solutions |

## API Endpoints

### Health Check

```bash
GET http://localhost:8000/health
```

### Add Document

```bash
POST http://localhost:8000/api/v1/add
Content-Type: multipart/form-data

data: @file.md
datasetName: knowledge-garden
```

### Cognify (Build Knowledge Graph)

```bash
POST http://localhost:8000/api/v1/cognify
Content-Type: application/json

{
  "datasets": ["knowledge-garden", "second-brain-patterns"]
}
```

### Search

```bash
POST http://localhost:8000/api/v1/search
Content-Type: application/json

{
  "query": "How do I capture patterns?",
  "dataset_name": "knowledge-garden"  # Optional
}
```

## Configuration

### Environment Variables

See `docker-compose.cognee.yml` (when created):

```env
# Database
COGNEE_DB_PASSWORD=<secure-password>
COGNEE_NEO4J_PASSWORD=<secure-password>

# OpenAI (required)
OPENAI_API_KEY=sk-your-key-here
COGNEE_LLM_MODEL=gpt-4
COGNEE_EMBEDDING_MODEL=text-embedding-3-small

# Authentication (disabled for local dev)
COGNEE_REQUIRE_AUTH=false
```

### Port Mappings

| Service | Container | Host | Purpose |
|---------|-----------|------|---------|
| PostgreSQL | 5432 | 5433 | Vector DB |
| Redis | 6379 | 6380 | Cache |
| Neo4j HTTP | 7474 | 7474 | Browser UI |
| Neo4j Bolt | 7687 | 7687 | Protocol |
| Cognee API | 8000 | 8000 | REST API |

## Workflows

### Initial Setup

```bash
# 1. Start Cognee stack
.claude/scripts/cognee-local.sh up

# 2. Wait for health checks
.claude/scripts/cognee-local.sh health

# 3. Initial sync via /land
# Make a change to any .rules/ file, then run:
/land

# 4. Verify in Neo4j Browser
open http://localhost:7474
```

### Daily Use

```bash
# Query knowledge
/query How do I use beads?

# At end of session
/land  # Auto-formats, syncs to Cognee, captures session
```

### Maintenance

```bash
# View logs
.claude/scripts/cognee-local.sh logs-api

# Check health
.claude/scripts/cognee-local.sh health

# Backup data
.claude/scripts/cognee-local.sh backup

# Reset everything
.claude/scripts/cognee-local.sh clean
.claude/scripts/cognee-local.sh up

# Re-sync via /land (make change to trigger sync)
/land
```

## Benefits

### For Knowledge Discovery

- **Semantic search**: Find information by concept, not just keywords
- **Related patterns**: Discover connections between ideas
- **Context retrieval**: Get full context around answers

### For Session Continuity

- **Work history**: "What did we do last week?"
- **Decision tracking**: "Why did we choose X approach?"
- **Problem solving**: "How did we solve this before?"

### For AI Agents

- **Context awareness**: Agents understand project conventions
- **Pattern application**: Automatically apply established patterns
- **Continuity**: Pick up where previous sessions left off

## Limitations

### Local Development

- Requires Docker and 4GB+ RAM
- OpenAI API key required (costs money)
- Network connectivity for embeddings

### Data Privacy

- Documents sent to OpenAI for embeddings
- Consider data sensitivity before syncing
- Use local embeddings for sensitive data (future enhancement)

### Performance

- Initial sync can take minutes for large knowledge bases
- Search latency ~1-2 seconds
- Neo4j requires warm-up time after restart

## Future Enhancements

- [ ] Local embeddings (no OpenAI required)
- [ ] Incremental sync (only changed files)
- [ ] Auto-sync on file save (file watcher)
- [ ] Chat interface (/chat command)
- [ ] Knowledge graph visualization in Obsidian
- [ ] Agent-to-agent knowledge sharing

## Troubleshooting

See `.claude/commands/query.md` for query-specific troubleshooting.

**Cognee won't start:**
```bash
# Check Docker resources
docker system df

# View logs
.claude/scripts/cognee-local.sh logs

# Reset
.claude/scripts/cognee-local.sh clean
.claude/scripts/cognee-local.sh up
```

**Stale results:**
```bash
# Run /land to sync latest changes
/land
```

**Slow queries:**
```bash
# Check Neo4j memory
.claude/scripts/cognee-local.sh shell-neo4j
# CALL dbms.listConfig() YIELD name, value WHERE name STARTS WITH 'dbms.memory'
```

## Related Documentation

- [Beads Integration](.rules/patterns/beads-integration.md)
- [/query Command](.claude/commands/query.md)
- [/land Command](.claude/commands/land.md)
- [Knowledge Garden](../GARDENING.md)
- [Cognee Docs](https://docs.cognee.ai/)
