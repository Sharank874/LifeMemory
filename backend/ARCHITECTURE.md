# LifeMemory AI Backend Architecture

## Overview

LifeMemory AI is a production-grade personal journaling and memory system with AI-powered reflection capabilities. The backend is built with strict privacy, user isolation, and evidence-grounded reasoning.

## Core Principles

1. **Strict User Isolation**: Every operation is scoped to `user_id`
2. **Temporal Intelligence**: Time, recency, and emotional context matter
3. **Evidence-Grounded**: All answers derived from retrieved journal entries
4. **Agent-Based Reasoning**: Multi-node LangGraph workflow (no single-prompt calls)
5. **Production-Ready**: FastAPI, Supabase, Docker, MLOps

## Architecture Layers

### 1. API Layer (`api/`)

**Endpoints:**
- `POST /journal/add` - Create journal entry (async embedding generation)
- `GET /journal/list` - List user's journals (paginated)
- `POST /ask` - Memory query via LangGraph agent
- `GET /insights/summary` - Summary statistics
- `GET /health` - Health check

**Authentication:**
- All endpoints (except `/health`) require Supabase JWT
- JWT verified on every request
- User ID extracted from token

### 2. Authentication Layer (`auth/`)

**Components:**
- JWT verification middleware
- User ID extraction
- Supabase client with RLS support

**Security:**
- Token expiration checking
- Signature verification
- User isolation enforced

### 3. Database Layer (`database/`)

**Schema:**
- `journals` table: User journal entries
- `journal_embeddings` table: Vector embeddings with metadata
- pgvector extension for similarity search

**Security:**
- Row Level Security (RLS) enabled
- Policies enforce `auth.uid() = user_id`
- All queries explicitly filter by `user_id`

**Connection:**
- Supabase client for REST API operations
- asyncpg pool for direct PostgreSQL access (vector operations)

### 4. Embedding Layer (`embeddings/`)

**Supported Providers:**
- OpenAI `text-embedding-3-large` (default, 3072 dim)
- Cohere `embed-english-v3.0` (1024 dim)

**Features:**
- Async embedding generation
- Batch processing support
- Configurable dimensions

### 5. Retrieval Layer (`retrieval/`)

**Hybrid Retrieval Strategy:**
- Vector similarity (cosine similarity)
- Temporal weighting (recency bias)
- Mood/emotion weighting
- Metadata filtering

**Query Processing:**
- Automatic temporal filter extraction
- Mood filter extraction
- User-scoped retrieval only

### 6. LangGraph Agent Pipeline (`graph/`)

**Workflow:**
```
User Question
   ↓
Intent Classifier (reflection/pattern/recall/temporal_comparison/advice)
   ↓
Memory Retriever (hybrid retrieval with filters)
   ↓
Temporal Pattern Analyzer (time-based patterns)
   ↓
Reflection Synthesizer (evidence-based answer generation)
   ↓
Final Answer
```

**Key Features:**
- Multi-node state machine
- Typed state (GraphState)
- Evidence tracking
- No hallucination (grounded in retrieved entries)

### 7. Analysis Layer (`analysis/`)

**Pattern Analysis:**
- Temporal patterns (hourly, daily, monthly)
- Mood distribution
- Entry frequency
- Productivity patterns

### 8. MLOps Layer (`mlops/`)

**Components:**
- **MLflow**: Prompt versioning, retrieval tracking, query logging
- **Evidently AI**: Embedding drift detection, topic drift
- **Ragas**: RAG evaluation (faithfulness, relevancy, precision, recall)

## Data Flow

### Journal Ingestion

1. User submits journal entry via `POST /journal/add`
2. Entry stored in `journals` table (synchronous)
3. Embedding generation scheduled as background task
4. Embedding stored in `journal_embeddings` table (async)
5. Metadata attached (date, week, month, mood, sentiment)

### Memory Query

1. User asks question via `POST /ask`
2. JWT verified, user_id extracted
3. LangGraph agent pipeline:
   - Intent classified
   - Relevant entries retrieved (hybrid)
   - Temporal patterns analyzed
   - Answer synthesized from evidence
4. Response includes answer + evidence entries

## Security Model

### Defense in Depth

1. **JWT Verification**: Every request authenticated
2. **Explicit Filtering**: All queries filter by `user_id`
3. **RLS Policies**: Database-level enforcement
4. **No Cross-User Access**: Impossible by design

### Data Privacy

- No user data used for training
- No cross-user data access
- Embeddings stored per-user
- All operations user-scoped

## Deployment

### Docker

- Multi-stage build
- Non-root user
- Health checks
- Optimized layers

### Docker Compose

- Backend service
- Redis (background jobs)
- MLflow (tracking)

### Environment Variables

- Supabase credentials
- API keys (OpenAI/Cohere)
- Database connection
- Model configuration

## Scalability Considerations

### Database

- Indexed queries (user_id, created_at, vector)
- Connection pooling (asyncpg)
- RLS for security without performance penalty

### Embeddings

- Async generation (non-blocking)
- Batch processing support
- Configurable providers

### Retrieval

- Efficient vector search (pgvector IVFFlat)
- Candidate re-ranking
- Configurable result limits

### Agent Pipeline

- Async LangGraph execution
- State management
- Error handling

## Monitoring & Observability

### MLOps

- MLflow: Track prompts, retrievals, queries
- Evidently: Monitor data drift
- Ragas: Evaluate RAG quality

### Logging

- Structured logging (to be configured)
- Error tracking
- Performance metrics

## Future Enhancements

1. **Advanced Pattern Detection**: NLP-based topic modeling
2. **Sentiment Analysis**: Automated mood detection
3. **Temporal Queries**: "What happened in December?"
4. **Multi-modal**: Image support for journal entries
5. **Export**: Data export functionality
6. **Backup**: Automated backups

## Technology Stack Summary

- **Framework**: FastAPI (async Python)
- **Database**: Supabase PostgreSQL + pgvector
- **Auth**: Supabase Auth (JWT)
- **LLM**: OpenAI GPT-4 (via LangChain)
- **Orchestration**: LangGraph
- **Embeddings**: OpenAI / Cohere
- **MLOps**: MLflow, Evidently AI, Ragas
- **Deployment**: Docker, Docker Compose
- **Background Jobs**: Prefect / Celery + Redis

## Code Quality

- Type hints throughout
- Docstrings for all functions
- Error handling
- Async/await patterns
- Production-ready error messages
- No hardcoded secrets

