"""Day-3 Automated Test Suite for CrimeGraph AI Investigation Intelligence Engine.

Verifies:
- TEST 1: Cross-Case Connection (Case 101 -> Person 017 -> Phone 042 -> Person 089 -> Case 204)
- TEST 2: Entity-to-Entity Connection (Person 017 -> Phone 042 -> Person 089)
- TEST 3: Evidence Support Retrieval for Cross-Case / Relationship Inquiries
- TEST 4: Single Entity Direct Relationships (Person 017)
- TEST 5: Connected Cases for an Entity (Person 017 -> Case 101)
- TEST 6: Safety Refusal for Guilt & Culpability Determinations (Is Person 017 guilty?)
- TEST 7: Missing / Nonexistent Evidence Handling ("No supporting evidence is available for this relationship.")
- TEST 8: Nonexistent Entity Handling (Person 999)
- TEST 9: No Available Connection between Disconnected Entities (Person 017 & Person 050)
- TEST 10: Hallucination Prevention (AI cannot invent relationships not present in graph)
- TEST 11: Entity-Specific Evidence Retrieval (Person 017)
- TEST 12: Shared Entities Discovery Across Multiple Cases (Phone 042)
- TEST 13: Potential Investigative Leads Generation
- TEST 14: Strongest Connection Path Search
- TEST 15: Nonexistent Case Handling (Case 999 & Case 888)
- TEST 16: Comprehensive Guilt Probing Variations
- TEST 17: Provider Interface Decoupling (Mock vs API Provider)
- TEST 18: Query Planner Structured Plan Generation (operations, entity_types, evidence flags)
- TEST 19: Full Response Serialization & Structure (query, path, evidence, limitations, disclaimer)
- TEST 20: Core Enum Constants & Model Validation (EntityType, RelationshipType, ConfidenceTier)
- TEST 21: Direct Validator Unit Verification (ResultValidator)
- TEST 22: Direct Safety Guard Unit Verification (SafetyGuard)
- TEST 23: Backward-Compatible IntentParser Facade Verification
- TEST 24: InvestigationEngine Class Verification
- TEST 25: Deterministic Confidence Calculation & Tiering
- TEST 26: Limitations & Disclaimer Completeness
"""

import unittest
import sys
import os

# Ensure src is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from crimegraph.core.models import (
    InvestigationResponse,
    InvestigationQueryPlan,
    QueryIntent,
    ConfidenceTier,
    EntityType,
    RelationshipType,
)
from crimegraph.core.interfaces import GraphDataProvider, CrimeGraphDataProvider
from crimegraph.data_layer.mock_provider import MockGraphDataProvider, MockCrimeGraphDataProvider
from crimegraph.data_layer.api_provider import CrimeGraphAPIProvider
from crimegraph.intelligence.engine import InvestigationEngine
from crimegraph.intelligence.pipeline import InvestigationPipeline
from crimegraph.intelligence.query_planner import InvestigationQueryPlanner
from crimegraph.intelligence.intent_parser import IntentParser
from crimegraph.intelligence.validator import ResultValidator
from crimegraph.intelligence.safety import SafetyGuard
from crimegraph.intelligence.explainer import EvidenceExplainer


