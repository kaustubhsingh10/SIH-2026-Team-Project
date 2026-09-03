"""Production Structured Logging Configuration for CrimeGraph AI.

Provides sanitized, structured log output configured via standard environment variables.
"""

import json
import logging
import os
import re
import sys
from typing import Any, Dict

SENSITIVE_PATTERNS = [
    (re.compile(r"Bearer\s+[A-Za-z0-9\-_.]+", re.IGNORECASE), "Bearer [REDACTED]"),
    (re.compile(r"eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+", re.IGNORECASE), "[REDACTED_JWT]"),
    (re.compile(r"eyJ[A-Za-z0-9\-_]+", re.IGNORECASE), "[REDACTED_TOKEN]"),
    (re.compile(r"(password|token|secret|authorization|api_key|jwt)[\"':=\s]+([^\s,;\"'}{]+)", re.IGNORECASE), r"\1=[REDACTED]")
]

WINDOWS_PATH_PATTERN = re.compile(r"[A-Za-z]:\\[\w\\\.\-]+")


def sanitize_log_message(msg: str) -> str:
    """Removes sensitive credentials and local Windows absolute paths from log lines."""
    if not isinstance(msg, str):
        msg = str(msg)

    for pattern, repl in SENSITIVE_PATTERNS:
        msg = pattern.sub(repl, msg)

    # Sanitize full drive letter paths e.g. C:\Users\... to relative-like references
    msg = WINDOWS_PATH_PATTERN.sub(lambda m: m.group(0).split("\\")[-1], msg)
    return msg


class StructuredFormatter(logging.Formatter):
    """Formats log records as structured text with automatic sanitization."""

    def format(self, record: logging.LogRecord) -> str:
        orig_msg = record.getMessage()
        clean_msg = sanitize_log_message(orig_msg)
        
        request_id = getattr(record, "request_id", "-")
        
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "request_id": request_id,
            "message": clean_msg
        }
        
        if os.environ.get("ENABLE_JSON_LOGS", "false").lower() == "true":
            return json.dumps(log_entry)
        
        return f"[{log_entry['timestamp']}] [{log_entry['level']}] [{log_entry['logger']}] [req:{request_id}] {clean_msg}"


def setup_observability_logging():
    """Initializes structured logging for all CrimeGraph components."""
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    root_logger = logging.getLogger("crimegraph")
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers
    if not any(isinstance(h.formatter, StructuredFormatter) for h in root_logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        formatter = StructuredFormatter(datefmt="%Y-%m-%dT%H:%M:%SZ")
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        root_logger.propagate = False

    return root_logger
