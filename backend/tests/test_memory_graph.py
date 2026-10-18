"""
The LangGraph workflow end to end, with a fake retriever and a fake LLM.

Checks the parts that make the assistant "evidence-grounded":
intent validation, the evidence gate, and the refusal when nothing relevant
is retrieved.
"""
import asyncio

import pytest

import graph.memory_graph as mg


class FakeRetriever:
    def __init__(self, entries):
        self.entries = entries
        self.calls = []

    async def extract_temporal_filters(self, q):
        return None

    async def extract_mood_filter(self, q):
        return "anxious" if "anxious" in q else None

    async def retrieve(self, **kw):
        self.calls.append(kw)
        assert kw["user_id"] == "user-a"           # retrieval is always scoped to the caller
        return self.entries


def make_graph(monkeypatch, entries, llm_replies):
    replies = iter(llm_replies)

    async def fake_llm(messages):
        return next(replies)

    monkeypatch.setattr(mg, "get_retriever", lambda: FakeRetriever(entries))
    monkeypatch.setattr(mg, "generate_with_fallback", fake_llm)
    monkeypatch.setattr(mg, "get_llm_provider", lambda: "fake")
    return mg.MemoryGraph()


ENTRIES = [
    {"id": "1", "content": "Presentation next week, cannot sleep.", "mood": "anxious",
     "entry_date": "2026-09-01", "created_at": "2026-09-01T22:10:00+00:00", "score": 0.82},
    {"id": "2", "content": "Walk in the park helped me calm down.", "mood": "calm",
     "entry_date": "2026-09-03", "created_at": "2026-09-03T13:00:00+00:00", "score": 0.61},
]


def test_answer_is_built_from_retrieved_entries(monkeypatch):
    g = make_graph(monkeypatch, ENTRIES, ["reflection", "You get anxious before deadlines [1]."])
    out = asyncio.run(g.process_query("user-a", "Why am I anxious?"))
    assert out["intent"] == "reflection"
    assert out["retrieved_count"] == 2
    assert "anxious" in out["answer"]
    assert g.retriever.calls[0]["mood_filter"] == "anxious"


def test_unknown_intent_falls_back_to_recall(monkeypatch):
    g = make_graph(monkeypatch, ENTRIES, ["DROP TABLE journals", "Here is what happened."])
    out = asyncio.run(g.process_query("user-a", "what happened?"))
    assert out["intent"] == "recall"


def test_no_evidence_means_no_made_up_answer(monkeypatch):
    g = make_graph(monkeypatch, [], ["recall", "THIS SHOULD NOT BE USED"])
    out = asyncio.run(g.process_query("user-a", "What did I do in Paris?"))
    assert out["retrieved_count"] == 0
    assert "don't have enough" in out["answer"]
    assert "SHOULD NOT" not in out["answer"]
    assert out["evidence"] == []


@pytest.mark.parametrize("passed,expected", [(True, "continue"), (False, "insufficient")])
def test_routing_after_safety_check(monkeypatch, passed, expected):
    g = make_graph(monkeypatch, ENTRIES, [])
    assert g._route_after_safety_check({"safety_check_passed": passed}) == expected
