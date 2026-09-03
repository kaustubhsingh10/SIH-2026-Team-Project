"""FastAPI Dependency for Audit Logging in CrimeGraph AI."""

from fastapi import Request
from crimegraph.audit.logger import AuditLogger


def get_audit_logger(request: Request) -> AuditLogger:
    """Retrieves the global AuditLogger instance attached to app.state."""
    if hasattr(request.app.state, "audit_logger") and request.app.state.audit_logger is not None:
        return request.app.state.audit_logger
    
    logger = AuditLogger()
    request.app.state.audit_logger = logger
    return logger
