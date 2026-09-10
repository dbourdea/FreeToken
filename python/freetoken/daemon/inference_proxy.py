"""Small request-preserving HTTP bridge from freetoken-swap to ``ft serve``.

No inference dependency is imported here. The daemon only parses the request
JSON long enough to select an allowlisted profile, then forwards the original
bytes and safe HTTP headers to the selected FreeToken engine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterator, Mapping
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class RequestModelError(ValueError):
    """The request cannot be routed because it has no valid model identifier."""


_HOP_BY_HOP = {"connection", "content-length", "host", "keep-alive", "proxy-authenticate",
               "proxy-authorization", "te", "trailer", "transfer-encoding", "upgrade"}


def request_model(body: bytes) -> str:
    try:
        doc = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RequestModelError("request body must be valid JSON with a model string") from exc
    model = doc.get("model") if isinstance(doc, dict) else None
    if not isinstance(model, str) or not model.strip() or "\x00" in model:
        raise RequestModelError("request body must include a non-empty model string")
    return model


def filter_request_body(body: bytes, drop_fields: tuple[str, ...]) -> bytes:
    """Remove only explicitly allowlisted top-level fields from a JSON request.

    The default empty policy returns the original bytes exactly. This never
    rewrites the model selector and deliberately has no expression or hook
    language, so a catalog cannot execute code in the daemon.
    """
    if not drop_fields:
        return body
    try:
        doc = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RequestModelError("request body must be valid JSON") from exc
    if not isinstance(doc, dict):
        raise RequestModelError("request body must be a JSON object")
    for field in drop_fields:
        doc.pop(field, None)
    return json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def forward_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Preserve application headers while removing client and proxy connection state."""
    return {key: value for key, value in headers.items() if key.lower() not in _HOP_BY_HOP}


@dataclass
class UpstreamResponse:
    status: int
    headers: dict[str, str]
    raw: object

    def chunks(self, size: int = 64 * 1024) -> Iterator[bytes]:
        try:
            while True:
                chunk = self.raw.read(size)
                if not chunk:
                    break
                yield chunk
        finally:
            self.close()

    def close(self) -> None:
        close = getattr(self.raw, "close", None)
        if close is not None:
            close()


def open_upstream(*, port: int, path_and_query: str, headers: Mapping[str, str], body: bytes,
                  method: str = "POST", timeout_s: float = 900.0) -> UpstreamResponse:
    request = Request(
        f"http://127.0.0.1:{port}{path_and_query}",
        data=body,
        headers=forward_headers(headers),
        method=method,
    )
    try:
        raw = urlopen(request, timeout=timeout_s)
    except HTTPError as exc:
        raw = exc
    return UpstreamResponse(
        status=raw.getcode(),
        headers=forward_headers(dict(raw.headers.items())),
        raw=raw,
    )
