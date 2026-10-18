"""
Hybrid retrieval system with temporal and mood weighting.
"""

from typing import List, Dict, Optional, Tuple
import datetime as dt
import asyncpg
from database.connection import get_db_pool
from embeddings.embedder import get_embedder
import numpy as np
from math import exp
import json
import logging
import ast

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Hybrid retriever with vector similarity, temporal, and mood weighting."""
    
    def __init__(self):
        self.embedder = get_embedder()
        self.embedding_dim = self.embedder.get_dimension()
    
    def _parse_embedding(self, embedding_value) -> Optional[np.ndarray]:
        """
        Parse embedding from database into numeric numpy array.
        
        pgvector columns are returned as strings by asyncpg (e.g., "[0.1, 0.2, ...]" or "{0.1, 0.2, ...}").
        This function safely converts them to float arrays for NumPy operations.
        
        Args:
            embedding_value: Raw embedding value from database (string, list, or array)
            
        Returns:
            Optional[np.ndarray]: Parsed embedding as float32 array, or None if parsing fails
        """
        if embedding_value is None:
            return None
        
        try:
            # If already a list or array, convert directly
            if isinstance(embedding_value, (list, tuple)):
                arr = np.array(embedding_value, dtype=np.float32)
                if arr.ndim == 1 and len(arr) == self.embedding_dim:
                    return arr
                return None
            
            # If already a numpy array, validate and return
            if isinstance(embedding_value, np.ndarray):
                if embedding_value.ndim == 1 and len(embedding_value) == self.embedding_dim:
                    return embedding_value.astype(np.float32)
                return None
            
            # If string, parse it (pgvector returns strings)
            if isinstance(embedding_value, str):
                # Try JSON first (most common format: "[0.1, 0.2, ...]")
                try:
                    parsed = json.loads(embedding_value)
                    arr = np.array(parsed, dtype=np.float32)
                    if arr.ndim == 1 and len(arr) == self.embedding_dim:
                        return arr
                except (json.JSONDecodeError, ValueError):
                    pass
                
                # Try ast.literal_eval for Python literal format
                try:
                    parsed = ast.literal_eval(embedding_value)
                    arr = np.array(parsed, dtype=np.float32)
                    if arr.ndim == 1 and len(arr) == self.embedding_dim:
                        return arr
                except (ValueError, SyntaxError, TypeError):
                    # TypeError: "{...}" literal-evals to a Python set, which
                    # NumPy cannot convert; fall through to the Postgres branch.
                    pass
                
                # Try PostgreSQL array format: "{0.1, 0.2, ...}"
                if embedding_value.startswith('{') and embedding_value.endswith('}'):
                    try:
                        # Remove braces and split by comma
                        values = embedding_value[1:-1].split(',')
                        arr = np.array([float(v.strip()) for v in values], dtype=np.float32)
                        if arr.ndim == 1 and len(arr) == self.embedding_dim:
                            return arr
                    except (ValueError, AttributeError):
                        pass
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to parse embedding: {type(embedding_value).__name__}, error: {str(e)}")
            return None
    
    async def retrieve(
        self,
        user_id: str,
        query: str,
        query_embedding: Optional[List[float]] = None,
        limit: int = 10,
        time_filter: Optional[Dict] = None,
        mood_filter: Optional[str] = None,
        recency_weight: float = 0.3,
        mood_weight: float = 0.2
    ) -> List[Dict]:
        """
        Retrieve relevant journal entries using hybrid approach.
        
        Args:
            user_id: User ID for strict isolation
            query: User's query text
            query_embedding: Pre-computed query embedding (optional)
            limit: Maximum number of results
            time_filter: Dict with 'start_date' and/or 'end_date' (ISO format)
            mood_filter: Mood to filter or weight by
            recency_weight: Weight for recency scoring (0-1)
            mood_weight: Weight for mood matching (0-1)
            
        Returns:
            List[Dict]: Retrieved journal entries with scores
        """
        pool = await get_db_pool()
        
        # Generate query embedding if not provided
        if query_embedding is None:
            query_embedding = await self.embedder.embed_text(query)
        
        # Build SQL query with filters
        # Only use journal_embeddings (derived data) - ensures we use latest embeddings only
        base_query = """
            SELECT 
                j.id,
                j.user_id,
                j.content,
                j.mood,
                j.entry_date,
                j.created_at,
                je.embedding,
                je.metadata
            FROM journal_embeddings je
            INNER JOIN journals j ON j.id = je.journal_id
            WHERE je.user_id = $1
        """
        
        params = [user_id]
        param_idx = 2
        
        # Add time filters (use entry_date for date-based filtering)
        if time_filter:
            if "start_date" in time_filter:
                base_query += f" AND je.entry_date >= ${param_idx}::date"
                # Convert ISO string to date if needed
                start_date = time_filter["start_date"]
                if isinstance(start_date, str):
                    start_date = dt.datetime.fromisoformat(start_date.split('T')[0]).date()
                params.append(start_date)
                param_idx += 1
            if "end_date" in time_filter:
                base_query += f" AND je.entry_date <= ${param_idx}::date"
                # Convert ISO string to date if needed
                end_date = time_filter["end_date"]
                if isinstance(end_date, str):
                    end_date = dt.datetime.fromisoformat(end_date.split('T')[0]).date()
                params.append(end_date)
                param_idx += 1
        
        # Add mood filter if specified
        if mood_filter:
            base_query += f" AND j.mood = ${param_idx}"
            params.append(mood_filter)
            param_idx += 1
        
        # Ensure we have embeddings
        base_query += " AND je.embedding IS NOT NULL"
        
        # Order by similarity first (we'll re-rank)
        # Fix: Use correct parameter syntax - asyncpg uses $1, $2, etc.
        # Convert embedding list to string format for pgvector (same as storage)
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        base_query += f"""
            ORDER BY je.embedding <=> ${param_idx}::vector
            LIMIT ${param_idx + 1}
        """
        params.append(embedding_str)  # Pass as string (same format as storage)
        params.append(limit * 3)  # Get more candidates for re-ranking
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(base_query, *params)
        
        # Safety guard: if no rows retrieved, return early
        if not rows:
            logger.info(f"No journal entries retrieved for user {user_id[:8]}...")
            return []
        
        # Re-rank with temporal and mood weighting
        scored_results = []
        now = dt.datetime.now(dt.datetime.now().astimezone().tzinfo)
        valid_embeddings_count = 0
        skipped_embeddings_count = 0
        
        for row in rows:
            # Parse embedding from database (pgvector returns as string)
            # CRITICAL: Must parse before NumPy operations to avoid dtype errors
            parsed_embedding = self._parse_embedding(row['embedding'])
            
            # Vector similarity score (cosine similarity, higher is better)
            if parsed_embedding is not None:
                vec_sim = self._cosine_similarity(query_embedding, parsed_embedding)
                if vec_sim is not None:
                    valid_embeddings_count += 1
                else:
                    # Similarity calculation failed, skip this row
                    skipped_embeddings_count += 1
                    logger.debug(f"Skipping row {row['id']}: cosine similarity calculation failed")
                    continue
            else:
                # Embedding parsing failed, skip this row
                skipped_embeddings_count += 1
                logger.debug(f"Skipping row {row['id']}: embedding parsing failed (type: {type(row['embedding']).__name__})")
                continue
            
            # Temporal recency score (use entry_date for recency calculation)
            entry_date = row.get('entry_date')
            if entry_date:
                if isinstance(entry_date, str):
                    entry_date = dt.datetime.fromisoformat(entry_date.split('T')[0]).date()
                elif hasattr(entry_date, 'date'):
                    entry_date = entry_date.date() if hasattr(entry_date, 'date') else entry_date
                days_ago = (now.date() - entry_date).days
            else:
                # Fallback to created_at if entry_date not available
                created_at = row['created_at']
                if isinstance(created_at, str):
                    created_at = dt.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                days_ago = (now - created_at).days
            
            recency_score = exp(-days_ago / 30.0)  # Exponential decay over 30 days
            
            # Mood matching score
            mood_score = 1.0
            if mood_filter and row['mood']:
                mood_score = 2.0 if row['mood'].lower() == mood_filter.lower() else 0.5
            
            # Combined score
            final_score = (
                (1 - recency_weight - mood_weight) * vec_sim +
                recency_weight * recency_score +
                mood_weight * mood_score
            )
            
            # Use entry_date for date display
            entry_date = row.get('entry_date')
            if entry_date:
                if hasattr(entry_date, 'isoformat'):
                    date_str = entry_date.isoformat()
                elif hasattr(entry_date, 'date'):
                    date_str = entry_date.date().isoformat()
                else:
                    date_str = str(entry_date)
            else:
                # Fallback to created_at if entry_date not available
                created_at = row['created_at']
                date_str = created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at)
            
            scored_results.append({
                "id": str(row['id']),
                "user_id": str(row['user_id']),
                "content": row['content'],
                "mood": row['mood'],
                "entry_date": date_str,
                "created_at": row['created_at'].isoformat() if hasattr(row['created_at'], 'isoformat') else str(row['created_at']),
                "metadata": row['metadata'] or {},
                "score": final_score,
                "vector_sim": vec_sim,
                "recency_score": recency_score,
                "mood_score": mood_score
            })
        
        # Log embedding usage statistics
        logger.info(
            f"Embedding processing complete: {valid_embeddings_count} valid, "
            f"{skipped_embeddings_count} skipped, {len(scored_results)} scored results"
        )
        
        # Safety guard: if too few valid embeddings, return early
        # This prevents pattern queries from failing with insufficient data
        if valid_embeddings_count < 2:
            logger.warning(
                f"Insufficient valid embeddings ({valid_embeddings_count}) for reliable similarity scoring. "
                f"Returning {len(scored_results)} results without vector similarity weighting."
            )
        
        # Sort by final score and return top results
        scored_results.sort(key=lambda x: x['score'], reverse=True)
        return scored_results[:limit]
    
    def _cosine_similarity(self, vec1: List[float], vec2) -> Optional[float]:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: Query embedding (List[float])
            vec2: Journal embedding (List[float], np.ndarray, or None)
            
        Returns:
            Optional[float]: Cosine similarity (0-1), or None if calculation fails
        """
        try:
            # Convert inputs to numpy arrays with explicit dtype
            vec1_arr = np.array(vec1, dtype=np.float32)
            
            # vec2 should already be parsed (np.ndarray), but validate
            if vec2 is None:
                return None
            
            if isinstance(vec2, np.ndarray):
                vec2_arr = vec2.astype(np.float32)
            elif isinstance(vec2, (list, tuple)):
                vec2_arr = np.array(vec2, dtype=np.float32)
            else:
                # Invalid type (e.g., string) - should not happen if _parse_embedding worked
                logger.warning(f"Invalid vec2 type in cosine_similarity: {type(vec2).__name__}")
                return None
            
            # Validate dimensions
            if vec1_arr.ndim != 1 or vec2_arr.ndim != 1:
                logger.warning(f"Invalid vector dimensions: vec1={vec1_arr.ndim}D, vec2={vec2_arr.ndim}D")
                return None
            
            if len(vec1_arr) != len(vec2_arr):
                logger.warning(f"Dimension mismatch: vec1={len(vec1_arr)}, vec2={len(vec2_arr)}")
                return None
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1_arr, vec2_arr)
            norm1 = np.linalg.norm(vec1_arr)
            norm2 = np.linalg.norm(vec2_arr)
            
            # Handle zero vectors
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = float(dot_product / (norm1 * norm2))
            
            # Clamp to valid range (should be [-1, 1] for cosine, but ensure it)
            return max(-1.0, min(1.0, similarity))
            
        except Exception as e:
            # NEVER raise - always fail gracefully
            logger.warning(f"Cosine similarity calculation failed: {str(e)}")
            return None
    
    async def extract_temporal_filters(self, query: str) -> Optional[Dict]:
        """
        Extract temporal filters from query text.
        
        Args:
            query: User query text
            
        Returns:
            Optional[Dict]: Dict with 'start_date' and/or 'end_date' if found
        """
        query_lower = query.lower()
        now = dt.datetime.now()
        
        # Simple keyword-based extraction (can be enhanced with NLP)
        filters = {}
        
        # Month names
        months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        for month_name, month_num in months.items():
            if month_name in query_lower:
                year = now.year
                # Check if year is mentioned
                if str(year) in query or str(year - 1) in query:
                    if str(year - 1) in query:
                        year = year - 1
                
                start = dt.datetime(year, month_num, 1)
                if month_num == 12:
                    end = dt.datetime(year + 1, 1, 1) - dt.timedelta(days=1)
                else:
                    end = dt.datetime(year, month_num + 1, 1) - dt.timedelta(days=1)
                
                filters['start_date'] = start.isoformat()
                filters['end_date'] = end.isoformat()
                return filters
        
        # "Last week", "last month", etc.
        if 'last week' in query_lower:
            end = now
            start = now - dt.timedelta(days=7)
            filters['start_date'] = start.isoformat()
            filters['end_date'] = end.isoformat()
            return filters
        
        if 'last month' in query_lower:
            end = now
            start = now - dt.timedelta(days=30)
            filters['start_date'] = start.isoformat()
            filters['end_date'] = end.isoformat()
            return filters
        
        return None
    
    async def extract_mood_filter(self, query: str) -> Optional[str]:
        """
        Extract mood filter from query text.
        
        Args:
            query: User query text
            
        Returns:
            Optional[str]: Mood string if found
        """
        query_lower = query.lower()
        
        # Mood keywords
        mood_keywords = {
            'anxious': 'anxious',
            'anxiety': 'anxious',
            'happy': 'happy',
            'sad': 'sad',
            'depressed': 'sad',
            'angry': 'angry',
            'frustrated': 'angry',
            'excited': 'excited',
            'calm': 'calm',
            'stressed': 'stressed',
            'burned out': 'burned_out',
            'burnout': 'burned_out',
            'grateful': 'grateful',
            'gratitude': 'grateful'
        }
        
        for keyword, mood in mood_keywords.items():
            if keyword in query_lower:
                return mood
        
        return None


def get_retriever() -> HybridRetriever:
    """Get or create retriever instance."""
    return HybridRetriever()

