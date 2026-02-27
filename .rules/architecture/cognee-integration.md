---
description: Cognee AI memory layer integration for BTC algo trading knowledge system
tags: [cognee, architecture, knowledge-graph, semantic-search, trading]
last_updated: 2026-02-26
---

# Cognee Integration Architecture

Cognee provides semantic search, knowledge graphs, and AI-powered insights over the BTC algo trading knowledge system. It runs on the compute server as a persistent service.

## Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Knowledge Garden                       │
│  (.claude/ + .rules/ + Session History)                 │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ /land (Step 8 - auto-sync)
                 ▼
┌─────────────────────────────────────────────────────────┐
│           Cognee — Compute Server                        │
│  btc-algo-trading-cognee.apps.compute.lan                            │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Cognee API (FastAPI)                           │    │
│  └──────────────────────┬──────────────────────────┘    │
│                         │                               │
│  ┌──────────────────────▼──────────────────────────┐    │
│  │  PostgreSQL + pgvector (btc-algo-trading-cognee-db)          │    │
│  │  NFS: /mnt/nfs/databases/btc-algo-trading/cognee       │    │
│  └─────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────┘
                            │
                            │ HTTP (LAN)
                            ▼
┌─────────────────────────────────────────────────────────┐
│                      Consumers                           │
│  • /query command (semantic search)                     │
│  • /land command (session capture + auto-sync)          │
│  • Claude agents (context retrieval)                    │
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

### 2. Cognee Stack (Compute Server)

**Deployed via Kamal** from `config/deploy.yml`.

**PostgreSQL + pgvector** (`btc-algo-trading-cognee-db` accessory)
- Document storage and metadata
- Vector embeddings for semantic search
- Full-text search capabilities
- NFS-backed persistence at `/mnt/nfs/databases/btc-algo-trading/cognee/` (db) and `/mnt/nfs/docker/btc-algo-trading-cognee/data/` (app data)

**Cognee API** (`btc-algo-trading-cognee` service)
- REST API (FastAPI)
- Document ingestion and processing
- Semantic search
- Accessible at `https://btc-algo-trading-cognee.apps.compute.lan`

## Data Flow

### Ingestion (Knowledge → Cognee)

```
1. User runs: /land (Step 8 auto-syncs when .claude/ or .rules/ changed)
   │
2. /land finds all .md files in .claude/ and .rules/
   │
3. For each file:
   │  ├─ Upload to Cognee API (POST /api/v1/add)
   │  ├─ Assign to dataset (btc-knowledge-garden or btc-patterns)
   │  └─ Store metadata (file path, last modified, etc.)
   │
4. Cognee processes files:
   │  ├─ Chunk documents (semantic chunking)
   │  ├─ Generate embeddings (OpenAI text-embedding-3-small)
   │  ├─ Extract entities (LLM-based)
   │  └─ Index for search (PostgreSQL + pgvector)
   │
5. Knowledge indexed and ready for queries
```

### Query (User → Cognee → Answer)

```
1. User runs: /query "How do I capture patterns?"
   │
2. Claude calls Cognee API:
   │  POST https://btc-algo-trading-cognee.apps.compute.lan/api/v1/search
   │  { "query": "How do I capture patterns?" }
   │
3. Cognee processes query:
   │  ├─ Generate query embedding
   │  ├─ Vector similarity search (pgvector)
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
   │  ├─ Dataset: btc-sessions
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
| `btc-knowledge-garden` | `.claude/` files | Commands, patterns, quick references |
| `btc-patterns` | `.rules/` files | Architecture, technical patterns |
| `btc-constitution` | CONSTITUTION.md, VISION.md, PLAN.md, AGENTS.md | Core values and guidance |
| `btc-strategies` | `strategies/` | Trading strategy code and docs |
| `btc-backtests` | `backtests/` | Backtest results and analysis |
| `btc-sessions` | `/land` session notes | Work history, decisions, solutions |

## API Endpoints

Base URL: `https://btc-algo-trading-cognee.apps.compute.lan`

### Health Check

```bash
GET /health
```

### Add Document

