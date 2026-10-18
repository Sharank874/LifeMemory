# LifeMemory AI Backend

Production-grade backend for LifeMemory AI - a privacy-first personal journaling and memory system.

## Architecture

- **Framework**: FastAPI (async Python)
- **Database**: Supabase PostgreSQL with pgvector
- **Authentication**: Supabase Auth with JWT
- **LLM Orchestration**: LangChain + LangGraph
- **Embeddings**: OpenAI text-embedding-3-large or Cohere embed-v3
- **MLOps**: MLflow, Evidently AI, Ragas
- **Deployment**: Docker + Docker Compose

## Setup

### 1. Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required variables:
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Supabase anon key
- `SUPABASE_SERVICE_ROLE_KEY`: Service role key (for database operations)
- `SUPABASE_JWT_SECRET`: JWT secret for token verification
- `OPENAI_API_KEY`: OpenAI API key (or `COHERE_API_KEY` if using Cohere)

### 2. Database Setup

Run the SQL schema in your Supabase SQL editor:

```bash
# The schema is in database/schema.sql
# Copy and paste it into Supabase SQL editor
```

This will:
- Enable pgvector extension
- Create `journals` and `journal_embeddings` tables
- Set up Row Level Security (RLS) policies
- Create necessary indexes

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Locally

```bash
uvicorn main:app --reload
```

### 5. Run with Docker

```bash
docker-compose up --build
```

## API Endpoints

### Health Check
- `GET /health` - Health check (no auth required)

### Journals
- `POST /journal/add` - Create a new journal entry
- `GET /journal/list?page=1&page_size=20` - List journal entries

### Memory Query
- `POST /ask` - Ask a question about your memories (uses LangGraph agent)

### Insights
- `GET /insights/summary` - Get summary statistics

## Authentication

All endpoints (except `/health`) require authentication via Supabase JWT token:

```
Authorization: Bearer <your-jwt-token>
```

## LangGraph Agent Pipeline

The `/ask` endpoint uses a multi-node LangGraph workflow:

1. **Intent Classifier** - Classifies query intent (reflection, pattern, recall, etc.)
2. **Memory Retriever** - Hybrid retrieval with temporal and mood weighting
3. **Temporal Pattern Analyzer** - Analyzes patterns in retrieved entries
4. **Reflection Synthesizer** - Generates evidence-based answer

## MLOps

- **MLflow**: Tracks prompts, retrievals, and query results
- **Evidently AI**: Detects embedding and topic drift
- **Ragas**: Evaluates RAG quality (faithfulness, relevancy, etc.)

## Development

### Project Structure

```
backend/
├── api/              # API endpoints
├── auth/             # Authentication middleware
├── database/         # Database connection and schema
├── embeddings/       # Embedding generation
├── retrieval/        # Hybrid retrieval system
├── graph/            # LangGraph agent pipeline
├── analysis/         # Pattern analysis
├── mlops/            # MLOps tracking and evaluation
├── main.py           # FastAPI application
└── requirements.txt  # Dependencies
```

## Production Deployment

The application is Docker-ready and can be deployed to:
- Render
- Railway
- AWS EC2
- Any Docker-compatible platform

Make sure to:
1. Set all environment variables
2. Run database migrations
3. Configure CORS for your frontend domain
4. Set up proper logging and monitoring

## Security

- **Row Level Security (RLS)**: All database queries are user-scoped
- **JWT Verification**: Every request is authenticated
- **No Cross-User Access**: Strict user isolation enforced
- **No Data Training**: User data is never used for training

## License

Proprietary - LifeMemory AI

