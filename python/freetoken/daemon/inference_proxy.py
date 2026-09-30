"""Small request-preserving HTTP bridge from freetoken-swap to ``ft serve``.

No inference dependency is imported here. The daemon only parses the request
JSON long enough to select an allowlisted profile, then forwards the original
bytes and safe HTTP headers to the selected FreeToken engine.
"""
# What: document small request preserving http bridge from freetoken swap in the inference_proxy docstring; why: introspection and maintainers read this exact docstring fragment to understand inference proxy behavior without executing it.
# What: document no inference dependency is imported here in the inference_proxy docstring; why: introspection and maintainers read this exact docstring fragment to understand inference proxy behavior without executing it.
# What: document json long enough to select an in the inference_proxy docstring; why: introspection and maintainers read this exact docstring fragment to understand inference proxy behavior without executing it.
# What: document bytes and safe http headers to in the inference_proxy docstring; why: introspection and maintainers read this exact docstring fragment to understand inference proxy behavior without executing it.
# What: preserve the paragraph boundary in the the inference_proxy docstring; why: introspection and maintainers read this paragraph break to understand inference proxy behavior without executing it.

# What: enable postponed evaluation of annotations; why: type hints in inference_proxy can reference runtime types without eager imports or forward-reference failures.
from __future__ import annotations

# What: import json for request model using json; why: request_model uses json loads, making that imported dependency available to its named operation.
import json

# What: import re for open upstream using re; why: open_upstream uses re fullmatch, making that imported dependency available to its named operation.
import re

# What: import iterator and mapping for chunks and forward headers using typing and iterator and mapping; why: chunks and forward_headers uses the iterator annotation in chunks and the mapping annotation in forward headers, making that imported dependency available to its named operation.
from collections.abc import Iterator, Mapping

# What: import dataclass and field for response state using dataclasses; why: UpstreamResponse needs generated initialization plus an internal non-constructor cancellation flag.
from dataclasses import dataclass
from dataclasses import field as dataclass_field

# What: import httperror for open upstream using urllib and error and httperror; why: open_upstream uses the httperror annotation in open upstream, making that imported dependency available to its named operation.
from urllib.error import HTTPError

# What: import request and urlopen for open upstream using urllib and request and request and urlopen; why: open_upstream uses request and urlopen, making that imported dependency available to its named operation.
from urllib.request import Request, urlopen

# What: import request field for set fields using catalog and request field; why: _set_fields uses the request field annotation in set fields, making that imported dependency available to its named operation.
from .catalog import RequestField


# What: define RequestModelError as the owner of its declared state; why: daemon callers use this class boundary so those methods share one request model error state invariant.
class RequestModelError(ValueError):
    """The request cannot be routed because it has no valid model identifier."""
# What: document the request cannot be routed because in the RequestModelError docstring; why: introspection and maintainers read this exact docstring fragment to understand request model error behavior without executing it.


# What: compute hop by hop from connection and content length and host and keep alive and proxy authenticate; why: excluded hop by hop local auth headers later reads hop by hop, so inference_proxy must retain the computed value under that name.
_HOP_BY_HOP = {"connection", "content-length", "host", "keep-alive", "proxy-authenticate",
               # What: apply the proxy authorization te trailer transfer encoding upgrade portion of hop by hop; why: inference_proxy uses this clause to evaluate hop by hop as one grouped value.
               "proxy-authorization", "te", "trailer", "transfer-encoding", "upgrade"}
# What: compute local auth headers from authorization and x api key and x ft token; why: excluded hop by hop local auth headers later reads local auth headers, so inference_proxy must retain the computed value under that name.
_LOCAL_AUTH_HEADERS = {"authorization", "x-api-key", "x-ft-token"}