```bash
POST /api/v1/add
Content-Type: multipart/form-data

data: @file.md
datasetName: btc-knowledge-garden
```

### Cognify (Build Knowledge Graph)

```bash
POST /api/v1/cognify
Content-Type: application/json

{
  "datasets": ["btc-knowledge-garden", "btc-patterns"]
}
```

### Search

```bash
POST /api/v1/search
Content-Type: application/json

{
  "query": "How do I capture patterns?",
  "dataset_name": "btc-knowledge-garden"  # Optional
}
```

### API Docs

```bash
open https://btc-algo-trading-cognee.apps.compute.lan/docs
```

## Deployment

### First Deploy

```bash
# 1. Copy secrets template and fill in values
cp .kamal/secrets.example .kamal/secrets
# edit .kamal/secrets with real values

# 2. Create NFS directories on compute server (one-time)
ssh root@10.10.20.138 "mkdir -p /mnt/nfs/databases/btc-algo-trading/cognee /mnt/nfs/docker/btc-algo-trading-cognee/data"

# 3. Deploy
kamal setup -c config/deploy.yml

# 4. Initial data sync
.claude/scripts/sync-to-cognee.sh
```

### Subsequent Deploys

```bash
kamal deploy -c config/deploy.yml
```

### Check Status

```bash
.claude/scripts/cognee-local.sh health
# or
kamal app details -c config/deploy.yml
```

## Configuration

### Kamal Deploy

See `config/deploy.cognee.yml` for full configuration.

Key settings:
- Service: `btc-algo-trading-cognee`
- Host: `btc-algo-trading-cognee.apps.compute.lan`
- DB accessory port: `5433` (avoids collision with muninn-cognee on 5432)
- NFS volumes: `/mnt/nfs/databases/btc-algo-trading/cognee/` (db), `/mnt/nfs/docker/btc-algo-trading-cognee/data/` (app)

### Secrets

Real secrets live in `.kamal/secrets` (gitignored). See `.kamal/secrets.example` for required keys:
- `KAMAL_REGISTRY_PASSWORD` — Harbor registry password
- `COGNEE_DB_PASSWORD` — PostgreSQL password
- `POSTGRES_PASSWORD` — Same as COGNEE_DB_PASSWORD
- `OPENAI_API_KEY` — OpenAI API key for embeddings

## Workflows

### Daily Use

```bash
# Query knowledge
/query How do I use beads?

# At end of session (auto-syncs to Cognee)
/land
```

### Sync Knowledge Manually

```bash
# Sync all datasets
.claude/scripts/sync-to-cognee.sh

# Sync specific dataset
.claude/scripts/sync-to-cognee.sh knowledge-garden
.claude/scripts/sync-to-cognee.sh patterns
.claude/scripts/sync-to-cognee.sh constitution

# Fresh sync (clear + re-upload)
.claude/scripts/sync-to-cognee.sh --clear
```

### Check Health

```bash
.claude/scripts/cognee-local.sh health
```

## Local Development Fallback

For offline work or testing, a local Docker stack is available:

```bash
# Requires .claude/docker/.env (copy from .env.example)

# Start local stack
.claude/scripts/cognee-local.sh --local up

# Check health
.claude/scripts/cognee-local.sh --local health

# Use local endpoint for sync
.claude/scripts/sync-to-cognee.sh --local
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

## Troubleshooting

**Cognee unreachable:**
```bash
# Check health endpoint
curl https://btc-algo-trading-cognee.apps.compute.lan/health

# Check deploy status
kamal app details -c config/deploy.yml

# View logs
kamal app logs -c config/deploy.yml
```

**Stale results:**
```bash
# Run /land to sync latest changes
/land
```

**Re-deploy after config change:**
```bash
kamal deploy -c config/deploy.yml
```

## Related Documentation

- [Beads Integration](.rules/patterns/beads-integration.md)
- [/query Command](.claude/commands/query.md)
- [/land Command](.claude/commands/land.md)
- [Kamal Deploy Config](../../config/deploy.yml)
- [Cognee Docs](https://docs.cognee.ai/)
