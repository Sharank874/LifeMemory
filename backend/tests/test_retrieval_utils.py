"""Pure helpers of the hybrid retriever: embedding parsing, cosine, query filters."""
import asyncio
import datetime as dt
import json

import numpy as np
import pytest

from retrieval.hybrid_retriever import HybridRetriever

DIM = 4


@pytest.fixture
def retriever():
    r = HybridRetriever.__new__(HybridRetriever)  # skip the embedding client
    r.embedding_dim = DIM
    return r


@pytest.mark.parametrize("raw", [
    json.dumps([0.1, 0.2, 0.3, 0.4]),        # pgvector text, JSON style
    "{0.1, 0.2, 0.3, 0.4}",                  # Postgres array literal
    [0.1, 0.2, 0.3, 0.4],                    # already a list
    np.array([0.1, 0.2, 0.3, 0.4]),          # already an array
])
def test_parse_embedding_accepts_every_storage_format(retriever, raw):
    out = retriever._parse_embedding(raw)
    assert out is not None and out.dtype == np.float32
    np.testing.assert_allclose(out, [0.1, 0.2, 0.3, 0.4], rtol=1e-6)


@pytest.mark.parametrize("raw", [None, "[1, 2]", "not a vector", [1, 2, 3, 4, 5], np.zeros((2, 2))])
def test_parse_embedding_rejects_bad_input(retriever, raw):
    assert retriever._parse_embedding(raw) is None


def test_cosine_similarity(retriever):
    a = [1.0, 0.0, 0.0, 0.0]
    assert retriever._cosine_similarity(a, np.array(a)) == pytest.approx(1.0)
    assert retriever._cosine_similarity(a, np.array([0, 1.0, 0, 0])) == pytest.approx(0.0)
    assert retriever._cosine_similarity(a, np.array([-1.0, 0, 0, 0])) == pytest.approx(-1.0)
    assert retriever._cosine_similarity(a, np.zeros(4)) == 0.0          # zero vector is safe
    assert retriever._cosine_similarity(a, np.ones(3)) is None           # dimension mismatch
    assert retriever._cosine_similarity(a, "oops") is None               # never raises


@pytest.mark.parametrize("query,mood", [
    ("Why was I so anxious before exams?", "anxious"),
    ("When do I feel burned out?", "burned_out"),
    ("What made me grateful last month?", "grateful"),
    ("What did I eat on Sunday?", None),
])
def test_mood_filter(retriever, query, mood):
    assert asyncio.run(retriever.extract_mood_filter(query)) == mood


def test_month_filter_covers_the_whole_month(retriever):
    f = asyncio.run(retriever.extract_temporal_filters("How was February?"))
    start = dt.datetime.fromisoformat(f["start_date"])
    end = dt.datetime.fromisoformat(f["end_date"])
    assert (start.month, start.day) == (2, 1)
    assert end.month == 2 and (end + dt.timedelta(days=1)).month == 3


def test_relative_filters(retriever):
    week = asyncio.run(retriever.extract_temporal_filters("what happened last week"))
    span = dt.datetime.fromisoformat(week["end_date"]) - dt.datetime.fromisoformat(week["start_date"])
    assert span == dt.timedelta(days=7)
    assert asyncio.run(retriever.extract_temporal_filters("tell me about my goals")) is None