# What: define request_model around body; why: its direct callers call request_model for request model and rely on this exact input and result contract.
def request_model(body: bytes) -> str:
    # What: establish the handler boundary for the protected operation; why: request_model routes failures to unicode decode error and jsondecode error and json while preserving cleanup and success flow.
    try:
        # What: compute doc from loads and body and json; why: model doc get model if isinstance doc later reads doc, so request_model must retain the computed value under that name.
        doc = json.loads(body)
    # What: handle unicode decode error and jsondecode error and json by raise request model error request body must be valid; why: request_model converts that failure into this concrete recovery, response, or cleanup behavior.
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        # What: raise RequestModelError for the caller; why:  request_model stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RequestModelError("request body must be valid JSON with a model string") from exc
    # What: compute model from isinstance and doc and dict and get and model; why: if not isinstance model str or later reads model, so request_model must retain the computed value under that name.
    model = doc.get("model") if isinstance(doc, dict) else None
    # What: gate on model and isinstance and str and strip before request model error; why: request_model admits request model error only for this predicate and excludes the opposite state.
    if not isinstance(model, str) or not model.strip() or "\x00" in model:
        # What: raise RequestModelError for the caller; why:  request_model stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RequestModelError("request body must include a non-empty model string")
    # What: return model from request_model; why: request_model exposes model so its caller can continue with the function\'s computed outcome.
    return model


# What: define _path_parent around doc and path and create; why: its direct callers call _path_parent for path parent and rely on this exact input and result contract.
def _path_parent(doc: dict, path: tuple[str, ...], *, create: bool) -> dict | None:
    # What: compute current from doc; why: child current get part later reads current, so _path_parent must retain the computed value under that name.
    current = doc
    # What: iterate across path to perform child and get and part and current; why: _path_parent repeats the body only while or for the loop header admits an iteration.
    for part in path[:-1]:
        # What: compute child from get and part and current; why: if not isinstance child dict later reads child, so _path_parent must retain the computed value under that name.
        child = current.get(part)
        # What: gate on isinstance and child and dict before create; why: _path_parent admits create only for this predicate and excludes the opposite state.
        if not isinstance(child, dict):
            # What: gate on create before the computed value; why: _path_parent admits the computed value only for this predicate and excludes the opposite state.
            if not create:
                # What: return no value from _path_parent; why: _path_parent returns no value to callers that depend on its completed result.
                return None
            # What: initialize child as an empty runtime accumulator; why: _path_parent appends or maps entries into it during current part child before consuming the aggregate.
            child = {}
            # What: compute current entry from child; why: current child later reads current entry, so _path_parent must retain the computed value under that name.
            current[part] = child
        # What: compute current from child; why: return current later reads current, so _path_parent must retain the computed value under that name.
        current = child
    # What: return current from _path_parent; why: _path_parent exposes current so its caller can continue with the function\'s computed outcome.
    return current


# What: define _set_fields around doc and fields; why: its direct callers call _set_fields for set fields and rely on this exact input and result contract.
def _set_fields(doc: dict, fields: tuple[RequestField, ...]) -> None:
    # What: iterate across fields to perform parent and path parent and doc and path and field; why: _set_fields repeats the body only while or for the loop header admits an iteration.
    for field in fields:
        # What: compute parent from path parent and doc and path and field and true; why: assert parent is not later reads parent, so _set_fields must retain the computed value under that name.
        parent = _path_parent(doc, field.path, create=True)
        # What: assert that parent is not group delimiter; why: _set_fields requires parent is not group delimiter to be true, so a false result stops the invalid state.
        assert parent is not None
        # What: compute leaf from path and field and 1; why: if field soft and leaf in parent later reads leaf, so _set_fields must retain the computed value under that name.
        leaf = field.path[-1]
        # What: gate on soft and field and leaf and parent before the computed value; why: _set_fields admits the computed value only for this predicate and excludes the opposite state.
        if field.soft and leaf in parent:
            # What: apply the continue portion of the enclosing predicate; why: this clause remains in _set_fields\'s enclosing expression so its grouping and evaluation order stay intact.
            continue
        # What: compute parent entry from value and field; why: the enclosing return or state update later reads parent entry, so _set_fields must retain the computed value under that name.
        parent[leaf] = field.value()


