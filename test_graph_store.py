"""Unit tests for KnowledgeGraphStore CRUD, integrity validation, and serialization."""

import unittest
from crimegraph.data.generator import generate_synthetic_investigation_data
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.models.entities import EntityType, Person, Phone, Case
from crimegraph.models.relationships import Relationship, RelationshipType
from crimegraph.models.evidence import Evidence


class TestKnowledgeGraphStore(unittest.TestCase):
    """Test graph store operations, references, and integrity checks."""

    def setUp(self):
        self.graph = generate_synthetic_investigation_data()

    def test_synthetic_graph_integrity(self):
        report = self.graph.validate_integrity()
        self.assertTrue(report["is_valid"], f"Graph integrity errors: {report['errors']}")
        self.assertEqual(len(report["errors"]), 0)
        self.assertGreater(report["entity_count"], 20)
        self.assertGreater(report["relationship_count"], 15)
        self.assertGreater(report["evidence_count"], 10)

    def test_broken_relationship_source_detection(self):
        bad_store = KnowledgeGraphStore()
        bad_store.add_entity(Person(id="PERSON_001", name="Valid Person"))
        bad_store.add_relationship(
            Relationship(
                id="REL_BAD",
                source_id="PERSON_NON_EXISTENT",
                relationship=RelationshipType.USES,
                target_id="PERSON_001",
                confidence=0.9
            )
        )
        report = bad_store.validate_integrity()
        self.assertFalse(report["is_valid"])
        self.assertTrue(any("source_id" in err for err in report["errors"]))

    def test_broken_evidence_reference_detection(self):
        bad_store = KnowledgeGraphStore()
        bad_store.add_entity(Person(id="PERSON_001", name="Person 1"))
        bad_store.add_entity(Phone(id="PHONE_001", phone_number="12345"))
        bad_store.add_relationship(
            Relationship(
                id="REL_001",
                source_id="PERSON_001",
                relationship=RelationshipType.USES,
                target_id="PHONE_001",
                confidence=0.9,
                evidence_ids=["EVID_NON_EXISTENT"]
            )
        )
        report = bad_store.validate_integrity()
        self.assertFalse(report["is_valid"])
        self.assertTrue(any("EVID_NON_EXISTENT" in err for err in report["errors"]))

    def test_get_case_subgraph(self):
        subgraph = self.graph.get_case_subgraph("CASE_101")
        self.assertIn("nodes", subgraph)
        self.assertIn("edges", subgraph)
        self.assertEqual(subgraph["case_id"], "CASE_101")
        node_ids = {n["id"] for n in subgraph["nodes"]}
        self.assertIn("CASE_101", node_ids)
        self.assertIn("PERSON_017", node_ids)

    def test_get_entity_details(self):
        details = self.graph.get_entity_details("PERSON_017")
        self.assertEqual(details["id"], "PERSON_017")
        self.assertEqual(details["type"], EntityType.PERSON.value)
        self.assertIn("CASE_101", details["cases"])
        self.assertGreater(len(details["relationships"]), 0)
        self.assertGreater(len(details["evidence"]), 0)

    def test_serialization_roundtrip(self):
        data_dict = self.graph.to_dict()
        reconstructed = KnowledgeGraphStore.from_dict(data_dict)
        self.assertEqual(len(reconstructed.entities), len(self.graph.entities))
        self.assertEqual(len(reconstructed.relationships), len(self.graph.relationships))
        self.assertEqual(len(reconstructed.evidence), len(self.graph.evidence))
        report = reconstructed.validate_integrity()
        self.assertTrue(report["is_valid"])

    def test_cypher_export(self):
        cypher = self.graph.to_cypher_script()
        self.assertIn("MERGE (n:PERSON {id: 'PERSON_017'", cypher)
        self.assertIn("MERGE (a)-[r:USES", cypher)


if __name__ == "__main__":
    unittest.main()
