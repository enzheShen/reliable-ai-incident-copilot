# ruff: noqa: S310, UP006, UP007, UP035

import json
import os
from typing import Any, Dict, Optional
from urllib.error import HTTPError
from urllib.request import Request, urlopen

TOXIPROXY_URL = os.getenv("TOXIPROXY_URL", "http://localhost:8474")
PROXY_NAME = "mock_llm"


def api(method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Any:
    body = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        f"{TOXIPROXY_URL}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=10) as response:  # noqa: S310 - local test endpoint
            content = response.read()
            return json.loads(content) if content else None
    except HTTPError as exc:
        if method == "DELETE" and exc.code == 404:
            return None
        raise RuntimeError(f"Toxiproxy {method} {path} failed with {exc.code}") from exc


def remove_toxic(name: str) -> None:
    api("DELETE", f"/proxies/{PROXY_NAME}/toxics/{name}")


def add_toxic(name: str, toxic_type: str, attributes: Dict[str, Any]) -> None:
    remove_toxic(name)
    api(
        "POST",
        f"/proxies/{PROXY_NAME}/toxics",
        {
            "name": name,
            "type": toxic_type,
            "stream": "downstream",
            "toxicity": 1.0,
            "attributes": attributes,
        },
    )
