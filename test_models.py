"""Unit tests for CrimeGraph data models and schema constraints.

Tests conformance to DATA_SCHEMA.md.
"""

import unittest
from pydantic import ValidationError
from crimegraph.models.entities import (
    EntityType,
    Person,
    Phone,
    Vehicle,
    Location,
    Organization,
    Account,
    Case,
    Event,
)
from crimegraph.models.relationships import Relationship, RelationshipType
from crimegraph.models.evidence import Evidence


class TestDataSchemaModels(unittest.TestCase):
    """Test schema validity, required fields, and boundary constraints."""

    def test_person_model_valid(self):
        person = Person(
            id="PERSON_017",
            name="Aarav Verma",
            aliases=["Shadow", "A. Verma"],
            age=34,
            gender="Male",
            phone_ids=["PHONE_042"],
            vehicle_ids=["VEHICLE_017"],
            address_ids=["LOC_003"],
            source_ids=["DOC_001"],
            confidence=0.96
        )
        self.assertEqual(person.id, "PERSON_017")
        self.assertEqual(person.entity_type, EntityType.PERSON.value)
        self.assertEqual(person.confidence, 0.96)
        self.assertIn("Shadow", person.aliases)

    def test_person_confidence_bounds(self):
        with self.assertRaises(ValidationError):
            Person(id="PERSON_ERR", name="Test", confidence=1.5)
        with self.assertRaises(ValidationError):
            Person(id="PERSON_ERR", name="Test", confidence=-0.1)

    def test_phone_model_valid(self):
        phone = Phone(
            id="PHONE_042",
            phone_number="+91-9876543210",
            owner_ids=["PERSON_017", "PERSON_089"],
            source_ids=["DOC_002"],
            confidence=0.94
        )
        self.assertEqual(phone.entity_type, EntityType.PHONE.value)
        self.assertEqual(phone.phone_number, "+91-9876543210")
        self.assertEqual(len(phone.owner_ids), 2)

    def test_vehicle_model_valid(self):
        vehicle = Vehicle(
            id="VEHICLE_017",
            registration_number="DL-01-AB-1234",
            type="Pickup Truck",
            owner_id="PERSON_017",
            source_ids=["DOC_003"],
            confidence=0.95
        )
        self.assertEqual(vehicle.entity_type, EntityType.VEHICLE.value)
        self.assertEqual(vehicle.registration_number, "DL-01-AB-1234")

    def test_location_model_valid(self):
        location = Location(
            id="LOC_001",
            name="ICD Tughlakabad",
            latitude=28.5024,
            longitude=77.2912,
            address="New Delhi"
        )
        self.assertEqual(location.entity_type, EntityType.LOCATION.value)
        self.assertAlmostEqual(location.latitude, 28.5024)

    def test_account_model_valid(self):
        account = Account(
            id="ACC_001",
            account_type="BANK_ACCOUNT",
            identifier="HDFC-0019283746",
            owner_id="PERSON_017"
        )
        self.assertEqual(account.entity_type, EntityType.ACCOUNT.value)
        self.assertEqual(account.identifier, "HDFC-0019283746")

    def test_case_model_valid(self):
        case = Case(
            id="CASE_101",
            case_number="FIR-2026-DEL-101",
            title="Operation Midnight Shadow",
            status="UNDER_INVESTIGATION",
            incident_date="2026-06-14T22:30:00Z",
            location_id="LOC_001"
        )
        self.assertEqual(case.entity_type, EntityType.CASE.value)
        self.assertEqual(case.case_number, "FIR-2026-DEL-101")

    def test_event_model_valid(self):
        event = Event(
            id="EVENT_001",
            event_type="VEHICLE_SIGHTING",
            timestamp="2026-06-14T21:45:00Z",
            location_id="LOC_001",
            description="Vehicle observed",
            source_id="EVID_001"
        )
        self.assertEqual(event.entity_type, EntityType.EVENT.value)
        self.assertEqual(event.event_type, "VEHICLE_SIGHTING")

    def test_evidence_model_and_tiers(self):
        ev_high = Evidence(
            evidence_id="EVID_001",
            source_document_id="DOC_001",
            source_text="Test source statement",
            page_number=1,
            confidence=0.95
        )
        self.assertEqual(ev_high.confidence_tier, "High")

        ev_med = Evidence(
            evidence_id="EVID_002",
            source_document_id="DOC_002",
            source_text="Medium confidence source",
            confidence=0.75
        )
        self.assertEqual(ev_med.confidence_tier, "Medium")

        ev_low = Evidence(
            evidence_id="EVID_003",
            source_document_id="DOC_003",
            source_text="Low confidence source",
            confidence=0.55
        )
        self.assertEqual(ev_low.confidence_tier, "Low")

    def test_relationship_model_valid(self):
        rel = Relationship(
            id="REL_001",
            source_id="PERSON_017",
            relationship=RelationshipType.USES,
            target_id="PHONE_042",
            confidence=0.95,
            evidence_ids=["EVID_001"]
        )
        self.assertEqual(rel.relationship, RelationshipType.USES)
        self.assertEqual(rel.source_id, "PERSON_017")
        self.assertEqual(rel.target_id, "PHONE_042")


if __name__ == "__main__":
    unittest.main()