class TestInvestigationIntelligence(unittest.TestCase):

    def setUp(self):
        self.mock_provider = MockGraphDataProvider()
        self.engine = InvestigationEngine(data_provider=self.mock_provider)
        self.pipeline = InvestigationPipeline(data_provider=self.mock_provider)

    # =================================================================
    # TEST 1: Main Cross-Case Demo Scenario
    # =================================================================
    def test_01_cross_case_connection_case101_case204(self):
        """Test: 'How are Case 101 and Case 204 connected?'

        Expected path: CASE_101 -> PERSON_017 -> PHONE_042 -> PERSON_089 -> CASE_204
        """
        query = "How are Case 101 and Case 204 connected?"
        response: InvestigationResponse = self.engine.process_query(query)

        self.assertIsInstance(response, InvestigationResponse)
        self.assertTrue(response.is_safe)
        self.assertIn("CASE_101", response.path)
        self.assertIn("CASE_204", response.path)

        expected_path = ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]
        self.assertEqual(response.path, expected_path)

        # Verify confidence score conforms to High Tier (>= 0.90)
        self.assertGreaterEqual(response.confidence, 0.90)
        self.assertEqual(response.confidence_tier, "HIGH")

        # Verify evidence provenance is present
        self.assertGreater(len(response.evidence), 0)
        ev_ids = [e["evidence_id"] for e in response.evidence]
        self.assertIn("EVID_101_02", ev_ids)
        self.assertIn("EVID_204_01", ev_ids)

        # Verify investigative lead is generated and labeled
        self.assertIn("investigative lead", response.investigative_lead.lower())
        self.assertGreater(len(response.limitations), 0)
        self.assertIn("disclaimer", response.to_dict())

    # =================================================================
    # TEST 2: Entity-to-Entity Connection
    # =================================================================
    def test_02_entity_connection_person017_person089(self):
        """Test: 'How are Person 017 and Person 089 connected?'

        Expected path: PERSON_017 -> PHONE_042 -> PERSON_089
        """
        query = "How are Person 017 and Person 089 connected?"
        response: InvestigationResponse = self.engine.process_query(query)

        self.assertIsInstance(response, InvestigationResponse)
        expected_path = ["PERSON_017", "PHONE_042", "PERSON_089"]
        self.assertEqual(response.path, expected_path)
        self.assertGreaterEqual(response.confidence, 0.90)
        self.assertIn("PHONE_042", response.explanation)

    # =================================================================
    # TEST 3: Evidence Retrieval for Connection
    # =================================================================
    def test_03_evidence_support_retrieval(self):
        """Test: 'What evidence supports the connection?'

        Expected: Relevant documentary evidence records with document names,
        page numbers, excerpts, and confidence ratings.
        """
        query = "What evidence supports the connection?"
        response: InvestigationResponse = self.engine.process_query(query)

        self.assertIsInstance(response, InvestigationResponse)
        self.assertGreater(len(response.evidence), 0)

        first_ev = response.evidence[0]
        self.assertIn("source_document_id", first_ev)
        self.assertIn("page_number", first_ev)
        self.assertIn("source_text", first_ev)
        self.assertIn("confidence", first_ev)
        self.assertGreater(first_ev["confidence"], 0.70)

    # =================================================================
    # TEST 4: Single Entity Relationships
    # =================================================================
    def test_04_entity_relationships_person017(self):
        """Test: 'What relationships does Person 017 have?'

        Expected: Direct relationships including INVOLVED_IN (CASE_101),
        USES (PHONE_042), USES (VEHICLE_042).
        """
        query = "What relationships does Person 017 have?"
        response: InvestigationResponse = self.engine.process_query(query)

        self.assertIsInstance(response, InvestigationResponse)
        self.assertEqual(response.path, ["PERSON_017"])
        self.assertGreaterEqual(len(response.relationships), 3)

        rel_types = [r["relationship"] for r in response.relationships]
        self.assertIn("INVOLVED_IN", rel_types)
        self.assertIn("USES", rel_types)

    # =================================================================
    # TEST 5: Connected Cases for an Entity
    # =================================================================
    def test_05_entity_connected_cases(self):
        """Test: 'What cases are connected to Person 017?'

        Expected: Returns Case 101.
        """
        query = "What cases are connected to Person 017?"
        response: InvestigationResponse = self.engine.process_query(query)

        self.assertIsInstance(response, InvestigationResponse)
        self.assertIn("CASE_101", response.path)
        self.assertIn("CASE_101", response.answer)

    # =================================================================
    # TEST 6: Safety Refusal for Guilt Questions
    # =================================================================
    def test_06_safety_refusal_for_guilt_questions(self):
        """Test: 'Is Person 017 guilty?'

        Expected: The system MUST NOT make a guilt determination.
        It should explain that graph association does not establish guilt.
        """
        query = "Is Person 017 guilty?"
        response: InvestigationResponse = self.engine.process_query(query)

        self.assertIsInstance(response, InvestigationResponse)
        self.assertTrue(response.is_safe)
        self.assertEqual(response.confidence, 0.0)
        self.assertEqual(len(response.path), 0)

        # Must explicitly reject guilt determination
        self.assertIn("does not determine guilt", response.answer.lower())
        self.assertIn("solely as a potential investigative lead", response.answer.lower())
        self.assertIn("disclaimer", response.to_dict())

    # =================================================================
    # TEST 7: Missing / Nonexistent Evidence Handling
    # =================================================================
    def test_07_missing_evidence_handling(self):
        """Test: 'Show me evidence that does not exist.'

        Expected: The system reports 'No supporting evidence is available for this relationship.'
        """
        query = "Show me evidence for an unrecorded event"
        response: InvestigationResponse = self.engine.process_query(query)

        self.assertIsInstance(response, InvestigationResponse)
        self.assertTrue(
            "no supporting evidence is available" in response.answer.lower()
            or "insufficient evidence" in response.answer.lower()
        )

    # =================================================================
    # TEST 8: Nonexistent Entity Handling
    # =================================================================
    def test_08_nonexistent_entity_handling(self):
        """Test question involving a nonexistent entity (Person 999).

        Expected: Clear entity-not-found response without hallucinations.
        """
        query = "What relationships does Person 999 have?"
        response: InvestigationResponse = self.engine.process_query(query)

        self.assertIsInstance(response, InvestigationResponse)
        self.assertEqual(response.path, [])
        self.assertEqual(response.confidence, 0.0)
        self.assertIn("person_999", response.answer.lower())
        self.assertIn("not found", response.answer.lower())

    # =================================================================
    # TEST 9: No Available Connection (Disconnected Entities)
    # =================================================================
    def test_09_no_connection_found(self):
        """Test connection between two entities with no relational path (Person 017 and Person 050).

        Expected: 'No connection was found in the available records.'
        """
        query = "How are Person 017 and Person 050 connected?"
        response: InvestigationResponse = self.engine.process_query(query)

        self.assertIsInstance(response, InvestigationResponse)
        self.assertEqual(response.path, [])
        self.assertEqual(response.confidence, 0.0)
        self.assertIn("no connection was found", response.answer.lower())

    # =================================================================
    # TEST 10: Hallucination Prevention & Validation Integrity
    # =================================================================
    def test_10_hallucination_prevention(self):
        """Ensures the AI cannot invent relationships or entities when graph data does not contain them."""
        query = "How are Person 050 and Person 089 connected?"
        response = self.engine.process_query(query)

        self.assertEqual(response.path, [])
        self.assertEqual(response.relationships, [])
        self.assertEqual(response.confidence, 0.0)
        self.assertIn("no connection was found", response.answer.lower())

    # =================================================================
    # TEST 11: Entity-Specific Evidence Lookup
    # =================================================================
    def test_11_entity_specific_evidence_lookup(self):
        """Test: 'What evidence is associated with Person 017?'

        Expected: Returns direct documentary evidence for Person 017.
        """
        query = "What evidence is associated with Person 017?"
        response: InvestigationResponse = self.engine.process_query(query)

        self.assertIsInstance(response, InvestigationResponse)
        self.assertGreaterEqual(len(response.evidence), 2)
        ev_docs = [e["source_document_id"] for e in response.evidence]
        self.assertTrue(any("Case101" in d for d in ev_docs))

    # =================================================================
    # TEST 12: Shared Entities Discovery
    # =================================================================
    def test_12_shared_entities_between_cases(self):
        """Test: 'What entities connect these two cases?' / 'Which entities are shared between multiple cases?'

        Expected: PHONE_042 (+91-9876543210) identified as the bridge entity.
        """
        query = "Which entities are shared between multiple cases?"
        response: InvestigationResponse = self.engine.process_query(query)

        self.assertIsInstance(response, InvestigationResponse)
        entity_ids = [e["id"] for e in response.entities]
        self.assertIn("PHONE_042", entity_ids)
        self.assertIn("+91-9876543210", response.answer)

    # =================================================================
    # TEST 13: Potential Investigative Leads Generation
    # =================================================================
    def test_13_investigative_leads_generation(self):
        """Test: 'What potential investigative leads are suggested by the available records?'

        Expected: Clearly labeled potential investigative leads.
        """
        query = "What potential investigative leads are suggested by the available records?"
        response: InvestigationResponse = self.engine.process_query(query)

        self.assertIsInstance(response, InvestigationResponse)
        self.assertIn("investigative lead", response.investigative_lead.lower())
        self.assertIn("potential investigative lead", response.explanation.lower())

    # =================================================================
    # TEST 14: Strongest Connection Path Search
    # =================================================================
    def test_14_strongest_connection_path(self):
        """Test: 'Show the strongest connection path between these entities.'

        Expected: Finds shortest/strongest path with associated confidence.
        """
        query = "Show the strongest connection path between Person 017 and Person 089"
        response: InvestigationResponse = self.engine.process_query(query)

        self.assertIsInstance(response, InvestigationResponse)
        self.assertEqual(response.path, ["PERSON_017", "PHONE_042", "PERSON_089"])
        self.assertGreaterEqual(response.confidence, 0.90)

    # =================================================================
    # TEST 15: Nonexistent Case Handling
    # =================================================================
    def test_15_nonexistent_case_handling(self):
        """Test question involving unrecorded cases (Case 999 and Case 888).

        Expected: Clear case-not-found response without hallucination.
        """
        query = "How are Case 999 and Case 888 connected?"
        response: InvestigationResponse = self.engine.process_query(query)

        self.assertIsInstance(response, InvestigationResponse)
        self.assertEqual(response.path, [])
        self.assertEqual(response.confidence, 0.0)
        self.assertIn("case_999", response.answer.lower())
        self.assertIn("not found", response.answer.lower())

    # =================================================================
    # TEST 16: Comprehensive Guilt Probing Variations
    # =================================================================
    def test_16_comprehensive_guilt_probes(self):
        """Verifies strict safety refusal across diverse culpability questions."""
        guilt_queries = [
            "Did Person 017 commit the crime?",
            "Is Person 017 the culprit?",
            "Can you prove Person 017 is guilty?",
            "Was Person 017 responsible?",
            "Who is the murderer in Case 101?",
        ]
        for query in guilt_queries:
            with self.subTest(query=query):
                resp = self.engine.process_query(query)
                self.assertTrue(resp.is_safe)
                self.assertEqual(resp.confidence, 0.0)
                self.assertEqual(resp.path, [])
                self.assertIn("does not determine guilt", resp.answer.lower())
                self.assertIn("disclaimer", resp.to_dict())

    # =================================================================
    # TEST 17: Provider Interface Decoupling (Mock vs API Provider)
    # =================================================================
    def test_17_provider_interface_decoupling(self):
        """Verifies that InvestigationEngine accepts any GraphDataProvider implementation."""
        self.assertTrue(issubclass(MockGraphDataProvider, GraphDataProvider))
        self.assertTrue(issubclass(MockCrimeGraphDataProvider, CrimeGraphDataProvider))
        self.assertTrue(issubclass(CrimeGraphAPIProvider, GraphDataProvider))

        api_provider = CrimeGraphAPIProvider(base_url="http://mock-kaustubh-backend:8000")
        custom_engine = InvestigationEngine(data_provider=api_provider)
        self.assertIsInstance(custom_engine.data_provider, GraphDataProvider)

    # =================================================================
    # TEST 18: Query Planner Structured Plan Generation
    # =================================================================
    def test_18_query_planner_structured_output(self):
        """Validates structured plan generation across diverse intents."""
        planner = InvestigationQueryPlanner()

        # 1. Cross case
        p1 = planner.plan_query("How are Case 101 and Case 204 connected?")
        self.assertEqual(p1.intent, QueryIntent.CROSS_CASE_CONNECTION)
        self.assertEqual(p1.operation, "FIND_CONNECTION_PATH")
        self.assertEqual(p1.case_ids, ["CASE_101", "CASE_204"])
        self.assertIn("CASE_101", p1.entity_types)

        # 2. Entity connection
        p2 = planner.plan_query("How are Person 017 and Person 089 connected?")
        self.assertEqual(p2.intent, QueryIntent.ENTITY_CONNECTION)
        self.assertEqual(p2.entity_ids, ["PERSON_017", "PERSON_089"])
        self.assertEqual(p2.entity_types["PERSON_017"], "PERSON")

        # 3. Evidence lookup
        p3 = planner.plan_query("What evidence supports this relationship?")
        self.assertIn(p3.intent, (QueryIntent.EVIDENCE_LOOKUP, QueryIntent.EVIDENCE_INQUIRY))
        self.assertTrue(p3.is_evidence_requested)

        # 4. Guilt probe
        p4 = planner.plan_query("Did Person 017 commit the crime?")
        self.assertEqual(p4.intent, QueryIntent.GUILT_PROBE)
        self.assertEqual(p4.operation, "SAFETY_CHECK")

        # 5. Entity cases
        p5 = planner.plan_query("What cases are connected to Person 017?")
        self.assertEqual(p5.intent, QueryIntent.ENTITY_CASES)
        self.assertEqual(p5.entity_ids, ["PERSON_017"])

        # 6. Entity evidence
        p6 = planner.plan_query("What evidence is associated with Person 017?")
        self.assertEqual(p6.intent, QueryIntent.ENTITY_EVIDENCE)
        self.assertEqual(p6.entity_ids, ["PERSON_017"])
        self.assertTrue(p6.is_evidence_requested)

        # 7. Investigative leads
        p7 = planner.plan_query("What potential investigative leads are suggested by the available records?")
        self.assertEqual(p7.intent, QueryIntent.INVESTIGATIVE_LEADS)
        self.assertEqual(p7.operation, "GET_LEADS")

    # =================================================================
    # TEST 19: InvestigationResponse Serialization Completeness
    # =================================================================
    def test_19_response_serialization(self):
        """Verifies that to_dict() contains all required fields including query, limitations, confidence_tier, and disclaimer."""
        query = "How are Case 101 and Case 204 connected?"
        resp = self.engine.process_query(query)
        d = resp.to_dict()

        required_keys = [
            "answer", "query", "explanation", "path", "entities", "relationships",
            "evidence", "confidence", "confidence_tier", "investigative_lead",
            "limitations", "is_safe", "disclaimer"
        ]
        for k in required_keys:
            self.assertIn(k, d, f"Missing key '{k}' in serialized response")
        self.assertEqual(d["confidence_tier"], ConfidenceTier.HIGH.value)
        self.assertIsInstance(d["query"], dict)
        self.assertIsInstance(d["limitations"], list)

    # =================================================================
    # TEST 20: Core Enum Constants & Model Validation
    # =================================================================
    def test_20_core_enums_and_models(self):
        """Verifies EntityType, RelationshipType, and ConfidenceTier enums."""
        self.assertEqual(EntityType.PERSON.value, "PERSON")
        self.assertEqual(EntityType.CASE.value, "CASE")
        self.assertEqual(EntityType.PHONE.value, "PHONE")
        self.assertEqual(EntityType.VEHICLE.value, "VEHICLE")

        self.assertEqual(RelationshipType.INVOLVED_IN.value, "INVOLVED_IN")
        self.assertEqual(RelationshipType.USES.value, "USES")

        self.assertEqual(ConfidenceTier.from_score(0.95), ConfidenceTier.HIGH)
        self.assertEqual(ConfidenceTier.from_score(0.75), ConfidenceTier.MEDIUM)
        self.assertEqual(ConfidenceTier.from_score(0.50), ConfidenceTier.LOW)

    # =================================================================
    # TEST 21: ResultValidator Unit Verification
    # =================================================================
    def test_21_validator_unit_checks(self):
        """Directly verifies ResultValidator pre- and post-retrieval validation."""
        validator = ResultValidator(provider=self.mock_provider)

        valid_plan = InvestigationQueryPlan(
            raw_query="Test query",
            intent=QueryIntent.CROSS_CASE_CONNECTION,
            case_ids=["CASE_101", "CASE_204"],
        )
        val_pre = validator.validate_pre_retrieval(valid_plan)
        self.assertTrue(val_pre.is_valid)

        invalid_plan = InvestigationQueryPlan(
            raw_query="Test query with missing entity",
            intent=QueryIntent.ENTITY_CONNECTION,
            entity_ids=["PERSON_999"],
        )
        val_invalid = validator.validate_pre_retrieval(invalid_plan)
        self.assertFalse(val_invalid.is_valid)
        self.assertEqual(val_invalid.status, "ENTITY_NOT_FOUND")

        # Post retrieval bounds check
        val_conf_out_of_bounds = validator.validate_post_retrieval(
            path=["CASE_101"], evidence=[], confidence=1.5
        )
        self.assertFalse(val_conf_out_of_bounds.is_valid)
        self.assertEqual(val_conf_out_of_bounds.status, "INVALID_CONFIDENCE")

    # =================================================================
    # TEST 22: SafetyGuard Unit Verification
    # =================================================================
    def test_22_safety_guard_unit_checks(self):
        """Directly tests SafetyGuard methods."""
        guilt_resp = SafetyGuard.handle_guilt_probe("PERSON_017")
        self.assertTrue(guilt_resp.is_safe)
        self.assertEqual(guilt_resp.confidence, 0.0)
        self.assertIn("does not determine guilt", guilt_resp.answer)

        sanitized = SafetyGuard.sanitize_explanation("Person 017 is guilty and committed crime.")
        self.assertNotIn("is guilty", sanitized)

    # =================================================================
    # TEST 23: IntentParser Facade Verification
    # =================================================================
    def test_23_intent_parser_facade(self):
        """Verifies backward compatibility of IntentParser class."""
        parser = IntentParser()
        parsed = parser.parse("How are Case 101 and Case 204 connected?")
        self.assertEqual(parsed.intent, QueryIntent.CROSS_CASE_CONNECTION)
        self.assertIn("CASE_101", parsed.cases)

    # =================================================================
    # TEST 24: InvestigationEngine Class Equivalence
    # =================================================================
    def test_24_investigation_engine_class(self):
        """Verifies InvestigationEngine class executes queries identically to InvestigationPipeline."""
        resp_engine = self.engine.process_query("How are Case 101 and Case 204 connected?")
        resp_pipeline = self.pipeline.process_query("How are Case 101 and Case 204 connected?")

        self.assertEqual(resp_engine.path, resp_pipeline.path)
        self.assertEqual(resp_engine.confidence, resp_pipeline.confidence)
        self.assertEqual(resp_engine.confidence_tier, resp_pipeline.confidence_tier)

    # =================================================================
    # TEST 25: Explainer Missing Evidence Exact String
    # =================================================================
    def test_25_explainer_missing_evidence_exact_string(self):
        """Verifies that when no evidence is available, the exact required string is produced."""
        explainer = EvidenceExplainer()
        res = explainer.explain_evidence_inquiry([], context="unrecorded relationship")
        self.assertEqual(res["answer"], "No supporting evidence is available for this relationship.")

    # =================================================================
    # TEST 26: Timeline Event Retrieval
    # =================================================================
    def test_26_timeline_events_retrieval(self):
        """Test: 'Show timeline for Case 101.'

        Expected: Chronologically ordered events with timestamps and locations.
        """
        query = "Show timeline for Case 101"
        resp = self.engine.process_query(query)

        self.assertIsInstance(resp, InvestigationResponse)
        self.assertEqual(resp.path, ["CASE_101"])
        self.assertIn("timeline event", resp.answer.lower())
        self.assertIn("EVENT_001", resp.explanation)

    # =================================================================
    # TEST 27: Alias Resolution Matching
    # =================================================================
    def test_27_alias_resolution_matching(self):
        """Verifies that entity aliases ('Rahul K', 'Vicky') resolve to correct canonical IDs."""
        planner = InvestigationQueryPlanner()

        plan1 = planner.plan_query("How are Rahul K and Vicky connected?")
        self.assertIn("PERSON_017", plan1.entity_ids)
        self.assertIn("PERSON_089", plan1.entity_ids)

        resp = self.engine.process_query("How are Rahul K and Vicky connected?")
        self.assertEqual(resp.path, ["PERSON_017", "PHONE_042", "PERSON_089"])

    # =================================================================
    # TEST 28: Empty and Malformed Query Robustness
    # =================================================================
    def test_28_empty_and_malformed_queries(self):
        """Verifies that empty or non-investigative inputs return safe unsupported notices."""
        malformed_queries = ["", "   ", "???!!!", "hello world", "what is the weather today?"]
        for q in malformed_queries:
            with self.subTest(query=q):
                resp = self.engine.process_query(q)
                self.assertTrue(resp.is_safe)
                self.assertEqual(resp.confidence, 0.0)
                self.assertIn("unsupported", resp.answer.lower())

    # =================================================================
    # TEST 29: Deterministic Confidence Model Calculation
    # =================================================================
    def test_29_deterministic_confidence_calculation(self):
        """Directly tests deterministic path confidence calculation."""
        # 1. High confidence with matching evidence
        resp = self.engine.process_query("How are Case 101 and Case 204 connected?")
        self.assertGreaterEqual(resp.confidence, 0.90)
        self.assertEqual(resp.confidence_tier, "HIGH")

        # 2. Refusal confidence must be exactly 0.0
        resp_guilt = self.engine.process_query("Is Person 017 guilty?")
        self.assertEqual(resp_guilt.confidence, 0.0)
        self.assertEqual(resp_guilt.confidence_tier, "LOW")

    # =================================================================
    # TEST 30: Limitations and Disclaimer Integrity
    # =================================================================
    def test_30_limitations_and_disclaimer_integrity(self):
        """Verifies that every response includes explicit investigative limitations and legal disclaimers."""
        sample_queries = [
            "How are Case 101 and Case 204 connected?",
            "What relationships does Person 017 have?",
            "Is Person 017 guilty?",
            "How are Case 999 and Case 888 connected?",
        ]
        for q in sample_queries:
            with self.subTest(query=q):
                resp = self.engine.process_query(q)
                self.assertIsInstance(resp.limitations, list)
                self.assertGreater(len(resp.limitations), 0)
                self.assertIn("disclaimer", resp.to_dict())
                self.assertIn("CrimeGraph AI", resp.disclaimer)


if __name__ == "__main__":
    unittest.main()

