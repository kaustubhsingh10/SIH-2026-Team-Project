"""Timeline and Event Correlation Engine for CrimeGraph AI (Day 23).

Coordinates:
1. Normalization and storage of investigation events.
2. Chronological sequence extraction by case, entity, or cross-case network.
3. Deterministic multi-dimensional event correlation.
4. Temporal conflict detection across multi-source assertions.
"""

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.models.entities import EntityType
from crimegraph.timeline.models import (
    CorrelationConfidence,
    CorrelationType,
    CrossCaseTimelineResponse,
    EventCorrelation,
    InvestigationEvent,
    TemporalConflict,
    TemporalPrecision,
    TimelineResponse,
)
from crimegraph.timeline.normalizer import TemporalNormalizer


class TimelineCorrelationEngine:
    """Master engine for event management, chronological timelines, and event correlation."""

    def __init__(self, store: KnowledgeGraphStore):
        self.store = store
        self._events: Dict[str, InvestigationEvent] = {}
        self._case_events: Dict[str, Set[str]] = defaultdict(set)
        self._entity_events: Dict[str, Set[str]] = defaultdict(set)
        self._temporal_conflicts: Dict[str, TemporalConflict] = {}

        # Sync existing graph events from KnowledgeGraphStore
        self._sync_graph_events()

    def _sync_graph_events(self):
        """Indexes all existing EVENT entities and timestamped entities from store."""
        # 1. Ingest all Event entities in graph store
        for ent in self.store.entities.values():
            if ent.entity_type == EntityType.EVENT.value:
                raw_ts = getattr(ent, "timestamp", None)
                norm_ts, prec, r_start, r_end = TemporalNormalizer.normalize_timestamp(raw_ts)
                
                # Derive linked case and entities from graph neighbors
                involved_entities = []
                case_id = getattr(ent, "case_id", None)
                location_id = getattr(ent, "location_id", None)
                
                for rel, neighbor in self.store.get_neighbors(ent.id, direction="undirected"):
                    if neighbor.entity_type == EntityType.CASE.value and not case_id:
                        case_id = neighbor.id
                    elif neighbor.entity_type == EntityType.LOCATION.value and not location_id:
                        location_id = neighbor.id
                    elif neighbor.id not in involved_entities:
                        involved_entities.append(neighbor.id)

                inv_event = InvestigationEvent(
                    event_id=ent.id,
                    case_id=case_id,
                    event_type=getattr(ent, "event_type", "EVENT"),
                    timestamp=norm_ts,
                    timestamp_precision=prec,
                    time_range_start=r_start,
                    time_range_end=r_end,
                    raw_timestamp=raw_ts,
                    location_id=location_id,
                    involved_entity_ids=involved_entities,
                    evidence_ids=list(getattr(ent, "source_ids", [])),
                    description=getattr(ent, "description", None),
                    confidence=getattr(ent, "confidence", 0.95),
                    source_type=getattr(ent, "origin", "SYNTHETIC_DATASET"),
                )
                self.register_event(inv_event)

    def register_event(self, event: InvestigationEvent) -> InvestigationEvent:
        """Registers a normalized event into the timeline index."""
        self._events[event.event_id] = event

        if event.case_id:
            self._case_events[event.case_id].add(event.event_id)

        for ent_id in event.involved_entity_ids:
            self._entity_events[ent_id].add(event.event_id)

        if event.location_id:
            self._entity_events[event.location_id].add(event.event_id)

        return event

    def record_temporal_conflict(self, conflict: TemporalConflict) -> TemporalConflict:
        """Records a detected temporal discrepancy."""
        self._temporal_conflicts[conflict.conflict_id] = conflict
        return conflict

    def get_event(self, event_id: str) -> Optional[InvestigationEvent]:
        """Retrieves an event by its unique ID."""
        return self._events.get(event_id)

    def list_events(self, case_id: Optional[str] = None, event_type: Optional[str] = None) -> List[InvestigationEvent]:
        """Lists events with optional case or event_type filtering."""
        results = list(self._events.values())
        if case_id:
            results = [e for e in results if e.case_id == case_id]
        if event_type:
            results = [e for e in results if e.event_type.upper() == event_type.upper()]
        return sorted(results, key=self._sort_key)

    def get_case_timeline(self, case_id: str) -> TimelineResponse:
        """Generates a complete chronological timeline with event correlations for a specific case."""
        case_id = case_id.strip()
        event_ids = set(self._case_events.get(case_id, []))

        # Also find events involving case's subgraph entities
        if case_id in self.store.entities:
            subgraph = self.store.get_case_subgraph(case_id)
            for node in subgraph.get("nodes", []):
                nid = node.get("id")
                if nid in self._entity_events:
                    event_ids.update(self._entity_events[nid])

        events = [self._events[eid] for eid in event_ids if eid in self._events]
        sorted_events = sorted(events, key=self._sort_key)

        # Correlate events within this case
        correlations = self.correlate_events(sorted_events)
        conflicts = [c for c in self._temporal_conflicts.values() if any(c.event_id == e.event_id or c.entity_id in e.involved_entity_ids for e in sorted_events)]

        earliest, latest = self._calculate_time_span(sorted_events)

        return TimelineResponse(
            case_id=case_id,
            total_events=len(sorted_events),
            events=sorted_events,
            correlations=correlations,
            conflicts=conflicts,
            time_span={"earliest": earliest, "latest": latest},
        )

    def get_entity_timeline(self, entity_id: str) -> TimelineResponse:
        """Generates a chronological timeline for a specific entity (person, phone, vehicle)."""
        entity_id = entity_id.strip()
        event_ids = self._entity_events.get(entity_id, set())

        events = [self._events[eid] for eid in event_ids if eid in self._events]
        sorted_events = sorted(events, key=self._sort_key)

        correlations = self.correlate_events(sorted_events)
        conflicts = [c for c in self._temporal_conflicts.values() if c.entity_id == entity_id or any(c.event_id == e.event_id for e in sorted_events)]

        earliest, latest = self._calculate_time_span(sorted_events)

        return TimelineResponse(
            entity_id=entity_id,
            total_events=len(sorted_events),
            events=sorted_events,
            correlations=correlations,
            conflicts=conflicts,
            time_span={"earliest": earliest, "latest": latest},
        )

    def get_cross_case_timeline(self, case_ids: List[str]) -> CrossCaseTimelineResponse:
        """Retrieves and correlates chronological events across multiple related cases."""
        all_event_ids: Set[str] = set()
        for cid in case_ids:
            cid = cid.strip()
            all_event_ids.update(self._case_events.get(cid, []))
            if cid in self.store.entities:
                subgraph = self.store.get_case_subgraph(cid)
                for node in subgraph.get("nodes", []):
                    nid = node.get("id")
                    if nid in self._entity_events:
                        all_event_ids.update(self._entity_events[nid])

        events = [self._events[eid] for eid in all_event_ids if eid in self._events]
        sorted_events = sorted(events, key=self._sort_key)

        # Cross-case correlations
        correlations = self.correlate_events(sorted_events, cross_case_only=False)

        # Identify bridge events (events with entities linked to multiple requested cases)
        bridge_events = []
        for ev in sorted_events:
            linked_cases = set()
            if ev.case_id:
                linked_cases.add(ev.case_id)
            for ent_id in ev.involved_entity_ids:
                for c_cand in case_ids:
                    if c_cand in self.store.entities:
                        subgraph = self.store.get_case_subgraph(c_cand)
                        if any(n.get("id") == ent_id for n in subgraph.get("nodes", [])):
                            linked_cases.add(c_cand)
            if len(linked_cases.intersection(set(case_ids))) > 1:
                bridge_events.append(ev)

        conflicts = [c for c in self._temporal_conflicts.values() if any(c.event_id == e.event_id or c.entity_id in e.involved_entity_ids for e in sorted_events)]

        return CrossCaseTimelineResponse(
            cases=case_ids,
            total_events=len(sorted_events),
            events=sorted_events,
            correlations=correlations,
            cross_case_bridge_events=bridge_events,
            conflicts=conflicts,
        )

    def correlate_events(
        self,
        events: List[InvestigationEvent],
        cross_case_only: bool = False
    ) -> List[EventCorrelation]:
        """Correlates pairs of events based on shared devices, shared entities, shared locations, and temporal proximity."""
        correlations = []
        n = len(events)

        for i in range(n):
            for j in range(i + 1, n):
                ev1 = events[i]
                ev2 = events[j]

                # If cross-case only filter is requested, ensure distinct cases
                if cross_case_only and ev1.case_id == ev2.case_id:
                    continue

                # 1. Check Shared Entities
                set1 = set(ev1.involved_entity_ids)
                set2 = set(ev2.involved_entity_ids)
                shared_ents = list(set1.intersection(set2))

                # Location match
                shared_loc = None
                if ev1.location_id and ev2.location_id and ev1.location_id == ev2.location_id:
                    shared_loc = ev1.location_id

                # Time delta
                delta_sec = TemporalNormalizer.calculate_time_delta_seconds(ev1.timestamp, ev2.timestamp)

                # Determine correlation
                corr_type = None
                explanation_parts = []
                conf = 0.80

                # Check shared phone/device specifically
                shared_phones = [eid for eid in shared_ents if "PHONE" in eid or (eid in self.store.entities and self.store.entities[eid].entity_type == EntityType.PHONE.value)]
                shared_vehicles = [eid for eid in shared_ents if "VEHICLE" in eid or (eid in self.store.entities and self.store.entities[eid].entity_type == EntityType.VEHICLE.value)]

                if shared_phones:
                    corr_type = CorrelationType.SHARED_DEVICE
                    explanation_parts.append(f"Both events share communication device(s): {', '.join(shared_phones)}")
                    conf = 0.95
                elif shared_vehicles:
                    corr_type = CorrelationType.SHARED_VEHICLE
                    explanation_parts.append(f"Both events share vehicle(s): {', '.join(shared_vehicles)}")
                    conf = 0.92
                elif shared_ents:
                    corr_type = CorrelationType.SHARED_ENTITY
                    explanation_parts.append(f"Both events involve shared entity: {', '.join(shared_ents)}")
                    conf = 0.88
                elif shared_loc and delta_sec is not None and delta_sec <= 7200:  # within 2 hours at same location
                    corr_type = CorrelationType.TEMPORAL_PROXIMITY
                    explanation_parts.append(f"Events occurred at same location ({shared_loc}) within {int(delta_sec // 60)} minutes")
                    conf = 0.85
                elif ev1.case_id and ev2.case_id and ev1.case_id != ev2.case_id and shared_ents:
                    corr_type = CorrelationType.CROSS_CASE_BRIDGE
                    explanation_parts.append(f"Cross-case link between {ev1.case_id} and {ev2.case_id} via {', '.join(shared_ents)}")
                    conf = 0.90

                if corr_type:
                    if delta_sec is not None:
                        explanation_parts.append(f"Time delta: {int(delta_sec // 60)} minutes")
                    
                    shared_cases = list({c for c in [ev1.case_id, ev2.case_id] if c})
                    
                    correlations.append(EventCorrelation(
                        source_event_id=ev1.event_id,
                        target_event_id=ev2.event_id,
                        correlation_type=corr_type,
                        correlation_confidence=CorrelationConfidence.DIRECTLY_SUPPORTED if conf >= 0.85 else CorrelationConfidence.POTENTIAL_CORRELATION,
                        time_delta_seconds=delta_sec,
                        shared_entities=shared_ents,
                        shared_cases=shared_cases,
                        explanation=". ".join(explanation_parts) + ".",
                        supporting_evidence_ids=list(set(ev1.evidence_ids + ev2.evidence_ids)),
                        confidence=conf,
                    ))

        return correlations

    @staticmethod
    def _sort_key(event: InvestigationEvent) -> Tuple[int, str]:
        """Deterministic chronological sorting key.

        Unknown or missing timestamps are placed at the end safely.
        """
        ts = event.timestamp
        if not ts:
            return (1, event.event_id)
        return (0, ts)

    @staticmethod
    def _calculate_time_span(events: List[InvestigationEvent]) -> Tuple[Optional[str], Optional[str]]:
        """Calculates earliest and latest timestamp from an event list."""
        valid_ts = [e.timestamp for e in events if e.timestamp and e.timestamp_precision != TemporalPrecision.UNKNOWN]
        if not valid_ts:
            return None, None
        return min(valid_ts), max(valid_ts)
