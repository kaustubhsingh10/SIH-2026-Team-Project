CrimeGraph SIH - Synthetic Graph Dataset
===============================================

IMPORTANT: This dataset is entirely synthetic and is intended for hackathon/demo/testing use.
It does not represent real criminals, suspects, victims, witnesses, or real investigations.

Files
-----
people.csv
  Nodes/persons with synthetic attributes.

relationships.csv
  Graph edges between people. Useful for NetworkX, Neo4j, Gephi, or graph ML.

cases.csv
  Synthetic crime cases and primary suspects.

case_person_links.csv
  Links people to cases with their synthetic role.

evidence.csv
  Synthetic evidence observations connecting people to cases.

Suggested graph model
---------------------
(:Person)-[:RELATIONSHIP {strength, interaction_count}]->(:Person)
(:Person)-[:INVOLVED_IN {role_in_case}]->(:Case)
(:Person)-[:HAS_EVIDENCE]->(:Evidence)

Potential SIH features
----------------------
- Find common connections between suspects
- Detect clusters/communities
- Rank highly connected persons
- Link prediction for possible hidden relationships
- Shortest-path investigation between two persons
- Case similarity based on shared people/evidence
- Timeline-based relationship analysis

All names, IDs, locations, dates, and relationships are fabricated.
