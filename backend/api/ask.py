"""
Memory query API endpoint using LangGraph agent.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from auth.supabase import get_current_user
from graph.memory_graph import get_memory_graph
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class AskRequest(BaseModel):
    """Request model for memory query."""
    question: str = Field(..., min_length=1, description="Question about your memories")


class EvidenceItem(BaseModel):
    """Evidence item from retrieved journal entries."""
    id: str
    date: str
    content: str
    mood: Optional[str]
    score: float


class AskResponse(BaseModel):
    """Response model for memory query."""
    answer: str
    evidence: List[EvidenceItem]
    intent: str
    retrieved_count: int
    llm_provider: str


@router.post("", response_model=AskResponse)
async def ask_question(
    request: AskRequest,
    http_request: Request,
    user_id: str = Depends(get_current_user)
):
    """
    Ask a question about your journal entries.
    
    Uses LangGraph agent pipeline to:
    1. Classify intent
    2. Retrieve relevant entries
    3. Analyze temporal patterns
    4. Synthesize evidence-based answer
    """
    request_id = getattr(http_request.state, "request_id", "unknown")
    
    if not request.question or not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty"
        )
    
    try:
        graph = get_memory_graph()
        result = await graph.process_query(user_id, request.question)
        
        # Log query processing (without sensitive content)
        logger.info(
            f"Query processed - request_id: {request_id}, "
            f"user_id: {user_id[:8]}..., "
            f"intent: {result.get('intent')}, "
            f"retrieved: {result.get('retrieved_count')}, "
            f"llm_provider: {result.get('llm_provider')}"
        )
        
        # Convert evidence to response model
        evidence_items = [
            EvidenceItem(
                id=item["id"],
                date=item.get("entry_date") or item.get("date", ""),  # Prefer entry_date
                content=item["content"],
                mood=item.get("mood"),
                score=item.get("score", 0.0)
            )
            for item in result.get("evidence", [])
        ]
        
        return AskResponse(
            answer=result["answer"],
            evidence=evidence_items,
            intent=result.get("intent", "recall"),
            retrieved_count=result.get("retrieved_count", 0),
            llm_provider=result.get("llm_provider", "unknown")
        )
        
    except Exception as e:
        logger.error(
            f"Error processing query - request_id: {request_id}, "
            f"user_id: {user_id[:8]}..., error: {str(e)}",
            exc_info=True  # Include full traceback in logs
        )
        
        # Return safe fallback response instead of 500 error
        # Never expose stack traces or internal errors to frontend
        return AskResponse(
            answer="I couldn't find enough relevant journal entries to answer that yet. Please try again later or write more entries related to this topic.",
            evidence=[],
            intent="recall",
            retrieved_count=0,
            llm_provider="unknown"
        )

