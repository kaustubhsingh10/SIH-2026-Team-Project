# CrimeGraph AI — REST API Integration Guide (Day 2)

This document provides the complete API specification and integration instructions for **Shruti (Frontend/Graph)** and **Aditya (AI Intelligence Layer)**.

---

## 1. Quickstart & Server Execution

### Starting the Backend Server
From the project root directory:
```powershell
python run_server.py
```
- **Base URL**: `http://127.0.0.1:8000`
- **Interactive Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc UI**: `http://127.0.0.1:8000/redoc`

### CORS Policy
CORS is configured to allow all origins (`*`), headers (`*`), and methods (`*`), making direct requests from frontend tools (React, Vite, Stitch, Next.js) seamless.

---

## 2. API Endpoints Reference

### A. Case Management APIs

#### 1. List All Cases
- **Method**: `GET`
- **Path**: `/api/cases`
- **Query Params**:
  - `status` *(optional, string)*: Filter by status (e.g. `ACTIVE`, `UNDER_INVESTIGATION`, `CLOSED`)
- **Response** `(200 OK)`:
  ```json
  [
    {
      "id": "CASE_101",
      "entity_type": "CASE",
      "case_number": "FIR-2026-DEL-101",
      "title": "Operation Midnight Shadow — Logistics Yard Cargo Hijack",
      "description": "Armed hijacking and diversion of multi-crore imported electronics...",
      "status": "UNDER_INVESTIGATION",
      "incident_date": "2026-06-14T22:30:00Z",
      "location_id": "LOC_001",
      "source_ids": ["DOC_CASE_101_FIR_REPORT.pdf", "EVID_101_01"]
    }
  ]
  ```

#### 2. Get Case Details
- **Method**: `GET`
- **Path**: `/api/cases/{case_id}`
- **Response** `(200 OK)`: Single Case JSON object.
- **Error** `(404 Not Found)`: `{"detail": "Case with ID 'CASE_999' not found"}`

#### 3. Get Case Subgraph (For Graph Visualization)
- **Method**: `GET`
- **Path**: `/api/cases/{case_id}/graph`
- **Response** `(200 OK)`:
  ```json
  {
    "case_id": "CASE_101",
    "nodes": [
      {
        "id": "PERSON_017",
        "entity_type": "PERSON",
        "name": "Aarav Verma",
        "aliases": ["A. Verma", "Shadow"],
        "confidence": 0.96
      }
    ],
    "edges": [
      {
        "id": "REL_001",
        "source_id": "PERSON_017",
        "relationship": "INVOLVED_IN",
        "target_id": "CASE_101",
        "confidence": 0.97,
        "evidence_ids": ["EVID_101_01"]
      }
    ]
  }
  ```

#### 4. Get Entities in Case
- **Method**: `GET`
- **Path**: `/api/cases/{case_id}/entities`
- **Query Params**:
  - `entity_type` *(optional, string)*: Filter by type (`PERSON`, `PHONE`, `VEHICLE`, etc.)
- **Response** `(200 OK)`: Array of Entity objects.

#### 5. Get Case Timeline
- **Method**: `GET`
- **Path**: `/api/cases/{case_id}/timeline`
- **Response** `(200 OK)`:
  ```json
  {
    "events": [
      {
        "id": "EVENT_001",
        "timestamp": "2026-06-14T21:45:00Z",
        "type": "VEHICLE_SIGHTING",
        "location_id": "LOC_001",
        "description": "White Bolero Pickup DL-01-AB-1234 observed exiting logistics yard gate."
      }
    ]
  }
  ```

#### 6. Cross-Case Connection Discovery (Main SIH Demo Endpoint)
- **Method**: `GET`
- **Path**: `/api/cases/connections`
- **Query Params**:
  - `case_a` *(required, string)*: e.g. `CASE_101`
  - `case_b` *(required, string)*: e.g. `CASE_204`
  - `max_depth` *(optional, int, default 6)*: Maximum hops
- **Response** `(200 OK)`:
  ```json
  {
    "connections": [
      {
        "case_a": "CASE_101",
        "case_b": "CASE_204",
        "shared_entities": ["PHONE_042"],
        "path": [
          "CASE_101",
          "PERSON_017",
          "PHONE_042",
          "PERSON_089",
          "CASE_204"
        ],
        "confidence": 0.93,
        "evidence_ids": [
          "EVID_042_01",
          "EVID_042_02",
          "EVID_101_01",
          "EVID_204_01"
        ]
      }
    ]
  }
  ```

---

### B. Entity Management APIs

#### 1. Search & Filter Entities
- **Method**: `GET`
- **Path**: `/api/entities`
- **Query Params**:
  - `type` *(optional)*: `PERSON`, `PHONE`, `VEHICLE`, `LOCATION`, `ORGANIZATION`, `ACCOUNT`, `EVENT`
  - `search` *(optional)*: Text query matching names, aliases, numbers, plates
  - `case_id` *(optional)*: Filter entities involved in a specific case
  - `min_confidence` *(optional, float)*: Confidence threshold (e.g. `0.90`)
- **Response** `(200 OK)`: Array of Entity objects.

