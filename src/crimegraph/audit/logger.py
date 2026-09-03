"""Persistent Audit Logger Engine for CrimeGraph AI.

Maintains append-oriented forensic logs and persists atomically to data/audit_log.json.
Guarantees strict isolation from synthetic_data.json and manual_data.json.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from crimegraph.audit.models import AuditActorType, AuditEvent, AuditResourceType, AuditStatus

logger = logging.getLogger("crimegraph.audit")

SENSITIVE_KEYS = {"password", "token", "secret", "authorization", "access_token", "api_key", "jwt"}


def sanitize_details(details: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitizes metadata to ensure no passwords, secrets, or raw tokens are ever logged."""
    if not isinstance(details, dict):
        return {}
    
    clean: Dict[str, Any] = {}
    for k, v in details.items():
        k_lower = str(k).lower()
        if any(s in k_lower for s in SENSITIVE_KEYS):
            clean[k] = "[REDACTED]"
        elif isinstance(v, dict):
            clean[k] = sanitize_details(v)
        elif isinstance(v, list):
            clean[k] = [sanitize_details(item) if isinstance(item, dict) else item for item in v]
        else:
            clean[k] = v
    return clean


def get_default_audit_log_path() -> Path:
    """Returns absolute path to audit log storage file."""
    env_path = os.environ.get("CRIMEGRAPH_AUDIT_LOG_PATH")
    if env_path:
        return Path(env_path).resolve()

    # Search for project data directory
    cur = Path(__file__).resolve().parent
    for _ in range(6):
        cand = cur / "data" / "audit_log.json"
        if cand.parent.exists():
            return cand.resolve()
        cur = cur.parent

    src_root = Path(__file__).resolve().parent.parent.parent.parent
    return (src_root / "data" / "audit_log.json").resolve()


class AuditLogger:
    """Centralized, append-oriented, and file-backed audit logging service."""

    def __init__(self, filepath: Optional[Union[str, Path]] = None):
        self.filepath = Path(filepath).resolve() if filepath else get_default_audit_log_path()
        self.events: List[AuditEvent] = []
        self.load_events()

    def load_events(self):
        """Loads historical audit records from audit_log.json upon server startup."""
        if self.filepath.exists() and self.filepath.stat().st_size > 0:
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                loaded = []
                for ev_raw in data.get("events", []):
                    if isinstance(ev_raw, dict):
                        loaded.append(AuditEvent(**ev_raw))
                self.events = loaded
            except Exception as e:
                logger.error(f"Error loading audit log from {self.filepath}: {e}")

    def save_events(self):
        """Persists audit log atomically to disk using process-PID temp files."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "metadata": {
                "version": "1.0",
                "type": "CRIMEGRAPH_AUDIT_LOG",
                "total_events": len(self.events)
            },
            "events": [e.model_dump() for e in self.events]
        }

        temp_file = self.filepath.parent / f".tmp_{self.filepath.name}.{os.getpid()}"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_file, self.filepath)
        except Exception as e:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass
            logger.error(f"Failed to persist audit log to {self.filepath}: {e}")

    def log(
        self,
        action: str,
        actor_id: str = "SYSTEM",
        actor_type: Union[AuditActorType, str] = AuditActorType.USER,
        resource_type: Union[AuditResourceType, str] = AuditResourceType.SYSTEM,
        resource_id: Optional[str] = None,
        case_id: Optional[str] = None,
        status: Union[AuditStatus, str] = AuditStatus.SUCCESS,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Appends and persists a new structured audit event."""
        clean_details = sanitize_details(details or {})
        
        # Coerce enums if passed as strings
        a_type = actor_type if isinstance(actor_type, AuditActorType) else AuditActorType(actor_type)
        r_type = resource_type if isinstance(resource_type, AuditResourceType) else AuditResourceType(resource_type)
        s_type = status if isinstance(status, AuditStatus) else AuditStatus(status)

        event = AuditEvent(
            actor_id=actor_id,
            actor_type=a_type,
            action=action,
            resource_type=r_type,
            resource_id=resource_id,
            case_id=case_id,
            status=s_type,
            details=clean_details
        )

        self.events.append(event)
        self.save_events()
        return event

    def get_events(
        self,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        case_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditEvent]:
        """Queries and filters audit events (newest first)."""
        filtered = list(reversed(self.events))

        if actor_id:
            filtered = [e for e in filtered if e.actor_id.lower() == actor_id.lower().strip()]
        if action:
            filtered = [e for e in filtered if e.action.upper() == action.upper().strip()]
        if resource_type:
            filtered = [e for e in filtered if str(e.resource_type).upper() == resource_type.upper().strip()]
        if case_id:
            filtered = [e for e in filtered if e.case_id and e.case_id.upper() == case_id.upper().strip()]
        if status:
            filtered = [e for e in filtered if str(e.status).upper() == status.upper().strip()]

        return filtered[offset: offset + limit]

    def count_events(
        self,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        case_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        """Returns the total number of matched audit events."""
        return len(self.get_events(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            case_id=case_id,
            status=status,
            limit=999999,
            offset=0
        ))
