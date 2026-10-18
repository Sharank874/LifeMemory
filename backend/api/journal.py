"""
Journal API endpoints for creating and listing journal entries.
Implements single-entry-per-day model with proper embedding replacement.
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
import uuid
import json
import logging
from auth.supabase import get_current_user, verify_token, get_supabase_rest_headers
from config.settings import get_settings
from database.connection import get_db_pool
from embeddings.embedder import get_embedder
import asyncpg
import httpx

router = APIRouter()
logger = logging.getLogger(__name__)


class JournalSave(BaseModel):
    """Request model for saving a journal entry (UPSERT)."""
    content: str = Field(..., min_length=1, description="Journal entry content")
    mood: Optional[str] = Field(None, description="Mood/emotion label")
    entry_date: Optional[str] = Field(None, description="Date in YYYY-MM-DD format (defaults to today)")


class JournalResponse(BaseModel):
    """Response model for journal entry."""
    id: str
    user_id: str
    entry_date: str
    content: str
    mood: Optional[str]
    created_at: str
    updated_at: str


class JournalListResponse(BaseModel):
    """Response model for journal list."""
    journals: List[JournalResponse]
    total: int
    page: int
    page_size: int


class DaysWithEntriesResponse(BaseModel):
    """Response model for days with entries."""
    dates: List[str]  # List of dates in YYYY-MM-DD format


async def generate_and_store_embedding(
    journal_id: str,
    user_id: str,
    entry_date: date,
    content: str,
    mood: Optional[str]
):
    """
    Background task to generate and store embedding for a journal entry.
    
    CRITICAL: Deletes ALL old embeddings for (user_id, entry_date) before creating new one.
    This ensures strict one-embedding-per-day enforcement, even if journal_id changes.
    
    Args:
        journal_id: Journal entry ID
        user_id: User ID
        entry_date: Entry date
        content: Journal content
        mood: Mood label
    """
    try:
        embedder = get_embedder()
        embedding = await embedder.embed_text(content)
        
        # Extract metadata
        metadata = {
            "mood": mood,
            "entry_date": entry_date.isoformat(),
            "week": entry_date.isocalendar()[1],
            "month": entry_date.month,
            "year": entry_date.year
        }
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # CRITICAL: Delete ALL embeddings for this user+date combination
            # This ensures we never have multiple embeddings for the same day
            # Even if journal_id changes on update, we clean up properly
            await conn.execute("""
                DELETE FROM journal_embeddings
                WHERE user_id = $1 AND entry_date = $2
            """, user_id, entry_date)
            
            # Insert new embedding (guaranteed to be the only one for this user+date)
            await conn.execute("""
    INSERT INTO journal_embeddings (
        id,
        journal_id,
        user_id,
        entry_date,
        embedding,
        chunk_text,
        metadata
    )
    VALUES (
        gen_random_uuid(),
        $1,
        $2,
        $3,
        $4::vector,
        $5,
        $6::jsonb
    )
