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
