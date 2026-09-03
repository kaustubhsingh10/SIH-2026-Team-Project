"""ML / Data Mining + Investigative Risk Scoring Engine for CrimeGraph AI.

Combines graph analytics feature extraction, statistical anomaly ranking, and rule-assisted
hybrid ML scoring to compute explainable Investigative Priority Scores (0-100).

IMPORTANT:
Risk scores measure INVESTIGATIVE PRIORITY for resource allocation based on observable
graph signals. They do NOT measure probability of guilt or criminal intent.
"""

from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Tuple

from crimegraph.communities.engine import CommunityDetectionEngine
from crimegraph.graph.correlation import CrossSourceCorrelationEngine
from crimegraph.graph.intelligence import NetworkIntelligenceEngine
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.graph.patterns import SuspiciousPatternEngine
from crimegraph.models.risk import (
    CaseRiskResponse,
    EntityRiskFeatureVector,
    EntityRiskResponse,
    RiskLevel,
    RiskPriorityItem,
    RiskSignal,
)


class InvestigativeRiskEngine:
    """Orchestrates feature mining, statistical anomaly weighting, and explainable risk scoring."""

    def __init__(self, graph_store: KnowledgeGraphStore):
        self.graph = graph_store
        self.key_player_engine = NetworkIntelligenceEngine(graph_store)
        self.pattern_engine = SuspiciousPatternEngine(graph_store)
        self.correlation_engine = CrossSourceCorrelationEngine(graph_store)
        self.community_engine = CommunityDetectionEngine(graph_store)

    def _get_entity_cases(self, entity_id: str) -> List[str]:
        cases = set()
        if entity_id.startswith("CASE_"):
            cases.add(entity_id)
            return sorted(list(cases))
        for rel, nbr in self.graph.get_neighbors(entity_id, direction="undirected"):
            if nbr.id.startswith("CASE_") or getattr(nbr, "entity_type", "") == "CASE":
                cases.add(nbr.id)
            elif getattr(nbr, "entity_type", "") == "PERSON":
                for p_rel, p_nbr in self.graph.get_neighbors(nbr.id, direction="undirected"):
                    if p_nbr.id.startswith("CASE_") or getattr(p_nbr, "entity_type", "") == "CASE":
                        cases.add(p_nbr.id)
        return sorted(list(cases))

    def _get_case_entities(self, case_id: str) -> List[str]:
        if case_id not in self.graph.entities:
            return []
        subgraph = self.graph.get_case_subgraph(case_id)
        return [node["id"] for node in subgraph.get("nodes", []) if node["id"] != case_id]

    def extract_feature_vector(self, entity_id: str) -> EntityRiskFeatureVector:
        """Extracts a structured 12-dimensional feature vector for an entity from graph analytics."""
        entity_id = entity_id.strip()
        entity = self.graph.get_entity(entity_id)
        if not entity:
            return EntityRiskFeatureVector(entity_id=entity_id, entity_type="UNKNOWN")

        # 1. Direct Topology Features
        neighbors = self.graph.get_neighbors(entity_id, direction="undirected")
        degree = len(neighbors)

        weighted_degree = 0.0
        evidence_ids_set = set()
        connected_case_ids = set()

        for rel, nbr in neighbors:
            weighted_degree += getattr(rel, "confidence", 0.95)
            for ev_id in getattr(rel, "evidence_ids", []):
                evidence_ids_set.add(ev_id)
            if nbr.id.startswith("CASE_") or getattr(nbr, "entity_type", "") == "CASE":
                connected_case_ids.add(nbr.id)

        # 2. Day 27 Community Membership
        comm_summary = self.community_engine.detect_communities()
        community_count = sum(
            1 for c in getattr(comm_summary, "communities", [])
            for m in getattr(c, "members", []) if getattr(m, "entity_id", None) == entity_id
        )

        # 3. Day 28 Key Player & Centrality
        kp_res = self.key_player_engine.get_advanced_key_players(limit=100)
        centrality_score = 0.0
        for kp in kp_res.key_players:
            if kp.entity_id == entity_id:
                centrality_score = float(kp.score)
                break

        # 4. Day 30 Pattern & Anomaly Features
        patterns = self.pattern_engine.detect_all_patterns(entity_id=entity_id, limit=50)
        pattern_count = len(patterns)
        anomaly_score = max([p.get("anomaly_score", 0.0) for p in patterns], default=0.0)

        # 5. Day 32 Cross-Source Correlation Features
        correlations = self.correlation_engine.detect_all_correlations(entity_id=entity_id, limit=50)
        cross_source_count = len(set(
            src for c in correlations for src in c.get("provenance_sources", [])
        ))
        correlation_score = max([c.get("correlation_score", 0.0) for c in correlations], default=0.0)

        # 6. Cross-Case Connectors
        cross_case_count = len(connected_case_ids)

        return EntityRiskFeatureVector(
            entity_id=entity_id,
            entity_type=getattr(entity, "entity_type", "ENTITY"),
            degree=degree,
            weighted_degree=round(weighted_degree, 2),
            case_count=len(connected_case_ids),
            community_count=community_count,
            cross_case_count=cross_case_count,
            centrality_score=round(centrality_score, 4),
            anomaly_score=round(anomaly_score, 4),
            pattern_count=pattern_count,
            correlation_score=round(correlation_score, 4),
            cross_source_count=cross_source_count,
            evidence_count=len(evidence_ids_set)
        )

    def calculate_entity_risk(self, entity_id: str) -> EntityRiskResponse:
        """Computes an explainable Investigative Priority Score (0-100) for a given entity."""
        entity_id = entity_id.strip()
        entity = self.graph.get_entity(entity_id)
        if not entity:
            raise KeyError(f"Entity '{entity_id}' not found")

        features = self.extract_feature_vector(entity_id)
        signals: List[RiskSignal] = []
        total_raw_points = 0.0

        # Signal 1: Cross-Case Bridge Connectivity (Weight: 25%)
        if features.cross_case_count > 1:
            pts = min(25.0, features.cross_case_count * 12.5)
            total_raw_points += pts
            signals.append(RiskSignal(
                signal_type="CROSS_CASE_HUB",
                description=f"Entity bridges {features.cross_case_count} independent investigation cases.",
                weight=0.25,
                score_contribution=round(pts, 2),
                evidence_ids=self._get_entity_cases(entity_id)[:3]
            ))

        # Signal 2: Topological Pattern Anomaly Density (Weight: 25%)
        if features.anomaly_score > 0.0 or features.pattern_count > 0:
            pts = min(25.0, (features.anomaly_score * 15.0) + (features.pattern_count * 5.0))
            total_raw_points += pts
            signals.append(RiskSignal(
                signal_type="ANOMALY_PATTERN_CLUSTER",
                description=f"Flagged in {features.pattern_count} suspicious activity patterns (Max Anomaly Score: {features.anomaly_score:.2f}).",
                weight=0.25,
                score_contribution=round(pts, 2),
                evidence_ids=[]
            ))

        # Signal 3: Cross-Source Multi-System Correlation (Weight: 25%)
        if features.correlation_score > 0.0 or features.cross_source_count > 1:
            pts = min(25.0, (features.correlation_score * 18.0) + (features.cross_source_count * 3.5))
            total_raw_points += pts
            signals.append(RiskSignal(
                signal_type="MULTI_SOURCE_CORRELATION",
                description=f"Corroborated across {features.cross_source_count} independent data sources with score {features.correlation_score:.2f}.",
                weight=0.25,
                score_contribution=round(pts, 2),
                evidence_ids=[]
            ))

        # Signal 4: Key-Player Centrality & Network Influence (Weight: 15%)
        if features.centrality_score > 0.0:
            pts = min(15.0, features.centrality_score * 15.0)
            total_raw_points += pts
            signals.append(RiskSignal(
                signal_type="KEY_PLAYER_INFLUENCE",
                description=f"High network reach and structural centrality score ({features.centrality_score:.4f}).",
                weight=0.15,
                score_contribution=round(pts, 2),
                evidence_ids=[]
            ))

        # Signal 5: Graph Degree & Interaction Volume (Weight: 10%)
        if features.degree > 0:
            pts = min(10.0, features.degree * 2.0)
            total_raw_points += pts
            signals.append(RiskSignal(
                signal_type="GRAPH_CONNECTIVITY_DENSITY",
                description=f"Directly connected to {features.degree} entities with weighted degree {features.weighted_degree:.1f}.",
                weight=0.10,
                score_contribution=round(pts, 2),
                evidence_ids=[]
            ))

        # Final Normalized Risk Score Calculation (0 - 100)
        risk_score = min(100.0, round(total_raw_points, 2))

        # Determine Categorical Risk Level
        if risk_score >= 85.0:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 60.0:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 30.0:
            risk_level = RiskLevel.MODERATE
        else:
            risk_level = RiskLevel.LOW

        # Format Human-Readable Explanation
        entity_name = getattr(entity, "name", entity_id)
        explanation = (
            f"Entity {entity_name} [{entity_id}] has an Investigative Priority Score of {risk_score:.1f}/100 ({risk_level.value}). "
            f"Driven by {len(signals)} observed graph signal(s): cross-case connectivity ({features.cross_case_count} cases), "
            f"anomaly patterns ({features.pattern_count} flagged), and multi-source correlation ({features.cross_source_count} sources)."
        )

        investigative_lead = (
            f"Prioritize investigative verification for {entity_name}. Examine cross-case bridge connections and "
            f"corroborate evidence items across source systems."
        )

        # Collect evidence & case references
        connected_cases = sorted(list(self._get_entity_cases(entity_id)))
        evidence_ids = []
        for rel, nbr in self.graph.get_neighbors(entity_id, direction="undirected"):
            for ev_id in getattr(rel, "evidence_ids", []):
                if ev_id not in evidence_ids:
                    evidence_ids.append(ev_id)

        source_records = [getattr(entity, "origin", "DATASET")]

        return EntityRiskResponse(
            entity_id=entity_id,
            entity_name=entity_name,
            entity_type=getattr(entity, "entity_type", "ENTITY"),
            risk_score=risk_score,
            risk_level=risk_level,
            confidence=0.95,
            features=features,
            signals=signals,
            involved_cases=connected_cases,
            evidence_ids=evidence_ids[:10],
            source_records=source_records,
            explanation=explanation,
            investigative_lead=investigative_lead
        )

    def calculate_case_risk(self, case_id: str) -> CaseRiskResponse:
        """Computes case-level investigation risk prioritization and complexity assessment."""
        case_id = case_id.strip().upper()
        case_entity = self.graph.get_entity(case_id)
        if not case_entity or getattr(case_entity, "entity_type", "") != "CASE":
            raise KeyError(f"Case '{case_id}' not found")

        case_entities = self._get_case_entities(case_id)
        scored_entities: List[EntityRiskResponse] = []
        for eid in case_entities:
            if self.graph.get_entity(eid):
                try:
                    scored_entities.append(self.calculate_entity_risk(eid))
                except Exception:
                    continue

        high_risk_count = sum(1 for e in scored_entities if e.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL))
        max_entity_score = max([e.risk_score for e in scored_entities], default=0.0)
        avg_entity_score = sum(e.risk_score for e in scored_entities) / max(1, len(scored_entities))

        # Patterns and correlations within case
        patterns = self.pattern_engine.detect_all_patterns(case_id=case_id, limit=50)
        correlations = self.correlation_engine.detect_all_correlations(case_id=case_id, limit=50)

        # Cross-case link count
        cross_case_links = sum(1 for e in scored_entities if len(e.involved_cases) > 1)

        # Case-Level Composite Risk Score
        case_raw_score = (max_entity_score * 0.40) + (avg_entity_score * 0.20) + min(20.0, len(patterns) * 4.0) + min(20.0, len(correlations) * 4.0)
        case_risk_score = min(100.0, round(case_raw_score, 2))

        if case_risk_score >= 85.0:
            case_risk_level = RiskLevel.CRITICAL
        elif case_risk_score >= 60.0:
            case_risk_level = RiskLevel.HIGH
        elif case_risk_score >= 30.0:
            case_risk_level = RiskLevel.MODERATE
        else:
            case_risk_level = RiskLevel.LOW

        top_entities_summary = [
            {
                "entity_id": e.entity_id,
                "entity_name": e.entity_name,
                "entity_type": e.entity_type,
                "risk_score": e.risk_score,
                "risk_level": e.risk_level.value
            }
            for e in sorted(scored_entities, key=lambda x: x.risk_score, reverse=True)[:5]
        ]

        case_title = getattr(case_entity, "name", case_id)
        explanation = (
            f"Case {case_id} [{case_title}] has an Investigation Risk Score of {case_risk_score:.1f}/100 ({case_risk_level.value}). "
            f"Contains {len(scored_entities)} entities ({high_risk_count} high-priority), {len(patterns)} pattern findings, "
            f"and {len(correlations)} cross-source correlations."
        )

        investigative_lead = f"Focus analytical resources on top risk entities in {case_id} ({', '.join([t['entity_name'] for t in top_entities_summary[:3]])})."

        case_signals = [
            RiskSignal(
                signal_type="HIGH_RISK_ENTITIES",
                description=f"{high_risk_count} entity(ies) flagged as HIGH or CRITICAL risk in case.",
                weight=0.40,
                score_contribution=round(max_entity_score * 0.40, 2),
                evidence_ids=[]
            ),
            RiskSignal(
                signal_type="PATTERN_DENSITY",
                description=f"Case flagged with {len(patterns)} topological anomaly patterns.",
                weight=0.30,
                score_contribution=round(min(20.0, len(patterns) * 4.0), 2),
                evidence_ids=[]
            ),
            RiskSignal(
                signal_type="CROSS_SOURCE_ALIGNMENT",
                description=f"Case exhibits {len(correlations)} multi-source correlation alignments.",
                weight=0.30,
                score_contribution=round(min(20.0, len(correlations) * 4.0), 2),
                evidence_ids=[]
            )
        ]

        return CaseRiskResponse(
            case_id=case_id,
            case_title=case_title,
            risk_score=case_risk_score,
            risk_level=case_risk_level,
            confidence=0.95,
            total_entities=len(scored_entities),
            high_risk_entity_count=high_risk_count,
            cross_case_link_count=cross_case_links,
            pattern_count=len(patterns),
            correlation_count=len(correlations),
            top_risk_entities=top_entities_summary,
            signals=case_signals,
            explanation=explanation,
            investigative_lead=investigative_lead
        )

    def get_priorities(
        self,
        case_id: Optional[str] = None,
        min_score: float = 0.0,
        risk_level: Optional[str] = None,
        limit: int = 50
    ) -> List[RiskPriorityItem]:
        """Returns a ranked list of investigation priority entities sorted by risk score descending."""
        if case_id:
            case_id = case_id.strip().upper()
            target_ids = self._get_case_entities(case_id)
        else:
            target_ids = list(self.graph.entities.keys())

        scored_items: List[EntityRiskResponse] = []
        for eid in target_ids:
            ent = self.graph.get_entity(eid)
            if ent and getattr(ent, "entity_type", "") != "CASE":
                try:
                    res = self.calculate_entity_risk(eid)
                    if res.risk_score >= min_score:
                        if risk_level and res.risk_level.value != risk_level.strip().upper():
                            continue
                        scored_items.append(res)
                except Exception:
                    continue

        scored_items.sort(key=lambda x: x.risk_score, reverse=True)

        priorities: List[RiskPriorityItem] = []
        for rank, item in enumerate(scored_items[:limit], start=1):
            primary_sig = item.signals[0].signal_type if item.signals else "BASELINE"
            priorities.append(RiskPriorityItem(
                rank=rank,
                entity_id=item.entity_id,
                entity_name=item.entity_name,
                entity_type=item.entity_type,
                risk_score=item.risk_score,
                risk_level=item.risk_level,
                primary_signal_type=primary_sig,
                involved_cases=item.involved_cases,
                evidence_ids=item.evidence_ids,
                explanation=item.explanation,
                investigative_lead=item.investigative_lead
            ))

        return priorities