""", journal_id, user_id, entry_date, str(embedding), content, json.dumps(metadata))
        
        logger.info(f"Generated and stored embedding for journal {journal_id} (date: {entry_date})")
        
    except Exception as e:
        logger.error(f"Error generating embedding for journal {journal_id}: {str(e)}", exc_info=True)


@router.post("/save", response_model=JournalResponse, status_code=status.HTTP_200_OK)
async def save_journal(
    journal: JournalSave,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
    token_data: dict = Depends(verify_token)
):
    """
    Save a journal entry (UPSERT - one entry per day per user).
    
    If an entry exists for the given date, it will be replaced.
    Old embeddings are deleted and new ones are generated.
    """
    # Parse entry_date (default to today)
    entry_date = date.today()
    if journal.entry_date:
        try:
            entry_date = datetime.strptime(journal.entry_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid entry_date format. Use YYYY-MM-DD format."
            )
    
    settings = get_settings()
    headers = get_supabase_rest_headers(token_data["token"])
    
    try:
        # Use direct PostgreSQL connection for UPSERT with proper conflict handling
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Check if entry_date column exists (for migration compatibility)
            has_entry_date = await _check_column_exists(conn, "journals", "entry_date")
            
            if not has_entry_date:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=(
                        "Database migration required. Please run the migration SQL in your Supabase SQL editor. "
                        "See backend/database/migration_add_entry_date.sql for the migration script."
                    )
                )
            
            # CRITICAL: Delete old embeddings FIRST (before UPSERT)
            # Delete by (user_id, entry_date) to ensure we catch all cases
            # This ensures strict one-embedding-per-day enforcement
            await conn.execute("""
                DELETE FROM journal_embeddings
                WHERE user_id = $1 AND entry_date = $2
            """, user_id, entry_date)
            
            # UPSERT journal entry (enforced by UNIQUE constraint on user_id, entry_date)
            # ON CONFLICT ensures we replace existing entry, not append
            row = await conn.fetchrow("""
                INSERT INTO journals (id, user_id, entry_date, content, mood)
                VALUES (gen_random_uuid(), $1, $2, $3, $4)
                ON CONFLICT (user_id, entry_date)
                DO UPDATE SET
                    content = EXCLUDED.content,
                    mood = EXCLUDED.mood,
                    updated_at = now()
                RETURNING id, user_id, entry_date, content, mood, created_at, updated_at
            """, user_id, entry_date, journal.content, journal.mood)
            
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to save journal entry"
                )
            
            journal_id = str(row['id'])
            
            # Schedule new embedding generation in background
            background_tasks.add_task(
                generate_and_store_embedding,
                journal_id,
                user_id,
                entry_date,
                journal.content,
                journal.mood
            )
            
            return JournalResponse(
                id=journal_id,
                user_id=str(row['user_id']),
                entry_date=row['entry_date'].isoformat(),
                content=row['content'],
                mood=row['mood'],
                created_at=row['created_at'].isoformat(),
                updated_at=row['updated_at'].isoformat()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving journal entry: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving journal entry: {str(e)}"
        )


@router.get("/get", response_model=JournalResponse)
async def get_journal(
    entry_date: str = Query(..., description="Date in YYYY-MM-DD format"),
    user_id: str = Depends(get_current_user),
    token_data: dict = Depends(verify_token)
):
    """
    Get a journal entry for a specific date.
    """
    try:
        entry_date_obj = datetime.strptime(entry_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid entry_date format. Use YYYY-MM-DD format."
        )
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Check if entry_date column exists (for migration compatibility)
        has_entry_date = await _check_column_exists(conn, "journals", "entry_date")
        
        if not has_entry_date:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Database migration required. Please run the migration SQL in your Supabase SQL editor. "
                    "See backend/database/migration_add_entry_date.sql for the migration script."
                )
            )
        row = await conn.fetchrow("""
            SELECT id, user_id, entry_date, content, mood, created_at, updated_at
            FROM journals
            WHERE user_id = $1 AND entry_date = $2
        """, user_id, entry_date_obj)
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No journal entry found for date {entry_date}"
            )
        
        return JournalResponse(
            id=str(row['id']),
            user_id=str(row['user_id']),
            entry_date=row['entry_date'].isoformat(),
            content=row['content'],
            mood=row['mood'],
            created_at=row['created_at'].isoformat(),
            updated_at=row['updated_at'].isoformat()
        )


@router.get("/days-with-entries", response_model=DaysWithEntriesResponse)
async def get_days_with_entries(
    month: str = Query(..., description="Month in YYYY-MM format"),
    user_id: str = Depends(get_current_user),
    token_data: dict = Depends(verify_token)
):
    """
    Get all dates in a month that have journal entries.
    Used for calendar UI to show checkmarks.
    """
    try:
        # Parse month and get start/end dates
        year, month_num = map(int, month.split("-"))
        start_date = date(year, month_num, 1)
        
        # Calculate end date (last day of month)
        if month_num == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month_num + 1, 1)
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Check if entry_date column exists (for migration compatibility)
            has_entry_date = await _check_column_exists(conn, "journals", "entry_date")
            
            if not has_entry_date:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=(
                        "Database migration required. Please run the migration SQL in your Supabase SQL editor. "
                        "See backend/database/migration_add_entry_date.sql for the migration script."
                    )
                )
            
            rows = await conn.fetch("""
                SELECT entry_date
                FROM journals
                WHERE user_id = $1
                  AND entry_date >= $2
                  AND entry_date < $3
                ORDER BY entry_date
            """, user_id, start_date, end_date)
            
            dates = [row['entry_date'].isoformat() for row in rows]
            
            return DaysWithEntriesResponse(dates=dates)
            
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid month format. Use YYYY-MM format."
        )
    except Exception as e:
        logger.error(f"Error retrieving days with entries: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving days with entries: {str(e)}"
        )


async def _check_column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    result = await conn.fetchrow("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = $1 AND column_name = $2
    """, table_name, column_name)

    # print("DEBUG CHECK:", table_name, column_name, result)

    return result is not None


@router.get("/list", response_model=JournalListResponse)
async def list_journals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user),
    token_data: dict = Depends(verify_token)
):
    """
    List journal entries for the authenticated user (paginated).
    """
    offset = (page - 1) * page_size
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Check if entry_date column exists (for migration compatibility)
        has_entry_date = await _check_column_exists(conn, "journals", "entry_date")
        
        if not has_entry_date:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Database migration required. Please run the migration SQL in your Supabase SQL editor. "
                    "See backend/database/migration_add_entry_date.sql for the migration script."
                )
            )
        
        # Get total count
        total_row = await conn.fetchrow("""
            SELECT COUNT(*) as count
            FROM journals
            WHERE user_id = $1
        """, user_id)
        total = total_row['count'] if total_row else 0
        
        # Get paginated results
        rows = await conn.fetch("""
            SELECT id, user_id, entry_date, content, mood, created_at, updated_at
            FROM journals
            WHERE user_id = $1
            ORDER BY entry_date DESC
            LIMIT $2 OFFSET $3
        """, user_id, page_size, offset)
        
        journals = [
            JournalResponse(
                id=str(row['id']),
                user_id=str(row['user_id']),
                entry_date=row['entry_date'].isoformat(),
                content=row['content'],
                mood=row['mood'],
                created_at=row['created_at'].isoformat(),
                updated_at=row['updated_at'].isoformat()
            )
            for row in rows
        ]
        
        return JournalListResponse(
            journals=journals,
            total=total,
            page=page,
            page_size=page_size
        )
