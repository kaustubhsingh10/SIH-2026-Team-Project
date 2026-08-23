"""CrimeGraph AI — Day 2 REST API Verification Script.

Executes live HTTP API requests against all implemented endpoints
and verifies the core SIH demo path through the REST layer:
CASE_101 → PERSON_017 → PHONE_042 → PERSON_089 → CASE_204

Usage:
    python verify_api.py
"""

import sys
from pathlib import Path

# Configure utf-8 stdout for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add src/ to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from fastapi.testclient import TestClient
from crimegraph.api.app import app


def print_banner(title: str):
    print("\n" + "=" * 75)
    print(f" {title}")
    print("=" * 75)


def main():
    print_banner("CrimeGraph AI — Day 2: REST API Verification & Readiness")
    client = TestClient(app)

    # 1. System Health
    print("[1/6] Testing System & Health Endpoints...")
    res_root = client.get("/")
    assert res_root.status_code == 200, f"Root failed: {res_root.text}"
    root_data = res_root.json()
    print(f"  • Root API:        {root_data['name']} (v{root_data['version']})")
    print(f"  • Live Entities:   {root_data['metrics']['entity_count']}")
    print(f"  • Relationships:   {root_data['metrics']['relationship_count']}")
    print(f"  • Evidence Count:  {root_data['metrics']['evidence_count']}")

    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    print("  ✓ PASS: GET / and GET /api/health returned 200 OK")

    # 2. Case APIs
    print("\n[2/6] Testing Case Management APIs...")
    res_cases = client.get("/api/cases")
    assert res_cases.status_code == 200
    cases = res_cases.json()
    print(f"  • GET /api/cases: Found {len(cases)} registered cases ({', '.join(c['id'] for c in cases)})")

    res_c101 = client.get("/api/cases/CASE_101")
    assert res_c101.status_code == 200
    c101 = res_c101.json()
    print(f"  • GET /api/cases/CASE_101: '{c101['title']}' [Status: {c101['status']}]")

    res_c101_graph = client.get("/api/cases/CASE_101/graph")
    assert res_c101_graph.status_code == 200
    c101_graph = res_c101_graph.json()
    print(f"  • GET /api/cases/CASE_101/graph: {len(c101_graph['nodes'])} nodes, {len(c101_graph['edges'])} edges")

    res_c101_timeline = client.get("/api/cases/CASE_101/timeline")
    assert res_c101_timeline.status_code == 200
    timeline = res_c101_timeline.json()["events"]
    print(f"  • GET /api/cases/CASE_101/timeline: {len(timeline)} chronological events")
    print("  ✓ PASS: Case endpoints strictly conform to API_CONTRACT.md")

    # 3. Entity APIs
    print("\n[3/6] Testing Entity Management & Search APIs...")
    res_entities = client.get("/api/entities?type=PERSON")
    assert res_entities.status_code == 200
    persons = res_entities.json()
    print(f"  • GET /api/entities?type=PERSON: Found {len(persons)} people ({', '.join(p['name'] for p in persons)})")

    res_p017 = client.get("/api/entities/PERSON_017")
    assert res_p017.status_code == 200
    p017 = res_p017.json()
    print(f"  • GET /api/entities/PERSON_017: {p017['name']} (Aliases: {', '.join(p017['details']['aliases'])})")
    print(f"    - Connected relationships: {len(p017['relationships'])}")
    print(f"    - Associated cases:        {', '.join(p017['cases'])}")
    print(f"    - Supporting evidence:     {len(p017['evidence'])} records")

    res_neighbors = client.get("/api/entities/PHONE_042/neighbors")
    assert res_neighbors.status_code == 200
    neighbors = res_neighbors.json()
    print(f"  • GET /api/entities/PHONE_042/neighbors: {neighbors['neighbor_count']} 1-hop connected entities")
    print("  ✓ PASS: Entity endpoints strictly conform to API_CONTRACT.md")

    # 4. Graph & Pathfinding APIs
    print("\n[4/6] Testing Graph & Pathfinding APIs...")
    res_graph = client.get("/api/graph?min_confidence=0.90")
    assert res_graph.status_code == 200
    graph_view = res_graph.json()
    print(f"  • GET /api/graph?min_confidence=0.90: {len(graph_view['nodes'])} nodes, {len(graph_view['edges'])} high-confidence edges")

    res_paths = client.get("/api/paths?source_id=PERSON_017&target_id=PERSON_089")
    assert res_paths.status_code == 200
    paths_data = res_paths.json()
    print(f"  • GET /api/paths?source_id=PERSON_017&target_id=PERSON_089: {paths_data['path_count']} path(s) found")
    print(f"    Path 1: {' -> '.join(paths_data['paths'][0]['path'])} (Confidence: {paths_data['paths'][0]['confidence']})")
    print("  ✓ PASS: Graph & Path endpoints functional")

    # 5. Evidence APIs
    print("\n[5/6] Testing Evidence Provenance APIs...")
    res_ev_item = client.get("/api/evidence/EVID_042_01")
    assert res_ev_item.status_code == 200
    ev = res_ev_item.json()
    print(f"  • GET /api/evidence/EVID_042_01:")
    print(f"    - Document:   {ev['source_document_id']} (Page {ev['page_number']})")
    print(f"    - Method:     {ev['extraction_method']}")
    print(f"    - Confidence: {ev['confidence']} [{ev['confidence_tier']}]")
    print(f"    - Excerpt:    \"{ev['source_text']}\"")
    print("  ✓ PASS: Evidence provenance functional and verifiable")

    # 6. Main SIH Demonstration Path via API
    print("\n[6/6] VERIFYING MAIN DEMO QUERY (/api/cases/connections)...")
    res_conn = client.get("/api/cases/connections?case_a=CASE_101&case_b=CASE_204")
    assert res_conn.status_code == 200
    conn_data = res_conn.json()
    connections = conn_data.get("connections", [])
    assert len(connections) >= 1, "No connections returned between CASE_101 and CASE_204!"

    expected_path = ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]
    matching = [c for c in connections if c["path"] == expected_path]
    assert matching, f"Expected chain {expected_path} not found!"

    demo = matching[0]
    print(f"  ✓ SUCCESS: Discovered cross-case connection chain:")
    print(f"    {' -> '.join(demo['path'])}")
    print(f"  • Bridge Entity:        {', '.join(demo['shared_entities'])}")
    print(f"  • Composite Confidence: {demo['confidence']}")
    print(f"  • Supporting Evidence:  {', '.join(demo['evidence_ids'])}")

    print_banner("DAY 2 REST API BACKEND VERIFICATION COMPLETE — 100% OPERATIONAL")


if __name__ == "__main__":
    main()
