from __future__ import annotations

import datetime
import logging
import sys
import threading
from collections import deque
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, ClassVar

from app.config import settings


class LogRecordData:
    """Structured representation of a runtime log entry."""

    def __init__(self, record: logging.LogRecord, formatted_msg: str) -> None:
        self.id = f"log-{record.created}-{record.msecs}"
        self.timestamp = datetime.datetime.fromtimestamp(record.created).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        self.level = record.levelname
        self.module = record.name
        self.message = record.getMessage()
        self.details = formatted_msg if record.exc_info else None
        self.created = record.created


class InMemoryLogBufferHandler(logging.Handler):
    """Thread-safe, bounded in-memory ring buffer log handler for REST API log queries."""

    _instance: InMemoryLogBufferHandler | None = None
    _lock: threading.Lock = threading.Lock()
    _buffer: ClassVar[deque] = deque(maxlen=2000)

    @classmethod
    def get_instance(cls) -> InMemoryLogBufferHandler:
        with cls._lock:
            if cls._instance is None:
                cls._instance = InMemoryLogBufferHandler()
                cls._instance.setFormatter(
                    logging.Formatter(
                        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                    )
                )
            return cls._instance

    def emit(self, record: logging.LogRecord) -> None:
        try:
            formatted = self.format(record)
            log_item = LogRecordData(record, formatted)
            with self._lock:
                self._buffer.appendleft(log_item)
        except Exception:
            self.handleError(record)

    def get_logs(
        self,
        level: str | None = None,
        module: str | None = None,
        search: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Thread-safe search and filter of captured log entries."""
        with self._lock:
            buffer_copy = list(self._buffer)

        results = []
        for log in buffer_copy:
            if level and log.level.upper() != level.upper():
                continue
            if module and module.lower() not in log.module.lower():
                continue
            if search:
                query = search.lower()
                if query not in log.message.lower() and query not in log.module.lower():
                    continue
            results.append(
                {
                    "id": log.id,
                    "timestamp": log.timestamp,
                    "level": log.level,
                    "module": log.module,
                    "message": log.message,
                    "details": log.details,
                }
            )
            if len(results) >= limit:
                break
        return results


def _get_rotating_file_handler() -> RotatingFileHandler:
    """Configure rotating file logger targeting data/logs/app.log."""
    log_dir = Path(settings.data_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    return handler


_file_handler_instance: RotatingFileHandler | None = None


def get_shared_logger(name: str) -> logging.Logger:
    """Create a structured, shared logger writing to Console, Rotating File, and InMemory Buffer."""
    global _file_handler_instance
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # 1. Console StreamHandler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 2. Rotating File Handler
        if _file_handler_instance is None:
            try:
                _file_handler_instance = _get_rotating_file_handler()
            except Exception:
                _file_handler_instance = None

        if _file_handler_instance:
            logger.addHandler(_file_handler_instance)

        # 3. Thread-safe Bounded In-Memory Buffer Handler
        buffer_handler = InMemoryLogBufferHandler.get_instance()
        logger.addHandler(buffer_handler)

    # Prevent propagation to the root logger to avoid duplicate logs
    logger.propagate = False
    return logger
