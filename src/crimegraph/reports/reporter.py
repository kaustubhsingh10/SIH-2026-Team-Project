"""Investigation Report Generator for CrimeGraph AI.

Generates evidence-linked investigation summaries adhering to PROJECT_SPEC.md F11 & Safety Principles.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.graph.traversal import find_cross_case_connections


class InvestigationReporter:
    """Generates structured evidence-linked investigation summaries."""

    def __init__(self, graph_store: KnowledgeGraphStore):
        self.graph = graph_store

    def generate_report(self, case_id: str) -> Dict[str, Any]:
        """Generates an investigation report matching API_CONTRACT.md POST /api/reports response."""
        report_id = f"REPORT_{uuid.uuid4().hex[:6].upper()}"
        case_ent = self.graph.get_entity(case_id)

        case_title = case_ent.title if case_ent and hasattr(case_ent, "title") else case_id
        case_desc = case_ent.description if case_ent and hasattr(case_ent, "description") else "Active Investigation Case File"

        # Get connected entities & relationships
        case_rels = [r for r in self.graph.relationships.values() if r.source_id == case_id or r.target_id == case_id]
        
        entities_summary = []
        evidence_index = []

        for r in case_rels:
            other_id = r.target_id if r.source_id == case_id else r.source_id
            other_ent = self.graph.get_entity(other_id)
            if other_ent:
                o_name = getattr(other_ent, "name", getattr(other_ent, "phone_number", getattr(other_ent, "registration_number", other_id)))
                o_type = getattr(other_ent, "entity_type", "ENTITY")
                entities_summary.append(f"- **{o_name}** (`{other_id}` | `{o_type}`): Connected via `{r.relationship}` (Confidence: {r.confidence:.2f})")

            for ev_id in r.evidence_ids:
                ev = self.graph.get_evidence(ev_id)
                if ev:
                    evidence_index.append(
                        f"  - [`{ev.evidence_id}`] Document: **{ev.source_document_id}** (Page {ev.page_number or 1}) | Method: {ev.extraction_method}\n"
                        f"    > \"{ev.source_text}\"\n"
                        f"    > *Confidence Score*: {ev.confidence} ({ev.confidence_tier})"
                    )

        # Cross-case discovery check
        cross_case_summary = ""
        other_cases = [c.id for c in self.graph.get_entities_by_type("CASE") if c.id != case_id]
        for oc_id in other_cases:
            conns = find_cross_case_connections(self.graph, case_id, oc_id)
            if conns:
                for c in conns:
                    path_str = " → ".join(c["path"])
                    cross_case_summary += (
                        f"\n### Cross-Case Link: `{case_id}` ↔ `{oc_id}`\n"
                        f"- **Discovered Path**: `{path_str}`\n"
                        f"- **Bridge Entities**: `{', '.join(c['shared_entities'])}`\n"
                        f"- **Composite Confidence**: **{c['confidence']:.2f}**\n"
                    )

        report_markdown = f"""# CrimeGraph AI — Investigative Intelligence Summary

**Report ID**: `{report_id}`  
**Case**: `{case_id}` — **{case_title}**  
**Generated Date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}  
**System Version**: CrimeGraph AI v1.0 (SIH 2026 Prototype)

---

> [!IMPORTANT]
> **LEGAL & SAFETY DISCLAIMER**: This report provides AI-generated investigative leads based on available records. It **does NOT determine guilt, label individuals as criminals, or make final legal decisions**. All findings require independent verification by qualified law-enforcement officers.

---

## 1. Case Overview
{case_desc}

---

## 2. Directly Linked Entities ({len(entities_summary)})
{chr(10).join(entities_summary) if entities_summary else "No direct entities linked."}

---

## 3. Automated Cross-Case Discoveries
{cross_case_summary if cross_case_summary else "No cross-case linkages detected."}

---

## 4. Evidence Lineage & Provenance Index ({len(evidence_index)})
{chr(10).join(evidence_index) if evidence_index else "No evidence records attached."}

---
*End of Report `{report_id}`*
"""

        return {
            "report_id": report_id,
            "case_id": case_id,
            "status": "generated",
            "timestamp": datetime.now().isoformat(),
            "content": report_markdown
        }
