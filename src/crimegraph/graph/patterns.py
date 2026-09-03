"""Advanced AI Pattern & Anomaly Intelligence Engine for CrimeGraph AI (Day 30).

Identifies deterministic, graph-grounded suspicious activity patterns, behavioral anomalies,
cross-case bridges, temporal clusters, and multi-source corroboration patterns across KnowledgeGraphStore topologies.

Strictly adheres to PROJECT_SPEC.md, DATA_SCHEMA.md, API_CONTRACT.md, and Safety Principles.
Zero guilt or accusatory claims: outputs represent investigative pattern leads only.
"""

from datetime import datetime
from enum import Enum
import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple

from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.graph.traversal import find_cross_case_connections
from crimegraph.models.entities import EntityType
from crimegraph.models.patterns import (
    PatternAnomalyItem,
    PatternQueryResponse,
    PatternSeverity,
    PatternType,
)
from crimegraph.models.relationships import RelationshipType

SEVERITY_WEIGHTS = {
    PatternSeverity.CRITICAL.value: 4,
    PatternSeverity.HIGH.value: 3,
    PatternSeverity.MEDIUM.value: 2,
    PatternSeverity.LOW.value: 1
}


class SuspiciousPatternEngine:
    """Graph-grounded suspicious pattern analysis and anomaly discovery engine."""

    def __init__(self, graph_store: KnowledgeGraphStore):
        self.graph = graph_store

    def _get_entity_cases(self, entity_id: str) -> Set[str]:
        """Discovers all case IDs connected to an entity directly or via 1-hop."""
        cases = set()
        if entity_id.startswith("CASE_"):
            cases.add(entity_id)
            return cases

        neighbors = self.graph.get_neighbors(entity_id, direction="undirected")
        for rel, neighbor in neighbors:
            if neighbor.id.startswith("CASE_") or getattr(neighbor, "entity_type", "") == EntityType.CASE.value:
                cases.add(neighbor.id)
            elif getattr(neighbor, "entity_type", "") == EntityType.PERSON.value:
                p_neighbors = self.graph.get_neighbors(neighbor.id, direction="undirected")
                for p_rel, p_nbr in p_neighbors:
                    if p_nbr.id.startswith("CASE_") or getattr(p_nbr, "entity_type", "") == EntityType.CASE.value:
                        cases.add(p_nbr.id)
        return cases

    def _get_entity_display_name(self, entity_id: str) -> str:
        """Retrieves human-readable label for an entity."""
        ent = self.graph.get_entity(entity_id)
        if not ent:
            return entity_id
        return getattr(ent, "name", getattr(ent, "phone_number", getattr(ent, "registration_number", getattr(ent, "title", entity_id))))

    # --------------------------------------------------------------------------
    # LEGACY DAY 20 PATTERN DETECTORS (BACKWARD COMPATIBILITY)
    # --------------------------------------------------------------------------

    def _detect_shared_devices(self) -> List[Dict[str, Any]]:
        """SHARED_DEVICE_CROSS_CASE: Detects phones/vehicles used across distinct cases."""
        patterns = []
        device_types = [EntityType.PHONE.value, EntityType.VEHICLE.value]

        for eid, ent in self.graph.entities.items():
            etype = getattr(ent, "entity_type", "")
            if etype not in device_types:
                continue

            neighbors = self.graph.get_neighbors(eid, direction="undirected")
            connected_persons = set()
            edge_confidences = []
            evidence_ids = set()
            rel_summaries = []

            for rel, nbr in neighbors:
                if getattr(nbr, "entity_type", "") == EntityType.PERSON.value:
                    connected_persons.add(nbr.id)
                    edge_confidences.append(rel.confidence)
                    for ev_id in getattr(rel, "evidence_ids", []):
                        evidence_ids.add(ev_id)
                    rel_summaries.append({
                        "relationship_id": rel.id,
                        "source": rel.source_id,
                        "target": rel.target_id,
                        "relationship": rel.relationship.value if hasattr(rel.relationship, "value") else str(rel.relationship),
                        "confidence": rel.confidence
                    })

            all_linked_cases = set()
            for pid in connected_persons:
                all_linked_cases.update(self._get_entity_cases(pid))

            if len(connected_persons) >= 2 and len(all_linked_cases) >= 2:
                avg_conf = sum(edge_confidences) / len(edge_confidences) if edge_confidences else 0.90
                dev_name = self._get_entity_display_name(eid)
                person_names = [f"{self._get_entity_display_name(p)} ({p})" for p in sorted(list(connected_persons))]
                inv_ents = sorted(list(connected_persons | {eid}))
                inv_cases = sorted(list(all_linked_cases))
                ev_list = sorted(list(evidence_ids))

                patterns.append({
                    "pattern_id": f"PAT_DEV_{eid}",
                    "pattern_type": PatternType.SHARED_DEVICE_CROSS_CASE.value,
                    "title": f"Shared Cross-Case Device ({dev_name})",
                    "severity": PatternSeverity.HIGH.value,
                    "involved_entities": inv_ents,
                    "involved_entity_ids": inv_ents,
                    "involved_cases": inv_cases,
                    "involved_case_ids": inv_cases,
                    "relationships": rel_summaries,
                    "supporting_evidence": ev_list,
                    "evidence_ids": ev_list,
                    "explanation": f"Device '{dev_name}' ({eid}) is linked to multiple individuals [{', '.join(person_names)}] across distinct cases [{', '.join(inv_cases)}].",
                    "confidence": round(avg_conf, 2),
                    "confidence_tier": "HIGH" if avg_conf >= 0.85 else "MEDIUM",
                    "anomaly_score": round(min(1.0, 0.50 * avg_conf + 0.50 * (len(inv_cases) / 3.0)), 4),
                    "investigative_significance": "Indicates potential operational overlap or burner line sharing between separate syndicates.",
                    "investigative_lead": "Prioritize investigation of shared burner hardware.",
                    "limitations": "Device sharing may indicate relay infrastructure or co-location rather than direct conspiracy.",
                    "disclaimer": "Investigative pattern discovery only. Does not establish legal culpability or criminal intent.",
                    "provenance_sources": ["DATASET"],
                    "scoring_factors": {"cross_case_count": float(len(inv_cases))}
                })

        return patterns

    def _detect_multi_case_coordinators(self) -> List[Dict[str, Any]]:
        """MULTI_CASE_COORDINATOR: Detects entities linked to 2 or more active cases."""
        patterns = []

        for eid, ent in self.graph.entities.items():
            if eid.startswith("CASE_") or getattr(ent, "entity_type", "") == EntityType.CASE.value:
                continue

            linked_cases = self._get_entity_cases(eid)
            if len(linked_cases) >= 2:
                neighbors = self.graph.get_neighbors(eid, direction="undirected")
                edge_confidences = [r.confidence for r, _ in neighbors]
                evidence_ids = {ev for r, _ in neighbors for ev in getattr(r, "evidence_ids", [])}
                avg_conf = sum(edge_confidences) / len(edge_confidences) if edge_confidences else 0.90

                ent_name = self._get_entity_display_name(eid)
                inv_cases = sorted(list(linked_cases))
                ev_list = sorted(list(evidence_ids))
                severity = PatternSeverity.HIGH.value if len(linked_cases) >= 3 or len(neighbors) >= 5 else PatternSeverity.MEDIUM.value

                rel_summaries = [
                    {"relationship_id": r.id, "source": r.source_id, "target": r.target_id, "relationship": r.relationship.value if hasattr(r.relationship, "value") else str(r.relationship)}
                    for r, _ in neighbors
                ]

                patterns.append({
                    "pattern_id": f"PAT_COORD_{eid}",
                    "pattern_type": PatternType.MULTI_CASE_COORDINATOR.value,
                    "title": f"Cross-Case Linkage ({ent_name})",
                    "severity": severity,
                    "involved_entities": [eid],
                    "involved_entity_ids": [eid],
                    "involved_cases": inv_cases,
                    "involved_case_ids": inv_cases,
                    "relationships": rel_summaries,
                    "supporting_evidence": ev_list,
                    "evidence_ids": ev_list,
                    "explanation": f"Entity '{ent_name}' ({eid}) participates in {len(neighbors)} direct relationship(s) spanning multiple active investigation files [{', '.join(inv_cases)}].",
                    "confidence": round(avg_conf, 2),
                    "confidence_tier": "HIGH" if avg_conf >= 0.85 else "MEDIUM",
                    "anomaly_score": round(min(1.0, 0.60 * (len(inv_cases) / 3.0) + 0.40 * (len(neighbors) / 6.0)), 4),
                    "investigative_significance": "Key pivot node connecting separate investigation files for potential cross-jurisdiction coordination.",
                    "investigative_lead": f"Cross-reference case files [{', '.join(inv_cases)}] through shared node '{ent_name}'.",
                    "limitations": "Cross-case presence may stem from legitimate commercial, logistical, or geographic proximity.",
                    "disclaimer": "Investigative pattern discovery only. Does not establish legal culpability or criminal intent.",
                    "provenance_sources": ["DATASET"],
                    "scoring_factors": {"cross_case_count": float(len(inv_cases))}
                })

        return patterns

    def _detect_cross_case_bridge_paths(self) -> List[Dict[str, Any]]:
        """CROSS_CASE_BRIDGE_PATH: Multi-hop path connecting distinct cases."""
        patterns = []
        cases = [eid for eid in self.graph.entities.keys() if eid.startswith("CASE_")]

        for i in range(len(cases)):
            for j in range(i + 1, len(cases)):
                ca, cb = cases[i], cases[j]
                conns = find_cross_case_connections(self.graph, ca, cb, max_depth=6)
                if conns:
                    top_conn = conns[0]
                    path_nodes = top_conn.get("path", [])
                    ev_list = top_conn.get("evidence_ids", [])
                    shared = top_conn.get("shared_entities", [])

                    patterns.append({
                        "pattern_id": f"PAT_PATH_{ca}_{cb}",
                        "pattern_type": PatternType.CROSS_CASE_BRIDGE_PATH.value,
                        "title": f"Cross-Case Connection Path ({ca} <-> {cb})",
                        "severity": PatternSeverity.HIGH.value,
                        "involved_entities": path_nodes,
                        "involved_entity_ids": path_nodes,
                        "involved_cases": [ca, cb],
                        "involved_case_ids": [ca, cb],
                        "relationships": [],
                        "supporting_evidence": ev_list,
                        "evidence_ids": ev_list,
                        "explanation": f"Discovered multi-hop relationship path connecting {ca} to {cb} via shared infrastructure [{', '.join(shared)}].",
                        "confidence": top_conn.get("confidence", 0.90),
                        "confidence_tier": "HIGH",
                        "anomaly_score": 0.85,
                        "investigative_significance": f"Discovers structural bridge connecting {ca} and {cb}.",
                        "investigative_lead": f"Cross-reference case files {ca} and {cb}.",
                        "limitations": "Multi-hop path reflects structural connectivity.",
                        "disclaimer": "Investigative pattern discovery only. Does not establish legal culpability or criminal intent.",
                        "provenance_sources": ["DATASET"],
                        "scoring_factors": {"hop_count": float(len(path_nodes))}
                    })
        return patterns

    def _detect_high_density_clusters(self) -> List[Dict[str, Any]]:
        """HIGH_DENSITY_CLUSTER: High density interactions."""
        patterns = []
        for eid, ent in self.graph.entities.items():
            if eid.startswith("CASE_"):
                continue
            neighbors = self.graph.get_neighbors(eid, direction="undirected")
            if len(neighbors) >= 4:
                ent_name = self._get_entity_display_name(eid)
                linked_cases = sorted(list(self._get_entity_cases(eid)))
                ev_ids = list({ev for r, _ in neighbors for ev in getattr(r, "evidence_ids", [])})
                inv_ents = sorted(list({eid} | {n.id for _, n in neighbors}))

                patterns.append({
                    "pattern_id": f"PAT_CLUSTER_{eid}",
                    "pattern_type": PatternType.HIGH_DENSITY_CLUSTER.value,
                    "title": f"High-Density Interaction Cluster ({ent_name})",
                    "severity": PatternSeverity.MEDIUM.value,
                    "involved_entities": inv_ents,
                    "involved_entity_ids": inv_ents,
                    "involved_cases": linked_cases,
                    "involved_case_ids": linked_cases,
                    "relationships": [],
                    "supporting_evidence": ev_ids,
                    "evidence_ids": ev_ids,
                    "explanation": f"Entity '{ent_name}' ({eid}) forms a high-density interaction cluster with {len(neighbors)} direct neighbors.",
                    "confidence": 0.90,
                    "confidence_tier": "HIGH",
                    "anomaly_score": round(min(1.0, len(neighbors) / 8.0), 4),
                    "investigative_significance": "Local coordination hub.",
                    "investigative_lead": f"Analyze cluster around '{ent_name}'.",
                    "limitations": "High degree may indicate legitimate central hub.",
                    "disclaimer": "Investigative pattern discovery only. Does not establish legal culpability or criminal intent.",
                    "provenance_sources": ["DATASET"],
                    "scoring_factors": {"cluster_degree": float(len(neighbors))}
                })
        return patterns

    # --------------------------------------------------------------------------
    # DAY 30 NEW ANOMALY DETECTORS
    # --------------------------------------------------------------------------

    def _detect_high_connectivity_hubs(self) -> List[Dict[str, Any]]:
        """HIGH_CONNECTIVITY_HUB: Entities with exceptionally high degree."""
        patterns = []
        for eid, ent in self.graph.entities.items():
            if eid.startswith("CASE_"):
                continue
            neighbors = self.graph.get_neighbors(eid, direction="undirected")
            degree = len(neighbors)
            if degree >= 4:
                ent_name = self._get_entity_display_name(eid)
                linked_cases = sorted(list(self._get_entity_cases(eid)))
                edge_confidences = [r.confidence for r, _ in neighbors]
                avg_conf = sum(edge_confidences) / len(edge_confidences) if edge_confidences else 0.90
                evidence_ids = sorted(list({ev for r, _ in neighbors for ev in getattr(r, "evidence_ids", [])}))
                inv_ents = sorted(list({eid} | {n.id for _, n in neighbors}))

                deg_norm = min(1.0, degree / 10.0)
                cross_norm = min(1.0, len(linked_cases) / 3.0)
                div_types = len({getattr(r.relationship, "value", str(r.relationship)) for r, _ in neighbors})
                div_norm = min(1.0, div_types / 4.0)
                anomaly_score = round(min(1.0, 0.35 * deg_norm + 0.35 * cross_norm + 0.30 * div_norm), 4)

                patterns.append({
                    "pattern_id": f"PAT_HUB_{eid}",
                    "pattern_type": PatternType.HIGH_CONNECTIVITY_HUB.value,
                    "title": f"High-Connectivity Hub Node ({ent_name})",
                    "severity": PatternSeverity.HIGH.value if anomaly_score >= 0.70 else PatternSeverity.MEDIUM.value,
                    "involved_entities": inv_ents,
                    "involved_entity_ids": inv_ents,
                    "involved_cases": linked_cases,
                    "involved_case_ids": linked_cases,
                    "relationships": [],
                    "supporting_evidence": evidence_ids,
                    "evidence_ids": evidence_ids,
                    "explanation": f"Entity '{ent_name}' [{eid}] exhibits an exceptionally high connectivity degree ({degree} connections) spanning {len(linked_cases)} case file(s).",
                    "confidence": round(avg_conf, 2),
                    "confidence_tier": "HIGH" if avg_conf >= 0.85 else "MEDIUM",
                    "anomaly_score": anomaly_score,
                    "investigative_significance": "Central network hub.",
                    "investigative_lead": f"Prioritize analysis of hub node '{ent_name}'.",
                    "limitations": "High degree may indicate legitimate central relay node.",
                    "disclaimer": "Investigative pattern discovery only. Does not establish legal culpability or criminal intent.",
                    "provenance_sources": ["DATASET"],
                    "scoring_factors": {"degree_norm": deg_norm, "cross_case_norm": cross_norm, "diversity_norm": div_norm}
                })
        return patterns

    # --------------------------------------------------------------------------
    # COMPREHENSIVE PATTERN DISCOVERY SWEEP
    # --------------------------------------------------------------------------
    def detect_all_patterns(
        self,
        case_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        pattern_type: Optional[str] = None,
        min_severity: Optional[str] = None,
        min_confidence: Optional[float] = None,
        min_score: Optional[float] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Executes full pattern & anomaly detection sweep over the graph store."""
        all_patterns: List[Dict[str, Any]] = []

        all_patterns.extend(self._detect_shared_devices())
        all_patterns.extend(self._detect_multi_case_coordinators())
        all_patterns.extend(self._detect_cross_case_bridge_paths())
        all_patterns.extend(self._detect_high_density_clusters())
        all_patterns.extend(self._detect_high_connectivity_hubs())

        # Filtering logic
        filtered: List[Dict[str, Any]] = []
        for pat in all_patterns:
            inv_cases = pat.get("involved_cases", pat.get("involved_case_ids", []))
            inv_ents = pat.get("involved_entities", pat.get("involved_entity_ids", []))

            # Case filter
            if case_id and case_id not in inv_cases:
                continue

            # Entity filter
            if entity_id and entity_id not in inv_ents:
                continue

            # Pattern type filter
            if pattern_type and pat.get("pattern_type", "").upper() != pattern_type.upper():
                continue

            # Severity filter
            if min_severity:
                min_weight = SEVERITY_WEIGHTS.get(min_severity.upper(), 1)
                pat_weight = SEVERITY_WEIGHTS.get(str(pat.get("severity", "")).upper(), 1)
                if pat_weight < min_weight:
                    continue

            # Confidence filter
            if min_confidence is not None and pat.get("confidence", 0.0) < min_confidence:
                continue

            # Anomaly Score filter
            if min_score is not None and pat.get("anomaly_score", 0.0) < min_score:
                continue

            filtered.append(pat)

        # Sort by anomaly score descending, then confidence descending
        filtered.sort(key=lambda x: (-x.get("anomaly_score", 0.0), -x.get("confidence", 0.0)))
        return filtered[:limit]