# What: define filter_request_body around body and drop fields and set fields and set fields by id and requested model and rewrite model; why: its direct callers call filter_request_body for filter request body and rely on this exact input and result contract.
def filter_request_body(
    # What: declare the body input for filter_request_body; why: filter_request_body consumes body during return body, so callers must bind it with the other signature inputs.
    body: bytes,
    # What: declare the drop fields input for filter_request_body; why: filter_request_body consumes drop fields during for field in drop fields, so callers must bind it with the other signature inputs.
    drop_fields: tuple[str, ...],
    # What: declare the set fields input for filter_request_body; why: filter_request_body consumes set fields during set fields doc set fields, so callers must bind it with the other signature inputs.
    set_fields: tuple[RequestField, ...] = (),
    # What: declare the set fields by id input for filter_request_body; why: filter_request_body consumes set fields by id during by id dict set fields by id get requested model, so callers must bind it with the other signature inputs.
    set_fields_by_id: tuple[tuple[str, tuple[RequestField, ...]], ...] = (),
    # What: mark the remaining parameters as keyword-only; why: filter_request_body prevents callers from confusing adjacent lifecycle and timing arguments.
    *,
    # What: declare the requested model input for filter_request_body; why: filter_request_body consumes requested model during by id dict set fields by id get requested model, so callers must bind it with the other signature inputs.
    requested_model: str | None = None,
    # What: declare the rewrite model input for filter_request_body; why: filter_request_body consumes rewrite model during if rewrite model is not, so callers must bind it with the other signature inputs.
    rewrite_model: str | None = None,
# What: complete the enclosing predicate with bytes; why: filter_request_body groups the supplied clauses as one enclosing predicate expression before its value is consumed.
) -> bytes:
    """Apply safe configured JSON-field transformations in pinned order.

    The default empty policy returns the original bytes exactly. A requested
    rewrite runs before drop/global/by-ID fields, matching the pinned filter
    order. There is no expression or hook language, so a catalog cannot
    execute code in the daemon.
    """
    # What: document apply safe configured json field transformations in in the filter_request_body docstring; why: introspection and maintainers read this exact docstring fragment to understand filter request body behavior without executing it.
    # What: document the default empty policy returns the in the filter_request_body docstring; why: introspection and maintainers read this exact docstring fragment to understand filter request body behavior without executing it.
    # What: document rewrite runs before drop global by id in the filter_request_body docstring; why: introspection and maintainers read this exact docstring fragment to understand filter request body behavior without executing it.
    # What: document order there is no expression or in the filter_request_body docstring; why: introspection and maintainers read this exact docstring fragment to understand filter request body behavior without executing it.
    # What: document execute code in the daemon in the filter_request_body docstring; why: introspection and maintainers read this exact docstring fragment to understand filter request body behavior without executing it.
    # What: preserve the paragraph boundary in the the filter_request_body docstring; why: introspection and maintainers read this paragraph break to understand filter request body behavior without executing it.
    # What: compute by id from get and requested model and dict and set fields by id; why: if rewrite model is and not drop fields later reads by id, so filter_request_body must retain the computed value under that name.
    by_id = dict(set_fields_by_id).get(requested_model, ())
    # What: gate on rewrite model and drop fields and set fields and by id before body; why: filter_request_body admits body only for this predicate and excludes the opposite state.
    if rewrite_model is None and not drop_fields and not set_fields and not by_id:
        # What: return body from filter_request_body; why: filter_request_body exposes body so its caller can continue with the function\'s computed outcome.
        return body
    # What: establish the handler boundary for the protected operation; why: filter_request_body routes failures to unicode decode error and jsondecode error and json while preserving cleanup and success flow.
    try:
        # What: compute doc from loads and body and json; why: if not isinstance doc dict later reads doc, so filter_request_body must retain the computed value under that name.
        doc = json.loads(body)
    # What: handle unicode decode error and jsondecode error and json by raise request model error request body must be valid; why: filter_request_body converts that failure into this concrete recovery, response, or cleanup behavior.
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        # What: raise RequestModelError for the caller; why:  filter_request_body stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RequestModelError("request body must be valid JSON") from exc
    # What: gate on isinstance and doc and dict before request model error; why: filter_request_body admits request model error only for this predicate and excludes the opposite state.
    if not isinstance(doc, dict):
        # What: raise RequestModelError for the caller; why:  filter_request_body stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RequestModelError("request body must be a JSON object")
    # What: gate on rewrite model before rewrite model and doc; why: filter_request_body admits rewrite model and doc only for this predicate and excludes the opposite state.
    if rewrite_model is not None:
        # What: compute doc entry from rewrite model; why: parent path parent doc path create later reads doc entry, so filter_request_body must retain the computed value under that name.
        doc["model"] = rewrite_model
    # What: iterate across drop fields to perform path and tuple and split and field; why: filter_request_body repeats the body only while or for the loop header admits an iteration.
    for field in drop_fields:
        # What: compute path from tuple and split and field and value; why: parent path parent doc path create later reads path, so filter_request_body must retain the computed value under that name.
        path = tuple(field.split("."))
        # What: compute parent from path parent and doc and path and false; why: if parent is not later reads parent, so filter_request_body must retain the computed value under that name.
        parent = _path_parent(doc, path, create=False)
        # What: gate on parent before pop and parent and path; why: filter_request_body admits pop and parent and path only for this predicate and excludes the opposite state.
        if parent is not None:
            # What: call parent.pop with path and 1 and the named fixture input; why: filter_request_body invokes parent.pop while performing set fields doc set fields; the call advances that operation through its result or side effect.
            parent.pop(path[-1], None)
    # What: call _set_fields with doc and set fields; why: filter_request_body invokes _set_fields while performing set fields doc by id; the call advances that operation through its result or side effect.
    _set_fields(doc, set_fields)
    # What: call _set_fields with doc and by id; why: filter_request_body invokes _set_fields while performing return json dumps doc separators ensure ascii encode; the call advances that operation through its result or side effect.
    _set_fields(doc, by_id)
    # What: return encode and dumps and doc and json and utf 8 from filter_request_body; why: filter_request_body exposes encode and dumps and doc and json and utf 8 so its caller can continue with the function\'s computed outcome.
    return json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


