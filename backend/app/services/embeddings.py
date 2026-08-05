from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterable

EMBEDDING_DIMENSIONS = 384
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
DOMAIN_TOKENS = tuple(
    sorted(
        {
            "401",
            "429",
            "504",
            "api",
            "authentication",
            "backlog",
            "cache",
            "capacity",
            "certificate",
            "clients",
            "connection",
            "cpu",
            "database",
            "deadline",
            "dependency",
            "deployment",
            "disk",
            "exceeded",
            "expired",
            "filesystem",
            "gateway",
            "handshake",
            "heap",
            "inode",
            "jwks",
            "lag",
            "latency",
            "leak",
            "limit",
            "load",
            "memory",
            "message",
            "new",
            "oom",
            "pool",
            "p95",
            "queue",
            "quota",
            "rate",
            "redis",
            "refused",
            "regression",
            "release",
            "rollback",
            "rss",
            "saturation",
            "signature",
            "slow",
            "space",
            "throttle",
            "throttling",
            "timeout",
            "tls",
            "token",
            "upstream",
            "version",
            "x509",
        }
    )
)
DOMAIN_INDEX = {token: index for index, token in enumerate(DOMAIN_TOKENS)}


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.casefold())


def deterministic_embedding(text: str) -> list[float]:
    """Create a dependency-free hashing embedding for deterministic local retrieval."""
    vector = [0.0] * EMBEDDING_DIMENSIONS
    for token in tokenize(text):
        if token in DOMAIN_INDEX:
            vector[DOMAIN_INDEX[token]] = 1.0
            continue
        digest = hashlib.sha256(token.encode()).digest()
        hashed_dimensions = EMBEDDING_DIMENSIONS - len(DOMAIN_TOKENS)
        index = len(DOMAIN_TOKENS) + int.from_bytes(digest[:4], "big") % hashed_dimensions
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[index] = sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        return [value / norm for value in vector]
    return vector


def runbook_embedding(title: str, keywords: Iterable[str]) -> list[float]:
    """Embed retrieval signals without diluting them with procedural prose."""
    return deterministic_embedding(" ".join([title, *keywords]))


def cosine_similarity(left: Iterable[float], right: Iterable[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))
