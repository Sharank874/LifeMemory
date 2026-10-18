"""
Pattern analysis utilities for temporal and behavioral patterns.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import statistics


class PatternAnalyzer:
    """Analyze patterns in journal entries."""
    
    @staticmethod
    def analyze_temporal_patterns(entries: List[Dict]) -> Dict:
        """
        Analyze temporal patterns in journal entries.
        
        Args:
            entries: List of journal entries with created_at timestamps
            
        Returns:
            Dict: Temporal pattern analysis
        """
        if not entries:
            return {}
        
        patterns = {
            "hourly_distribution": defaultdict(int),
            "daily_distribution": defaultdict(int),
            "monthly_distribution": defaultdict(int),
            "mood_by_time": defaultdict(lambda: defaultdict(int)),
            "entry_frequency": {
                "total": len(entries),
                "per_week": 0,
                "per_month": 0
            }
        }
        
        timestamps = []
        for entry in entries:
            try:
                created_at = datetime.fromisoformat(entry["created_at"].replace('Z', '+00:00'))
                timestamps.append(created_at)
                
                patterns["hourly_distribution"][created_at.hour] += 1
                patterns["daily_distribution"][created_at.strftime("%A")] += 1
                patterns["monthly_distribution"][created_at.strftime("%B")] += 1
                
                if entry.get("mood"):
                    patterns["mood_by_time"][created_at.hour][entry["mood"]] += 1
                    
            except Exception:
                continue
        
        if timestamps:
            # Calculate frequency
            if len(timestamps) > 1:
                timestamps.sort()
                time_span_days = (timestamps[-1] - timestamps[0]).days
                if time_span_days > 0:
                    patterns["entry_frequency"]["per_week"] = (len(timestamps) / time_span_days) * 7
                    patterns["entry_frequency"]["per_month"] = (len(timestamps) / time_span_days) * 30
        
        # Convert defaultdicts to regular dicts
        patterns["hourly_distribution"] = dict(patterns["hourly_distribution"])
        patterns["daily_distribution"] = dict(patterns["daily_distribution"])
        patterns["monthly_distribution"] = dict(patterns["monthly_distribution"])
        patterns["mood_by_time"] = {
            k: dict(v) for k, v in patterns["mood_by_time"].items()
        }
        
        return patterns
    
    @staticmethod
    def find_most_productive_time(entries: List[Dict], positive_moods: List[str] = None) -> Optional[Dict]:
        """
        Find time periods when user is most productive/positive.
        
        Args:
            entries: List of journal entries
            positive_moods: List of mood labels considered positive
            
        Returns:
            Optional[Dict]: Time period with highest positive activity
        """
        if positive_moods is None:
            positive_moods = ["happy", "excited", "grateful", "calm", "productive"]
        
        positive_moods_lower = [m.lower() for m in positive_moods]
        
        hourly_scores = defaultdict(int)
        for entry in entries:
            try:
                created_at = datetime.fromisoformat(entry["created_at"].replace('Z', '+00:00'))
                hour = created_at.hour
                
                if entry.get("mood") and entry["mood"].lower() in positive_moods_lower:
                    hourly_scores[hour] += 2  # Higher weight for positive moods
                else:
                    hourly_scores[hour] += 1
                    
            except Exception:
                continue
        
        if not hourly_scores:
            return None
        
        best_hour = max(hourly_scores.items(), key=lambda x: x[1])[0]
        
        return {
            "hour": best_hour,
            "time_range": f"{best_hour}:00 - {best_hour + 1}:00",
            "score": hourly_scores[best_hour]
        }
    
    @staticmethod
    def detect_mood_trends(entries: List[Dict], days: int = 30) -> Dict:
        """
        Detect mood trends over time.
        
        Args:
            entries: List of journal entries
            days: Number of days to analyze
            
        Returns:
            Dict: Mood trend analysis
        """
        now = datetime.now(datetime.now().astimezone().tzinfo)
        cutoff = now - timedelta(days=days)
        
        recent_entries = []
        for entry in entries:
            try:
                created_at = datetime.fromisoformat(entry["created_at"].replace('Z', '+00:00'))
                if created_at >= cutoff and entry.get("mood"):
                    recent_entries.append({
                        "date": created_at,
                        "mood": entry["mood"]
                    })
            except Exception:
                continue
        
        if not recent_entries:
            return {"trend": "insufficient_data"}
        
        # Simple trend: count mood changes
        mood_counts = defaultdict(int)
        for entry in recent_entries:
            mood_counts[entry["mood"]] += 1
        
        most_common = max(mood_counts.items(), key=lambda x: x[1])[0] if mood_counts else None
        
        return {
            "trend": "stable" if len(set(e["mood"] for e in recent_entries)) <= 2 else "varied",
            "most_common_mood": most_common,
            "mood_distribution": dict(mood_counts),
            "total_entries": len(recent_entries)
        }


def get_pattern_analyzer() -> PatternAnalyzer:
    """Get pattern analyzer instance."""
    return PatternAnalyzer()

