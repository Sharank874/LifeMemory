"""Temporal and mood pattern analysis over journal entries."""
from datetime import datetime, timedelta, timezone

from analysis.pattern_analyzer import PatternAnalyzer


def entry(ts: datetime, mood=None):
    return {"created_at": ts.isoformat(), "mood": mood}


def test_empty_input():
    assert PatternAnalyzer.analyze_temporal_patterns([]) == {}
    assert PatternAnalyzer.find_most_productive_time([]) is None
    assert PatternAnalyzer.detect_mood_trends([])["trend"] == "insufficient_data"


def test_temporal_distribution_and_frequency():
    base = datetime(2026, 3, 2, 7, tzinfo=timezone.utc)  # a Monday
    entries = [entry(base + timedelta(days=i), "happy") for i in range(15)]  # 15 entries over 14 days
    p = PatternAnalyzer.analyze_temporal_patterns(entries)
    assert p["hourly_distribution"] == {7: 15}
    assert p["daily_distribution"]["Monday"] == 3
    assert p["entry_frequency"]["per_week"] == 15 / 14 * 7


def test_positive_moods_weigh_more_when_finding_best_time():
    day = datetime(2026, 3, 2, tzinfo=timezone.utc)
    entries = [entry(day.replace(hour=8), "happy"), entry(day.replace(hour=8), "excited"),
               entry(day.replace(hour=22), "sad"), entry(day.replace(hour=22), "tired"),
               entry(day.replace(hour=22), "sad")]
    best = PatternAnalyzer.find_most_productive_time(entries)
    assert best["hour"] == 8 and best["score"] == 4      # 2 positive x 2 beats 3 neutral x 1


def test_mood_trend_ignores_entries_older_than_window():
    now = datetime.now(timezone.utc)
    entries = [entry(now - timedelta(days=1), "calm"), entry(now - timedelta(days=2), "calm"),
               entry(now - timedelta(days=3), "stressed"), entry(now - timedelta(days=90), "sad")]
    t = PatternAnalyzer.detect_mood_trends(entries, days=30)
    assert t["total_entries"] == 3
    assert t["most_common_mood"] == "calm"
    assert t["trend"] == "stable"
    assert "sad" not in t["mood_distribution"]
