"""Dataset loader and serializer for CrimeGraph AI.

Maintains strict separation between original static dataset and manually created investigation data.
Supports atomic file writes, dynamic environmental paths, automated backups, and disaster recovery.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union
from crimegraph.graph.store import KnowledgeGraphStore
from crimegraph.data.generator import generate_synthetic_investigation_data
from crimegraph.data.backup import (
    create_manual_data_backup,
    restore_manual_data_from_backup,
    validate_manual_dataset_schema,
)
from crimegraph.observability.metrics import metrics

logger = logging.getLogger("crimegraph.data")


def get_default_dataset_path() -> Path:
    """Returns path to dataset file, respecting CRIMEGRAPH_DATA_PATH env var if set."""
    env_path = os.environ.get("CRIMEGRAPH_DATA_PATH") or os.environ.get("DATASET_PATH")
    if env_path:
        return Path(env_path)

    # Search upwards from current file to find project root containing data/synthetic_data.json
    cur = Path(__file__).resolve().parent
    for _ in range(6):
        cand = cur / "data" / "synthetic_data.json"
        if cand.exists():
            return cand
        if (cur / "PROJECT_SPEC.md").exists() or (cur / ".git").exists():
            cand = cur / "data" / "synthetic_data.json"
            return cand
        cur = cur.parent

    # Check current working directory
    cwd_cand = Path.cwd() / "data" / "synthetic_data.json"
    if cwd_cand.exists():
        return cwd_cand

    # Fallback to source-tree project root
    src_root = Path(__file__).resolve().parent.parent.parent.parent
    return src_root / "data" / "synthetic_data.json"


def get_default_manual_data_path() -> Path:
    """Returns path to manual entity/relationship file, respecting CRIMEGRAPH_MANUAL_DATA_PATH env var if set."""
    env_path = os.environ.get("CRIMEGRAPH_MANUAL_DATA_PATH") or os.environ.get("MANUAL_DATA_PATH")
    if env_path:
        return Path(env_path)

    dataset_path = get_default_dataset_path()
    return dataset_path.parent / "manual_data.json"


def _merge_manual_data_into_store(store: KnowledgeGraphStore, man_data: Dict[str, Any]):
    """Safely merges manual entities and relationships into KnowledgeGraphStore without duplicates."""
    for ent in man_data.get("entities", []):
        if isinstance(ent, dict):
            ent["origin"] = "MANUAL"
            if ent.get("id") not in store.entities:
                store.add_entity(ent)
            else:
                # Update existing entity if needed without error
                store.update_entity(ent["id"], ent)
    for rel in man_data.get("relationships", []):
        if isinstance(rel, dict):
            rel["origin"] = "MANUAL"
            store.add_relationship(rel)


def load_dataset(
    filepath: Optional[Union[str, Path]] = None,
    manual_filepath: Optional[Union[str, Path]] = None,
) -> KnowledgeGraphStore:
    """Loads knowledge graph from static dataset and merges persisted manual entities/relationships.
    
    Safe recovery semantics:
    - If dataset file is missing, generates synthetic dataset.
    - If manual data file is missing or corrupted, automatically recovers from the latest valid backup.
    - If no valid backup exists, initializes cleanly without touching baseline static dataset.
    - Prevents entity/relationship duplication on repeated loads.
    """
    path = Path(filepath).resolve() if filepath else get_default_dataset_path()

    if not path.exists():
        store = generate_synthetic_investigation_data()
        save_dataset(store, path)
    else:
        store = KnowledgeGraphStore.from_json(path)

    # Load manual entities and relationships if present, with automated backup recovery
    man_path = Path(manual_filepath).resolve() if manual_filepath else get_default_manual_data_path()
    man_loaded = False

    if man_path.exists() and man_path.stat().st_size > 0:
        try:
            with open(man_path, "r", encoding="utf-8") as f:
                man_data = json.load(f)

            is_valid, err_msg = validate_manual_dataset_schema(man_data)
            if is_valid:
                _merge_manual_data_into_store(store, man_data)
                man_loaded = True
            else:
                logger.warning(f"Corrupted or invalid manual data at {man_path.name}: {err_msg}. Initiating backup recovery...")
                recovered = restore_manual_data_from_backup(man_path)
                if recovered:
                    _merge_manual_data_into_store(store, recovered)
                    man_loaded = True
        except (json.JSONDecodeError, Exception) as err:
            logger.warning(f"Failed to read manual data at {man_path.name}: {err}. Initiating backup recovery...")
            recovered = restore_manual_data_from_backup(man_path)
            if recovered:
                _merge_manual_data_into_store(store, recovered)
                man_loaded = True

    elif not man_path.exists():
        # Check if backups exist to recover from accidental deletion
        recovered = restore_manual_data_from_backup(man_path)
        if recovered:
            _merge_manual_data_into_store(store, recovered)
            man_loaded = True

    logger.info(f"Loaded knowledge graph store successfully with {len(store.entities)} entities, {len(store.relationships)} relationships, {len(store.evidence)} evidence items.")
    return store


def save_dataset(store: KnowledgeGraphStore, filepath: Optional[Union[str, Path]] = None) -> Path:
    """Saves the knowledge graph store to JSON."""
    path = Path(filepath).resolve() if filepath else get_default_dataset_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    store.to_json(path)
    return path


def save_manual_data(store: KnowledgeGraphStore, filepath: Optional[Union[str, Path]] = None) -> Path:
    """Saves only manually created entities and relationships to separate storage file atomically.
    
    Creates a pre-save backup of the existing manual data to ensure zero data loss.
    Uses atomic temp-file replace strategy (write to temp file in same directory + os.replace).
    """
    path = Path(filepath).resolve() if filepath else get_default_manual_data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # 1. Create a pre-save backup of previous state if it exists
    if path.exists() and path.stat().st_size > 0:
        create_manual_data_backup(path)
    
    # 2. Extract current manual records
    manual_entities = [e.model_dump() for e in store.get_manual_entities()]
    manual_relationships = [r.model_dump() for r in store.get_manual_relationships()]
    
    payload = {
        "metadata": {
            "version": "1.0",
            "type": "CRIMEGRAPH_MANUAL_DATA",
            "entity_count": len(manual_entities),
            "relationship_count": len(manual_relationships)
        },
        "entities": manual_entities,
        "relationships": manual_relationships
    }
    
    temp_file = path.parent / f".tmp_{path.name}.{os.getpid()}"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, path)
        metrics.record_persistence(success=True)
        logger.info(f"Persisted manual data atomically: {len(manual_entities)} entities, {len(manual_relationships)} relationships.")
    except Exception as err:
        metrics.record_persistence(success=False)
        if temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass
        logger.error(f"Failed to atomically persist manual data: {err}")
        raise
        
    return path
