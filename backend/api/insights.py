"""
Insights API endpoint for summary statistics and patterns.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Optional
from auth.supabase import get_current_user, verify_token, get_supabase_rest_headers
from config.settings import get_settings
from datetime import datetime, timedelta
from collections import defaultdict
import httpx

router = APIRouter()


class InsightSummary(BaseModel):
    """Summary insights response."""
    total_entries: int
    entries_this_week: int
    entries_this_month: int
    mood_distribution: Dict[str, int]
    most_active_day: Optional[str]
    most_active_time: Optional[str]
    recent_themes: List[str]


@router.get("/summary", response_model=InsightSummary)
async def get_insights_summary(
    user_id: str = Depends(get_current_user),
    token_data: dict = Depends(verify_token)
):
    """
    Get summary insights about journal entries.
    
    Returns statistics and patterns from the user's journal history.
    """
    settings = get_settings()
    headers = get_supabase_rest_headers(token_data["token"])
    
    try:
        # Get all journals for user via REST API
        rest_url = f"{settings.SUPABASE_URL}/rest/v1/journals"
        response = httpx.get(
            rest_url,
            headers=headers,
            params={
                "user_id": f"eq.{user_id}",
                "select": "*",
                "order": "created_at.asc"
            },
            timeout=10.0
        )
        response.raise_for_status()
        journals_data = response.json()
        
        if not journals_data:
            return InsightSummary(
                total_entries=0,
                entries_this_week=0,
                entries_this_month=0,
                mood_distribution={},
                most_active_day=None,
                most_active_time=None,
                recent_themes=[]
            )
        
        journals = journals_data
        total_entries = len(journals)
        
        # Calculate time-based stats
        now = datetime.now(datetime.now().astimezone().tzinfo)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        entries_this_week = 0
        entries_this_month = 0
        mood_distribution = defaultdict(int)
        day_of_week_count = defaultdict(int)
        hour_count = defaultdict(int)
        
        for journal in journals:
            try:
                created_at = datetime.fromisoformat(journal["created_at"].replace('Z', '+00:00'))
                
                if created_at >= week_ago:
                    entries_this_week += 1
                if created_at >= month_ago:
                    entries_this_month += 1
                
                if journal.get("mood"):
                    mood_distribution[journal["mood"]] += 1
                
                day_of_week_count[created_at.strftime("%A")] += 1
                hour_count[created_at.hour] += 1
                
            except Exception:
                continue
        
        # Find most active day and time
        most_active_day = max(day_of_week_count.items(), key=lambda x: x[1])[0] if day_of_week_count else None
        most_active_hour = max(hour_count.items(), key=lambda x: x[1])[0] if hour_count else None
        most_active_time = f"{most_active_hour}:00" if most_active_hour is not None else None
        
        # Extract recent themes (simplified - can be enhanced with NLP)
        recent_themes = []
        recent_journals = [j for j in journals if datetime.fromisoformat(j["created_at"].replace('Z', '+00:00')) >= week_ago]
        if recent_journals:
            # Simple keyword extraction (can be enhanced)
            all_text = " ".join([j.get("content", "")[:200] for j in recent_journals[:10]])
            # This is a placeholder - in production, use proper topic modeling
            recent_themes = ["Recent activity"] if all_text else []
        
        return InsightSummary(
            total_entries=total_entries,
            entries_this_week=entries_this_week,
            entries_this_month=entries_this_month,
            mood_distribution=dict(mood_distribution),
            most_active_day=most_active_day,
            most_active_time=most_active_time,
            recent_themes=recent_themes
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating insights: {str(e)}"
        )