# What: define forward_headers around headers; why: its direct callers call forward_headers for forward headers and rely on this exact input and result contract.
def forward_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Preserve application headers without forwarding daemon authentication.

    The router terminates its bearer/Basic/``x-api-key`` credential and optional
    ``X-FT-Token`` locally. None is an engine credential, so forwarding one would
    disclose a control-plane secret to the child process and its logs.
    """
    # What: document preserve application headers without forwarding daemon in the forward_headers docstring; why: introspection and maintainers read this exact docstring fragment to understand forward headers behavior without executing it.
    # What: document the router terminates its bearer basic in the forward_headers docstring; why: introspection and maintainers read this exact docstring fragment to understand forward headers behavior without executing it.
    # What: document x ft token locally is an engine credential in the forward_headers docstring; why: introspection and maintainers read this exact docstring fragment to understand forward headers behavior without executing it.
    # What: document disclose a control plane secret to the in the forward_headers docstring; why: introspection and maintainers read this exact docstring fragment to understand forward headers behavior without executing it.
    # What: preserve the paragraph boundary in the the forward_headers docstring; why: introspection and maintainers read this paragraph break to understand forward headers behavior without executing it.
    # What: compute excluded from hop by hop and local auth headers; why: return key value for key value later reads excluded, so forward_headers must retain the computed value under that name.
    excluded = _HOP_BY_HOP | _LOCAL_AUTH_HEADERS
    # What: return key and value and items and excluded from forward_headers; why: forward_headers exposes key and value and items and excluded so its caller can continue with the function\'s computed outcome.
    return {key: value for key, value in headers.items() if key.lower() not in excluded}


# What: define response_headers around headers; why: its direct callers call response_headers for response headers and rely on this exact input and result contract.
def response_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Remove only hop-by-hop fields from an engine response.

    Local router credentials are an inbound-only concern.  A response may
    legitimately contain an application authentication challenge or similarly
    named metadata, which must retain normal upstream-header semantics.
    """
    # What: document remove only hop by hop fields from an in the response_headers docstring; why: introspection and maintainers read this exact docstring fragment to understand response headers behavior without executing it.
    # What: document local router credentials are an inbound only in the response_headers docstring; why: introspection and maintainers read this exact docstring fragment to understand response headers behavior without executing it.
    # What: document legitimately contain an application authentication challenge in the response_headers docstring; why: introspection and maintainers read this exact docstring fragment to understand response headers behavior without executing it.
    # What: document named metadata which must retain normal in the response_headers docstring; why: introspection and maintainers read this exact docstring fragment to understand response headers behavior without executing it.
    # What: preserve the paragraph boundary in the the response_headers docstring; why: introspection and maintainers read this paragraph break to understand response headers behavior without executing it.
    # What: return key and value and items and hop by hop from response_headers; why: response_headers exposes key and value and items and hop by hop so its caller can continue with the function\'s computed outcome.
    return {key: value for key, value in headers.items() if key.lower() not in _HOP_BY_HOP}