#### 2. Get Entity Details & Evidence Provenance
- **Method**: `GET`
- **Path**: `/api/entities/{entity_id}`
- **Response** `(200 OK)`:
  ```json
  {
    "id": "PERSON_017",
    "type": "PERSON",
    "name": "Aarav Verma",
    "details": {
      "id": "PERSON_017",
      "entity_type": "PERSON",
      "name": "Aarav Verma",
      "aliases": ["A. Verma", "Shadow", "Rocky"],
      "age": 34,
      "gender": "Male",
      "confidence": 0.96
    },
    "relationships": [
      {
        "id": "REL_002",
        "source_id": "PERSON_017",
        "relationship": "USES",
        "target_id": "PHONE_042",
        "target_name": "+91-9876543210",
        "confidence": 0.95,
        "evidence_ids": ["EVID_042_01"]
      }
    ],
    "cases": ["CASE_101"],
    "evidence": [
      {
        "evidence_id": "EVID_042_01",
        "source_document_id": "DOC_CASE_101_FORENSIC_PHONE_EXTRACTION.pdf",
        "source_text": "Handset triage recovered encrypted messaging sessions...",
        "page_number": 7,
        "timestamp": "2026-06-17T10:00:00Z",
        "extraction_method": "DIGITAL_FORENSICS",
        "confidence": 0.95
      }
    ]
  }
  ```

#### 3. Get Entity Neighbors (1-Hop Adjacency)
- **Method**: `GET`
- **Path**: `/api/entities/{entity_id}/neighbors`
- **Query Params**:
  - `direction` *(optional, default "undirected")*: `"undirected"`, `"outgoing"`, or `"incoming"`
- **Response** `(200 OK)`:
  ```json
  {
    "entity_id": "PHONE_042",
    "neighbor_count": 2,
    "neighbors": [
      {
        "relationship": { "id": "REL_002", "relationship": "USES", ... },
        "neighbor": { "id": "PERSON_017", "name": "Aarav Verma", ... }
      }
    ]
  }
  ```

---

### C. Graph & Pathfinding APIs

#### 1. Full / Filtered Graph View
- **Method**: `GET`
- **Path**: `/api/graph`
- **Query Params**:
  - `entity_type`, `relationship_type`, `min_confidence`, `case_id`
- **Response** `(200 OK)`: `{ "nodes": [...], "edges": [...] }`

#### 2. Multi-Hop Path Query Between Any Two Entities
- **Method**: `GET`
- **Path**: `/api/paths`
- **Query Params**:
  - `source_id` *(required)*: e.g. `PERSON_017`
  - `target_id` *(required)*: e.g. `PERSON_089`
  - `max_depth` *(optional, default 6)*
  - `directed` *(optional, boolean, default false)*
- **Response** `(200 OK)`:
  ```json
  {
    "source_id": "PERSON_017",
    "target_id": "PERSON_089",
    "path_count": 1,
    "paths": [
      {
        "source_id": "PERSON_017",
        "target_id": "PERSON_089",
        "path": ["PERSON_017", "PHONE_042", "PERSON_089"],
        "shared_entities": ["PHONE_042"],
        "confidence": 0.93,
        "evidence_ids": ["EVID_042_01", "EVID_042_02"],
        "steps": [...],
        "hop_count": 2
      }
    ]
  }
  ```

---

### D. Evidence Provenance APIs

#### 1. List Evidence Records
- **Method**: `GET`
- **Path**: `/api/evidence`
- **Query Params**: `source_document_id`, `min_confidence`, `case_id`
- **Response** `(200 OK)`: Array of Evidence objects.

#### 2. Get Evidence Item
- **Method**: `GET`
- **Path**: `/api/evidence/{evidence_id}`
- **Response** `(200 OK)`:
  ```json
  {
    "evidence_id": "EVID_042_01",
    "source_document_id": "DOC_CASE_101_FORENSIC_PHONE_EXTRACTION.pdf",
    "source_text": "Handset triage recovered encrypted messaging sessions...",
    "page_number": 7,
    "timestamp": "2026-06-17T10:00:00Z",
    "extraction_method": "DIGITAL_FORENSICS",
    "confidence": 0.95,
    "confidence_tier": "High"
  }
  ```

---

## 3. Guide for Shruti (Frontend Integration)
- **Node Styling**: Use `entity_type` (`PERSON`, `PHONE`, `VEHICLE`, etc.) for node colors and icons.
- **Edge Labels**: Use `relationship` (`USES`, `INVOLVED_IN`, `SEEN_AT`) for edge badges and tooltips.
- **Confidence Badges**: Render green for `High` ($\ge 0.90$), amber for `Medium` ($0.70-0.89$), and grey for `Low` ($< 0.70$).
- **Evidence Modal**: Click an edge or node to open an evidence modal querying `/api/evidence/{evidence_id}`.

---

## 4. Guide for Aditya (AI Intelligence Layer)
- Query `/api/cases/connections` or `/api/paths` to retrieve structured, grounded evidence paths for reasoning.
- When generating narrative summaries or lead cards, cite the returned `evidence_ids` and exact `source_text` snippets.
- Use `confidence` to explicitly distinguish between hard evidence and speculative leads per [`PROJECT_SPEC.md`](file:///C:/Users/kaust/.gemini/antigravity/scratch/SIH-2026-Team-Project/PROJECT_SPEC.md) Safety Principles.
