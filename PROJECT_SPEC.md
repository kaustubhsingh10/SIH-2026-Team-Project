# CrimeGraph AI — Project Specification

## 1. Project Overview

CrimeGraph AI is an AI-powered investigative intelligence platform that
converts fragmented investigation records into an evidence-linked
knowledge graph.

The system helps investigators discover relationships between people,
vehicles, phones, locations, cases, events and other entities.

The system provides investigative leads and evidence-linked connections.
It does NOT determine guilt or make final criminal judgments.

---

## 2. Problem

Investigation information is often distributed across:

- Case records
- Reports
- Statements
- Call records
- Vehicle information
- Location information
- Financial records
- Other evidence

Manually identifying connections across these sources is time-consuming.

CrimeGraph AI aims to automatically structure this information and
surface potentially relevant connections.

---

## 3. Target Users

Primary:

- Investigators
- Law-enforcement analysts
- Case officers

Secondary:

- Supervisors
- Intelligence analysts

---

## 4. Core Features

### F1 — Case Management
- Create cases
- View cases
- Search cases
- View case details

### F2 — Document Ingestion
- Upload investigation documents
- Extract text
- Process structured/unstructured information

### F3 — AI Entity Extraction
Extract:

- Person
- Phone
- Vehicle
- Location
- Account
- Organization
- Case
- Event

### F4 — Relationship Extraction

Identify relationships such as:

- CONTACTED
- USED
- OWNED
- VISITED
- LOCATED_AT
- INVOLVED_IN
- CONNECTED_TO

### F5 — Entity Resolution

Identify possible duplicate entities.

Example:

Rahul Kumar
R. Kumar
Rahul K.

should be flagged as a possible match.

### F6 — Knowledge Graph

Represent entities and relationships as a graph.

### F7 — Cross-Case Discovery

Find entities or relationships connecting multiple cases.

### F8 — Timeline

Display events chronologically.

### F9 — AI Investigator

Allow natural-language investigation queries.

Examples:

- "Find connections between Case 101 and Case 204."
- "Who is connected to Person 17?"
- "Which entities appear in multiple cases?"
- "Show events around the incident."

### F10 — Evidence Provenance

Every AI-generated finding must show:

- Source
- Evidence
- Timestamp
- Confidence

### F11 — Investigation Report

Generate an evidence-linked investigation summary.

---

## 5. Safety Principle

CrimeGraph AI provides investigative leads.

It must NOT:

- Declare a person guilty
- Automatically label someone as a criminal
- Make final legal decisions
- Invent evidence
- Present uncertain AI output as fact

AI-generated findings must be presented as potential leads
requiring human verification.

---

## 6. Main User Flow

User
 ↓
Dashboard
 ↓
Select Case
 ↓
Upload Documents
 ↓
Document Processing
 ↓
AI Entity Extraction
 ↓
Relationship Extraction
 ↓
Entity Resolution
 ↓
Knowledge Graph
 ↓
Cross-Case Analysis
 ↓
AI Investigator
 ↓
Evidence Verification
 ↓
Investigation Report

---

## 7. MVP Features

The 10-day prototype MUST prioritize:

1. Document ingestion
2. Entity extraction
3. Relationship extraction
4. Knowledge graph
5. Graph visualization
6. Cross-case relationship discovery
7. Natural-language investigation queries
8. Evidence provenance
9. Timeline
10. Report generation

---

## 8. Demo Scenario

Use synthetic investigation data.

Example:

Case 101
 ↓
Person 017
 ↓
Phone 042
 ↓
Person 089
 ↓
Case 204

The connection should initially be hidden.

CrimeGraph should discover and explain the connection.

---

## 9. Non-Goals

Do NOT spend prototype time on:

- Production-scale deployment
- Real police databases
- Training a custom LLM
- Complex mobile applications
- Facial recognition
- Predictive policing
- Automatic criminal-risk scoring

---

## 10. Success Criteria

The prototype is successful if a judge can:

1. Upload investigation data
2. See entities automatically extracted
3. See relationships on a graph
4. Explore an entity
5. Discover a cross-case connection
6. Ask a natural-language question
7. See the evidence supporting the answer
8. View the timeline
9. Generate a report

---

## 11. Team Ownership

Kaustubh:
- AI extraction
- AI Investigator
- Entity resolution

Aditya:
- UI/UX
- Dashboard
- Graph interface
- User experience

Shruti:
- Data
- Neo4j
- Graph algorithms
- Testing
- Integration

---

## 12. Development Constraint

Prototype deadline: 10 days.

Prioritize a reliable end-to-end demonstration over a large number
of incomplete features.
