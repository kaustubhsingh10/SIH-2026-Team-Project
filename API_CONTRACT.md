# CrimeGraph AI — API Contract

## 1. General Rules

All APIs return JSON.

All IDs are unique strings.

All timestamps use ISO 8601 format.

API changes must be documented before implementation.

Do not silently change existing response structures.

---

# 2. Document Extraction

## POST /api/extract

### Purpose

Extract entities, relationships and events from investigation text.

### Request

{
  "document_id": "DOC_001",
  "text": "Person A travelled in Vehicle V17..."
}

### Response

{
  "document_id": "DOC_001",

  "entities": [],

  "relationships": [],

  "events": [],

  "evidence": []
  ## Entity Object

{
  "id": "PERSON_017",
  "type": "PERSON",
  "name": "Person A",
  "confidence": 0.96,
  "evidence_ids": ["EVID_001"]
}
}
## Relationship Object

{
  "id": "REL_001",
  "source_id": "PERSON_017",
  "relationship": "USED",
  "target_id": "VEHICLE_042",
  "confidence": 0.94,
  "evidence_ids": ["EVID_002"]
}
## GET /api/cases/{case_id}/graph

Returns graph data for a case.
{
  "nodes": [],
  "edges": []
}
## GET /api/entities/{entity_id}

Returns entity details and relationships.
{
  "id": "PERSON_017",
  "type": "PERSON",
  "name": "Person A",
  "relationships": [],
  "cases": [],
  "evidence": []
}
## GET /api/cases/connections

Find relationships between cases.## GET /api/cases/connections

Find relationships between cases.
{
  "connections": [
    {
      "case_a": "CASE_101",
      "case_b": "CASE_204",

      "shared_entities": [
        "PHONE_042"
      ],

      "path": [
        "CASE_101",
        "PERSON_017",
        "PHONE_042",
        "PERSON_089",
        "CASE_204"
      ],

      "confidence": 0.91,

      "evidence_ids": [
        "EVID_021",
        "EVID_034"
      ]
      
---

# 7. Timeline API

```markdown
## GET /api/cases/{case_id}/timeline

Returns chronological events.
{
  "events": [
    {
      "id": "EVENT_001",
      "timestamp": "2026-08-12T18:30:00Z",
      "type": "VEHICLE_SIGHTING",
      "location_id": "LOC_007",
      "description": "Vehicle V17 observed."
    }
  ]
}## POST /api/reports

Generate an investigation report.

Request:

{
  "case_id": "CASE_101"
}

Response:

{
  "report_id": "REPORT_001",
  "status": "generated",
  "content": "..."
}
    }
  ]
}

---

# 🔥 The relationship between the 3 files

This is the easiest way to explain it to your team:

```text
PROJECT_SPEC.md
       ↓
WHAT are we building?
       ↓
DATA_SCHEMA.md
       ↓
WHAT information does it contain?
       ↓
API_CONTRACT.md
       ↓
HOW do our modules communicate?
Input
 ↓
Gemini
 ↓
Entity extraction
 ↓
Relationship extraction
 ↓
Confidence
 ↓
Evidence
 ↓
Validation
 ↓
Output
