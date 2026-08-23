"""AI Components Test Suite for CrimeGraph AI."""

import pytest
from crimegraph.data.loader import load_dataset
from crimegraph.ai.extractor import DocumentExtractor
from crimegraph.ai.resolution import EntityResolver
from crimegraph.ai.investigator import AIInvestigator
from crimegraph.reports.reporter import InvestigationReporter


@pytest.fixture
def graph_store():
    return load_dataset()


def test_document_extractor():
    extractor = DocumentExtractor()
    doc_id = "DOC_TEST_99"
    text = "Rahul Kumar operated vehicle MH-04-XY-9999 and called +91-9876543210."
    res = extractor.extract_from_document(doc_id, text)

    assert res["document_id"] == doc_id
    assert len(res["entities"]) >= 2
    assert len(res["evidence"]) >= 2


def test_entity_resolver(graph_store):
    resolver = EntityResolver(graph_store)
    candidates = resolver.find_pending_matches()
    assert len(candidates) >= 1

    cand = candidates[0]
    assert "entity_a" in cand
    assert "entity_b" in cand
    assert "similarity" in cand
    assert cand["status"] == "PENDING_REVIEW"


def test_ai_investigator(graph_store):
    investigator = AIInvestigator(graph_store)

    # Test cross case query
    res = investigator.query("Find connections between Case 101 and Case 204")
    assert res["query_type"] == "CROSS_CASE_CONNECTION"
    assert res["confidence"] >= 0.90

    # Test person connections query
    res_p = investigator.query("Who is connected to Person 17?")
    assert res_p["query_type"] == "ENTITY_CONNECTIONS"
    assert res_p["entity_id"] == "PERSON_017"

    # Test shared entities query
    res_s = investigator.query("Which entities appear in multiple cases?")
    assert res_s["query_type"] == "SHARED_ENTITIES"


def test_investigation_reporter(graph_store):
    reporter = InvestigationReporter(graph_store)
    rep = reporter.generate_report("CASE_101")
    assert rep["case_id"] == "CASE_101"
    assert rep["status"] == "generated"
    assert "LEGAL & SAFETY DISCLAIMER" in rep["content"]
