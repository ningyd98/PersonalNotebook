"""Phase 3C-hotfix v3.1: refusal/confidence unit tests"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.api.chat_routes import _evaluate_refusal, _extract_score
from app.schemas.schemas import Citation


def test_extract_score_dict():
    assert _extract_score({"score": 0.5}) == 0.5
    assert _extract_score({"rerank_score": 0.9}) == 0.9
    assert _extract_score({"rerank_score": 0.9, "score": 0.5}) == 0.9  # rerank priority
    assert _extract_score({}) == 0.0


def test_extract_score_pydantic():
    c = Citation(evidence_id="ev_0", source_type="text", document_id="00000000-0000-0000-0000-000000000001", filename="test.md", score=0.75, content_preview="test")
    assert _extract_score(c) == 0.75
    c2 = Citation(evidence_id="ev_1", source_type="text", document_id="00000000-0000-0000-0000-000000000001", filename="test.md", score=0.6, rerank_score=0.92, content_preview="test")
    assert _extract_score(c2) == 0.92


def test_extract_score_object():
    class Obj: pass
    o = Obj(); o.score = 0.5
    assert _extract_score(o) == 0.5
    o2 = Obj(); o2.rerank_score = 0.88
    assert _extract_score(o2) == 0.88


def test_no_evidence():
    r = _evaluate_refusal([], "some meaningful answer", [])
    assert r["should_refuse"] == True
    assert r["confidence"] == 0.0
    assert r["reason"] == "no_evidence"


def test_empty_answer():
    r = _evaluate_refusal([{"score": 0.9}], "", [{"score": 0.9}])
    assert r["should_refuse"] == True
    assert r["reason"] == "empty_answer"
    assert r["confidence"] == 0.0


def test_empty_answer_with_high_scores():
    r = _evaluate_refusal([{"score": 0.95}], "   ", [{"score": 0.95}])
    assert r["should_refuse"] == True
    assert r["reason"] == "empty_answer"


def test_no_verified_citations():
    r = _evaluate_refusal([{"score": 0.8}], "What is AI?", [])
    assert r["should_refuse"] == True
    assert r["reason"] == "no_verified_citations"


def test_low_score_dict_citation():
    r = _evaluate_refusal([{"score": 0.1}], "Some answer", [{"score": 0.1}])
    assert r["should_refuse"] == True
    assert r["reason"] == "low_confidence_citations"
    assert r["confidence"] <= 0.1


def test_high_score_dict_citation():
    r = _evaluate_refusal([{"score": 0.9}], "Deep learning uses neural networks", [{"rerank_score": 0.9}])
    assert r["should_refuse"] == False
    assert r["confidence"] > 0.6
    assert r["reason"] is None


def test_high_score_pydantic_citation():
    cit = Citation(evidence_id="ev_0", source_type="text", document_id="00000000-0000-0000-0000-000000000001", filename="t.md", rerank_score=0.85, score=0.7, content_preview="test")
    r = _evaluate_refusal([{"score": 0.9}], "Neural networks are a class of ML algorithms", [cit])
    assert r["should_refuse"] == False
    assert r["confidence"] > 0.6


def test_low_score_pydantic_citation():
    cit = Citation(evidence_id="ev_0", source_type="text", document_id="00000000-0000-0000-0000-000000000001", filename="t.md", score=0.15, content_preview="test")
    r = _evaluate_refusal([{"score": 0.2}], "Some answer text here", [cit])
    assert r["should_refuse"] == True
    assert r["reason"] == "low_confidence_citations"


def test_confidence_increases_with_score():
    r1 = _evaluate_refusal([{"score": 0.5}], "Good answer here", [{"score": 0.5}])
    r2 = _evaluate_refusal([{"score": 0.9}], "Good answer here", [{"score": 0.9}])
    assert r2["confidence"] > r1["confidence"]


def test_confidence_clamped():
    r = _evaluate_refusal([{"score": 1.0}], "Perfect answer right here yes", [{"score": 1.0}])
    assert 0.6 <= r["confidence"] <= 1.0
    assert r["should_refuse"] == False
