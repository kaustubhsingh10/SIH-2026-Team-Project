# SIH-2026-Team-Project: CrimeGraph AI Investigation Platform

> "Smart India Hackathon 2026 project repository — collaborative development, source code, documentation, and resources for our team’s solution.”

CrimeGraph AI is an AI-powered investigative intelligence platform that converts fragmented investigation records into an evidence-linked knowledge graph.

---

## 1. Day-3 Architecture & 8-Step Modular Orchestration

```text
                     Investigator Question
                               ↓
             1. Question Understanding & Query Planning
             (Intent, Entity/Case IDs, Operation, Evidence Flag)
                               ↓
             2. Pre-Retrieval Grounding & Safety Gate
             (Entity/Case Existence & Guilt Probe Gating)
                               ↓
             3. Graph Retrieval via GraphDataProvider
             (MockGraphDataProvider / CrimeGraphAPIProvider)
                               ↓
             4. Path & Relationship Analysis
             (Shortest Path, Strongest Path, Adjacency Traversal)
                               ↓
             5. Evidence Retrieval & Provenance
             (Document ID, Excerpt, Page, Timestamp, Extraction Method)
                               ↓
             6. Post-Retrieval Validation & Confidence Calculation
             (Deterministic Rule-Based Confidence & Integrity Validation)
                               ↓
             7. Evidence-Grounded Explanation & Leads
             (Structured Facts → Grounded Synthesizer / Optional LLM)
                               ↓
             8. Structured Investigation Result
             (InvestigationResponse conforming to API_CONTRACT.md)
```

The data/graph layer is the single source of truth. The AI reasoning engine **never invents graph relationships, entities, dates, or evidence**.

---

## 2. Directory Structure

```text
SIH-2026-Team-Project/
├── PROJECT_SPEC.md                      # Source of truth: Project scope & MVP
├── DATA_SCHEMA.md                       # Source of truth: Data schemas
├── API_CONTRACT.md                      # Source of truth: API contracts
├── README.md                            # Documentation & integration guide
├── demo.py                              # Live interactive CLI demo script (13 queries)
├── run_server.py                        # FastAPI backend server
├── src/
│   └── crimegraph/
│       ├── api/                         # FastAPI routes & endpoints
│       ├── core/
│       │   ├── models.py                # Data models, QueryIntent, InvestigationQueryPlan, Response & Result
│       │   └── interfaces.py            # Abstract GraphDataProvider / CrimeGraphDataProvider
│       ├── data_layer/
│       │   ├── mock_provider.py         # MockGraphDataProvider (Synthetic SIH Demo dataset fallback)
│       │   └── api_provider.py          # CrimeGraphAPIProvider (Kaustubh's HTTP backend client)
│       ├── intelligence/
│       │   ├── engine.py                # Primary Day-3 InvestigationEngine entrypoint
│       │   ├── pipeline.py              # Modular investigation pipeline orchestrator
│       │   ├── query_planner.py         # Structured query planner & entity extractor
│       │   ├── intent_parser.py         # Backward-compatible intent parser facade
│       │   ├── validator.py             # Pre- and post-retrieval grounding & bounds validator
│       │   ├── safety.py                # Guilt refusal & ethical safety guardrails
│       │   └── explainer.py             # Evidence-grounded explanation & lead generator
│       ├── graph/                       # Graph store & traversal algorithms
│       └── models/                      # Entity & Relationship schemas
├── web/                                 # Frontend Web UI (HTML, CSS, JS)
└── tests/
    └── test_investigation_intelligence.py # Automated test suite (30 comprehensive test cases)
```

---

## 3. Supported Day-3 Investigation Queries

The engine natively supports all core SIH demonstration queries:

1. **Cross-Case Connection**:
   - Query: `"How are Case 101 and Case 204 connected?"`
   - Discovered Path: `CASE_101 → PERSON_017 → PHONE_042 → PERSON_089 → CASE_204`
   - Confidence: `0.92 (HIGH Tier)`
2. **Entity-to-Entity Connection**:
   - Query: `"How are Person 017 and Person 089 connected?"`
   - Discovered Path: `PERSON_017 → PHONE_042 → PERSON_089`
3. **Cross-Case Shared Entities**:
   - Query: `"What entities connect these two cases?"` / `"Which entities are shared between multiple cases?"`
   - Result: `PHONE_042` (+91-9876543210)
4. **Evidence Provenance Lookup**:
   - Query: `"What evidence supports this relationship?"` / `"What evidence supports the connection?"`
   - Result: Full documentary citations with document IDs, page numbers, text excerpts, and confidence ratings.
5. **Strongest Path Analysis**:
   - Query: `"What is the strongest connection path between these entities?"`
   - Result: Shortest/highest-confidence path traversal (`PERSON_017 → PHONE_042 → PERSON_089`).
6. **Direct Entity Relationships**:
   - Query: `"What relationships does Person 017 have?"`
   - Result: Documented graph edges (`INVOLVED_IN`, `USES` Phone, `USES` Vehicle).
7. **Safety & Guilt Determination Refusal**:
   - Query: `"Is Person 017 guilty?"` / `"Did Person 017 commit the crime?"`
   - Result: Standardized safety refusal explaining that graph associations are solely leads for human investigation and do not establish guilt.
8. **Entity-Specific Evidence**:
   - Query: `"What evidence is associated with Person 017?"`
   - Result: Documentary records directly referencing `PERSON_017`.
9. **Entity-Connected Cases**:
   - Query: `"What cases are connected to Person 017?"`
   - Result: `CASE_101`.
10. **Potential Investigative Leads Generation**:
    - Query: `"What potential investigative leads are suggested by the available records?"`
    - Result: Auditable leads clearly marked as `POTENTIAL INVESTIGATIVE LEAD`.
