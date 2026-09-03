"""Network Intelligence and Advanced Key Player Engine for CrimeGraph AI (Day 28).

Provides explainable graph centrality, closeness, PageRank, community-reach,
bridge detection, cross-case influence ranking, and Key Player classification.
Adheres strictly to API_CONTRACT.md, DATA_SCHEMA.md, and SIH 2026 Problem Statement B3.
"""

from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple

from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.models.entities import EntityType
from crimegraph.models.intelligence import (
    KeyPlayerItem,
    KeyPlayerResponse,
    KeyPlayerRole,
    KeyPlayerSubMetrics,
)


class NetworkIntelligenceEngine:
    """Calculates network centrality, closeness, PageRank, bridge importance,
    cross-case reach, and key player intelligence across the knowledge graph.
    """

    def __init__(self, graph: KnowledgeGraphStore):
        self.graph = graph

    def compute_betweenness_centrality(self, node_ids: Optional[Set[str]] = None) -> Dict[str, float]:
        """Calculates betweenness centrality using Brandes' algorithm.
        
        If node_ids is provided, computes betweenness on the subgraph induced by node_ids.
        Otherwise computes over the entire graph.
        """
        nodes = sorted(list(node_ids)) if node_ids is not None else sorted(list(self.graph.entities.keys()))
        if not nodes:
            return {}

        node_set = set(nodes)
        betweenness = {v: 0.0 for v in nodes}

        # Build adjacency mapping restricted to node_set
        adj: Dict[str, Set[str]] = {v: set() for v in nodes}
        for rel in self.graph.get_all_relationships():
            u, v = rel.source_id, rel.target_id
            if u in node_set and v in node_set and u != v:
                adj[u].add(v)
                adj[v].add(u)

        for s in nodes:
            S: List[str] = []
            P: Dict[str, List[str]] = {w: [] for w in nodes}
            sigma: Dict[str, int] = {w: 0 for w in nodes}
            sigma[s] = 1
            d: Dict[str, int] = {w: -1 for w in nodes}
            d[s] = 0

            Q: deque = deque([s])
            while Q:
                v = Q.popleft()
                S.append(v)
                for w in sorted(adj[v]):
                    if d[w] < 0:
                        Q.append(w)
                        d[w] = d[v] + 1
                    if d[w] == d[v] + 1:
                        sigma[w] += sigma[v]
                        P[w].append(v)

            delta: Dict[str, float] = {w: 0.0 for w in nodes}
            while S:
                w = S.pop()
                for v in P[w]:
                    if sigma[w] > 0:
                        delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
                if w != s:
                    betweenness[w] += delta[w]

        # Undirected graph adjustment
        for v in nodes:
            betweenness[v] = betweenness[v] / 2.0

        return betweenness

    def compute_closeness_centrality(self, node_ids: Optional[Set[str]] = None) -> Dict[str, float]:
        """Calculates closeness centrality (reciprocal sum of shortest path distances)."""
        nodes = sorted(list(node_ids)) if node_ids is not None else sorted(list(self.graph.entities.keys()))
        if not nodes:
            return {}

        node_set = set(nodes)
        N = len(nodes)
        if N <= 1:
            return {v: 1.0 for v in nodes}

        adj: Dict[str, Set[str]] = {v: set() for v in nodes}
        for rel in self.graph.get_all_relationships():
            u, v = rel.source_id, rel.target_id
            if u in node_set and v in node_set and u != v:
                adj[u].add(v)
                adj[v].add(u)

        closeness: Dict[str, float] = {}
        for s in nodes:
            # BFS for shortest path distances
            dist: Dict[str, int] = {s: 0}
            Q: deque = deque([s])
            while Q:
                u = Q.popleft()
                for v in sorted(adj[u]):
                    if v not in dist:
                        dist[v] = dist[u] + 1
                        Q.append(v)

            reachable_count = len(dist)
            total_dist = sum(dist.values())

            if total_dist > 0 and reachable_count > 1:
                # Wasserman & Faust formula for disconnected components
                raw_c = (reachable_count - 1) / total_dist
                component_fraction = (reachable_count - 1) / (N - 1)
                closeness[s] = raw_c * component_fraction
            else:
                closeness[s] = 0.0

        return closeness

    def compute_pagerank(
        self,
        node_ids: Optional[Set[str]] = None,
        damping: float = 0.85,
        max_iter: int = 100,
        tol: float = 1e-6
    ) -> Dict[str, float]:
        """Calculates PageRank centrality iteratively."""
        nodes = sorted(list(node_ids)) if node_ids is not None else sorted(list(self.graph.entities.keys()))
        if not nodes:
            return {}

        node_set = set(nodes)
        N = len(nodes)
        if N == 1:
            return {nodes[0]: 1.0}

        adj: Dict[str, List[str]] = {v: [] for v in nodes}
        for rel in self.graph.get_all_relationships():
            u, v = rel.source_id, rel.target_id
            if u in node_set and v in node_set and u != v:
                adj[u].append(v)
                adj[v].append(u)

        pr = {v: 1.0 / N for v in nodes}

        for _ in range(max_iter):
            next_pr = {v: (1.0 - damping) / N for v in nodes}
            dangling_sum = sum(pr[v] for v in nodes if len(adj[v]) == 0)

            for u in nodes:
                deg = len(adj[u])
                if deg > 0:
                    share = damping * (pr[u] / deg)
                    for v in adj[u]:
                        next_pr[v] += share
                else:
                    share = damping * (pr[u] / N)
                    for v in nodes:
                        next_pr[v] += share

            diff = sum(abs(next_pr[v] - pr[v]) for v in nodes)
            pr = next_pr
            if diff < tol:
                break

        return pr

    def find_connected_cases_for_entity(self, entity_id: str, max_depth: int = 2) -> Set[str]:
        """Finds all distinct Case IDs connected to an entity within max_depth hops."""
        if entity_id not in self.graph.entities:
            return set()

        entity = self.graph.get_entity(entity_id)
        if entity and entity.entity_type == EntityType.CASE.value:
            return {entity_id}

        connected_cases: Set[str] = set()
        visited: Set[str] = {entity_id}
        queue: deque = deque([(entity_id, 0)])

        while queue:
            curr_id, depth = queue.popleft()
            curr_entity = self.graph.get_entity(curr_id)
            if curr_entity and curr_entity.entity_type == EntityType.CASE.value:
                connected_cases.add(curr_id)

            if depth < max_depth:
                for _, neighbor in self.graph.get_neighbors(curr_id):
                    if neighbor.id not in visited:
                        visited.add(neighbor.id)
                        queue.append((neighbor.id, depth + 1))

        return connected_cases

    def classify_key_player_role(self, metrics: Dict[str, Any], case_count: int, community_reach: int) -> KeyPlayerRole:
        """Deterministically classifies an entity into a Key Player role based on graph metrics."""
        d_score = metrics.get("degree_score", 0.0)
        b_score = metrics.get("betweenness_score", 0.0)
        c_score = metrics.get("closeness_score", 0.0)
        p_score = metrics.get("pagerank_score", 0.0)
        br_score = metrics.get("bridge_score", 0.0)
        cr_score = metrics.get("cross_case_score", 0.0)
        overall = metrics.get("composite_score", 0.0)

        if case_count >= 2 and cr_score >= 0.40:
            return KeyPlayerRole.CROSS_CASE_INFLUENCER
        if br_score >= 0.50 or b_score >= 0.50:
            return KeyPlayerRole.BRIDGE_ENTITY
        if d_score >= 0.65 and p_score >= 0.55:
            return KeyPlayerRole.CORE_HUB
        if c_score >= 0.50 and b_score >= 0.35:
            return KeyPlayerRole.INFORMATION_BROKER
        if community_reach >= 2 and overall >= 0.50:
            return KeyPlayerRole.COMMUNITY_INFLUENCER
        if d_score >= 0.50:
            return KeyPlayerRole.HIGH_CONNECTIVITY_ENTITY

        return KeyPlayerRole.EMERGING_KEY_PLAYER

    def calculate_entity_metrics(
        self,
        entity_id: str,
        betweenness_map: Optional[Dict[str, float]] = None,
        closeness_map: Optional[Dict[str, float]] = None,
        pagerank_map: Optional[Dict[str, float]] = None,
        max_degree: int = 1,
        max_betweenness: float = 1.0,
        max_closeness: float = 1.0,
        max_pagerank: float = 1.0,
        total_case_count: int = 1,
        total_rel_types: int = 1
    ) -> Dict[str, Any]:
        """Calculates normalized sub-metrics and composite score for an entity."""
        entity = self.graph.get_entity(entity_id)
        if not entity:
            raise KeyError(f"Entity '{entity_id}' not found in knowledge graph store")

        # 1. Degree & Neighborhood
        incident_neighbors = self.graph.get_neighbors(entity_id, direction="undirected")
        incident_edges = [rel for rel, _ in incident_neighbors]
        neighbors = set()
        for rel in incident_edges:
            other = rel.target_id if rel.source_id == entity_id else rel.source_id
            if other != entity_id:
                neighbors.add(other)

        raw_degree = len(neighbors)
        degree_score = round(min(1.0, raw_degree / max(1, max_degree)), 4)

        # 2. Betweenness / Bridge Importance
        raw_betweenness = (betweenness_map or {}).get(entity_id, 0.0)
        betweenness_score = round(
            min(1.0, raw_betweenness / max_betweenness) if max_betweenness > 0 else 0.0,
            4
        )

        # 3. Closeness Centrality
        raw_closeness = (closeness_map or {}).get(entity_id, 0.0)
        closeness_score = round(
            min(1.0, raw_closeness / max_closeness) if max_closeness > 0 else 0.0,
            4
        )

        # 4. PageRank Influence
        raw_pagerank = (pagerank_map or {}).get(entity_id, 0.0)
        pagerank_score = round(
            min(1.0, raw_pagerank / max_pagerank) if max_pagerank > 0 else 0.0,
            4
        )

        # 5. Cross-Case Reach
        connected_cases = sorted(list(self.find_connected_cases_for_entity(entity_id, max_depth=2)))
        case_count = len(connected_cases)
        if case_count <= 0:
            cross_case_score = 0.0
        elif case_count == 1:
            cross_case_score = 0.40
        else:
            cross_case_score = round(min(1.0, 0.40 + 0.30 * (case_count - 1)), 4)

        # 6. Relationship Diversity & Evidence Support
        rel_types: Set[str] = set()
        confidences: List[float] = []
        evidence_ids: Set[str] = set()

        for rel in incident_edges:
            rtype = rel.relationship.value if hasattr(rel.relationship, "value") else str(rel.relationship)
            rel_types.add(rtype)
            confidences.append(rel.confidence)
            evidence_ids.update(rel.evidence_ids)

        if getattr(entity, "source_ids", None):
            evidence_ids.update(entity.source_ids)

        diversity_count = len(rel_types)
        rel_diversity_score = round(min(1.0, diversity_count / max(1, min(total_rel_types, 4))), 4)

        if confidences:
            avg_conf = sum(confidences) / len(confidences)
            ev_count = len(evidence_ids)
            ev_bonus = min(1.0, ev_count / 3.0)
            evidence_support_score = round(0.6 * avg_conf + 0.4 * ev_bonus, 4)
        else:
            evidence_support_score = 0.85

        # 7. Bridge Score (betweenness + cross-case bonus)
        bridge_score = round(min(1.0, 0.6 * betweenness_score + 0.4 * cross_case_score), 4)

        # 8. Community Reach Score
        community_reach_count = min(3, max(1, case_count))
        community_reach_score = round(min(1.0, community_reach_count / 3.0), 4)

        # Composite Influence Score
        # Weights: Degree (20%), Betweenness (20%), Closeness (15%), PageRank (15%), Cross-Case (15%), Bridge (15%)
        composite_score = round(
            0.20 * degree_score +
            0.20 * betweenness_score +
            0.15 * closeness_score +
            0.15 * pagerank_score +
            0.15 * cross_case_score +
            0.15 * bridge_score,
            4
        )

        metrics_dict = {
            "degree_score": degree_score,
            "betweenness_score": betweenness_score,
            "closeness_score": closeness_score,
            "pagerank_score": pagerank_score,
            "cross_case_score": cross_case_score,
            "community_reach_score": community_reach_score,
            "bridge_score": bridge_score,
            "composite_score": composite_score,
            "direct_connections": raw_degree,
            "raw_betweenness": round(raw_betweenness, 4),
            "case_count": case_count,
            "community_reach_count": community_reach_count,
            "relationship_types_count": diversity_count,
            "relationship_diversity_score": rel_diversity_score,
            "evidence_support_score": evidence_support_score,
            "evidence_count": len(evidence_ids),
            "average_edge_confidence": round(sum(confidences)/len(confidences), 4) if confidences else 0.95
        }

        role = self.classify_key_player_role(metrics_dict, case_count, community_reach_count)

        return {
            "entity_id": entity_id,
            "entity_name": getattr(entity, "name", getattr(entity, "title", getattr(entity, "id", entity_id))),
            "entity_type": entity.entity_type,
            "influence_score": composite_score,
            "influence_role": role,
            "connected_cases": connected_cases,
            "supporting_evidence_ids": sorted(list(evidence_ids)),
            "provenance": getattr(entity, "origin", "DATASET"),
            "confidence": round(sum(confidences)/len(confidences), 4) if confidences else 0.95,
            "metrics": metrics_dict
        }

    def generate_explanation_reasons(self, entity_data: Dict[str, Any]) -> List[str]:
        """Generates clear, investigative, non-culpatory factual reasons for an entity's network ranking."""
        m = entity_data.get("metrics", {})
        reasons = []

        direct_conn = m.get("direct_connections", 0)
        if direct_conn >= 3:
            reasons.append(f"Highly connected within network graph with {direct_conn} direct entity associations")
        elif direct_conn >= 1:
            reasons.append(f"Directly connected to {direct_conn} entity record(s)")

        cases = entity_data.get("connected_cases", [])
        if len(cases) >= 2:
            case_str = ", ".join(cases)
            reasons.append(f"Acts as a cross-case linkage across {len(cases)} distinct cases ({case_str})")
        elif len(cases) == 1:
            reasons.append(f"Associated with case {cases[0]}")

        betweenness_score = m.get("betweenness_score", 0.0)
        if betweenness_score >= 0.5:
            reasons.append("Pivotal communication/activity bridge connecting otherwise distinct network clusters")
        elif betweenness_score >= 0.2:
            reasons.append("Intermediate structural bridge within the observed network graph")

        closeness_score = m.get("closeness_score", 0.0)
        if closeness_score >= 0.5:
            reasons.append("High closeness centrality allowing rapid information propagation across the graph")

        ev_count = m.get("evidence_count", 0)
        avg_conf = m.get("average_edge_confidence", 0.0)
        if ev_count > 0:
            reasons.append(f"Supported by {ev_count} verified evidentiary item(s) (avg confidence {int(avg_conf * 100)}%)")

        return reasons

    def generate_explanation_text(self, entity_data: Dict[str, Any]) -> str:
        """Generates a cohesive, non-guilt investigative summary for a key player."""
        name = entity_data.get("entity_name", entity_data.get("entity_id"))
        role = entity_data.get("influence_role", "KEY_PLAYER")
        score = entity_data.get("influence_score", 0.0)
        cases = entity_data.get("connected_cases", [])
        m = entity_data.get("metrics", {})

        role_str = str(role).replace("_", " ").title()
        case_info = f"across {len(cases)} cases ({', '.join(cases)})" if len(cases) >= 2 else f"in case {cases[0]}" if cases else "in knowledge graph"

        return (
            f"{name} is classified as a {role_str} {case_info} with a composite network influence score of {score:.4f}. "
            f"Demonstrates high structural connectivity with {m.get('direct_connections', 0)} direct associations and "
            f"betweenness centrality of {m.get('betweenness_score', 0.0):.4f}."
        )

    def rank_entities(
        self,
        scope_entity_ids: Optional[Set[str]] = None,
        entity_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Ranks entities deterministically by composite network influence score."""
        all_entity_ids = set(self.graph.entities.keys())
        target_ids = (scope_entity_ids & all_entity_ids) if scope_entity_ids is not None else all_entity_ids

        if not target_ids:
            return []

        if entity_type:
            target_ids = {
                eid for eid in target_ids
                if self.graph.entities[eid].entity_type == entity_type.strip().upper()
            }

        if not target_ids:
            return []

        betweenness_map = self.compute_betweenness_centrality(scope_entity_ids)
        closeness_map = self.compute_closeness_centrality(scope_entity_ids)
        pagerank_map = self.compute_pagerank(scope_entity_ids)

        all_cases = self.graph.get_entities_by_type(EntityType.CASE)
        total_cases = max(1, len(all_cases))
        all_rels = self.graph.get_all_relationships()
        total_rel_types = max(1, len({r.relationship for r in all_rels}))

        max_degree = 1
        max_betweenness = 0.0001
        max_closeness = 0.0001
        max_pagerank = 0.0001

        for eid in target_ids:
            degree = len(self.graph.get_neighbors(eid))
            if degree > max_degree:
                max_degree = degree
            if betweenness_map.get(eid, 0.0) > max_betweenness:
                max_betweenness = betweenness_map[eid]
            if closeness_map.get(eid, 0.0) > max_closeness:
                max_closeness = closeness_map[eid]
            if pagerank_map.get(eid, 0.0) > max_pagerank:
                max_pagerank = pagerank_map[eid]

        ranked_list: List[Dict[str, Any]] = []
        for eid in sorted(target_ids):
            item = self.calculate_entity_metrics(
                entity_id=eid,
                betweenness_map=betweenness_map,
                closeness_map=closeness_map,
                pagerank_map=pagerank_map,
                max_degree=max_degree,
                max_betweenness=max_betweenness,
                max_closeness=max_closeness,
                max_pagerank=max_pagerank,
                total_case_count=total_cases,
                total_rel_types=total_rel_types
            )
            item["reasons"] = self.generate_explanation_reasons(item)
            item["explanation"] = self.generate_explanation_text(item)
            ranked_list.append(item)

        # Deterministic sorting
        ranked_list.sort(
            key=lambda x: (-x["influence_score"], -x["metrics"]["direct_connections"], x["entity_id"])
        )

        for idx, item in enumerate(ranked_list, start=1):
            item["rank"] = idx

        if limit is not None and limit > 0:
            ranked_list = ranked_list[:limit]

        return ranked_list

    def get_advanced_key_players(
        self,
        case_id: Optional[str] = None,
        role: Optional[str] = None,
        entity_type: Optional[str] = None,
        limit: int = 10,
        min_score: float = 0.0
    ) -> KeyPlayerResponse:
        """Retrieves explainable Key Player & Influencer Intelligence (Day 28)."""
        scope_ids = None
        analysis_scope = "GLOBAL"

        if case_id:
            case_id = case_id.strip()
            if case_id not in self.graph.entities:
                raise KeyError(f"Case '{case_id}' not found in knowledge graph store")
            subgraph = self.graph.get_case_subgraph(case_id)
            scope_ids = set(node["id"] for node in subgraph.get("nodes", []))
            analysis_scope = f"CASE:{case_id}"

        filter_type = None if (not entity_type or entity_type.upper() in ["ALL", "*"]) else entity_type.strip().upper()
        filter_role = None if (not role or role.upper() in ["ALL", "*"]) else role.strip().upper()

        ranked_raw = self.rank_entities(scope_entity_ids=scope_ids, entity_type=filter_type, limit=None)

        filtered_items: List[KeyPlayerItem] = []
        for raw in ranked_raw:
            if raw["influence_score"] < min_score:
                continue

            r_val = raw["influence_role"]
            r_str = r_val.value if hasattr(r_val, "value") else str(r_val)
            if filter_role and r_str.upper() != filter_role:
                continue

            m = raw["metrics"]
            sub_metrics = KeyPlayerSubMetrics(
                degree_score=m["degree_score"],
                betweenness_score=m["betweenness_score"],
                closeness_score=m["closeness_score"],
                pagerank_score=m["pagerank_score"],
                cross_case_score=m["cross_case_score"],
                community_reach_score=m["community_reach_score"],
                bridge_score=m["bridge_score"],
                direct_connections=m["direct_connections"],
                raw_betweenness=m["raw_betweenness"],
                case_count=m["case_count"],
                community_reach_count=m["community_reach_count"],
                evidence_count=m["evidence_count"],
                average_edge_confidence=m["average_edge_confidence"]
            )

            kp_item = KeyPlayerItem(
                rank=len(filtered_items) + 1,
                entity_id=raw["entity_id"],
                entity_name=raw["entity_name"],
                entity_type=raw["entity_type"],
                score=raw["influence_score"],
                influence_role=KeyPlayerRole(r_str),
                metrics=sub_metrics,
                connected_case_ids=raw["connected_cases"],
                connected_entity_count=m["direct_connections"],
                bridge_count=int(m["raw_betweenness"]),
                supporting_evidence_ids=raw["supporting_evidence_ids"],
                provenance=raw["provenance"],
                explanation=raw["explanation"],
                reasons=raw["reasons"],
                confidence=raw["confidence"]
            )
            filtered_items.append(kp_item)

            if limit > 0 and len(filtered_items) >= limit:
                break

        return KeyPlayerResponse(
            scope=analysis_scope,
            case_id=case_id,
            filter_role=filter_role,
            filter_entity_type=filter_type,
            total_entities_analyzed=len(scope_ids) if scope_ids else len(self.graph.entities),
            key_players_count=len(filtered_items),
            key_players=filtered_items
        )

    def get_case_influencers(
        self,
        case_id: str,
        entity_type: Optional[str] = "PERSON",
        limit: int = 10
    ) -> Dict[str, Any]:
        """Returns ranked influencer entities associated with a specific case."""
        case_id = case_id.strip()
        if case_id not in self.graph.entities:
            raise KeyError(f"Case '{case_id}' not found in knowledge graph store")

        subgraph = self.graph.get_case_subgraph(case_id)
        node_ids = {n["id"] for n in subgraph.get("nodes", [])}

        results = self.rank_entities(
            scope_entity_ids=node_ids,
            entity_type=entity_type,
            limit=limit
        )

        return {
            "case_id": case_id,
            "entity_type_filter": entity_type.upper() if entity_type else "ALL",
            "total_entities_analyzed": len(node_ids),
            "results_count": len(results),
            "results": results
        }

    def get_case_network_intelligence(self, case_id: str) -> Dict[str, Any]:
        """Provides comprehensive network topology, bridge analysis, and cross-case intelligence for a case."""
        case_id = case_id.strip()
        if case_id not in self.graph.entities:
            raise KeyError(f"Case '{case_id}' not found in knowledge graph store")

        subgraph = self.graph.get_case_subgraph(case_id)
        node_ids = {n["id"] for n in subgraph.get("nodes", [])}

        all_ranked = self.rank_entities(scope_entity_ids=node_ids, limit=10)
        key_individuals = self.rank_entities(scope_entity_ids=node_ids, entity_type="PERSON", limit=5)
        bridge_entities = [e for e in all_ranked if e["metrics"]["betweenness_score"] >= 0.25]
        cross_case_connectors = [e for e in all_ranked if e["metrics"]["case_count"] >= 2]

        return {
            "case_id": case_id,
            "network_summary": {
                "total_nodes": len(subgraph.get("nodes", [])),
                "total_edges": len(subgraph.get("edges", [])),
                "bridge_entities_count": len(bridge_entities),
                "cross_case_connectors_count": len(cross_case_connectors),
                "high_influence_entities_count": len([e for e in all_ranked if e["influence_score"] >= 0.70])
            },
            "key_individuals": key_individuals,
            "top_influencers": all_ranked,
            "bridge_entities": bridge_entities,
            "cross_case_connectors": cross_case_connectors,
            "safety_notice": "Network influence metrics indicate structural connectivity and do not establish legal guilt."
        }
