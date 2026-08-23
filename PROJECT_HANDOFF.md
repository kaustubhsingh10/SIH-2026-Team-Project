\# CrimeGraph AI — Project Handoff



\## Project Overview



CrimeGraph AI is a backend system for representing crime-related information as a graph and performing graph-based analysis such as multi-hop traversal and pathfinding.



This file is a handoff document for another developer or AI agent so development can continue from the current state.



\---



\## Current Status



Day 1 backend foundation has been implemented.



The project currently contains the basic graph/data foundation, graph entities, relationships, evidence records, in-memory adjacency storage, and graph traversal functionality.



The graph traversal implementation must remain REAL and must NOT be replaced with mocked or hardcoded results.



\---



\## Completed Work



The following functionality has been implemented:



\- Graph entities

\- Graph relationships

\- Evidence records

\- In-memory adjacency store

\- Graph connections

\- Multi-hop BFS pathfinding

\- Graph verification/testing

\- Initial project structure

\- Initial test setup



\---



\## Important Graph Requirement



Graph traversal must use real graph data.



Do NOT:



\- Hardcode paths

\- Return fake BFS results

\- Mock graph traversal

\- Create predefined answers just for tests



The system should actually traverse the in-memory adjacency structure using BFS.



\---



\## Project Structure



The project root is:



SIH-2026-Team-Project



Important directories/files include:



src/crimegraph/

tests/

conftest.py

.gitignore

API\_CONTRACT.md



The exact project structure should be inspected before making changes.



\---



\## Remaining Day 1 API Work



According to the current project requirements, the following API functionality is incomplete.



\### 1. AI Extraction



Endpoint:



POST /api/extract



Purpose:



Accept crime-related text and extract structured entities and relationships using AI/LLM/NER.



Concept:



Input text

→ AI/NER extraction

→ structured entities

→ relationships

→ graph data



\---



\### 2. Case Timeline



Endpoint:



GET /api/cases/{case\_id}/timeline



Purpose:



Return the timeline of events associated with a particular crime case.



The returned events should be ordered chronologically.



\---



\### 3. AI Report Generation



Endpoint:



POST /api/reports



Purpose:



Generate an AI-based report using the available structured crime/case information.



The implementation must follow the API contract.



\---



\### 4. FastAPI HTTP Server



A FastAPI server wrapper is required to expose the backend functionality through REST APIs.



The API routes should connect to the existing graph/data implementation rather than creating a separate duplicate data system.



\---



\## Priority



Complete the remaining work in this order:



1\. Inspect the existing project.

2\. Read API\_CONTRACT.md carefully.

3\. Inspect the existing graph implementation.

4\. Inspect entities and relationships.

5\. Inspect the adjacency store.

6\. Inspect the BFS implementation.

7\. Inspect existing tests.

8\. Implement POST /api/extract.

9\. Implement GET /api/cases/{case\_id}/timeline.

10\. Implement POST /api/reports.

11\. Add the FastAPI server and routes.

12\. Connect the API routes to the existing backend logic.

13\. Add/update tests.

14\. Run the complete test suite.

15\. Fix any failures.

16\. Verify that API responses match API\_CONTRACT.md.



\---



\## Important Instructions



Before modifying code:



\- Read the existing implementation.

\- Read API\_CONTRACT.md.

\- Understand the current graph architecture.

\- Do not rewrite working functionality unnecessarily.

\- Do not create duplicate graph stores.

\- Do not replace BFS with mocked results.

\- Follow the existing project structure.

\- Keep the implementation modular.

\- Add tests for new functionality.



\---



\## Definition of Done



Day 1 API work should be considered complete when:



\- Real graph traversal works.

\- Multi-hop BFS works.

\- POST /api/extract works.

\- GET /api/cases/{case\_id}/timeline works.

\- POST /api/reports works.

\- FastAPI exposes the backend through HTTP.

\- API responses follow API\_CONTRACT.md.

\- Tests pass.

\- Core graph functionality remains real and is not mocked.



\---



\## Instructions for the Next AI Agent



You are continuing an existing project.



DO NOT start the project from scratch.



First inspect the entire repository and understand what has already been implemented.



Start by reading:



1\. API\_CONTRACT.md

2\. src/crimegraph/

3\. tests/

4\. conftest.py

5\. Existing graph/entity/relationship files



Determine which functionality already exists and which functionality is missing.



Then implement only the missing functionality.



After making changes:



1\. List the files that were changed.

2\. Explain what was implemented.

3\. Run the tests.

4\. Report any failing tests.

5\. Fix errors where appropriate.

6\. Explain what should be done next.



Preserve all working functionality from the existing project.

