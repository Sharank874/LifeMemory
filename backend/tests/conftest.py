"""
Test setup: the suite runs fully offline with dummy credentials.

No Supabase project, database, embedding provider or LLM is contacted:
network-facing pieces (retriever SQL, LLM router) are replaced with fakes
inside the individual tests.
"""
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

# Dummy values only, so that config.settings validates. Never real keys.
os.environ.update({
    "ENV": "test",
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_ANON_KEY": "test-anon-key",
    "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
    "SUPABASE_JWT_SECRET": "test-jwt-secret",
    "DATABASE_URL": "postgresql://user:pass@localhost:5432/test",
    "USE_COHERE": "true",
    "COHERE_API_KEY": "test-cohere-key",
    "GROQ_API_KEY": "",
    "GEMINI_API_KEY": "",
    "OPENAI_API_KEY": "",
    "LANGCHAIN_TRACING_V2": "false",
})
