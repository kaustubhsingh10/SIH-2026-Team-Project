"""Multi-Source Data Layer Abstraction for CrimeGraph AI.

Implements DAY-21 Multi-Source Architecture:
- DataSource Base Class
- SyntheticDataSource
- ManualDataSource
- AdditionalSourceAdapter
- MultiSourceIngestionPipeline (Normalization, Deduplication, Provenance, Conflict Detection)
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import json

from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.models.entities import Entity, EntityType
from crimegraph.models.relationships import Relationship
from crimegraph.models.evidence import Evidence


class DataSource(ABC):
    """Abstract base class for all CrimeGraph AI data sources."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name identifier of the data source."""
        pass

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Type of data source (e.g. SYNTHETIC_DATASET, MANUAL_INVESTIGATION, EXTERNAL_CONNECTOR)."""
        pass

    @abstractmethod
    def fetch_records(self) -> Dict[str, Any]:
        """Fetches raw or structured records from the data source.
        
        Returns:
            Dict containing 'nodes', 'edges', 'evidence', 'cases'.
        """
        pass


class SyntheticDataSource(DataSource):
    """Data source connector for canonical synthetic investigation datasets."""

    def __init__(self, filepath: Optional[Union[str, Path]] = None):
        self.filepath = Path(filepath) if filepath else None

    @property
    def name(self) -> str:
        return "Synthetic Investigation Dataset"

    @property
    def source_type(self) -> str:
        return "SYNTHETIC_DATASET"

    def fetch_records(self) -> Dict[str, Any]:
        if self.filepath and self.filepath.exists():
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            from crimegraph.data.loader import get_default_dataset_path
            path = get_default_dataset_path()
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        return {"nodes": [], "edges": [], "evidence": {}, "cases": []}


class ManualDataSource(DataSource):
    """Data source connector for manual officer investigation notes and edits."""

    def __init__(self, manual_records: Optional[Dict[str, Any]] = None):
        self.records = manual_records or {"nodes": [], "edges": [], "evidence": {}, "cases": []}

    @property
    def name(self) -> str:
        return "Manual Officer Investigation Notes"

    @property
    def source_type(self) -> str:
        return "MANUAL_INVESTIGATION"

    def fetch_records(self) -> Dict[str, Any]:
        return self.records


class AdditionalSourceAdapter(DataSource):
    """Adapter connector for external digital forensics, CDR telco intercepts, or third-party feeds."""

    def __init__(self, source_name: str, adapter_data: Optional[Dict[str, Any]] = None):
        self._name = source_name
        self.data = adapter_data or {"nodes": [], "edges": [], "evidence": {}, "cases": []}

    @property
    def name(self) -> str:
        return self._name

    @property
    def source_type(self) -> str:
        return "EXTERNAL_CONNECTOR"

    def fetch_records(self) -> Dict[str, Any]:
        return self.data


class MultiSourceIngestionPipeline:
    """Multi-Source Data Normalization, Deduplication, and Ingestion Engine.
    
    Ensures:
    - Normalization into canonical entity/relationship/evidence model.
    - Deduplication without generating duplicate entities.
    - Provenance tracking (source, document_id, extraction_method).
    - Source conflict detection and flagging.
    - Safe handling of source failures or malformed inputs.
    """

    def __init__(self, target_store: Optional[KnowledgeGraphStore] = None):
        self.store = target_store or KnowledgeGraphStore()
        self.registered_sources: List[DataSource] = []
        self.conflicts: List[Dict[str, Any]] = []
        self.provenance_log: List[Dict[str, Any]] = []

    def register_source(self, source: DataSource) -> None:
        """Registers a new data source connector."""
        self.registered_sources.append(source)

    def ingest_all(self) -> KnowledgeGraphStore:
        """Ingests, normalizes, and merges all registered data sources into the target KnowledgeGraphStore."""
        for source in self.registered_sources:
            try:
                records = source.fetch_records()
                self._process_records(records, source)
            except Exception as err:
                self.provenance_log.append({
                    "source": source.name,
                    "status": "FAILED",
                    "error": str(err)
                })

        return self.store

    def _process_records(self, records: Dict[str, Any], source: DataSource) -> None:
        if not isinstance(records, dict):
            return

        # 1. Process Evidence Items
        evidence_dict = records.get("evidence", {})
        if isinstance(evidence_dict, dict):
            for ev_id, ev_data in evidence_dict.items():
                if isinstance(ev_data, dict):
                    ev_dict = dict(ev_data)
                    ev_dict["evidence_id"] = ev_dict.get("evidence_id", ev_id)
                    ev_dict["source_document_id"] = ev_dict.get("source_document_id", "DOC_EXTRACTION")
                    ev_dict["source_text"] = ev_dict.get("source_text", "Extracted evidence text")
                    ev_dict["confidence"] = float(ev_dict.get("confidence", 0.95))
                    ev_dict["extraction_method"] = ev_dict.get("extraction_method", source.source_type)
                    self.store.add_evidence(ev_dict)

        # 2. Process & Deduplicate Nodes / Entities
        nodes = records.get("nodes") if "nodes" in records else records.get("entities", [])
        if isinstance(nodes, list):
            for node_data in nodes:
                if isinstance(node_data, dict) and "id" in node_data:
                    entity_id = node_data["id"]
                    
                    if entity_id in self.store.entities:
                        existing_ent = self.store.entities[entity_id]
                        new_name = node_data.get("name") or node_data.get("title") or entity_id
                        existing_name = getattr(existing_ent, "name", getattr(existing_ent, "title", entity_id))
                        if existing_name and new_name and existing_name != new_name:
                            self.conflicts.append({
                                "entity_id": entity_id,
                                "type": "NAME_CONFLICT",
                                "existing_value": existing_name,
                                "conflicting_value": new_name,
                                "source": source.name
                            })
                    else:
                        node_dict = dict(node_data)
                        raw_type = (node_dict.get("entity_type") or node_dict.get("type") or "PERSON").upper()
                        if raw_type not in ["PERSON", "PHONE", "VEHICLE", "LOCATION", "ORGANIZATION", "ACCOUNT", "CASE", "EVENT"]:
                            if "PHONE" in raw_type or raw_type.startswith("PHONE"):
                                raw_type = "PHONE"
                            elif any(w in raw_type for w in ["VEHICLE", "TRUCK", "CAR", "VAN"]):
                                raw_type = "VEHICLE"
                            elif "LOC" in raw_type:
                                raw_type = "LOCATION"
                            elif "CASE" in raw_type:
                                raw_type = "CASE"
                            else:
                                raw_type = "PERSON"
                        node_dict["entity_type"] = raw_type
                        if "name" not in node_dict and "title" not in node_dict and raw_type != "CASE":
                            node_dict["name"] = entity_id
                        if raw_type == "CASE" and "title" not in node_dict:
                            node_dict["title"] = entity_id
                        if raw_type == "PHONE" and "phone_number" not in node_dict:
                            node_dict["phone_number"] = node_dict.get("name") or entity_id
                        if raw_type == "VEHICLE" and "registration_number" not in node_dict:
                            node_dict["registration_number"] = node_dict.get("name") or entity_id
                        if raw_type == "LOCATION" and "name" not in node_dict:
                            node_dict["name"] = entity_id
                        if raw_type == "ORGANIZATION" and "name" not in node_dict:
                            node_dict["name"] = entity_id
                        if raw_type == "ACCOUNT" and "account_number" not in node_dict:
                            node_dict["account_number"] = entity_id
                        if raw_type == "EVENT" and "description" not in node_dict:
                            node_dict["description"] = node_dict.get("name") or entity_id
                        self.store.add_entity(node_dict)

        # 3. Process Relationships / Edges
        edges = records.get("edges") if "edges" in records else records.get("relationships", [])
        if isinstance(edges, list):
            for edge_data in edges:
                if isinstance(edge_data, dict):
                    src_id = edge_data.get("source") or edge_data.get("source_id")
                    tgt_id = edge_data.get("target") or edge_data.get("target_id")
                    rel_type = edge_data.get("relationship", "CONNECTED_TO")
                    if src_id and tgt_id:
                        rel_id = edge_data.get("id") or f"{src_id}_{rel_type}_{tgt_id}"
                        if rel_id not in self.store.relationships:
                            edge_dict = dict(edge_data)
                            edge_dict["id"] = rel_id
                            edge_dict["source_id"] = src_id
                            edge_dict["target_id"] = tgt_id
                            edge_dict["relationship"] = rel_type
                            edge_dict["source_type"] = source.source_type
                            self.store.add_relationship(edge_dict)

        self.provenance_log.append({
            "source": source.name,
            "source_type": source.source_type,
            "status": "SUCCESS",
            "nodes_ingested": len(nodes) if isinstance(nodes, list) else 0,
            "edges_ingested": len(edges) if isinstance(edges, list) else 0
        })
