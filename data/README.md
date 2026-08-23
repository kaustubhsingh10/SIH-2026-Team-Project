# CrimeGraph Data Sources

## 1. Overview

CrimeGraph uses a hybrid data strategy consisting of:

1. Official public crime statistics from NCRB/data.gov.in.
2. Synthetic investigation-level data created specifically for the CrimeGraph prototype.

These two data sources serve different purposes and must remain clearly separated.

---

# 2. Official NCRB Data

## Source

National Crime Records Bureau (NCRB) / data.gov.in

## Dataset File

NCRB_Table_1A.1.csv

## Dataset Title

State/UT-wise Number of Indian Penal Code (IPC) Crimes from 2020 to 2022

## Dataset Description

This dataset contains State/UT-wise aggregated statistics related to
Indian Penal Code (IPC) cognizable crimes in India.

The dataset provides crime statistics for:

- 2020
- 2021
- 2022

It also includes population, crime rate and chargesheeting information
for 2022.

## Geographic Coverage

State and Union Territory level.

## Available Data

The official dataset is used to obtain information such as:

- State/UT
- IPC crime statistics for 2020
- IPC crime statistics for 2021
- IPC crime statistics for 2022
- Mid-year projected population for 2022
- Rate of cognizable crimes
- Chargesheeting rate

## Purpose in CrimeGraph

The official NCRB data may be used for:

- State/UT-wise crime analysis
- Year-wise crime trends
- Crime rate comparison
- Chargesheeting rate analysis
- Geographic crime context
- Dashboard charts and visualizations
- Official statistical context

## Limitations

This dataset contains aggregated statistics.

It does not contain detailed investigation-level records such as:

- Individual persons
- Phone numbers
- Vehicles
- Bank accounts
- Detailed case relationships
- Call records
- Transaction records
- Individual evidence
- Suspect networks

Therefore, aggregated NCRB statistics must not be used to fabricate
investigation-level relationships.

---

# 3. Synthetic Investigation Data

CrimeGraph requires detailed investigation-level entities and
relationships to demonstrate graph intelligence.

These records are synthetic and fictional.

Synthetic entities may include:

- Cases
- Persons
- Phones
- Vehicles
- Locations
- Bank Accounts
- Evidence

Synthetic relationships may include:

- Person connected to phone
- Person associated with vehicle
- Person associated with location
- Phone shared or used by multiple persons
- Person connected to case
- Evidence supporting an entity relationship
- Person connected to bank account
- Entity associated with multiple cases

## Main Demonstration Scenario

The primary CrimeGraph demonstration must support the following
interconnected investigation path:

CASE_101
→ PERSON_017
→ PHONE_042
→ PERSON_089
→ CASE_204

The synthetic graph must contain additional entities and relationships
so that the main path exists within a substantially richer investigation
network.

## Important Safety Rule

All synthetic persons, phone numbers, vehicles, bank accounts,
evidence and investigation scenarios must be fictional.

No synthetic data should be presented as an actual investigation record.

---

# 4. Data Separation

CrimeGraph maintains a strict separation between official statistical
data and synthetic investigation data.

Official NCRB Data:

Official Dataset
↓
Crime Statistics
↓
State/UT Analysis
↓
Trends and Context

Synthetic Investigation Data:

Synthetic Cases
↓
Entities
↓
Relationships
↓
Evidence
↓
Investigation Knowledge Graph

Official NCRB statistics and synthetic investigation data may appear
within the same application but must remain logically distinct.

---

# 5. Data Directories

## raw/

Contains original source data that should remain unchanged.

Example:

NCRB_Table_1A.1.csv

The original dataset should not be manually modified.

---

## processed/

Contains cleaned and transformed data generated from raw source data.

Examples may include:

- normalized_state_crime_statistics.json
- crime_trends.json
- dashboard_statistics.json

Processed files may be generated automatically by the backend data
processing pipeline.

---

## synthetic/

Contains synthetic investigation data generated for the CrimeGraph
prototype.

Examples may include:

- cases.json
- entities.json
- relationships.json
- evidence.json

These files may be generated or managed by the CrimeGraph backend.

---

# 6. Data Processing Rules

The data processing pipeline must follow this flow:

RAW NCRB DATA
↓
Validation
↓
Cleaning
↓
Normalization
↓
Processed Analytics Data

Synthetic data must follow this flow:

Synthetic Scenario
↓
Entity Generation
↓
Relationship Generation
↓
Evidence Attachment
↓
CrimeGraph Investigation Knowledge Graph

The official data pipeline and synthetic investigation pipeline should
remain separate.

---

# 7. Usage Rules

Official NCRB data may be used for:

- Statistical analysis
- Trend analysis
- Geographic comparison
- Dashboard visualizations
- Contextual information

Official NCRB data must not be used to:

- Identify an individual
- Infer individual guilt
- Fabricate investigation records
- Fabricate evidence
- Create unsupported relationships

Synthetic investigation data is used only for demonstrating the
CrimeGraph prototype.

---

# 8. Data Integrity

The system should validate:

- Required fields
- Unique entity identifiers
- Valid State/UT values
- Valid numerical statistics
- Valid entity references
- Valid graph relationships
- Evidence references
- Absence of broken relationships

Processed data must remain traceable to its source.

---

# 9. Data Privacy and Ethics

CrimeGraph is a prototype intended for investigation intelligence
demonstration.

The prototype uses:

- Public aggregated statistics
- Clearly labelled synthetic investigation data

The system must not claim that a person is guilty solely because of
graph associations.

Graph connections represent:

- Potential connections
- Evidence-supported relationships
- Possible investigative leads

They do not independently establish guilt or criminal liability.

---

# 10. Future Data Sources

The data architecture is designed to support future authorized sources,
including:

- FIR or case management systems
- Police investigation systems
- Court systems
- Authorized call detail records
- Authorized financial investigation data
- Authorized CCTV metadata
- Other official crime data systems

Any future sensitive data integration must follow applicable law,
authorization requirements and privacy protections.
