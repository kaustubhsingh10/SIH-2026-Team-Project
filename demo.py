"""CrimeGraph AI - Day 3 Interactive Demonstration Script (SIH 2026).

Demonstrates the Core SIH Investigation Intelligence Engine Queries:
    python demo.py
"""

import sys
import os

# Ensure src is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from crimegraph.data_layer.mock_provider import MockGraphDataProvider
from crimegraph.intelligence.engine import InvestigationEngine


def print_banner():
    print("=" * 80)
    print("           CRIMEGRAPH AI - EVIDENCE-GROUNDED INVESTIGATION ENGINE")
    print("                      SIH 2026 Prototype (Day 3)")
    print("=" * 80)
    print("Core Safety Principle: Outputs are evidence-linked investigative leads for human")
    print("verification and do NOT constitute legal proof or determinations of guilt.")
    print("=" * 80 + "\n")


def run_demo():
    print_banner()

    data_provider = MockGraphDataProvider()
    engine = InvestigationEngine(data_provider=data_provider)

    sample_questions = [
        "1. How are Case 101 and Case 204 connected?",
        "2. How are Person 017 and Person 089 connected?",
        "3. What entities connect these two cases?",
        "4. What evidence supports this relationship?",
        "5. Which entities are shared between multiple cases?",
        "6. What is the strongest connection path between these entities?",
        "7. What relationships does Person 017 have?",
        "8. Is Person 017 guilty?",
        "9. What evidence is associated with Person 017?",
        "10. What cases are connected to Person 017?",
        "11. What potential investigative leads are suggested by the available records?",
        "12. What relationships does Person 999 have?",
        "13. How are Case 999 and Case 888 connected?",
    ]

    print("RUNNING SIH 2026 DEMONSTRATION QUESTIONS:\n")
    for q in sample_questions:
        num, clean_q = q.split(". ", 1)
        print(f"[{num}] INVESTIGATOR INQUIRY: \"{clean_q}\"")
        resp = engine.process_query(clean_q)

        print(f"    [FINDING] {resp.answer}")
        if resp.path:
            print(f"    [PATH] {' -> '.join(resp.path)}")
        if resp.confidence > 0:
            print(f"    [CONFIDENCE] {resp.confidence:.2f} ({resp.confidence_tier} Tier)")
        if resp.evidence:
            print(f"    [EVIDENCE PROVENANCE] ({len(resp.evidence)} record(s)):")
            for ev in resp.evidence:
                print(f"       * [{ev['source_document_id']}, p.{ev['page_number']}] \"{ev['source_text']}\" (Conf: {ev['confidence']:.2f})")
        if resp.investigative_lead:
            print(f"    [LEAD] {resp.investigative_lead}")
        if resp.limitations:
            print(f"    [LIMITATIONS] {'; '.join(resp.limitations)}")
        print(f"    [DISCLAIMER] {resp.disclaimer}")
        print("-" * 80 + "\n")


if __name__ == "__main__":
    run_demo()

