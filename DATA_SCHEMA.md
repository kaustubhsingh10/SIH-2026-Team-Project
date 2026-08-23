# CrimeGraph AI — Data Schema

## 1. Entity Types

### Person

Fields:

- id
- name
- aliases
- age
- gender
- phone_ids
- vehicle_ids
- address_ids
- source_ids
- confidence

---

### Phone

Fields:

- id
- phone_number
- owner_ids
- source_ids
- confidence

---

### Vehicle

Fields:

- id
- registration_number
- type
- owner_id
- source_ids
- confidence

---

### Location

Fields:

- id
- name
- latitude
- longitude
- address
- source_ids

---

### Organization

Fields:

- id
- name
- aliases
- address
- source_ids

---

### Account

Fields:

- id
- account_type
- identifier
- owner_id
- source_ids

---

### Case

Fields:

- id
- case_number
- title
- description
- status
- incident_date
- location_id
- source_ids

---

### Event

Fields:

- id
- event_type
- timestamp
- location_id
- description
- source_id

## 2. Relationship Types

### Person → Person

CONTACTED
KNOWS
ASSOCIATED_WITH

### Person → Phone

USES
OWNS

### Person → Vehicle

USES
OWNS

### Person → Location

VISITED
LOCATED_AT

### Person → Case

INVOLVED_IN

### Vehicle → Location

SEEN_AT

### Phone → Location

LOCATED_AT

### Person → Organization

WORKS_FOR
ASSOCIATED_WITH

### Account → Person

OWNED_BY

### Event → Person

INVOLVES

### Event → Location

OCCURRED_AT

## 3. Evidence Model

Every extracted entity and relationship must be traceable to
its source.

Evidence fields:

- evidence_id
- source_document_id
- source_text
- page_number
- timestamp
- extraction_method
- confidence
Relationship:

Person_017 --USED--> Vehicle_042

Evidence:

Document: Case101_Report.pdf
Page: 4
Text: "Person 017 was observed using Vehicle 042."
Confidence: 0.94

## 4. Confidence

Confidence must be between 0 and 1.

0.90 - 1.00 = High
0.70 - 0.89 = Medium
Below 0.70 = Low

Confidence is an AI estimate and does not represent legal certainty.

## 5. Entity Resolution

Possible duplicate entities should NOT automatically be merged.

Example:

PERSON_017
Name: Rahul Kumar

PERSON_092
Name: R. Kumar

Possible Match:

similarity: 0.92

Reasons:

- Similar name
- Same phone
- Same vehicle

Status:

PENDING_REVIEW

## 6. Core Graph Pattern

(Person)
   |
   | USES
   ↓
(Phone)

(Person)
   |
   | USES
   ↓
(Vehicle)
   |
   | SEEN_AT
   ↓
(Location)

(Person)
   |
   | INVOLVED_IN
   ↓
(Case)

Case 101
   ↓
Person 017
   ↓
Phone 042
   ↓
Person 089
   ↓
Case 204