11. **Timeline / Chronological Events**:
    - Query: `"Show events around the incident."` / `"Show timeline for Case 101."`
    - Result: Chronologically ordered incident events with timestamps and locations.
12. **Missing Evidence & Nonexistent Entity / Case Safety**:
    - Query: `"What relationships does Person 999 have?"` / `"How are Case 999 and Case 888 connected?"`
    - Result: Clean entity-not-found / case-not-found response without hallucinations.

---

## 4. Frontend Integration Guide (For Shruti)

The AI Investigation Engine returns a standardized `InvestigationResponse` object conforming strictly to `API_CONTRACT.md`.

### Response Schema:
```json
{
  "answer": "A potential cross-case connection was identified between CASE_101 and CASE_204 via the investigative path: CASE_101 -> PERSON_017 -> PHONE_042 -> PERSON_089 -> CASE_204 with HIGH confidence (0.92).",
  "query": {
    "raw_query": "How are Case 101 and Case 204 connected?",
    "intent": "CROSS_CASE_CONNECTION",
    "operation": "FIND_CONNECTION_PATH",
    "case_ids": ["CASE_101", "CASE_204"],
    "entity_ids": [],
    "entity_types": {
      "CASE_101": "CASE",
      "CASE_204": "CASE"
    },
    "is_evidence_requested": false
  },
  "path": [
    "CASE_101",
    "PERSON_017",
    "PHONE_042",
    "PERSON_089",
    "CASE_204"
  ],
  "entities": [
    { "id": "PERSON_017", "type": "PERSON", "name": "Rahul Kumar", "confidence": 0.96 },
    { "id": "PHONE_042", "type": "PHONE", "name": "+91-9876543210", "confidence": 0.94 },
    { "id": "PERSON_089", "type": "PERSON", "name": "Vikram Singh", "confidence": 0.95 }
  ],
  "relationships": [
    { "id": "REL_001", "source_id": "PERSON_017", "relationship": "INVOLVED_IN", "target_id": "CASE_101", "confidence": 0.95 },
    { "id": "REL_002", "source_id": "PERSON_017", "relationship": "USES", "target_id": "PHONE_042", "confidence": 0.94 },
    { "id": "REL_006", "source_id": "PERSON_089", "relationship": "USES", "target_id": "PHONE_042", "confidence": 0.91 },
    { "id": "REL_007", "source_id": "PERSON_089", "relationship": "INVOLVED_IN", "target_id": "CASE_204", "confidence": 0.96 }
  ],
  "evidence": [
    {
      "evidence_id": "EVID_101_02",
      "source_document_id": "Case101_CDR_Analysis.pdf",
      "source_text": "Call Detail Records confirm Person 017 operated Phone 042 (+91-9876543210) during the incident timeframe.",
      "page_number": 4,
      "timestamp": "2026-08-11T14:20:00Z",
      "extraction_method": "AI_EXTRACTION",
      "confidence": 0.94
    },
    {
      "evidence_id": "EVID_204_01",
      "source_document_id": "Case204_Telecom_Report.pdf",
      "source_text": "Subscriber verification records indicate Phone 042 was actively used by Person 089 (Vikram Singh) to coordinate logistics in Case 204.",
      "page_number": 5,
      "timestamp": "2026-08-15T11:30:00Z",
      "extraction_method": "AI_EXTRACTION",
      "confidence": 0.91
    }
  ],
  "confidence": 0.92,
  "confidence_tier": "HIGH",
  "explanation": "Based on available records, CASE_101 connects to CASE_204 through shared/bridging entities. Specifically, PERSON_017 is linked to PHONE_042, which is further associated with PERSON_089 in CASE_204.\n\nSupporting Documentary Evidence:\n- [Case101_CDR_Analysis.pdf, p.4]: \"Call Detail Records confirm Person 017 operated Phone 042 (+91-9876543210) during the incident timeframe.\" (Conf: 0.94)\n- [Case204_Telecom_Report.pdf, p.5]: \"Subscriber verification records indicate Phone 042 was actively used by Person 089 (Vikram Singh) to coordinate logistics in Case 204.\" (Conf: 0.91)",
  "investigative_lead": "POTENTIAL INVESTIGATIVE LEAD: Review communication and movement logs for bridge entity 'PHONE_042' to establish whether operational coordination occurred between PERSON_017 and PERSON_089 across CASE_101 and CASE_204.",
  "limitations": [
    "Cross-case link is based on intermediate phone co-usage and timeline proximity.",
    "Does not establish formal conspiracy or shared culpability without primary witness verification."
  ],
  "is_safe": true,
  "disclaimer": "CrimeGraph AI outputs are potential investigative leads for human verification and do NOT constitute legal proof or determinations of guilt."
}
```

---

## 5. Backend Integration Guide (For Kaustubh)

The AI Investigation Engine connects via the abstract `CrimeGraphDataProvider` (`GraphDataProvider`) interface in `src/crimegraph/core/interfaces.py`.

- **Mock / Offline Mode**: Uses `MockGraphDataProvider` (`MockCrimeGraphDataProvider`).
- **Live HTTP Backend Integration**:
  ```python
  from crimegraph.data_layer.api_provider import CrimeGraphAPIProvider
  from crimegraph.intelligence.engine import InvestigationEngine

  # Point to Kaustubh's backend conforming to API_CONTRACT.md
  backend_provider = CrimeGraphAPIProvider(base_url="http://localhost:8000")
  engine = InvestigationEngine(data_provider=backend_provider)

  response = engine.process_query("How are Case 101 and Case 204 connected?")
  ```

---

## 6. Running Tests & Demo

### Running Automated Test Suite (30 Tests):
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

### Running Interactive Demonstration:
```bash
python demo.py
```
