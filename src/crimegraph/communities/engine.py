"""Community & Criminal Group Detection Engine for CrimeGraph AI (Day 27).

Provides deterministic graph community detection, shared infrastructure identification,
bridge entity detection, density analysis, and explainable investigative risk scoring.
Adheres strictly to the non-guilt guarantee.
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.models.entities import EntityType
from crimegraph.communities.models import (
    CommunityClassification,
    CommunityConfidenceTier,
    CommunityDetectionSummary,
    CommunityMember,
    DetectedCommunity,
    MemberRole,
)


class CommunityDetectionEngine:
    """Deterministic, explainable community and group detection engine."""

    def __init__(self, store: KnowledgeGraphStore):
        self.store = store

    def detect_communities(
        self,
        case_id: Optional[str] = None,
        min_cluster_size: int = 3
    ) -> CommunityDetectionSummary:
        """Detects densely connected communities across the graph or within a case scope."""
        # 1. Determine target entity subset
        if case_id:
            if case_id not in self.store.entities:
                raise ValueError(f"Case '{case_id}' not found in knowledge graph.")
            subgraph = self.store.get_case_subgraph(case_id)
            target_entity_ids = set(node["id"] for node in subgraph.get("nodes", []))
        else:
            target_entity_ids = set(self.store.entities.keys())

        # Build adjacency graph
        adj: Dict[str, Set[str]] = defaultdict(set)
        edge_map: Dict[Tuple[str, str], str] = {}
        for r_id, rel in self.store.relationships.items():
            u, v = rel.source_id, rel.target_id
            if u in target_entity_ids and v in target_entity_ids:
                adj[u].add(v)
                adj[v].add(u)
                edge_map[(min(u, v), max(u, v))] = r_id

        # 2. Extract Connected Components / Dense Clusters
        visited: Set[str] = set()
        raw_components: List[Set[str]] = []

        # Sort entity IDs for deterministic traversal order
        sorted_entities = sorted(list(target_entity_ids))
        for eid in sorted_entities:
            if eid not in visited and adj[eid]:
                comp: Set[str] = set()
                queue = [eid]
                visited.add(eid)
                while queue:
                    curr = queue.pop(0)
                    comp.add(curr)
                    for nbr in sorted(list(adj[curr])):
                        if nbr not in visited:
                            visited.add(nbr)
                            queue.append(nbr)
                if len(comp) >= min_cluster_size:
                    raw_components.append(comp)

        # 3. Analyze, Score, and Characterize each Detected Community
        detected_list: List[DetectedCommunity] = []
        clustered_count = 0

        for comp_idx, comp_nodes in enumerate(raw_components, 1):
            community = self._analyze_community(comp_idx, comp_nodes, adj, edge_map, case_id)
            detected_list.append(community)
            clustered_count += len(comp_nodes)

        # Sort communities by member count descending, then density score
        detected_list.sort(key=lambda c: (c.member_count, c.density_score), reverse=True)

        return CommunityDetectionSummary(
            total_communities=len(detected_list),
            total_clustered_entities=clustered_count,
            case_id=case_id,
            communities=detected_list
        )

    def get_community_by_id(self, community_id: str) -> Optional[DetectedCommunity]:
        """Finds a specific detected community by its generated ID."""
        summary = self.detect_communities()
        for c in summary.communities:
            if c.community_id == community_id:
                return c
        return None

    def _analyze_community(
        self,
        index: int,
        nodes: Set[str],
        adj: Dict[str, Set[str]],
        edge_map: Dict[Tuple[str, str], str],
        scoped_case_id: Optional[str]
    ) -> DetectedCommunity:
        """Calculates topological metrics, structural roles, classification, and explainable leads."""
        n = len(nodes)
        node_list = sorted(list(nodes))
        
        # Calculate internal and external relationships
        internal_edges: Set[str] = set()
        external_edge_count = 0
        node_degrees: Dict[str, int] = defaultdict(int)

        for u in node_list:
            for v in adj[u]:
                if v in nodes:
                    if u < v:
                        pair = (u, v)
                        if pair in edge_map:
                            internal_edges.add(edge_map[pair])
                    node_degrees[u] += 1
                else:
                    external_edge_count += 1

        internal_count = len(internal_edges)
        possible_edges = (n * (n - 1)) / 2 if n > 1 else 1
        density = round(internal_count / possible_edges, 4) if possible_edges > 0 else 0.0

        # Structural Roles: Core, Bridge, Infrastructure, Peripheral
        members: List[CommunityMember] = []
        central_ids: List[str] = []
        bridge_ids: List[str] = []
        shared_infra_ids: List[str] = []
        cases_involved: Set[str] = set()
        evidence_ids: Set[str] = set()
        provenance_ids: Set[str] = set()

        avg_degree = sum(node_degrees.values()) / n if n > 0 else 0

        for eid in node_list:
            ent = self.store.entities.get(eid)
            etype = ent.entity_type if ent else "UNKNOWN"
            ename = getattr(ent, "name", None) or getattr(ent, "phone_number", None) or getattr(ent, "registration_number", None) or eid
            deg = node_degrees[eid]

            # Collect linked cases & evidence
            if etype == EntityType.CASE.value:
                cases_involved.add(eid)
            for sid in getattr(ent, "source_ids", []):
                evidence_ids.add(sid)
            for p in self.store.get_entity_provenance(eid):
                provenance_ids.add(p.provenance_id)

            # Determine Member Role
            if etype in [EntityType.PHONE.value, EntityType.VEHICLE.value, EntityType.ACCOUNT.value]:
                role = MemberRole.INFRASTRUCTURE
                shared_infra_ids.append(eid)
            elif deg > avg_degree + 1 or deg >= 3:
                role = MemberRole.CORE
                central_ids.append(eid)
            elif len(adj[eid] - nodes) > 0 or etype == EntityType.PERSON.value and deg >= 2:
                role = MemberRole.BRIDGE
                bridge_ids.append(eid)
            else:
                role = MemberRole.PERIPHERAL

            members.append(CommunityMember(
                entity_id=eid,
                entity_type=etype,
                name=ename,
                structural_role=role,
                degree=deg,
                betweenness_score=round(deg / max(1, n - 1), 3)
            ))

        # Check for cross-case links
        if not cases_involved:
            # Inspect connected neighbors for cases
            for eid in node_list:
                for nbr in adj[eid]:
                    if nbr in self.store.entities and self.store.entities[nbr].entity_type == EntityType.CASE.value:
                        cases_involved.add(nbr)

        # Classification Determination
        if len(cases_involved) >= 2:
            classification = CommunityClassification.CROSS_CASE_COMMUNITY
        elif shared_infra_ids and any(self.store.entities[i].entity_type == EntityType.PHONE.value for i in shared_infra_ids):
            classification = CommunityClassification.SHARED_DEVICE_CLUSTER
        elif density >= 0.40:
            classification = CommunityClassification.HIGH_CONNECTIVITY_COMMUNITY
        elif shared_infra_ids:
            classification = CommunityClassification.FINANCIAL_LINKED_CLUSTER
        else:
            classification = CommunityClassification.MIXED_EVIDENCE_COMMUNITY

        # Investigative Risk Indicator (Explainable, based on density + shared infra + cross-case)
        risk_score = 0.50
        if len(cases_involved) >= 2:
            risk_score += 0.25
        if shared_infra_ids:
            risk_score += 0.15
        if density >= 0.30:
            risk_score += 0.10
        risk_score = min(1.0, round(risk_score, 2))

        # Confidence & Tier
        confidence = 0.90 if len(evidence_ids) >= 3 else 0.75
        tier = CommunityConfidenceTier.HIGH if confidence >= 0.85 else CommunityConfidenceTier.MEDIUM

        # Explainable Investigative Leads
        leads = [
            f"Cluster connects {n} entities with {internal_count} verified relationships (density: {density:.2f}).",
            f"Key infrastructure identified: {shared_infra_ids or 'None directly clustered'}."
        ]
        if len(cases_involved) >= 2:
            leads.append(f"Cross-case coordination detected across cases: {sorted(list(cases_involved))}.")
        if central_ids:
            leads.append(f"Highly connected central nodes: {central_ids}.")

        limitations = [
            "Graph topology indicates relational proximity, not criminal conspiracy.",
            "All identified bridges and infrastructure require human officer corroboration."
        ]

        return DetectedCommunity(
            community_id=f"COMM_CLUST_{index:03d}",
            classification=classification,
            members=members,
            member_entity_ids=node_list,
            member_count=n,
            internal_relationship_count=internal_count,
            external_relationship_count=external_edge_count,
            density_score=density,
            group_risk_score=risk_score,
            confidence=confidence,
            confidence_tier=tier,
            central_entity_ids=central_ids,
            bridge_entity_ids=bridge_ids,
            shared_infrastructure_ids=shared_infra_ids,
            linked_case_ids=sorted(list(cases_involved)),
            supporting_evidence_ids=sorted(list(evidence_ids)),
            supporting_relationship_ids=sorted(list(internal_edges)),
            source_provenance_ids=sorted(list(provenance_ids)),
            investigative_leads=leads,
            limitations=limitations
        )
