from __future__ import annotations

import logging
import logging.config
from contextvars import ContextVar, Token
from typing import Any

from pythonjsonlogger.json import JsonFormatter

correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")
SENSITIVE_KEYS = {
    "access_token",
    "api-key",
    "api_key",
    "authorization",
    "cookie",
    "password",
    "refresh_token",
    "secret",
    "set-cookie",
    "token",
    "x-api-key",
}


def redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return redact_mapping(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    return value


def redact_mapping(value: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, item in value.items():
        if key.casefold() in SENSITIVE_KEYS:
            redacted[key] = "[REDACTED]"
        else:
            redacted[key] = redact_value(item)
    return redacted


class CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id.get()
        return True


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in list(vars(record).items()):
            if key.casefold() in SENSITIVE_KEYS:
                setattr(record, key, "[REDACTED]")
            else:
                setattr(record, key, redact_value(value))
        record.msg = redact_value(record.msg)
        record.args = redact_value(record.args)
        return True


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.addFilter(CorrelationFilter())
    handler.addFilter(SensitiveDataFilter())
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
