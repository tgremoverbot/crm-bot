from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

from pythonjsonlogger import jsonlogger

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def configure_logging(level: str = "INFO", app_name: str = "app") -> None:
    """Configure root logger to emit structured JSON to stdout."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(ContextFilter())

    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s",
        rename_fields={"asctime": "ts", "levelname": "level", "name": "logger"},
        json_ensure_ascii=False,
    )
    handler.setFormatter(formatter)

    root.addHandler(handler)
    root.setLevel(log_level)

    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).setLevel(max(log_level, logging.INFO))

    logging.getLogger(app_name).setLevel(log_level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
