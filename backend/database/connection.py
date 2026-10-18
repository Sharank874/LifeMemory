"""
Database connection and setup utilities for Supabase PostgreSQL.
"""

from typing import Optional
from supabase import create_client, Client
import asyncpg
from config.settings import get_settings

# Global Supabase client
_supabase_client: Optional[Client] = None
_db_pool: Optional[asyncpg.Pool] = None


def get_supabase_client() -> Client:
    """Get or create Supabase client instance."""
    global _supabase_client
    if _supabase_client is None:
        settings = get_settings()
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    return _supabase_client


async def get_db_pool() -> asyncpg.Pool:
    """Get or create asyncpg connection pool for direct PostgreSQL access."""
    global _db_pool
    if _db_pool is None:
        settings = get_settings()
        
        # Use DATABASE_URL if provided (recommended for production)
        db_url = settings.DATABASE_URL
        
        if not db_url:
            # Construct from Supabase credentials
            if not settings.SUPABASE_DB_PASSWORD:
                raise ValueError(
                    "Either DATABASE_URL or SUPABASE_DB_PASSWORD must be set. "
                    "Get the database password from Supabase Dashboard > Settings > Database"
                )
            
            # Extract project reference from Supabase URL
            # Format: https://[project-ref].supabase.co
            project_ref = settings.SUPABASE_URL.replace("https://", "").replace(".supabase.co", "")
            
            # Supabase direct connection format
            db_url = f"postgresql://postgres.{project_ref}:{settings.SUPABASE_DB_PASSWORD}@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
        
        # Disable prepared statements for pgbouncer compatibility
        # Supabase pooler (pgbouncer) doesn't support prepared statements
        _db_pool = await asyncpg.create_pool(
            dsn=db_url,
            min_size=2,
            max_size=10,
            command_timeout=60,
            statement_cache_size=0  # Required for pgbouncer/pooler
        )
    return _db_pool


async def verify_database_setup():
    """Verify pgvector extension is enabled and tables exist."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Enable pgvector extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Verify tables exist (they should be created via migrations)
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename IN ('journals', 'journal_embeddings')
        """)
        
        if len(tables) < 2:
            raise RuntimeError("Required tables (journals, journal_embeddings) not found. Run migrations first.")


async def close_db_pool():
    """Close database connection pool."""
    global _db_pool
    if _db_pool:
        await _db_pool.close()
        _db_pool = None

