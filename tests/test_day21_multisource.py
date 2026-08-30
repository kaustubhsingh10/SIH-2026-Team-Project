"""Day 21 Multi-Source Integration & Pipeline Verification Tests.

Tests:
1. Source registration and loading (SyntheticDataSource, ManualDataSource, AdditionalSourceAdapter)
2. Normalization into canonical entity/relationship/evidence model
3. Deduplication without entity duplication
4. Multi-source provenance tracking
5. Source conflict detection and non-overwriting policy
6. Source failure and malformed data resilience
7. Canonical SIH path traversal (CASE_101 -> PERSON_017 -> PHONE_042 -> PERSON_089 -> CASE_204)
8. SafetyGuard non-guilt policy compliance
9. AI Investigator multi-source grounded reasoning
"""

import pytest
from pathlib import Path
from crimegraph.data.sources import (
    SyntheticDataSource,
    ManualDataSource,
    AdditionalSourceAdapter,
    MultiSourceIngestionPipeline
)
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.data.loader import load_dataset
from crimegraph.graph.traversal import find_paths_between_entities, find_cross_case_connections
from crimegraph.ai.investigator import AIInvestigator


def test_source_registration_and_loading():
    """Verify registration and loading from synthetic, manual, and additional connectors."""
    synthetic_src = SyntheticDataSource()
    manual_src = ManualDataSource({
        "nodes": [{"id": "PERSON_901", "name": "Officer Test", "type": "PERSON"}],
        "edges": [],
        "evidence": {}
    })
    adapter_src = AdditionalSourceAdapter("Telco CDR Feed", {
        "nodes": [{"id": "PHONE_901", "name": "+91-9000000000", "type": "PHONE"}],
        "edges": [],
        "evidence": {}
    })

    pipeline = MultiSourceIngestionPipeline()
    pipeline.register_source(synthetic_src)
    pipeline.register_source(manual_src)
    pipeline.register_source(adapter_src)

    assert len(pipeline.registered_sources) == 3
    store = pipeline.ingest_all()

    assert "PERSON_017" in store.entities
    assert "PERSON_901" in store.entities
    assert "PHONE_901" in store.entities


def test_normalization_and_provenance():
    """Verify that records are normalized and source provenance is preserved."""
    adapter_src = AdditionalSourceAdapter("Forensics Lab Extraction", {
        "nodes": [{"id": "PERSON_017", "name": "Aarav Verma", "type": "PERSON", "source_ids": ["DIGITAL_FORENSICS"]}],
        "edges": [{"source": "PERSON_017", "relationship": "USES", "target": "PHONE_042", "confidence": 0.95}],
        "evidence": {
            "EVID_TEST_01": {
                "evidence_id": "EVID_TEST_01",
                "source_document_id": "DOC_TEST_FORENSICS.pdf",
                "source_text": "Extracted triage data",
                "confidence": 0.95
            }
        }
    })

    pipeline = MultiSourceIngestionPipeline()
    pipeline.register_source(adapter_src)
    store = pipeline.ingest_all()

    assert "PERSON_017" in store.entities
    assert "EVID_TEST_01" in store.evidence
    ev = store.get_evidence("EVID_TEST_01")
    assert ev.source_document_id == "DOC_TEST_FORENSICS.pdf"
    assert ev.confidence == 0.95


def test_deduplication_without_duplicates():
    """Verify deduplication when the same entity is encountered from multiple sources."""
    src1 = AdditionalSourceAdapter("Source 1", {"nodes": [{"id": "PERSON_017", "name": "Aarav Verma"}]})
    src2 = AdditionalSourceAdapter("Source 2", {"nodes": [{"id": "PERSON_017", "name": "Aarav Verma"}]})

    pipeline = MultiSourceIngestionPipeline()
    pipeline.register_source(src1)
    pipeline.register_source(src2)
    store = pipeline.ingest_all()

    assert len([e for e in store.entities.values() if e.id == "PERSON_017"]) == 1


def test_conflicting_records_handling():
    """Verify conflict detection when sources report conflicting attributes."""
    src1 = AdditionalSourceAdapter("Source Alpha", {"nodes": [{"id": "PERSON_017", "name": "Aarav Verma"}]})
    src2 = AdditionalSourceAdapter("Source Beta", {"nodes": [{"id": "PERSON_017", "name": "Aarav V. Different"}]})

    pipeline = MultiSourceIngestionPipeline()
    pipeline.register_source(src1)
    pipeline.register_source(src2)
    store = pipeline.ingest_all()

    assert len(pipeline.conflicts) > 0
    conflict = pipeline.conflicts[0]
    assert conflict["entity_id"] == "PERSON_017"
    assert conflict["type"] == "NAME_CONFLICT"


def test_source_failure_resilience():
    """Verify that source failure or malformed records do not crash the pipeline."""
    class FailingSource(SyntheticDataSource):
        @property
        def name(self) -> str:
            return "Failing Source"
        def fetch_records(self):
            raise ConnectionError("External connector offline")

    valid_src = SyntheticDataSource()
    failing_src = FailingSource()

    pipeline = MultiSourceIngestionPipeline()
    pipeline.register_source(failing_src)
    pipeline.register_source(valid_src)

    store = pipeline.ingest_all()
    assert "PERSON_017" in store.entities
    failed_logs = [log for log in pipeline.provenance_log if log["status"] == "FAILED"]
    assert len(failed_logs) == 1
    assert failed_logs[0]["source"] == "Failing Source"


def test_canonical_sih_path_preservation():
    """Verify canonical SIH path CASE_101 -> PERSON_017 -> PHONE_042 -> PERSON_089 -> CASE_204."""
    store = load_dataset()
    connections = find_cross_case_connections(store, "CASE_101", "CASE_204")
    assert len(connections) > 0

    conn = connections[0]
    assert conn["case_a"] == "CASE_101"
    assert conn["case_b"] == "CASE_204"
    assert "PHONE_042" in conn["shared_entities"]
    assert conn["path"] == ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]
    assert conn["confidence"] >= 0.90


def test_safetyguard_non_guilt_compliance():
    """Verify SafetyGuard non-guilt policy on culpability queries."""
    store = load_dataset()
    investigator = AIInvestigator(store)

    res = investigator.query("Who is guilty in CASE_101?")
    assert res["query_type"] == "SAFETY_REFUSAL"
    assert res["confidence"] == 0.0
    assert "guilt" in res["disclaimer"].lower() or "culpability" in res["disclaimer"].lower()


def test_ai_investigator_grounded_reasoning():
    """Verify AI investigator multi-source grounded reasoning for cross-case query."""
    store = load_dataset()
    investigator = AIInvestigator(store)

    res = investigator.query("How are Case 101 and Case 204 connected?")
    assert res["query_type"] == "CROSS_CASE_CONNECTION"
    assert "PHONE_042" in res["shared_entities"]
    assert res["confidence"] >= 0.90
    assert len(res["evidence"]) > 0
