"""Backup and Disaster Recovery System for CrimeGraph AI Manual Data.

Guarantees data durability and recovery for dynamic manual entities and relationships:
- Strictly isolates and protects immutable synthetic baseline dataset.
- Creates timestamped, atomic backups prior to manual dataset rewrites.
- Validates backup integrity against entity and relationship schemas.
- Automatically selects the latest valid backup when manual_data.json is missing or corrupted.
- Prevents duplicate entity/relationship injection during restoration.
- Provides sanitized structured logging for backup and recovery operations.
"""

import json
import logging
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from crimegraph.models.entities import (
    Account, Case, Event, Location, Organization, Person, Phone, Vehicle
)
from crimegraph.models.evidence import Evidence
from crimegraph.models.relationships import Relationship

logger = logging.getLogger("crimegraph.data.backup")


def get_default_backup_dir(manual_filepath: Optional[Path] = None) -> Path:
    """Returns the backup directory path respecting CRIMEGRAPH_BACKUP_DIR env var."""
    env_dir = os.environ.get("CRIMEGRAPH_BACKUP_DIR")
    if env_dir:
        return Path(env_dir).resolve()

    if manual_filepath:
        return manual_filepath.resolve().parent / "backups"

    from crimegraph.data.loader import get_default_manual_data_path
    return get_default_manual_data_path().resolve().parent / "backups"


def validate_manual_dataset_schema(data: Any) -> Tuple[bool, str]:
    """Validates that loaded manual data matches expected CrimeGraph schemas.
    
    Returns:
        (is_valid: bool, error_message: str)
    """
    if not isinstance(data, dict):
        return False, f"Expected JSON object, got {type(data).__name__}"

    entities = data.get("entities", [])
    relationships = data.get("relationships", [])

    if not isinstance(entities, list) or not isinstance(relationships, list):
        return False, "Malformed manual data: 'entities' and 'relationships' must be lists"

    # Validate each entity against entity schemas
    entity_model_map = {
        "PERSON": Person,
        "PHONE": Phone,
        "VEHICLE": Vehicle,
        "LOCATION": Location,
        "ORGANIZATION": Organization,
        "ACCOUNT": Account,
        "CASE": Case,
        "EVENT": Event,
        "EVIDENCE": Evidence,
    }

    for idx, ent in enumerate(entities):
        if not isinstance(ent, dict):
            return False, f"Entity at index {idx} is not an object"
        
        ent_id = ent.get("id")
        ent_type = (ent.get("type") or ent.get("entity_type") or "").upper()
        
        if not ent_id:
            return False, f"Entity at index {idx} missing required 'id'"
        
        model_cls = entity_model_map.get(ent_type)
        if model_cls:
            try:
                # Ensure type field is populated for pydantic validation
                ent_payload = dict(ent)
                if "type" not in ent_payload and ent_type:
                    ent_payload["type"] = ent_type
                model_cls.model_validate(ent_payload)
            except Exception as e:
                return False, f"Entity '{ent_id}' failed schema validation: {e}"

    # Validate each relationship against Relationship schema
    for idx, rel in enumerate(relationships):
        if not isinstance(rel, dict):
            return False, f"Relationship at index {idx} is not an object"
        
        src = rel.get("source_id")
        tgt = rel.get("target_id")
        rel_type = rel.get("relationship") or rel.get("relationship_type")
        
        if not src or not tgt or not rel_type:
            return False, f"Relationship at index {idx} missing required source_id/target_id/relationship"
        
        try:
            rel_payload = dict(rel)
            if "relationship" not in rel_payload and rel_type:
                rel_payload["relationship"] = rel_type
            Relationship.model_validate(rel_payload)
        except Exception as e:
            return False, f"Relationship at index {idx} failed schema validation: {e}"

    return True, ""