# What: generate dataclass initialization and value semantics for UpstreamResponse; why: UpstreamResponse acts as a typed state record with consistent construction, comparison, and representation.
@dataclass
# What: define UpstreamResponse as the owner of chunks and close; why: daemon callers use this class boundary so those methods share one upstream response state invariant.
class UpstreamResponse:
    # What: compute status from the named fixture input; why: status raw getcode later reads status, so inference_proxy must retain the computed value under that name.
    status: int
    # What: compute headers from the named fixture input; why: def open upstream port int path and query str later reads headers, so inference_proxy must retain the computed value under that name.
    headers: dict[str, str]
    # What: compute raw from the named fixture input; why: chunk self raw read size later reads raw, so inference_proxy must retain the computed value under that name.
    raw: object
    # What: track whether an explicit close has interrupted the response; why: a concurrent socket close may surface as a low-level read error that represents expected cancellation rather than a server failure.
    _closed: bool = dataclass_field(default=False, init=False, repr=False)

    # What: define chunks around size; why: its direct callers call chunks for chunks and rely on this exact input and result contract.
    def chunks(self, size: int = 64 * 1024) -> Iterator[bytes]:
        # What: establish the handler boundary for the protected operation; why: UpstreamResponse.chunks routes failures to the unconditional cleanup block while preserving cleanup and success flow.
        try:
            # What: iterate across the computed value to perform chunk and read and size and raw; why: chunks repeats the body only while or for the loop header admits an iteration.
            while True:
                # What: read the next upstream block while distinguishing cancellation races; why: closing Python's HTTP response from another thread can invalidate its internal file pointer during this call.
                try:
                    # What: retain the next raw response block; why: non-empty data must continue through the streaming iterator unchanged.
                    chunk = self.raw.read(size)
                # What: handle close-induced low-level stream state errors; why: expected cancellation should terminate cleanly while unrelated transport defects still propagate.
                except (AttributeError, ValueError):
                    # What: re-raise when no explicit close occurred; why: only a proven cancellation race may be converted into normal end-of-stream behavior.
                    if not self._closed:
                        # What: propagate the unexpected read failure; why: callers must retain visibility into genuine upstream corruption or implementation defects.
                        raise
                    # What: end iteration after a concurrent explicit close; why: cancellation already owns cleanup and should not emit an ASGI exception traceback.
                    return
                # What: gate on chunk before the computed value; why: chunks admits the computed value only for this predicate and excludes the opposite state.
                if not chunk:
                    # What: apply the break portion of the enclosing predicate; why: this clause remains in chunks\'s enclosing expression so its grouping and evaluation order stay intact.
                    break
                # What: apply the yield chunk portion of the enclosing predicate; why: this clause remains in chunks\'s enclosing expression so its grouping and evaluation order stay intact.
                yield chunk
        # What: run self close on every exit path; why: chunks performs this cleanup after success, rejection, or exception so resources and accounting cannot remain stranded.
        finally:
            # What: call self.close with the declared inputs; why: chunks invokes self.close while performing the enclosing return; the call advances that operation through its result or side effect.
            self.close()

    # What: define close around the current object state; why: its direct callers call close for close and rely on this exact input and result contract.
    def close(self) -> None:
        # What: mark the response closed before touching the raw transport; why: a blocked reader awakened by raw.close can observe cancellation before it raises from invalid internal state.
        self._closed = True
        # What: compute close from getattr and raw and close; why: if close is not later reads close, so close must retain the computed value under that name.
        close = getattr(self.raw, "close", None)
        # What: gate on close before close; why: close admits close only for this predicate and excludes the opposite state.
        if close is not None:
            # What: call close with the declared inputs; why: close invokes close while performing the enclosing return; the call advances that operation through its result or side effect.
            close()


