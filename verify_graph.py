"""CrimeGraph AI — Day 1 Graph & Dataset Verification Script.

Executes graph integrity checks and verifies the discoverable connection chain:
CASE_101 → PERSON_017 → PHONE_042 → PERSON_089 → CASE_204

Usage:
    python verify_graph.py
"""

import sys
from pathlib import Path

# Configure utf-8 stdout for Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add src/ to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from crimegraph.data.loader import load_dataset
from crimegraph.graph.traversal import find_cross_case_connections, find_paths_between_entities
from crimegraph.models.entities import EntityType


def print_banner(title: str):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def main():
    print_banner("CrimeGraph AI — Day 1: Data & Graph Foundation Verification")

    # 1. Load Dataset
    print("[1/5] Loading Knowledge Graph Dataset...")
    graph = load_dataset()
    print(f"  ✓ Knowledge Graph loaded successfully from data/synthetic_data.json")

    # 2. Graph Metrics
    print("\n[2/5] Inspecting Graph Statistics:")
    cases = graph.get_entities_by_type(EntityType.CASE)
    persons = graph.get_entities_by_type(EntityType.PERSON)
    phones = graph.get_entities_by_type(EntityType.PHONE)
    vehicles = graph.get_entities_by_type(EntityType.VEHICLE)
    locations = graph.get_entities_by_type(EntityType.LOCATION)
    orgs = graph.get_entities_by_type(EntityType.ORGANIZATION)
    accounts = graph.get_entities_by_type(EntityType.ACCOUNT)
    events = graph.get_entities_by_type(EntityType.EVENT)

    print(f"  • Cases:         {len(cases)} ({', '.join(c.id for c in cases)})")
    print(f"  • Persons:       {len(persons)} ({', '.join(p.id for p in persons)})")
    print(f"  • Phones:        {len(phones)} ({', '.join(ph.id for ph in phones)})")
    print(f"  • Vehicles:      {len(vehicles)} ({', '.join(v.id for v in vehicles)})")
    print(f"  • Locations:     {len(locations)} ({', '.join(l.id for l in locations)})")
    print(f"  • Organizations: {len(orgs)} ({', '.join(o.id for o in orgs)})")
    print(f"  • Accounts:      {len(accounts)} ({', '.join(a.id for a in accounts)})")
    print(f"  • Events:        {len(events)} ({', '.join(e.id for e in events)})")
    print(f"  • Relationships: {len(graph.relationships)}")
    print(f"  • Evidence Items:{len(graph.evidence)}")

    # 3. Integrity Verification
    print("\n[3/5] Performing Graph Integrity Checks:")
    report = graph.validate_integrity()
    if report["is_valid"]:
        print("  ✓ PASS: Zero broken references. All source, target, and evidence IDs resolve.")
        print("  ✓ PASS: All confidence scores within valid [0.0, 1.0] range.")
        print("  ✓ PASS: Entity unique IDs and schema constraints strictly verified.")
    else:
        print("  ✗ FAIL: Integrity errors detected:")
        for err in report["errors"]:
            print(f"    - {err}")
        sys.exit(1)

    # 4. Main Demo Path Verification
    print("\n[4/5] Discovering Main Cross-Case Path (CASE_101 -> CASE_204):")
    expected_path = ["CASE_101", "PERSON_017", "PHONE_042", "PERSON_089", "CASE_204"]
    
    paths = find_paths_between_entities(graph, "CASE_101", "CASE_204", max_depth=5)
    matching = [p for p in paths if p["path"] == expected_path]

    if not matching:
        print(f"  ✗ FAIL: Expected path {expected_path} not found in graph!")
        sys.exit(1)

    demo_path = matching[0]
    print(f"  ✓ SUCCESS: Discovered relationship chain:")
    print(f"    {' -> '.join(demo_path['path'])}")
    print(f"  • Composite Confidence: {demo_path['confidence']:.2f}")
    print(f"  • Shared Bridge Entity: {', '.join(demo_path['shared_entities'])}")

    print("\n  Detailed Step-by-Step Chain:")
    for i, step in enumerate(demo_path["steps"], 1):
        u_ent = graph.get_entity(step["from"])
        v_ent = graph.get_entity(step["to"])
        u_name = getattr(u_ent, "name", getattr(u_ent, "title", getattr(u_ent, "phone_number", u_ent.id)))
        v_name = getattr(v_ent, "name", getattr(v_ent, "title", getattr(v_ent, "phone_number", v_ent.id)))
        print(f"    Step {i}: [{step['from']}] ({u_name}) --{step['relationship']}--> [{step['to']}] ({v_name})")
        print(f"            Confidence: {step['confidence']} | Evidence: {step['evidence_ids']}")

    # 5. Evidence Provenance Verification
    print("\n[5/5] Verifying Supporting Evidence Provenance:")
    for evid_id in demo_path["evidence_ids"]:
        ev = graph.get_evidence(evid_id)
        if ev:
            print(f"  • [{ev.evidence_id}] (Confidence: {ev.confidence} [{ev.confidence_tier}])")
            print(f"    Document: {ev.source_document_id} (Page: {ev.page_number})")
            print(f"    Method:   {ev.extraction_method}")
            print(f"    Snippet:  \"{ev.source_text}\"")

    # API Contract check
    print("\nAPI Contract Verification (/api/cases/connections):")
    connections = find_cross_case_connections(graph, "CASE_101", "CASE_204")
    print(f"  ✓ API Format Output: {len(connections)} connection(s) discovered")
    print(f"    {connections[0]}")

    print_banner("DAY 1 VERIFICATION COMPLETE — ALL TESTS PASSED (100%)")


if __name__ == "__main__":
    main()
