from __future__ import annotations

import logging
import logging.config
from contextvars import ContextVar, Token
from typing import Any

from pythonjsonlogger.json import JsonFormatter

correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")
SENSITIVE_KEYS = {"authorization", "cookie", "set-cookie", "api_key", "api-key", "x-api-key"}


def redact_mapping(value: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, item in value.items():
        if key.casefold() in SENSITIVE_KEYS:
            redacted[key] = "[REDACTED]"
        elif isinstance(item, dict):
            redacted[key] = redact_mapping(item)
        else:
            redacted[key] = item
    return redacted


class CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id.get()
        return True


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.addFilter(CorrelationFilter())
    handler.setFormatter(
        JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(correlation_id)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())


def bind_correlation_id(value: str) -> Token[str]:
    return correlation_id.set(value)


def reset_correlation_id(token: Token[str]) -> None:
    correlation_id.reset(token)
