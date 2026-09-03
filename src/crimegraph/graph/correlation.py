"""Cross-Source Intelligence Correlation Engine for CrimeGraph AI (Day 32).

Analyzes multi-source data records (DATASET, MANUAL, NLP_EXTRACT, SOCIAL, EVIDENCE) to discover
meaningful overlaps, reinforcing relationship signals, temporal correlations, location co-occurrences,
cross-case connections, and contradiction detection.

Strictly adheres to PROJECT_SPEC.md, DATA_SCHEMA.md, API_CONTRACT.md, and Safety Principles.
Outputs represent explainable investigative correlation leads only, NEVER proof of legal guilt.
"""

from datetime import datetime, timedelta
import math
from typing import Any, Dict, List, Optional, Set, Tuple

from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.models.correlation import (
    CorrelationItem,
    CorrelationSeverity,
    CorrelationType,
)


class CrossSourceCorrelationEngine:
    """Core intelligence engine for discovering cross-source correlations across graph data."""

    def __init__(self, graph_store: KnowledgeGraphStore):
        self.graph = graph_store

    def detect_all_correlations(
        self,
        case_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        correlation_type: Optional[str] = None,
        min_score: float = 0.0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Executes all correlation detectors and returns structured, explainable correlation items."""
        correlations: List[Dict[str, Any]] = []

        # Run detectors
        correlations.extend(self._detect_entity_correlations())
        correlations.extend(self._detect_relationship_correlations())
        correlations.extend(self._detect_temporal_correlations())
        correlations.extend(self._detect_location_correlations())
        correlations.extend(self._detect_cross_case_correlations())
        correlations.extend(self._detect_contradictions())

        # Filtering
        filtered: List[Dict[str, Any]] = []
        for item in correlations:
            # Case filter
            if case_id:
                c_ids = item.get("involved_case_ids", item.get("involved_cases", []))
                if case_id not in c_ids:
                    continue

            # Entity filter
            if entity_id:
                e_ids = item.get("involved_entity_ids", item.get("involved_entities", []))
                if entity_id not in e_ids and item.get("primary_entity_id") != entity_id:
                    continue

            # Correlation type filter
            if correlation_type:
                ctype = item.get("correlation_type", "")
                if ctype != correlation_type and ctype.lower() != correlation_type.lower():
                    continue

            # Minimum score filter
            score = item.get("correlation_score", item.get("confidence", 0.0))
            if score < min_score:
                continue

            filtered.append(item)

        # Sort by correlation_score descending
        filtered.sort(key=lambda x: x.get("correlation_score", 0.0), reverse=True)
        return filtered[:limit]

    def _detect_entity_correlations(self) -> List[Dict[str, Any]]:
        """Detects entities appearing across multiple independent source types or evidence files."""
        results: List[Dict[str, Any]] = []

        for eid, ent in self.graph.entities.items():
            if eid.startswith("CASE_"):
                continue

            # Gather sources
            sources: Set[str] = set()
            origin = getattr(ent, "origin", "DATASET")
            sources.add(str(origin))

            # Gather linked evidence and their sources
            neighbors = self.graph.get_neighbors(eid, direction="undirected")
            evidence_ids: List[str] = []
            cases: Set[str] = set()

            for r, nbr in neighbors:
                if nbr.id.startswith("CASE_"):
                    cases.add(nbr.id)
                ev_list = getattr(r, "evidence_ids", [])
                for ev_id in ev_list:
                    evidence_ids.append(ev_id)
                    ev_obj = self.graph.evidence.get(ev_id)
                    if ev_obj:
                        ev_source = getattr(ev_obj, "source_type", "DATASET")
                        sources.add(str(ev_source))

            if len(sources) >= 2 or len(evidence_ids) >= 2:
                name = getattr(ent, "name", getattr(ent, "title", eid))
                etype = getattr(ent, "entity_type", "ENTITY")

                id_match = 1.0 if len(evidence_ids) >= 3 else 0.70
                src_div = min(1.0, len(sources) / 3.0)
                ev_score = min(1.0, len(evidence_ids) / 4.0)

                comp_score = round(min(1.0, 0.35 * id_match + 0.35 * src_div + 0.30 * ev_score), 4)

                item_dict = {
                    "correlation_id": f"CORR_ENT_{eid}",
                    "correlation_type": CorrelationType.ENTITY_CORRELATION.value,
                    "title": f"Multi-Source Entity Correlation ({name})",
                    "severity": CorrelationSeverity.HIGH.value if comp_score >= 0.80 else CorrelationSeverity.MEDIUM.value,
                    "confidence": getattr(ent, "confidence", 0.95),
                    "correlation_score": comp_score,
                    "primary_entity_id": eid,
                    "involved_entities": [eid],
                    "involved_entity_ids": [eid],
                    "involved_cases": sorted(list(cases)),
                    "involved_case_ids": sorted(list(cases)),
                    "supporting_evidence": evidence_ids[:5],
                    "evidence_ids": evidence_ids[:5],
                    "source_records": [{"source": s, "entity_id": eid} for s in sources],
                    "scoring_factors": {
                        "identifier_match": id_match,
                        "source_diversity": src_div,
                        "evidence_count_score": ev_score
                    },
                    "explanation": f"Entity '{name}' ({eid}) is corroborated across {len(sources)} independent source systems ({', '.join(sorted(list(sources)))}) and {len(evidence_ids)} evidence items.",
                    "investigative_lead": f"Cross-verify records for '{name}' across independent source systems.",
                    "provenance_sources": sorted(list(sources)),
                    "disclaimer": "Investigative correlation lead only. Multi-source alignment quantifies graph and temporal overlap for investigative prioritization. It does NOT establish legal guilt."
                }
                results.append(item_dict)

        return results

    def _detect_relationship_correlations(self) -> List[Dict[str, Any]]:
        """Detects relationships supported by multiple evidence files or independent sources."""
        results: List[Dict[str, Any]] = []

        for rel in self.graph.relationships:
            ev_ids = getattr(rel, "evidence_ids", [])
            if len(ev_ids) >= 2:
                s_id, t_id = rel.source, rel.target
                rel_type = getattr(rel, "relationship_type", "CONNECTED_TO")

                s_ent = self.graph.get_entity(s_id)
                t_ent = self.graph.get_entity(t_id)

                s_name = getattr(s_ent, "name", s_id) if s_ent else s_id
                t_name = getattr(t_ent, "name", t_id) if t_ent else t_id

                cases: Set[str] = set()
                if s_id.startswith("CASE_"):
                    cases.add(s_id)
                if t_id.startswith("CASE_"):
                    cases.add(t_id)

                comp_score = round(min(1.0, 0.40 + 0.20 * len(ev_ids)), 4)

                item_dict = {
                    "correlation_id": f"CORR_REL_{rel.id}",
                    "correlation_type": CorrelationType.RELATIONSHIP_CORRELATION.value,
                    "title": f"Corroborated Relationship ({s_name} - {rel_type} - {t_name})",
                    "severity": CorrelationSeverity.HIGH.value if len(ev_ids) >= 3 else CorrelationSeverity.MEDIUM.value,
                    "confidence": getattr(rel, "confidence", 0.95),
                    "correlation_score": comp_score,
                    "primary_entity_id": s_id,
                    "involved_entities": [s_id, t_id],
                    "involved_entity_ids": [s_id, t_id],
                    "involved_cases": sorted(list(cases)),
                    "involved_case_ids": sorted(list(cases)),
                    "supporting_evidence": ev_ids,
                    "evidence_ids": ev_ids,
                    "source_records": [{"evidence_id": ev} for ev in ev_ids],
                    "scoring_factors": {
                        "evidence_corroboration_count": len(ev_ids)
                    },
                    "explanation": f"Relationship '{rel_type}' between '{s_name}' and '{t_name}' is independently backed by {len(ev_ids)} evidence records ({', '.join(ev_ids)}).",
                    "investigative_lead": f"High-confidence relationship reinforced by multi-source evidence ({', '.join(ev_ids)}).",
                    "provenance_sources": ["DATASET", "EVIDENCE"],
                    "disclaimer": "Investigative correlation lead only. Multi-source alignment quantifies graph and temporal overlap for investigative prioritization. It does NOT establish legal guilt."
                }
                results.append(item_dict)

        return results

    def _detect_temporal_correlations(self) -> List[Dict[str, Any]]:
        """Detects events or evidence items occurring within close temporal windows."""
        results: List[Dict[str, Any]] = []
        ev_items = list(self.graph.evidence.values())

        for i in range(len(ev_items)):
            for j in range(i + 1, len(ev_items)):
                e1, e2 = ev_items[i], ev_items[j]
                t1_str = getattr(e1, "timestamp", None)
                t2_str = getattr(e2, "timestamp", None)

                if t1_str and t2_str:
                    try:
                        dt1 = datetime.fromisoformat(t1_str.replace("Z", "+00:00"))
                        dt2 = datetime.fromisoformat(t2_str.replace("Z", "+00:00"))
                        diff_hours = abs((dt1 - dt2).total_seconds()) / 3600.0

                        if diff_hours <= 24.0:
                            linked_e1 = set(getattr(e1, "linked_entity_ids", []))
                            linked_e2 = set(getattr(e2, "linked_entity_ids", []))
                            common_entities = list(linked_e1.intersection(linked_e2))

                            if common_entities:
                                comp_score = round(min(1.0, 0.50 + (24.0 - diff_hours) / 48.0 + 0.20 * len(common_entities)), 4)
                                item_dict = {
                                    "correlation_id": f"CORR_TEMP_{e1.id}_{e2.id}",
                                    "correlation_type": CorrelationType.TEMPORAL_CORRELATION.value,
                                    "title": f"Temporal Co-Occurrence ({diff_hours:.1f}h Window)",
                                    "severity": CorrelationSeverity.HIGH.value if diff_hours <= 4.0 else CorrelationSeverity.MEDIUM.value,
                                    "confidence": 0.90,
                                    "correlation_score": comp_score,
                                    "primary_entity_id": common_entities[0],
                                    "involved_entities": common_entities,
                                    "involved_entity_ids": common_entities,
                                    "involved_cases": [],
                                    "involved_case_ids": [],
                                    "supporting_evidence": [e1.id, e2.id],
                                    "evidence_ids": [e1.id, e2.id],
                                    "source_records": [{"evidence_id": e1.id, "time": t1_str}, {"evidence_id": e2.id, "time": t2_str}],
                                    "scoring_factors": {
                                        "temporal_window_hours": round(diff_hours, 2),
                                        "common_entity_count": len(common_entities)
                                    },
                                    "explanation": f"Evidence '{e1.id}' and '{e2.id}' occurred within {diff_hours:.1f} hours of each other with shared entities ({', '.join(common_entities)}).",
                                    "investigative_lead": f"Analyze temporal timeline alignment around {t1_str}.",
                                    "provenance_sources": ["EVIDENCE", "TIMELINE"],
                                    "disclaimer": "Investigative correlation lead only. Multi-source alignment quantifies graph and temporal overlap for investigative prioritization. It does NOT establish legal guilt."
                                }
                                results.append(item_dict)
                    except ValueError:
                        continue

        return results

    def _detect_location_correlations(self) -> List[Dict[str, Any]]:
        """Detects co-location overlaps across entities and events."""
        results: List[Dict[str, Any]] = []
        loc_map: Dict[str, List[str]] = {}

        for eid, ent in self.graph.entities.items():
            loc = getattr(ent, "location", None) or getattr(ent, "jurisdiction", None)
            if loc:
                loc_map.setdefault(loc, []).append(eid)

        for loc, eids in loc_map.items():
            non_case_eids = [e for e in eids if not e.startswith("CASE_")]
            if len(non_case_eids) >= 3:
                comp_score = round(min(1.0, 0.40 + 0.15 * len(non_case_eids)), 4)
                item_dict = {
                    "correlation_id": f"CORR_LOC_{hash(loc) % 10000}",
                    "correlation_type": CorrelationType.LOCATION_CORRELATION.value,
                    "title": f"Location Cluster Correlation ({loc})",
                    "severity": CorrelationSeverity.MEDIUM.value,
                    "confidence": 0.88,
                    "correlation_score": comp_score,
                    "primary_entity_id": non_case_eids[0],
                    "involved_entities": non_case_eids[:5],
                    "involved_entity_ids": non_case_eids[:5],
                    "involved_cases": [],
                    "involved_case_ids": [],
                    "supporting_evidence": [],
                    "evidence_ids": [],
                    "source_records": [{"location": loc, "entity_count": len(non_case_eids)}],
                    "scoring_factors": {
                        "location_density": len(non_case_eids)
                    },
                    "explanation": f"Geographical location '{loc}' is shared by {len(non_case_eids)} active entities in the network.",
                    "investigative_lead": f"Examine regional operational presence at location '{loc}'.",
                    "provenance_sources": ["DATASET"],
                    "disclaimer": "Investigative correlation lead only. Multi-source alignment quantifies graph and temporal overlap for investigative prioritization. It does NOT establish legal guilt."
                }
                results.append(item_dict)

        return results

    def _detect_cross_case_correlations(self) -> List[Dict[str, Any]]:
        """Detects cross-case linkages connecting independent investigation files."""
        results: List[Dict[str, Any]] = []

        all_cases = [eid for eid in self.graph.entities.keys() if eid.startswith("CASE_")]
        for i in range(len(all_cases)):
            for j in range(i + 1, len(all_cases)):
                ca, cb = all_cases[i], all_cases[j]
                nbrs_a = set(nbr.id for _, nbr in self.graph.get_neighbors(ca, direction="undirected"))
                nbrs_b = set(nbr.id for _, nbr in self.graph.get_neighbors(cb, direction="undirected"))
                common = list(nbrs_a.intersection(nbrs_b))

                if common:
                    comp_score = round(min(1.0, 0.60 + 0.15 * len(common)), 4)
                    item_dict = {
                        "correlation_id": f"CORR_XCASE_{ca}_{cb}",
                        "correlation_type": CorrelationType.CROSS_CASE_CORRELATION.value,
                        "title": f"Cross-Case Overlap ({ca} <-> {cb})",
                        "severity": CorrelationSeverity.HIGH.value,
                        "confidence": 0.95,
                        "correlation_score": comp_score,
                        "primary_entity_id": common[0],
                        "involved_entities": common,
                        "involved_entity_ids": common,
                        "involved_cases": [ca, cb],
                        "involved_case_ids": [ca, cb],
                        "supporting_evidence": [],
                        "evidence_ids": [],
                        "source_records": [{"case_a": ca, "case_b": cb, "shared_nodes": common}],
                        "scoring_factors": {
                            "shared_node_count": len(common)
                        },
                        "explanation": f"Investigation files '{ca}' and '{cb}' share {len(common)} direct node connections ({', '.join(common)}).",
                        "investigative_lead": f"Cross-reference case files [{ca}, {cb}] through shared node '{common[0]}'.",
                        "provenance_sources": ["DATASET"],
                        "disclaimer": "Investigative correlation lead only. Multi-source alignment quantifies graph and temporal overlap for investigative prioritization. It does NOT establish legal guilt."
                    }
                    results.append(item_dict)

        return results

    def _detect_contradictions(self) -> List[Dict[str, Any]]:
        """Detects conflicting attribute or confidence signals across multi-source records."""
        results: List[Dict[str, Any]] = []

        for eid, ent in self.graph.entities.items():
            aliases = getattr(ent, "aliases", [])
            conf = getattr(ent, "confidence", 1.0)
            if conf < 0.60 or len(aliases) >= 4:
                name = getattr(ent, "name", eid)
                item_dict = {
                    "correlation_id": f"CORR_CONTR_{eid}",
                    "correlation_type": CorrelationType.CONTRADICTION_DETECTION.value,
                    "title": f"Source Discrepancy Signal ({name})",
                    "severity": CorrelationSeverity.MEDIUM.value,
                    "confidence": conf,
                    "correlation_score": 0.70,
                    "primary_entity_id": eid,
                    "involved_entities": [eid],
                    "involved_entity_ids": [eid],
                    "involved_cases": [],
                    "involved_case_ids": [],
                    "supporting_evidence": [],
                    "evidence_ids": [],
                    "source_records": [{"entity_id": eid, "confidence": conf, "aliases_count": len(aliases)}],
                    "scoring_factors": {
                        "confidence_gap": round(1.0 - conf, 4),
                        "alias_count": len(aliases)
                    },
                    "explanation": f"Entity '{name}' ({eid}) exhibits multi-source attribute discrepancies or multiple distinct aliases ({len(aliases)} aliases recorded).",
                    "investigative_lead": f"Reconcile alias conflicts for '{name}' via primary document verification.",
                    "contradiction_details": f"Confidence rating is lower ({conf:.2f}) due to conflicting source attributes.",
                    "provenance_sources": ["DATASET", "MANUAL"],
                    "disclaimer": "Investigative correlation lead only. Multi-source alignment quantifies graph and temporal overlap for investigative prioritization. It does NOT establish legal guilt."
                }
                results.append(item_dict)

        return results
