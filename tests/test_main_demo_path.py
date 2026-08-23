"""Verification tests for the Main Demo Connection Chain:

CASE_101 → PERSON_017 → PHONE_042 → PERSON_089 → CASE_204
"""

import unittest
from crimegraph.data.generator import generate_synthetic_investigation_data
from crimegraph.graph.traversal import find_paths_between_entities, find_cross_case_connections


class TestMainDemoPath(unittest.TestCase):
    """Verifies that the cross-case discovery path exists and has valid evidence provenance."""

    def setUp(self):
        self.graph = generate_synthetic_investigation_data()

    def test_demo_path_discovery(self):
        """Verifies graph traversal finds CASE_101 -> PERSON_017 -> PHONE_042 -> PERSON_089 -> CASE_204."""
        paths = find_paths_between_entities(self.graph, "CASE_101", "CASE_204", max_depth=5)
        self.assertGreater(len(paths), 0, "No path found between CASE_101 and CASE_204")

        # Find the primary demo path
        expected_path = ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]
        matching_paths = [p for p in paths if p["path"] == expected_path]
        self.assertEqual(len(matching_paths), 1, f"Expected path {expected_path} not found in {paths}")

        demo_path = matching_paths[0]

        # Verify bridge entity
        self.assertIn("PHONE_042", demo_path["shared_entities"])

        # Verify composite confidence
        self.assertGreaterEqual(demo_path["confidence"], 0.90)

        # Verify supporting evidence records exist
        self.assertIn("EVID_042_01", demo_path["evidence_ids"])
        self.assertIn("EVID_042_02", demo_path["evidence_ids"])

    def test_cross_case_connections_api(self):
        """Verifies output format matches API_CONTRACT.md Section 6."""
        connections = find_cross_case_connections(self.graph, "CASE_101", "CASE_204")
        self.assertGreater(len(connections), 0)

        primary = connections[0]
        self.assertEqual(primary["case_a"], "CASE_101")
        self.assertEqual(primary["case_b"], "CASE_204")
        self.assertEqual(primary["path"], ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"])
        self.assertIn("PHONE_042", primary["shared_entities"])
        self.assertGreaterEqual(primary["confidence"], 0.90)
        self.assertGreater(len(primary["evidence_ids"]), 0)

    def test_evidence_provenance_integrity(self):
        """Verifies that all evidence items along the path contain source quotes, docs, and high confidence."""
        demo_evidence_ids = ["EVID_101_01", "EVID_042_01", "EVID_042_02", "EVID_204_01"]

        for eid in demo_evidence_ids:
            ev = self.graph.get_evidence(eid)
            self.assertIsNotNone(ev, f"Evidence {eid} is missing from store")
            self.assertGreaterEqual(ev.confidence, 0.90, f"Evidence {eid} confidence too low")
            self.assertTrue(len(ev.source_text) > 20, f"Evidence {eid} source text too short")
            self.assertTrue(ev.source_document_id.startswith("DOC_"), f"Invalid source_document_id on {eid}")


if __name__ == "__main__":
    unittest.main()
