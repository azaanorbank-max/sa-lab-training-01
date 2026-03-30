"""
Structured JSON logger used by all services.

Every log line emits a JSON object with mandatory fields:
  timestamp, service, level, correlation_id, event

Extra keyword arguments are merged into the top-level JSON object.
This makes logs grep-able, filterable, and directly ingestible by any
log aggregator (ELK, Loki, CloudWatch, etc.) without parsing.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

_SKIP_FIELDS = frozenset({
    "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "name", "message", "taskName",
})


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": getattr(record, "service", record.name),
            "level": record.levelname,
            "correlation_id": getattr(record, "correlation_id", None),
            "event": getattr(record, "event", record.getMessage()),
        }
        # Merge any extra fields passed via logger.info(..., extra={...})
        for key, val in record.__dict__.items():
            if key not in _SKIP_FIELDS and not key.startswith("_"):
                log_obj[key] = val

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, default=str)


def get_logger(service_name: str) -> logging.Logger:
    logger = logging.getLogger(service_name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
