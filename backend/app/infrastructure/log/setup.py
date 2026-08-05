import logging
import sys
from copy import copy

LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(trace_id)s] %(name)s: %(message)s"
AUDIT_LOG_FORMAT = "%(asctime)s [AUDIT] [%(trace_id)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


class TraceIDFilter(logging.Filter):
    _global_trace_id: str = ""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "trace_id") or not record.trace_id:
            record.trace_id = self._global_trace_id or "-"
        return True


_trace_filter = TraceIDFilter()


def set_trace_id(trace_id: str) -> None:
    TraceIDFilter._global_trace_id = trace_id


def get_trace_id() -> str:
    return TraceIDFilter._global_trace_id


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    handler.addFilter(_trace_filter)

    for h in root.handlers[:]:
        root.removeHandler(h)
    root.addHandler(handler)


def get_audit_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"audit.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(AUDIT_LOG_FORMAT, datefmt=DATE_FORMAT))
        handler.addFilter(copy(_trace_filter))
        logger.addHandler(handler)
        logger.propagate = False
    return logger