# What: define open_upstream around port and path and query and headers and body and method and timeout s and base url; why: its direct callers call open_upstream for open upstream and rely on this exact input and result contract.
def open_upstream(*, port: int, path_and_query: str, headers: Mapping[str, str], body: bytes,
                  # What: declare the method input for open_upstream; why: open_upstream consumes method during method method, so callers must bind it with the other signature inputs.
                  method: str = "POST", timeout_s: float = 900.0,
                  # What: declare the base url input for open_upstream; why: open_upstream consumes base url during base url base url or owned base, so callers must bind it with the other signature inputs.
                  base_url: str | None = None) -> UpstreamResponse:
    # What: compute owned base from port and http; why: base url base url or owned base later reads owned base, so open_upstream must retain the computed value under that name.
    owned_base = f"http://127.0.0.1:{port}"
    # What: compute base url from base url and owned base; why: rf http port a za z0 9 base url later reads base url, so open_upstream must retain the computed value under that name.
    base_url = base_url or owned_base
    # What: gate on any and fullmatch and base url and re and segment before value error; why: open_upstream admits value error only for this predicate and excludes the opposite state.
    if (
        # What: call re.fullmatch with port and http and a za z0 9 and value and base url; why: open_upstream invokes re.fullmatch while performing rf http port a za z0 9 base url; the call advances that operation through its result or side effect.
        re.fullmatch(
            # What: apply the rf http port a za z0 9 base url portion of the enclosing predicate; why: this clause remains in open_upstream\'s enclosing expression so its grouping and evaluation order stay intact.
            rf"http://127\.0\.0\.1:{port}(?:/[A-Za-z0-9._~-]+)*", base_url
        # What: complete the re.fullmatch call with port and base url; why: open_upstream groups the supplied clauses as one re.fullmatch call before its value is consumed.
        )
        # What: apply the is portion of the enclosing predicate; why: this clause remains in open_upstream\'s enclosing expression so its grouping and evaluation order stay intact.
        is None
        # What: call any with segment and split and base url and value and value; why: open_upstream consumes the any return value while evaluating or any(segment in {".", ".."} for segment in base_url.split("/")).
        or any(segment in {".", ".."} for segment in base_url.split("/"))
    # What: complete the enclosing predicate with if re fullmatch f http 127 0 0 1 port; why: open_upstream groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise ValueError for the caller; why:  open_upstream stops this rejected path before it can mutate state, dispatch work, or report success.
        raise ValueError("upstream base URL must target the manager-owned loopback port")
    # What: gate on startswith and path and query before value error; why: open_upstream admits value error only for this predicate and excludes the opposite state.
    if not path_and_query.startswith("/"):
        # What: raise ValueError for the caller; why:  open_upstream stops this rejected path before it can mutate state, dispatch work, or report success.
        raise ValueError("upstream path must be absolute")
    # What: compute request from request and body and method and path and query; why: raw urlopen request timeout timeout s later reads request, so open_upstream must retain the computed value under that name.
    request = Request(
        # What: call base_url.rstrip with value; why: open_upstream invokes base_url.rstrip while performing data body; the call advances that operation through its result or side effect.
        f"{base_url.rstrip('/')}{path_and_query}",
        # What: supply data to Request; why: open_upstream binds this body value to Request's data input.
        data=body,
        # What: supply headers to forward_headers; why: open_upstream binds this forward headers and headers value to forward_headers's headers input.
        headers=forward_headers(headers),
        # What: supply method to Request; why: open_upstream binds this method value to Request's method input.
        method=method,
    # What: complete the Request call with data and headers and method; why: open_upstream groups the supplied clauses as one Request call before its value is consumed.
    )
    # What: establish the handler boundary for the protected operation; why: open_upstream routes failures to httperror while preserving cleanup and success flow.
    try:
        # What: compute raw from urlopen and request and timeout s; why: raw exc later reads raw, so open_upstream must retain the computed value under that name.
        raw = urlopen(request, timeout=timeout_s)
    # What: handle httperror by raw exc; why: open_upstream converts that failure into this concrete recovery, response, or cleanup behavior.
    except HTTPError as exc:
        # What: compute raw from exc; why: status raw getcode later reads raw, so open_upstream must retain the computed value under that name.
        raw = exc
    # What: return upstream response and raw and getcode and response headers from open_upstream; why: open_upstream exposes upstream response and raw and getcode and response headers so its caller can continue with the function\'s computed outcome.
    return UpstreamResponse(
        # What: supply status to raw.getcode; why: open_upstream binds this getcode and raw value to raw.getcode's status input.
        status=raw.getcode(),
        # What: supply headers to response_headers; why: open_upstream binds this response headers and dict and items and headers value to response_headers's headers input.
        headers=response_headers(dict(raw.headers.items())),
        # What: supply raw to UpstreamResponse; why: open_upstream binds this raw value to UpstreamResponse's raw input.
        raw=raw,
    # What: complete the UpstreamResponse call with status and headers and raw; why: open_upstream groups the supplied clauses as one UpstreamResponse call before its value is consumed.
    )