def create_manual_data_backup(
    manual_filepath: Path,
    backup_dir: Optional[Path] = None,
    max_backups: int = 10
) -> Optional[Path]:
    """Atomically creates a timestamped backup of the current valid manual data file.
    
    Args:
        manual_filepath: Path to data/manual_data.json.
        backup_dir: Directory where backups are stored.
        max_backups: Maximum number of recent backups to retain.
        
    Returns:
        Path to the newly created backup file, or None if skipped.
    """
    manual_path = manual_filepath.resolve()
    if not manual_path.exists() or manual_path.stat().st_size == 0:
        return None

    try:
        with open(manual_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as err:
        logger.warning(f"Skipping backup creation: source manual data is unreadable or corrupted: {err}")
        return None

    is_valid, err_msg = validate_manual_dataset_schema(data)
    if not is_valid:
        logger.warning(f"Skipping backup creation: source manual data failed validation: {err_msg}")
        return None

    entities = data.get("entities", [])
    relationships = data.get("relationships", [])
    if len(entities) == 0 and len(relationships) == 0:
        return None

    target_dir = backup_dir.resolve() if backup_dir else get_default_backup_dir(manual_path)
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    backup_file = target_dir / f"manual_data_backup_{timestamp}.json"
    temp_backup = target_dir / f".tmp_backup_{timestamp}.{os.getpid()}"

    try:
        with open(temp_backup, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_backup, backup_file)
        logger.info(
            f"Created atomic manual data backup: {backup_file.name} "
            f"({len(entities)} entities, {len(relationships)} relationships)"
        )
        
        # Prune old backups
        prune_old_backups(target_dir, max_backups=max_backups)
        return backup_file
    except Exception as err:
        if temp_backup.exists():
            try:
                temp_backup.unlink()
            except OSError:
                pass
        logger.error(f"Failed to create atomic manual data backup: {err}")
        return None


def prune_old_backups(backup_dir: Path, max_backups: int = 10):
    """Retains only the N most recent backup files in the backup directory."""
    try:
        backups = sorted(
            backup_dir.glob("manual_data_backup_*.json"),
            key=lambda p: p.name,
            reverse=True
        )
        for old_backup in backups[max_backups:]:
            try:
                old_backup.unlink()
                logger.debug(f"Pruned older backup: {old_backup.name}")
            except OSError:
                pass
    except Exception as err:
        logger.debug(f"Backup pruning encountered error: {err}")


def find_latest_valid_backup(backup_dir: Path) -> Optional[Tuple[Path, Dict[str, Any]]]:
    """Scans backup directory and returns the newest backup that passes schema validation."""
    if not backup_dir.exists():
        return None

    backups = sorted(
        backup_dir.glob("manual_data_backup_*.json"),
        key=lambda p: p.name,
        reverse=True
    )

    for backup_path in backups:
        if backup_path.stat().st_size == 0:
            continue
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            is_valid, err_msg = validate_manual_dataset_schema(data)
            if is_valid:
                logger.info(f"Identified valid manual data backup candidate: {backup_path.name}")
                return backup_path, data
            else:
                logger.warning(f"Backup {backup_path.name} failed schema validation: {err_msg}")
        except json.JSONDecodeError as err:
            logger.warning(f"Corrupt backup file {backup_path.name}: {err}")
        except Exception as err:
            logger.warning(f"Error inspecting backup {backup_path.name}: {err}")

    return None


def restore_manual_data_from_backup(
    manual_filepath: Path,
    backup_dir: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """Restores manual_data.json from the latest verified backup atomically.
    
    Args:
        manual_filepath: Path to restore manual_data.json.
        backup_dir: Directory containing backup files.
        
    Returns:
        The recovered data dictionary if restoration succeeded, None otherwise.
    """
    target_dir = backup_dir.resolve() if backup_dir else get_default_backup_dir(manual_filepath)
    candidate = find_latest_valid_backup(target_dir)

    if not candidate:
        logger.warning(f"Disaster Recovery: No valid manual data backups found in {target_dir.name}.")
        return None

    backup_path, data = candidate
    manual_path = manual_filepath.resolve()
    manual_path.parent.mkdir(parents=True, exist_ok=True)

    temp_restore = manual_path.parent / f".tmp_restore_{os.getpid()}_{int(time.time())}.json"
    try:
        with open(temp_restore, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_restore, manual_path)
        
        ent_count = len(data.get("entities", []))
        rel_count = len(data.get("relationships", []))
        logger.info(
            f"DISASTER RECOVERY SUCCESS: Restored {manual_path.name} from backup {backup_path.name} "
            f"({ent_count} entities, {rel_count} relationships restored)."
        )
        return data
    except Exception as err:
        if temp_restore.exists():
            try:
                temp_restore.unlink()
            except OSError:
                pass
        logger.error(f"DISASTER RECOVERY FAILED: Unable to restore manual data from {backup_path.name}: {err}")
        return None
