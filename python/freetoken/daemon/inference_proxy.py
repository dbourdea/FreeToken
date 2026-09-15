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

from .catalog import RequestField


class RequestModelError(ValueError):
    """The request cannot be routed because it has no valid model identifier."""


_HOP_BY_HOP = {"connection", "content-length", "host", "keep-alive", "proxy-authenticate",
               "proxy-authorization", "te", "trailer", "transfer-encoding", "upgrade"}
_LOCAL_AUTH_HEADERS = {"authorization", "x-api-key", "x-ft-token"}


def request_model(body: bytes) -> str:
    try:
        doc = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RequestModelError("request body must be valid JSON with a model string") from exc
    model = doc.get("model") if isinstance(doc, dict) else None
    if not isinstance(model, str) or not model.strip() or "\x00" in model:
        raise RequestModelError("request body must include a non-empty model string")
    return model


def _path_parent(doc: dict, path: tuple[str, ...], *, create: bool) -> dict | None:
    current = doc
    for part in path[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            if not create:
                return None
            child = {}
            current[part] = child
        current = child
    return current


def _set_fields(doc: dict, fields: tuple[RequestField, ...]) -> None:
    for field in fields:
        parent = _path_parent(doc, field.path, create=True)
        assert parent is not None
        leaf = field.path[-1]
        if field.soft and leaf in parent:
            continue
        parent[leaf] = field.value()


def filter_request_body(
    body: bytes,
    drop_fields: tuple[str, ...],
    set_fields: tuple[RequestField, ...] = (),
    set_fields_by_id: tuple[tuple[str, tuple[RequestField, ...]], ...] = (),
    *,
    requested_model: str | None = None,
    rewrite_model: str | None = None,
) -> bytes:
    """Apply safe configured JSON-field transformations in pinned order.

    The default empty policy returns the original bytes exactly. This never
    rewrites the model selector and deliberately has no expression or hook
    language, so a catalog cannot execute code in the daemon.
    """
    by_id = dict(set_fields_by_id).get(requested_model, ())
    if rewrite_model is None and not drop_fields and not set_fields and not by_id:
        return body
    try:
        doc = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RequestModelError("request body must be valid JSON") from exc
    if not isinstance(doc, dict):
        raise RequestModelError("request body must be a JSON object")
    if rewrite_model is not None:
        doc["model"] = rewrite_model
    for field in drop_fields:
        path = tuple(field.split("."))
        parent = _path_parent(doc, path, create=False)
        if parent is not None:
            parent.pop(path[-1], None)
    _set_fields(doc, set_fields)
    _set_fields(doc, by_id)
    return json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def forward_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Preserve application headers without forwarding daemon authentication.

    The router terminates its bearer/Basic/``x-api-key`` credential and optional
    ``X-FT-Token`` locally. None is an engine credential, so forwarding one would
    disclose a control-plane secret to the child process and its logs.
    """
    excluded = _HOP_BY_HOP | _LOCAL_AUTH_HEADERS
    return {key: value for key, value in headers.items() if key.lower() not in excluded}


def response_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Remove only hop-by-hop fields from an engine response.

    Local router credentials are an inbound-only concern.  A response may
    legitimately contain an application authentication challenge or similarly
    named metadata, which must retain normal upstream-header semantics.
    """
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
        headers=response_headers(dict(raw.headers.items())),
        raw=raw,
    )
