"""Named, validated FreeToken engine profiles for ``ft daemon``.

This intentionally borrows the useful *catalog* idea from llama-swap without
accepting its shell-command model.  A profile describes only FreeToken's native
``--model``, ``--port`` and argument-vector contract, so loading a catalog never
creates a shell injection path and the daemon remains torch-free.
"""
# What: document named validated free token engine profiles for in the catalog docstring; why: introspection and maintainers read this exact docstring fragment to understand catalog behavior without executing it.
# What: document this intentionally borrows the useful catalog in the catalog docstring; why: introspection and maintainers read this exact docstring fragment to understand catalog behavior without executing it.
# What: document accepting its shell command model a profile in the catalog docstring; why: introspection and maintainers read this exact docstring fragment to understand catalog behavior without executing it.
# What: document model port and argument vector contract so in the catalog docstring; why: introspection and maintainers read this exact docstring fragment to understand catalog behavior without executing it.
# What: document creates a shell injection path and in the catalog docstring; why: introspection and maintainers read this exact docstring fragment to understand catalog behavior without executing it.
# What: preserve the paragraph boundary in the the catalog docstring; why: introspection and maintainers read this paragraph break to understand catalog behavior without executing it.

# What: enable postponed evaluation of annotations; why: type hints in catalog can reference runtime types without eager imports or forward-reference failures.
from __future__ import annotations

# What: import dataclass and replace for module initialization and init using dataclasses and dataclass and replace; why: module initialization and __init__ uses dataclass and replace, making that imported dependency available to its named operation.
from dataclasses import dataclass, replace
# What: import json for value using json; why: value uses json loads, making that imported dependency available to its named operation.
import json
# What: import re for module initialization using re; why: module initialization uses re compile, making that imported dependency available to its named operation.
import re
# What: import any for value using typing and any; why: value uses the any annotation in value, making that imported dependency available to its named operation.
from typing import Any

# What: establish the handler boundary for the protected operation; why: catalog routes failures to module not found error while preserving cleanup and success flow.
try:  # tomllib joined the stdlib in Python 3.11; FreeToken supports 3.10 too.
    # What: import tomllib for load using tomllib; why: load uses tomllib tomldecode error, making that imported dependency available to its named operation.
    import tomllib
# What: handle module not found error by import tomli as tomllib; why: catalog converts that failure into this concrete recovery, response, or cleanup behavior.
except ModuleNotFoundError:  # pragma: no cover - exercised in the Python 3.10 package build
    # What: import tomli for load using tomli and tomllib; why: load uses tomllib tomldecode error, making that imported dependency available to its named operation.
    import tomli as tomllib


# What: compute simple name from compile and re and a za z0 9 and a za z0 9 and value; why: if not isinstance name str or later reads simple name, so catalog must retain the computed value under that name.
_SIMPLE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
# What: compute model segment from compile and re and a za z0 9 and a za z0 9 and value; why: and all model segment fullmatch segment for segment later reads model segment, so catalog must retain the computed value under that name.
_MODEL_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
# What: compute safe http path from compile and re and a za z0 9 and value and a za z0 9; why: or not safe http path fullmatch value later reads safe http path, so catalog must retain the computed value under that name.
_SAFE_HTTP_PATH = re.compile(r"^/(?:[A-Za-z0-9._~-]+(?:/[A-Za-z0-9._~-]+)*)?$")
# What: compute upstream suffix from compile and re and a za z0 9 and a za z0 9 and value; why: isinstance suffix str and upstream suffix fullmatch suffix later reads upstream suffix, so catalog must retain the computed value under that name.
_UPSTREAM_SUFFIX = re.compile(r"^\.[A-Za-z0-9][A-Za-z0-9._-]{0,31}$")
# What: compute http header name from compile and re and value and a za z; why: isinstance header str and http header name fullmatch header later reads http header name, so catalog must retain the computed value under that name.
_HTTP_HEADER_NAME = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]{1,64}$")
# What: compute proxy template from compile and re and http and port and p; why: match proxy template fullmatch value later reads proxy template, so catalog must retain the computed value under that name.
_PROXY_TEMPLATE = re.compile(
    # What: apply the r http port p prefix a za z0 9 portion of proxy template; why: catalog uses this clause to evaluate proxy template as one grouped value.
    r"^http://127\.0\.0\.1:\$\{PORT\}(?P<prefix>/(?:[A-Za-z0-9._~-]+(?:/[A-Za-z0-9._~-]+)*)?)?$"
# What: complete the re.compile call with ordered positional inputs; why: catalog groups the supplied clauses as one re.compile call before its value is consumed.
)

# What: compute default check endpoint from health; why: check endpoint str default check endpoint later reads default check endpoint, so catalog must retain the computed value under that name.
DEFAULT_CHECK_ENDPOINT = "/health"
# What: compute default proxy from http and port; why: proxy str default proxy later reads default proxy, so catalog must retain the computed value under that name.
DEFAULT_PROXY = "http://127.0.0.1:${PORT}"
# What: compute default upstream no activation suffixes from js and json and css and png and gif; why: catalog consumes default upstream no activation suffixes during upstream no activation suffixes tuple str default upstream no activation suffixes, so default upstream no activation suffixes value receives the compute.
DEFAULT_UPSTREAM_NO_ACTIVATION_SUFFIXES = (
    # What: apply the js json css png gif jpg portion of default upstream no activation suffixes; why: catalog uses this clause to evaluate default upstream no activation suffixes as one grouped value.
    ".js", ".json", ".css", ".png", ".gif", ".jpg", ".jpeg", ".ico", ".txt",
# What: complete the DEFAULT_UPSTREAM_NO_ACTIVATION_SUFFIXES collection with js and json and css and png; why: catalog groups the supplied clauses as one DEFAULT_UPSTREAM_NO_ACTIVATION_SUFFIXES collection before its value is consumed.
)
# What: compute default activity session headers from x session id and x litellm session id; why: activity session headers tuple str default activity session headers later reads default activity session headers, so catalog must retain the computed value under that name.
DEFAULT_ACTIVITY_SESSION_HEADERS = ("x-session-id", "x-litellm-session-id")


# What: define CatalogError as the owner of its declared state; why: daemon callers use this class boundary so those methods share one catalog error state invariant.
class CatalogError(ValueError):
    """A catalog is malformed or requests an unsafe/ambiguous profile."""
# What: document a catalog is malformed or requests in the CatalogError docstring; why: introspection and maintainers read this exact docstring fragment to understand catalog error behavior without executing it.


# What: generate dataclass initialization and value semantics for RoutingGroup; why: RoutingGroup acts as a typed state record with consistent construction, comparison, and representation.
@dataclass(frozen=True)
# What: define RoutingGroup as the owner of its declared state; why: daemon callers use this class boundary so those methods share one routing group state invariant.
class RoutingGroup:
    """An atomically validated native equivalent of a llama-swap group."""
# What: document an atomically validated native equivalent of in the RoutingGroup docstring; why: introspection and maintainers read this exact docstring fragment to understand routing group behavior without executing it.

    # What: compute name from the named fixture input; why: name str later reads name, so catalog must retain the computed value under that name.
    name: str
    # What: compute members from the named fixture input; why: if name in group members later reads members, so catalog must retain the computed value under that name.
    members: tuple[str, ...]
    # What: compute swap from true; why: render the applicable pinned llama swap model list later reads swap, so catalog must retain the computed value under that name.
    swap: bool = True
    # What: compute exclusive from true; why: unknown sorted set raw group members swap later reads exclusive, so catalog must retain the computed value under that name.
    exclusive: bool = True
    # What: compute persistent from false; why: unknown sorted set raw group members swap later reads persistent, so catalog must retain the computed value under that name.
    persistent: bool = False


# What: generate dataclass initialization and value semantics for RouterSettings; why: RouterSettings acts as a typed state record with consistent construction, comparison, and representation.
@dataclass(frozen=True)
# What: define RouterSettings as the owner of its declared state; why: daemon callers use this class boundary so those methods share one router settings state invariant.
class RouterSettings:
    """Global router policy, deliberately free of command execution fields."""
# What: document global router policy deliberately free of in the RouterSettings docstring; why: introspection and maintainers read this exact docstring fragment to understand router settings behavior without executing it.

    # What: compute api keys from the named fixture input; why: api keys default ttl s unload timeout s upstream timeout s later reads api keys, so catalog must retain the computed value under that name.
    api_keys: tuple[str, ...] = ()
    # What: compute default ttl s from 0 0; why: api keys default ttl s unload timeout s upstream timeout s later reads default ttl s, so catalog must retain the computed value under that name.
    default_ttl_s: float = 0.0
    # What: compute unload timeout s from 30 0; why: unload timeout s float later reads unload timeout s, so catalog must retain the computed value under that name.
    unload_timeout_s: float = 30.0
    # What: compute upstream timeout s from 900 0; why: upstream timeout s float later reads upstream timeout s, so catalog must retain the computed value under that name.
    upstream_timeout_s: float = 900.0
    # What: compute scheduler from fifo; why: scheduler groups include aliases in list global concurrency limit later reads scheduler, so catalog must retain the computed value under that name.
    scheduler: str = "fifo"
    # What: compute groups from the named fixture input; why: for group in self settings groups later reads groups, so catalog must retain the computed value under that name.
    groups: tuple[RoutingGroup, ...] = ()
    # What: compute include aliases in list from false; why: if self settings include aliases in list later reads include aliases in list, so catalog must retain the computed value under that name.
    include_aliases_in_list: bool = False
    # What: compute global concurrency limit from 0; why: scheduler groups include aliases in list global concurrency limit later reads global concurrency limit, so catalog must retain the computed value under that name.
    global_concurrency_limit: int = 0
    # What: compute send loading state from false; why: send loading state bool later reads send loading state, so catalog must retain the computed value under that name.
    send_loading_state: bool = False
    # What: compute preload model from the named fixture input; why: if settings preload model is not later reads preload model, so catalog must retain the computed value under that name.
    preload_model: str | None = None
    # What: compute startup routing profile from the named fixture input; why: settings startup routing profile is not later reads startup routing profile, so catalog must retain the computed value under that name.
    startup_routing_profile: str | None = None
    # What: compute upstream no activation suffixes from default upstream no activation suffixes; why: upstream no activation suffixes later reads upstream no activation suffixes, so catalog must retain the computed value under that name.
    upstream_no_activation_suffixes: tuple[str, ...] = DEFAULT_UPSTREAM_NO_ACTIVATION_SUFFIXES
    # What: compute activity max entries from 1000; why: activity max entries capture buffer mb later reads activity max entries, so catalog must retain the computed value under that name.
    activity_max_entries: int = 1000
    # What: compute capture buffer mb from 0; why: activity max entries capture buffer mb later reads capture buffer mb, so catalog must retain the computed value under that name.
    capture_buffer_mb: int = 0
    # What: compute activity session headers from default activity session headers; why: activity session headers later reads activity session headers, so catalog must retain the computed value under that name.
    activity_session_headers: tuple[str, ...] = DEFAULT_ACTIVITY_SESSION_HEADERS
    # What: compute performance disabled from false; why: performance disabled performance every s later reads performance disabled, so catalog must retain the computed value under that name.
    performance_disabled: bool = False
    # What: compute performance every s from 5 0; why: performance disabled performance every s later reads performance every s, so catalog must retain the computed value under that name.
    performance_every_s: float = 5.0


# What: generate dataclass initialization and value semantics for ModelCapabilities; why: ModelCapabilities acts as a typed state record with consistent construction, comparison, and representation.
@dataclass(frozen=True)
# What: define ModelCapabilities as the owner of empty and public and model_listing_fields; why: daemon callers use this class boundary so those methods share one model capabilities state invariant.
class ModelCapabilities:
    """Validated model-list metadata; it never enables inference behavior."""
# What: document validated model list metadata it never enables in the ModelCapabilities docstring; why: introspection and maintainers read this exact docstring fragment to understand model capabilities behavior without executing it.

    # What: compute input modalities from the named fixture input; why: self input modalities or self output modalities or self tools or later reads input modalities, so catalog must retain the computed value under that name.
    input_modalities: tuple[str, ...] = ()
    # What: compute output modalities from the named fixture input; why: self input modalities or self output modalities or self tools or later reads output modalities, so catalog must retain the computed value under that name.
    output_modalities: tuple[str, ...] = ()
    # What: compute tools from false; why: self input modalities or self output modalities or self tools or later reads tools, so catalog must retain the computed value under that name.
    tools: bool = False
    # What: compute context from 0; why: self input modalities or self output modalities or self tools or later reads context, so catalog must retain the computed value under that name.
    context: int = 0

    # What: define empty around the current object state; why: its direct callers call empty for empty and rely on this exact input and result contract.
    def empty(self) -> bool:
        # What: return input modalities and output modalities and tools and context from empty; why: empty exposes input modalities and output modalities and tools and context so its caller can continue with the function\'s computed outcome.
        return not (
            # What: apply the self input modalities or self output modalities or self tools or portion of the enclosing predicate; why: this clause remains in empty\'s enclosing expression so its grouping and evaluation order stay intact.
            self.input_modalities or self.output_modalities or self.tools or self.context
        # What: complete the empty signature with self; why: ModelCapabilities.empty groups the supplied clauses as one empty signature before its value is consumed.
        )

    # What: define public around the current object state; why:  its direct callers call public for public and rely on this exact input and result contract.
    def public(self) -> dict[str, Any]:
        # What: initialize doc as an empty runtime accumulator; why: ModelCapabilities.public appends or maps entries into it during doc in list self input modalities before consuming the aggregate.
        doc: dict[str, Any] = {}
        # What: gate on input modalities before doc and list and input modalities; why: public admits doc and list and input modalities only for this predicate and excludes the opposite state.
        if self.input_modalities:
            # What: compute doc entry from list and input modalities; why: doc out list self output modalities later reads doc entry, so public must retain the computed value under that name.
            doc["in"] = list(self.input_modalities)
        # What: gate on output modalities before doc and list and output modalities; why: public admits doc and list and output modalities only for this predicate and excludes the opposite state.
        if self.output_modalities:
            # What: compute doc entry from list and output modalities; why: doc tools later reads doc entry, so public must retain the computed value under that name.
            doc["out"] = list(self.output_modalities)
        # What: gate on tools before doc; why: public admits doc only for this predicate and excludes the opposite state.
        if self.tools:
            # What: compute doc entry from true; why: doc context self context later reads doc entry, so public must retain the computed value under that name.
            doc["tools"] = True
        # What: gate on context before context and doc; why: public admits context and doc only for this predicate and excludes the opposite state.
        if self.context:
            # What: compute doc entry from context; why: return doc later reads doc entry, so public must retain the computed value under that name.
            doc["context"] = self.context
        # What: return doc from public; why: public exposes doc so its caller can continue with the function\'s computed outcome.
        return doc

    # What: define model_listing_fields around the current object state; why: its direct callers call model_listing_fields for model listing fields and rely on this exact input and result contract.
    def model_listing_fields(self) -> dict[str, Any]:
        """Render the applicable pinned llama-swap model-list contract."""
        # What: document render the applicable pinned llama swap model list in the model_listing_fields docstring; why: introspection and maintainers read this exact docstring fragment to understand model listing fields behavior without executing it.
        # What: initialize doc as an empty runtime accumulator; why: ModelCapabilities.model_listing_fields appends or maps entries into it during doc architecture architecture before consuming the aggregate.
        doc: dict[str, Any] = {}
        # What: gate on input modalities and output modalities before architecture and dict and str and any; why: model_listing_fields admits architecture and dict and str and any only for this predicate and excludes the opposite state.
        if self.input_modalities or self.output_modalities:
            # What: initialize architecture as an empty runtime accumulator; why: ModelCapabilities.model_listing_fields appends or maps entries into it during architecture input modalities list self input modalities before consuming the aggregate.
            architecture: dict[str, Any] = {}
            # What: gate on input modalities before architecture and list and input modalities; why: model_listing_fields admits architecture and list and input modalities only for this predicate and excludes the opposite state.
            if self.input_modalities:
                # What: compute architecture entry from list and input modalities; why: architecture output modalities list self output modalities later reads architecture entry, so model_listing_fields must retain the computed value under that name.
                architecture["input_modalities"] = list(self.input_modalities)
            # What: gate on output modalities before architecture and list and output modalities; why: model_listing_fields admits architecture and list and output modalities only for this predicate and excludes the opposite state.
            if self.output_modalities:
                # What: compute architecture entry from list and output modalities; why: architecture modality later reads architecture entry, so model_listing_fields must retain the computed value under that name.
                architecture["output_modalities"] = list(self.output_modalities)
            # What: gate on input modalities and output modalities before architecture and join and input modalities and output modalities; why: model_listing_fields admits architecture and join and input modalities and output modalities only for this predicate and excludes the opposite state.
            if self.input_modalities and self.output_modalities:
                # What: compute architecture entry from join and input modalities and output modalities and value and value; why: doc architecture architecture later reads architecture entry, so model_listing_fields must retain the computed value under that name.
                architecture["modality"] = (
                    # What: call operation.join with input modalities; why: model_listing_fields consumes the operation.join return value while evaluating f"{'+'.join(self.input_modalities)}->{'+'.join(self.output_modalities)}".
                    f"{'+'.join(self.input_modalities)}->{'+'.join(self.output_modalities)}"
                # What: complete the architecture entry expression with architecture modality f join self input modalities join self output modalities; why: ModelCapabilities.model_listing_fields groups the supplied clauses as one architecture entry expression before its value is consumed.
                )
            # What: compute doc entry from architecture; why: doc capabilities function calling later reads doc entry, so model_listing_fields must retain the computed value under that name.
            doc["architecture"] = architecture
        # What: gate on tools before doc; why: model_listing_fields admits doc only for this predicate and excludes the opposite state.
        if self.tools:
            # What: map the function calling field as true; why: ModelCapabilities.model_listing_fields carries function calling through doc entry into doc supported parameters tools tool choice.
            doc["capabilities"] = {"function_calling": True}
            # What: compute doc entry from tools and tool choice; why: doc context length self context later reads doc entry, so model_listing_fields must retain the computed value under that name.
            doc["supported_parameters"] = ["tools", "tool_choice"]
        # What: gate on context before context and doc; why: model_listing_fields admits context and doc only for this predicate and excludes the opposite state.
        if self.context:
            # What: compute doc entry from context; why: doc context window self context later reads doc entry, so model_listing_fields must retain the computed value under that name.
            doc["context_length"] = self.context
            # What: compute doc entry from context; why: doc meta n ctx self context later reads doc entry, so model_listing_fields must retain the computed value under that name.
            doc["context_window"] = self.context
            # What: map the n ctx field as context; why: ModelCapabilities.model_listing_fields carries n ctx through doc entry into return doc.
            doc["meta"] = {"n_ctx": self.context}
        # What: return doc from model_listing_fields; why: model_listing_fields exposes doc so its caller can continue with the function\'s computed outcome.
        return doc


# What: generate dataclass initialization and value semantics for RequestField; why: RequestField acts as a typed state record with consistent construction, comparison, and representation.
@dataclass(frozen=True)
# What: define RequestField as the owner of key and value; why: daemon callers use this class boundary so those methods share one request field state invariant.
class RequestField:
    """One immutable, validated JSON field assignment."""
# What: document one immutable validated json field assignment in the RequestField docstring; why: introspection and maintainers read this exact docstring fragment to understand request field behavior without executing it.

    # What: compute path from the named fixture input; why: return join self path later reads path, so catalog must retain the computed value under that name.
    path: tuple[str, ...]
    # What: compute value json from the named fixture input; why: return json loads self value json later reads value json, so catalog must retain the computed value under that name.
    value_json: str
    # What: compute soft from false; why: field key if field soft else field value later reads soft, so catalog must retain the computed value under that name.
    soft: bool = False

    # What: expose key as a read-only computed property; why: callers read key through attribute access while its getter retains control of the derived value.
    @property
    # What: define key around the current object state; why: the registered API client call key for key and rely on this exact input and result contract.
    def key(self) -> str:
        # What: return join and path and value from key; why: key exposes join and path and value so its caller can continue with the function\'s computed outcome.
        return ".".join(self.path)

    # What: define value around the current object state; why: its direct callers call value for value and rely on this exact input and result contract.
    def value(self) -> Any:
        # What: return loads and value json and json from value; why: value exposes loads and value json and json so its caller can continue with the function\'s computed outcome.
        return json.loads(self.value_json)


# What: define _request_fields_public around fields; why: its direct callers call _request_fields_public for request fields public and rely on this exact input and result contract.
def _request_fields_public(fields: tuple[RequestField, ...]) -> dict[str, Any]:
    # What: return key and value and field and fields from _request_fields_public; why: _request_fields_public exposes key and value and field and fields so its caller can continue with the function\'s computed outcome.
    return {
        # What: call field.value with the declared inputs; why: _request_fields_public invokes field.value while performing for field in fields; the call advances that operation through its result or side effect.
        field.key + ("?" if field.soft else ""): field.value()
        # What: apply the for field in fields portion of the enclosing predicate; why: this clause remains in _request_fields_public\'s enclosing expression so its grouping and evaluation order stay intact.
        for field in fields
    # What: complete the _request_fields_public signature with fields; why: _request_fields_public groups the supplied clauses as one _request_fields_public signature before its value is consumed.
    }


# What: generate dataclass initialization and value semantics for ModelSelector; why: ModelSelector acts as a typed state record with consistent construction, comparison, and representation.
@dataclass(frozen=True)
# What: define ModelSelector as the owner of metadata and public; why: daemon callers use this class boundary so those methods share one model selector state invariant.
class ModelSelector:
    """A per-request virtual model resolved to one concrete local profile."""
# What: document a per request virtual model resolved to in the ModelSelector docstring; why: introspection and maintainers read this exact docstring fragment to understand model selector behavior without executing it.

    # What: compute name from the named fixture input; why: name self name later reads name, so  catalog must retain the computed value under that name.
    name: str
    # What: compute strategy from the named fixture input; why: strategy self strategy later reads strategy, so catalog must retain the computed value under that name.
    strategy: str
    # What: compute targets from the named fixture input; why: targets list self targets later reads targets, so catalog must retain the computed value under that name.
    targets: tuple[str, ...]
    # What: compute display name from the named fixture input; why: if self display name later reads display name, so  catalog must retain the computed value under that name.
    display_name: str | None = None
    # What: compute description from the named fixture input; why: if self description later reads description, so  catalog must retain the computed value under that name.
    description: str | None = None
    # What: compute unlisted from false; why: if self unlisted later reads unlisted, so  catalog must retain the computed value under that name.
    unlisted: bool = False
    # What: compute metadata json from value; why: return json loads self metadata json later reads metadata json, so  catalog must retain the computed value under that name.
    metadata_json: str = "{}"

    # What: define metadata around the current object state; why:  its direct callers call metadata for metadata and rely on this exact input and result contract.
    def metadata(self) -> dict[str, Any]:
        # What: return loads and metadata json and json from metadata; why: metadata exposes loads and metadata json and json so its caller can continue with the function\'s computed outcome.
        return json.loads(self.metadata_json)

    # What: define public around the current object state; why:  its direct callers call public for public and rely on this exact input and result contract.
    def public(self) -> dict[str, Any]:
        # What: compute doc from name and strategy and list and targets and name; why: doc display name self display name later reads doc, so public must retain the computed value under that name.
        doc: dict[str, Any] = {
            # What: map the name field as name; why: ModelSelector.public carries name through doc into doc display name self display name.
            "name": self.name,
            # What: map the strategy field as strategy; why: ModelSelector.public carries strategy through doc into doc display name self display name.
            "strategy": self.strategy,
            # What: map the targets field as list and targets; why: ModelSelector.public carries targets through doc into doc display name self display name.
            "targets": list(self.targets),
        # What: complete the doc mapping with name and strategy and targets; why: ModelSelector.public groups the supplied clauses as one doc mapping before its value is consumed.
        }
        # What: gate on display name before display name and doc; why:  public admits display name and doc only for this predicate and excludes the opposite state.
        if self.display_name:
            # What: compute doc entry from display name; why: doc description self description later reads doc entry, so  public must retain the computed value under that name.
            doc["displayName"] = self.display_name
        # What: gate on description before description and doc; why:  public admits description and doc only for this predicate and excludes the opposite state.
        if self.description:
            # What: compute doc entry from description; why: doc unlisted later reads doc entry, so public must retain the computed value under that name.
            doc["description"] = self.description
        # What: gate on unlisted before doc; why:  public admits doc only for this predicate and excludes the opposite state.
        if self.unlisted:
            # What: compute doc entry from true; why: doc metadata metadata later reads doc entry, so public must retain the computed value under that name.
            doc["unlisted"] = True
        # What: compute metadata from metadata; why: if metadata later reads metadata, so  public must retain the computed value under that name.
        metadata = self.metadata()
        # What: gate on metadata before metadata and doc; why:  public admits metadata and doc only for this predicate and excludes the opposite state.
        if metadata:
            # What: compute doc entry from metadata; why: return doc later reads doc entry, so public must retain the computed value under that name.
            doc["metadata"] = metadata
        # What: return doc from public; why: public exposes doc so its caller can continue with the function\'s computed outcome.
        return doc


# What: generate dataclass initialization and value semantics for RoutingProfile; why: RoutingProfile acts as a typed state record with consistent construction, comparison, and representation.
@dataclass(frozen=True)
# What: define RoutingProfile as the owner of replacement and public; why: daemon callers use this class boundary so those methods share one routing profile state invariant.
class RoutingProfile:
    """A runtime-selectable set of client model-ID replacements."""
# What: document a runtime selectable set of client model id in the RoutingProfile docstring; why: introspection and maintainers read this exact docstring fragment to understand routing profile behavior without executing it.

    # What: compute name from the named fixture input; why: name self name later reads name, so  catalog must retain the computed value under that name.
    name: str
    # What: compute pins from the named fixture input; why: for pin target in self pins later reads pins, so catalog must retain the computed value under that name.
    pins: tuple[tuple[str, str | None], ...]
    # What: compute description from the named fixture input; why: if self description later reads description, so  catalog must retain the computed value under that name.
    description: str | None = None

    # What: define replacement around model id; why: its direct callers call replacement for replacement and rely on this exact input and result contract.
    def replacement(self, model_id: str) -> tuple[bool, str | None]:
        # What: iterate across pins to perform pin and model id and target; why: replacement repeats the body only while or for the loop header admits an iteration.
        for pin, target in self.pins:
            # What: gate on pin and model id before target; why: replacement admits target only for this predicate and excludes the opposite state.
            if pin == model_id:
                # What: return target and true from replacement; why: replacement exposes target and true so its caller can continue with the function\'s computed outcome.
                return True, target
        # What: return false from replacement; why: replacement exposes false so its caller can continue with the function\'s computed outcome.
        return False, None

    # What: define public around the current object state; why:  its direct callers call public for public and rely on this exact input and result contract.
    def public(self) -> dict[str, Any]:
        # What: compute doc from name and pin and target and pins and name; why: doc description self description later reads doc, so public must retain the computed value under that name.
        doc: dict[str, Any] = {
            # What: map the name field as name; why: RoutingProfile.public carries name through doc into doc description self description.
            "name": self.name,
            # What: map the pins field as pin and target and pins; why: RoutingProfile.public carries pins through doc into doc description self description.
            "pins": {pin: target for pin, target in self.pins},
        # What: complete the doc mapping with name and pins; why: RoutingProfile.public groups the supplied clauses as one doc mapping before its value is consumed.
        }
        # What: gate on description before description and doc; why:  public admits description and doc only for this predicate and excludes the opposite state.
        if self.description:
            # What: compute doc entry from description; why: return doc later reads doc entry, so public must retain the computed value under that name.
            doc["description"] = self.description
        # What: return doc from public; why: public exposes doc so its caller can continue with the function\'s computed outcome.
        return doc


# What: generate dataclass initialization and value semantics for ModelProfile; why: ModelProfile acts as a typed state record with consistent construction, comparison, and representation.
@dataclass(frozen=True)
# What: define ModelProfile as the owner of metadata and proxy_base_url and request and public; why: daemon callers use this class boundary so those methods share one model profile state invariant.
class ModelProfile:
    # What: compute name from the named fixture input; why: doc name self name later reads name, so catalog must retain the computed value under that name.
    name: str
    # What: compute model from the named fixture input; why: body dict str any model self model later reads model, so catalog must retain the computed value under that name.
    model: str
    # What: compute args from the named fixture input; why: body dict str any model self model later reads args, so catalog must retain the computed value under that name.
    args: tuple[str, ...]
    # What: compute port from the named fixture input; why: def proxy base url port int str later reads port, so catalog must retain the computed value under that name.
    port: int | None = None
    # What: compute description from the named fixture input; why: if self description later reads description, so  catalog must retain the computed value under that name.
    description: str | None = None
    # What: compute ready timeout s from 120 0; why: doc ready timeout s self ready timeout s later reads ready timeout s, so catalog must retain the computed value under that name.
    ready_timeout_s: float = 120.0
    # What: compute ttl s from the named fixture input; why: if self ttl s is not later reads ttl s, so catalog must retain the computed value under that name.
    ttl_s: float | None = None
    # What: compute unload timeout s from the named fixture input; why: if self unload timeout s is not later reads unload timeout s, so catalog must retain the computed value under that name.
    unload_timeout_s: float | None = None
    # What: compute priority from 0; why: if self priority later reads priority, so catalog must retain the computed value under that name.
    priority: int = 0
    # What: compute group from the named fixture input; why: if self group is not later reads group, so catalog must retain the computed value under that name.
    group: str | None = None
    # What: compute drop fields from the named fixture input; why: if self drop fields later reads drop fields, so catalog must retain the computed value under that name.
    drop_fields: tuple[str, ...] = ()
    # What: compute aliases from the named fixture input; why: if self aliases later reads aliases, so catalog must retain the computed value under that name.
    aliases: tuple[str, ...] = ()
    # What: compute unlisted from false; why: if self unlisted later reads unlisted, so  catalog must retain the computed value under that name.
    unlisted: bool = False
    # What: compute concurrency limit from 0; why: if self concurrency limit later reads concurrency limit, so catalog must retain the computed value under that name.
    concurrency_limit: int = 0
    # What: compute send loading state from the named fixture input; why: if self send loading state is not later reads send loading state, so catalog must retain the computed value under that name.
    send_loading_state: bool | None = None
    # What: compute capabilities from model capabilities; why: if not self capabilities empty later reads capabilities, so catalog must retain the computed value under that name.
    capabilities: ModelCapabilities = ModelCapabilities()
    # What: compute set fields from the named fixture input; why: if self set fields later reads set fields, so catalog must retain the computed value under that name.
    set_fields: tuple[RequestField, ...] = ()
    # What: compute set fields by id from the named fixture input; why: if self set fields by id later reads set fields by id, so catalog must retain the computed value under that name.
    set_fields_by_id: tuple[tuple[str, tuple[RequestField, ...]], ...] = ()
    # What: compute check endpoint from default check endpoint; why: if self check endpoint default check endpoint later reads check endpoint, so catalog must retain the computed value under that name.
    check_endpoint: str = DEFAULT_CHECK_ENDPOINT
    # What: compute proxy from default proxy; why: return self proxy replace port str port later reads proxy, so catalog must retain the computed value under that name.
    proxy: str = DEFAULT_PROXY
    # What: compute use model name from the named fixture input; why: if self use model name is not later reads use model name, so catalog must retain the computed value under that name.
    use_model_name: str | None = None
    # What: compute display name from the named fixture input; why: if self display name later reads display name, so  catalog must retain the computed value under that name.
    display_name: str | None = None
    # What: compute metadata json from value; why: return json loads self metadata json later reads metadata json, so  catalog must retain the computed value under that name.
    metadata_json: str = "{}"
    # What: compute upstream timeout s from the named fixture input; why: if self upstream timeout s is not later reads upstream timeout s, so catalog must retain the computed value under that name.
    upstream_timeout_s: float | None = None

    # What: define metadata around the current object state; why:  its direct callers call metadata for metadata and rely on this exact input and result contract.
    def metadata(self) -> dict[str, Any]:
        # What: return loads and metadata json and json from metadata; why: metadata exposes loads and metadata json and json so its caller can continue with the function\'s computed outcome.
        return json.loads(self.metadata_json)

    # What: define proxy_base_url around port; why: its direct callers call proxy_base_url for proxy base url and rely on this exact input and result contract.
    def proxy_base_url(self, port: int) -> str:
        """Resolve the validated loopback template to this owned child port."""
        # What: document resolve the validated loopback template to in the proxy_base_url docstring; why: introspection and maintainers read this exact docstring fragment to understand proxy base url behavior without executing it.
        # What: return replace and proxy and str and port and port from proxy_base_url; why: proxy_base_url exposes replace and proxy and str and port and port so its caller can continue with the function\'s computed outcome.
        return self.proxy.replace("${PORT}", str(port))

    # What: define request around the current object state; why: its direct callers call request for request and rely on this exact input and result contract.
    def request(self) -> dict[str, Any]:
        # What: map the model field as model; why: ModelProfile.request sends this field through body so the router selects the canonical model or alias for upstream dispatch.
        body: dict[str, Any] = {"model": self.model, "args": list(self.args)}
        # What: gate on port before port and body; why: request admits port and body only for this predicate and excludes the opposite state.
        if self.port is not None:
            # What: compute body entry from port; why: body dynamic port later reads body entry, so request must retain the computed value under that name.
            body["port"] = self.port
            # What: gate on port before body; why: request admits body only for this predicate and excludes the opposite state.
            if self.port == 0:
                # What: compute body entry from true; why: return body later reads body entry, so request must retain the computed value under that name.
                body["dynamicPort"] = True
        # What: return body from request; why: request exposes body so its caller can continue with the function\'s computed outcome.
        return body

    # What: define public around the current object state; why:  its direct callers call public for public and rely on this exact input and result contract.
    def public(self) -> dict[str, Any]:
        # What: compute doc from request; why: doc name self name later reads doc, so public must retain the computed value under that name.
        doc = self.request()
        # What: compute doc entry from name; why: doc display name self display name later reads doc entry, so public must retain the computed value under that name.
        doc["name"] = self.name
        # What: gate on display name before display name and doc; why:  public admits display name and doc only for this predicate and excludes the opposite state.
        if self.display_name:
            # What: compute doc entry from display name; why: doc description self description later reads doc entry, so  public must retain the computed value under that name.
            doc["displayName"] = self.display_name
        # What: gate on description before description and doc; why:  public admits description and doc only for this predicate and excludes the opposite state.
        if self.description:
            # What: compute doc entry from description; why: doc ready timeout s self ready timeout s later reads doc entry, so public must retain the computed value under that name.
            doc["description"] = self.description
        # What: compute doc entry from ready timeout s; why: doc ttl s self ttl s later reads doc entry, so public must retain the computed value under that name.
        doc["readyTimeoutS"] = self.ready_timeout_s
        # What: gate on ttl s before ttl s and doc; why: public admits ttl s and doc only for this predicate and excludes the opposite state.
        if self.ttl_s is not None:
            # What: compute doc entry from ttl s; why: doc unload timeout s self unload timeout s later reads doc entry, so public must retain the computed value under that name.
            doc["ttlS"] = self.ttl_s
        # What: gate on unload timeout s before unload timeout s and doc; why: public admits unload timeout s and doc only for this predicate and excludes the opposite state.
        if self.unload_timeout_s is not None:
            # What: compute doc entry from unload timeout s; why: doc priority self priority later reads doc entry, so public must retain the computed value under that name.
            doc["unloadTimeoutS"] = self.unload_timeout_s
        # What: gate on priority before priority and doc; why: public admits priority and doc only for this predicate and excludes the opposite state.
        if self.priority:
            # What: compute doc entry from priority; why: doc group self group later reads doc entry, so public must retain the computed value under that name.
            doc["priority"] = self.priority
        # What: gate on group before group and doc; why: public admits group and doc only for this predicate and excludes the opposite state.
        if self.group is not None:
            # What: compute doc entry from group; why: doc drop fields list self drop fields later reads doc entry, so public must retain the computed value under that name.
            doc["group"] = self.group
        # What: gate on drop fields before doc and list and drop fields; why: public admits doc and list and drop fields only for this predicate and excludes the opposite state.
        if self.drop_fields:
            # What: compute doc entry from list and drop fields; why: doc aliases list self aliases later reads doc entry, so public must retain the computed value under that name.
            doc["dropFields"] = list(self.drop_fields)
        # What: gate on aliases before doc and list and aliases; why: public admits doc and list and aliases only for this predicate and excludes the opposite state.
        if self.aliases:
            # What: compute doc entry from list and aliases; why: doc unlisted later reads doc entry, so public must retain the computed value under that name.
            doc["aliases"] = list(self.aliases)
        # What: gate on unlisted before doc; why:  public admits doc only for this predicate and excludes the opposite state.
        if self.unlisted:
            # What: compute doc entry from true; why: doc concurrency limit self concurrency limit later reads doc entry, so public must retain the computed value under that name.
            doc["unlisted"] = True
        # What: gate on concurrency limit before concurrency limit and doc; why: public admits concurrency limit and doc only for this predicate and excludes the opposite state.
        if self.concurrency_limit:
            # What: compute doc entry from concurrency limit; why: doc send loading state self send loading state later reads doc entry, so public must retain the computed value under that name.
            doc["concurrencyLimit"] = self.concurrency_limit
        # What: gate on send loading state before send loading state and doc; why: public admits send loading state and doc only for this predicate and excludes the opposite state.
        if self.send_loading_state is not None:
            # What: compute doc entry from send loading state; why: doc capabilities self capabilities public later reads doc entry, so public must retain the computed value under that name.
            doc["sendLoadingState"] = self.send_loading_state
        # What: gate on empty and capabilities before doc and public and capabilities; why: public admits doc and public and capabilities only for this predicate and excludes the opposite state.
        if not self.capabilities.empty():
            # What: compute doc entry from public and capabilities; why: doc set fields request fields public self set fields later reads doc entry, so public must retain the computed value under that name.
            doc["capabilities"] = self.capabilities.public()
        # What: gate on set fields before doc and request fields public and set fields; why: public admits doc and request fields public and set fields only for this predicate and excludes the opposite state.
        if self.set_fields:
            # What: compute doc entry from request fields public and set fields; why: doc set fields by id later reads doc entry, so public must retain the computed value under that name.
            doc["setFields"] = _request_fields_public(self.set_fields)
        # What: gate on set fields by id before doc and model id and request fields public and fields and set fields by id; why: public admits doc and model id and request fields public and fields and set fields by id only for this predicate and excludes the opposite state.
        if self.set_fields_by_id:
            # What: compute doc entry from model id and request fields public and fields and set fields by id; why: doc check endpoint self check endpoint later reads doc entry, so public must retain the computed value under that name.
            doc["setFieldsById"] = {
                # What: call _request_fields_public with fields; why: public invokes _request_fields_public while performing for model id fields in self set fields by id; the call advances that operation through its result or side effect.
                model_id: _request_fields_public(fields)
                # What: apply the for model id fields in self set fields by id portion of doc entry; why: public uses this clause to evaluate doc entry as one grouped value.
                for model_id, fields in self.set_fields_by_id
            # What: complete the doc entry expression with doc set fields by id model id request fields public fields for model id fields in; why: ModelProfile.public groups the supplied clauses as one doc entry expression before its value is consumed.
            }
        # What: gate on check endpoint and default check endpoint before check endpoint and doc; why: public admits check endpoint and doc only for this predicate and excludes the opposite state.
        if self.check_endpoint != DEFAULT_CHECK_ENDPOINT:
            # What: compute doc entry from check endpoint; why: doc proxy self proxy later reads doc entry, so public must retain the computed value under that name.
            doc["checkEndpoint"] = self.check_endpoint
        # What: gate on proxy and default proxy before proxy and doc; why: public admits proxy and doc only for this predicate and excludes the opposite state.
        if self.proxy != DEFAULT_PROXY:
            # What: compute doc entry from proxy; why: doc use model name self use model name later reads doc entry, so public must retain the computed value under that name.
            doc["proxy"] = self.proxy
        # What: gate on use model name before use model name and doc; why: public admits use model name and doc only for this predicate and excludes the opposite state.
        if self.use_model_name is not None:
            # What: compute doc entry from use model name; why: doc metadata metadata later reads doc entry, so public must retain the computed value under that name.
            doc["useModelName"] = self.use_model_name
        # What: compute metadata from metadata; why: if metadata later reads metadata, so  public must retain the computed value under that name.
        metadata = self.metadata()
        # What: gate on metadata before metadata and doc; why:  public admits metadata and doc only for this predicate and excludes the opposite state.
        if metadata:
            # What: compute doc entry from metadata; why: doc upstream timeout s self upstream timeout s later reads doc entry, so public must retain the computed value under that name.
            doc["metadata"] = metadata
        # What: gate on upstream timeout s before upstream timeout s and doc; why: public admits upstream timeout s and doc only for this predicate and excludes the opposite state.
        if self.upstream_timeout_s is not None:
            # What: compute doc entry from upstream timeout s; why: return doc later reads doc entry, so public must retain the computed value under that name.
            doc["upstreamTimeoutS"] = self.upstream_timeout_s
        # What: return doc from public; why: public exposes doc so its caller can continue with the function\'s computed outcome.
        return doc


# What: define ModelCatalog as the owner of __init__ and empty and load and get and public; why: daemon callers use this class boundary so those methods share one model catalog state invariant.
class ModelCatalog:
    # What: define __init__ around profiles and settings and selectors and routing profiles and path; why: its direct callers call __init__ for init and rely on this exact input and result contract.
    def __init__(
        # What: declare the self input for __init__; why: __init__ consumes self during self profiles dict profiles, so callers must bind it with the other signature inputs.
        self,
        # What: declare the profiles input for __init__; why: __init__ consumes profiles during self profiles dict profiles, so callers must bind it with the other signature inputs.
        profiles: dict[str, ModelProfile],
        # What: declare the settings input for __init__; why: __init__ consumes settings during settings settings or router settings, so callers must bind it with the other signature inputs.
        settings: RouterSettings | None = None,
        # What: mark the remaining parameters as keyword-only; why: __init__ prevents callers from confusing adjacent lifecycle and timing arguments.
        *,
        # What: declare the selectors input for __init__; why: __init__ consumes selectors during self selectors dict selectors or, so callers must bind it with the other signature inputs.
        selectors: dict[str, ModelSelector] | None = None,
        # What: declare the routing profiles input for __init__; why: __init__ consumes routing profiles during self routing profiles dict routing profiles or, so callers must bind it with the other signature inputs.
        routing_profiles: dict[str, RoutingProfile] | None = None,
        # What: declare the path input for __init__; why: __init__ consumes path during self path path, so callers must bind it with the other signature inputs.
        path: str | None = None,
    # What: complete the enclosing predicate with def init profiles dict str model profile settings router settings selectors; why: ModelCatalog.__init__ groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: compute profiles from dict and profiles; why: canonical set self profiles later reads profiles, so __init__ must retain the computed value under that name.
        self._profiles = dict(profiles)
        # What: initialize aliases as an empty runtime accumulator; why: ModelCatalog.__init__ appends or maps entries into it during for alias in profile aliases before consuming the aggregate.
        aliases: dict[str, str] = {}
        # What: compute canonical from set and profiles; why: if alias in canonical later reads canonical, so __init__ must retain the computed value under that name.
        canonical = set(self._profiles)
        # What: iterate across items and profiles to perform model id and name; why: __init__ repeats the body only while or for the loop header admits an iteration.
        for name, profile in self._profiles.items():
            # What: call _model_id with name; why: __init__ invokes _model_id while performing model id profile name; the call advances that operation through its result or side effect.
            _model_id(name)
            # What: call _model_id with name and profile; why: __init__ invokes _model_id while performing if name profile name; the call advances that operation through its result or side effect.
            _model_id(profile.name)
            # What: gate on name and profile before catalog error and name and profile; why: __init__ admits catalog error and name and profile only for this predicate and excludes the opposite state.
            if name != profile.name:
                # What: raise CatalogError for the caller; why:  ModelCatalog.__init__ stops this rejected path before it can mutate state, dispatch work, or report success.
                raise CatalogError(f"profile key {name!r} must match profile name {profile.name!r}")
            # What: iterate across aliases and profile to perform alias and model id; why: __init__ repeats the body only while or for the loop header admits an iteration.
            for alias in profile.aliases:
                # What: compute alias from model id and alias; why: if alias in canonical later reads alias, so __init__ must retain the computed value under that name.
                alias = _model_id(alias)
                # What: gate on alias and canonical before catalog error and alias; why: __init__ admits catalog error and alias only for this predicate and excludes the opposite state.
                if alias in canonical:
                    # What: raise CatalogError for the caller; why:  ModelCatalog.__init__ stops this rejected path before it can mutate state, dispatch work, or report success.
                    raise CatalogError(f"model alias {alias!r} conflicts with a configured profile")
                # What: gate on alias and aliases before catalog error and alias and name and aliases; why: __init__ admits catalog error and alias and name and aliases only for this predicate and excludes the opposite state.
                if alias in aliases:
                    # What: raise CatalogError for the caller; why:  ModelCatalog.__init__ stops this rejected path before it can mutate state, dispatch work, or report success.
                    raise CatalogError(
                        # What: apply the f model alias alias r is portion of the enclosing predicate; why: this clause remains in __init__\'s enclosing expression so its grouping and evaluation order stay intact.
                        f"model alias {alias!r} is assigned to both {aliases[alias]!r} and {name!r}"
                    # What: complete the CatalogError call with alias; why: ModelCatalog.__init__ groups the supplied clauses as one CatalogError call before its value is consumed.
                    )
                # What: compute aliases entry from name; why: self aliases aliases later reads aliases entry, so __init__ must retain the computed value under that name.
                aliases[alias] = name
        # What: compute aliases from aliases; why: the enclosing return or state update later reads aliases, so __init__ must retain the computed value under that name.
        self._aliases = aliases
        # What: compute selectors from dict and selectors; why: for name selector in self selectors items later reads selectors, so __init__ must retain the computed value under that name.
        self._selectors = dict(selectors or {})
        # What: compute occupied from canonical and set and aliases; why: if name in occupied later reads occupied, so __init__ must retain the computed value under that name.
        occupied = canonical | set(aliases)
        # What: iterate across items and selectors to perform model id and name; why: __init__ repeats the body only while or for the loop header admits an iteration.
        for name, selector in self._selectors.items():
            # What: call _model_id with name; why: __init__ invokes _model_id while performing if name selector name; the call advances that operation through its result or side effect.
            _model_id(name)
            # What: gate on name and selector before catalog error and name and selector; why: __init__ admits catalog error and name and selector only for this predicate and excludes the opposite state.
            if name != selector.name:
                # What: raise CatalogError for the caller; why:  ModelCatalog.__init__ stops this rejected path before it can mutate state, dispatch work, or report success.
                raise CatalogError(
                    # What: apply the f selector key name r must portion of the enclosing predicate; why: this clause remains in __init__\'s enclosing expression so its grouping and evaluation order stay intact.
                    f"selector key {name!r} must match selector name {selector.name!r}"
                # What: complete the CatalogError call with name; why: ModelCatalog.__init__ groups the supplied clauses as one CatalogError call before its value is consumed.
                )
            # What: gate on name and occupied before catalog error and name; why: __init__ admits catalog error and name only for this predicate and excludes the opposite state.
            if name in occupied:
                # What: raise CatalogError for the caller; why:  ModelCatalog.__init__ stops this rejected path before it can mutate state, dispatch work, or report success.
                raise CatalogError(f"selector {name!r} conflicts with a model ID or alias")
            # What: iterate across targets and selector to perform target and selectors and catalog error and name; why: __init__ repeats the body only while or for the loop header admits an iteration.
            for target in selector.targets:
                # What: gate on target and selectors before catalog error and name and target; why: __init__ admits catalog error and name and target only for this predicate and excludes the opposite state.
                if target in self._selectors:
                    # What: raise CatalogError for the caller; why:  ModelCatalog.__init__ stops this rejected path before it can mutate state, dispatch work, or report success.
                    raise CatalogError(
                        # What: apply the f selector name r target target portion of the enclosing predicate; why: this clause remains in  __init__\'s enclosing expression so its grouping and evaluation order stay intact.
                        f"selector {name!r} target {target!r} cannot reference another selector"
                    # What: complete the CatalogError call with name; why: ModelCatalog.__init__ groups the supplied clauses as one CatalogError call before its value is consumed.
                    )
                # What: establish the handler boundary for the protected operation; why: ModelCatalog.__init__ routes failures to catalog error while preserving cleanup and success flow.
                try:
                    # What: call self.get with target; why: __init__ invokes self.get while performing except catalog error as exc; the call advances that operation through its result or side effect.
                    self.get(target)
                # What: handle catalog error by raise catalog error; why: ModelCatalog.__init__ converts that failure into this concrete recovery, response, or cleanup behavior.
                except CatalogError as exc:
                    # What: raise CatalogError for the caller; why:  ModelCatalog.__init__ stops this rejected path before it can mutate state, dispatch work, or report success.
                    raise CatalogError(
                        # What: apply the f selector name r target target portion of the enclosing predicate; why: this clause remains in  __init__\'s enclosing expression so its grouping and evaluation order stay intact.
                        f"selector {name!r} target {target!r} is not a configured model or alias"
                    # What: apply the from exc portion of the enclosing predicate; why: this clause remains in __init__\'s enclosing expression so its grouping and evaluation order stay intact.
                    ) from exc
        # What: compute routing profiles from dict and routing profiles; why: for name routing profile in self routing profiles items later reads routing profiles, so __init__ must retain the computed value under that name.
        self._routing_profiles = dict(routing_profiles or {})
        # What: iterate across items and routing profiles to perform simple name and name; why: __init__ repeats the body only while or for the loop header admits an iteration.
        for name, routing_profile in self._routing_profiles.items():
            # What: preserve the exact simple name name profile name literal fragment; why: __init__ passes this fragment verbatim through _simple_name(name, "profile name"), because changing it would alter a protocol payload, serialized fixture, or public message.
            _simple_name(name, "profile name")
            # What: gate on name and routing profile before catalog error and name and routing profile; why: __init__ admits catalog error and name and routing profile only for this predicate and excludes the opposite state.
            if name != routing_profile.name:
                # What: raise CatalogError for the caller; why:  ModelCatalog.__init__ stops this rejected path before it can mutate state, dispatch work, or report success.
                raise CatalogError(
                    # What: apply the f routing profile key name r portion of the enclosing predicate; why: this clause remains in __init__\'s enclosing expression so its grouping and evaluation order stay intact.
                    f"routing profile key {name!r} must match profile name {routing_profile.name!r}"
                # What: complete the CatalogError call with name; why: ModelCatalog.__init__ groups the supplied clauses as one CatalogError call before its value is consumed.
                )
            # What: gate on pins and routing profile before catalog error and name; why: __init__ admits catalog error and name only for this predicate and excludes the opposite state.
            if not routing_profile.pins:
                # What: raise CatalogError for the caller; why:  ModelCatalog.__init__ stops this rejected path before it can mutate state, dispatch work, or report success.
                raise CatalogError(f"profiles.{name}.pins must contain at least one entry")
            # What: iterate across pins and routing profile to perform model id and pin; why: __init__ repeats the body only while or for the loop header admits an iteration.
            for pin, target in routing_profile.pins:
                # What: call _model_id with pin; why: __init__ invokes _model_id while performing if target is not and not; the call advances that operation through its result or side effect.
                _model_id(pin)
                # What: gate on target and has routable id before catalog error and name and pin and target; why: __init__ admits catalog error and name and pin and target only for this predicate and excludes the opposite state.
                if target is not None and not self.has_routable_id(target):
                    # What: raise CatalogError for the caller; why:  ModelCatalog.__init__ stops this rejected path before it can mutate state, dispatch work, or report success.
                    raise CatalogError(
                        # What: apply the f profiles name pins pin references portion of the enclosing predicate; why: this clause remains in __init__\'s enclosing expression so its grouping and evaluation order stay intact.
                        f"profiles.{name}.pins.{pin} references unknown model {target!r}"
                    # What: complete the CatalogError call with name; why: ModelCatalog.__init__ groups the supplied clauses as one CatalogError call before its value is consumed.
                    )
        # What: compute settings from settings and router settings; why: if settings preload model is not later reads settings, so __init__ must retain the computed value under that name.
        settings = settings or RouterSettings()
        # What: gate on preload model and settings before selector and preload model and catalog error and settings; why: __init__ admits selector and preload model and catalog error and settings only for this predicate and excludes the opposite state.
        if settings.preload_model is not None:
            # What: gate on selector and preload model and settings before catalog error; why: __init__ admits catalog error only for this predicate and excludes the opposite state.
            if self.selector(settings.preload_model) is not None:
                # What: raise CatalogError for the caller; why:  ModelCatalog.__init__ stops this rejected path before it can mutate state, dispatch work, or report success.
                raise CatalogError("router.preload_model must name a concrete model or alias")
            # What: compute settings from replace and settings and name and get; why: settings startup routing profile is not later reads settings, so __init__ must retain the computed value under that name.
            settings = replace(settings, preload_model=self.get(settings.preload_model).name)
        # What: gate on startup routing profile and routing profiles and settings before catalog error; why: __init__ admits catalog error only for this predicate and excludes the opposite state.
        if (
            # What: apply the settings startup routing profile is not portion of the enclosing predicate; why: this clause remains in __init__\'s enclosing expression so its grouping and evaluation order stay intact.
            settings.startup_routing_profile is not None
            # What: apply the and settings startup routing profile not in self routing profiles portion of the enclosing predicate; why: this clause remains in __init__\'s enclosing expression so its grouping and evaluation order stay intact.
            and settings.startup_routing_profile not in self._routing_profiles
        # What: complete the enclosing predicate with if settings startup routing profile is not and settings startup routing profile not in self routing profiles; why: ModelCatalog.__init__ groups the supplied clauses as one enclosing predicate expression before its value is consumed.
        ):
            # What: raise CatalogError for the caller; why:  ModelCatalog.__init__ stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError("router.startup_routing_profile references an unknown profile")
        # What: compute settings from settings; why: the enclosing return or state update later reads settings, so __init__ must retain the computed value under that name.
        self.settings = settings
        # What: compute path from path; why: the enclosing return or state update later reads path, so __init__ must retain the computed value under that name.
        self.path = path

    # What: bind empty to the class rather than an instance; why: factory and parser callers construct empty from class-level state without requiring an existing object.
    @classmethod
    # What: define empty around the current object state; why: the registered API client call empty for empty and rely on this exact input and result contract.
    def empty(cls) -> "ModelCatalog":
        # What: return no value from empty; why: empty returns no value to callers that depend on its completed result.
        return cls({})

    # What: bind load to the class rather than an instance; why: factory and parser callers construct load from class-level state without requiring an existing object.
    @classmethod
    # What: define load around path; why: the registered API client call load for load and rely on this exact input and result contract.
    def load(cls, path: str) -> "ModelCatalog":
        # What: establish the handler boundary for the protected operation; why: ModelCatalog.load routes failures to oserror and tomldecode error and tomllib while preserving cleanup and success flow.
        try:
            # What: enter the open managed context before raw tomllib load source; why: load releases this resource or lock after raw tomllib load source on both success and failure paths.
            with open(path, "rb") as source:
                # What: compute raw from load and source and tomllib; why: models raw get models later reads raw, so load must retain the computed value under that name.
                raw = tomllib.load(source)
        # What: handle oserror and tomldecode error and tomllib by raise catalog error f cannot read catalog path; why: ModelCatalog.load converts that failure into this concrete recovery, response, or cleanup behavior.
        except (OSError, tomllib.TOMLDecodeError) as exc:
            # What: raise CatalogError for the caller; why:  ModelCatalog.load stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError(f"cannot read catalog {path!r}: {exc}") from exc
        # What: compute models from get and raw and models; why: if not isinstance models dict later reads models, so load must retain the computed value under that name.
        models = raw.get("models")
        # What: gate on isinstance and models and dict before catalog error; why: load admits catalog error only for this predicate and excludes the opposite state.
        if not isinstance(models, dict):
            # What: raise CatalogError for the caller; why:  ModelCatalog.load stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError("catalog requires a [models] table")
        # What: initialize profiles as an empty runtime accumulator; why: ModelCatalog.load appends or maps entries into it during profiles model id name profile model id name value before consuming the aggregate.
        profiles: dict[str, ModelProfile] = {}
        # What: iterate across items and models to perform profiles and profile and value and model id and name; why: load repeats the body only while or for the loop header admits an iteration.
        for name, value in models.items():
            # What: compute profiles entry from profile and value and model id and name; why: raw profiles raw get profiles later reads profiles entry, so load must retain the computed value under that name.
            profiles[_model_id(name)] = _profile(_model_id(name), value)
        # What: compute raw selectors from get and raw and selectors; why: if not isinstance raw selectors dict later reads raw selectors, so load must retain the computed value under that name.
        raw_selectors = raw.get("selectors", {})
        # What: gate on isinstance and raw selectors and dict before catalog error; why: load admits catalog error only for this predicate and excludes the opposite state.
        if not isinstance(raw_selectors, dict):
            # What: raise CatalogError for the caller; why:  ModelCatalog.load stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError("selectors must be a table")
        # What: compute selectors from model id and name and selector and value; why: selectors selectors later reads selectors, so load must retain the computed value under that name.
        selectors = {
            # What: call _model_id with name; why: load invokes _model_id while performing for name value in raw selectors items; the call advances that operation through its result or side effect.
            _model_id(name): _selector(_model_id(name), value)
            # What: call raw_selectors.items with the declared inputs; why: load consumes the raw_selectors.items return value while evaluating for name, value in raw_selectors.items().
            for name, value in raw_selectors.items()
        # What: complete the selectors expression with selectors model id name selector model id name value for name; why: ModelCatalog.load groups the supplied clauses as one selectors expression before its value is consumed.
        }
        # What: compute raw profiles from get and raw and profiles; why: if not isinstance raw profiles dict later reads raw profiles, so load must retain the computed value under that name.
        raw_profiles = raw.get("profiles", {})
        # What: gate on isinstance and raw profiles and dict before catalog error; why: load admits catalog error only for this predicate and excludes the opposite state.
        if not isinstance(raw_profiles, dict):
            # What: raise CatalogError for the caller; why:  ModelCatalog.load stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError("profiles must be a table")
        # What: compute routing profiles from simple name and name and routing profile and value; why: routing profiles routing profiles later reads routing profiles, so load must retain the computed value under that name.
        routing_profiles = {
            # What: call _simple_name with name and profile and name; why: load invokes _simple_name while performing simple name name profile name value; the call advances that operation through its result or side effect.
            _simple_name(name, "profile name"): _routing_profile(
                # What: call _simple_name with name and profile and name; why: load consumes the _simple_name return value while evaluating _simple_name(name, "profile name"), value.
                _simple_name(name, "profile name"), value
            # What: complete the _routing_profile call with simple name and value; why: ModelCatalog.load groups the supplied clauses as one _routing_profile call before its value is consumed.
            )
            # What: call raw_profiles.items with the declared inputs; why: load consumes the raw_profiles.items return value while evaluating for name, value in raw_profiles.items().
            for name, value in raw_profiles.items()
        # What: complete the routing_profiles expression with routing profiles simple name name profile name routing profile simple name name profile; why: ModelCatalog.load groups the supplied clauses as one routing_profiles expression before its value is consumed.
        }
        # What: return profiles and router settings and selectors and routing profiles from load; why: load exposes profiles and router settings and selectors and routing profiles so its caller can continue with the function\'s computed outcome.
        return cls(
            # What: apply the profiles portion of the enclosing predicate; why: this clause remains in load\'s enclosing expression so its grouping and evaluation order stay intact.
            profiles,
            # What: call _router_settings with get and raw and router and profiles; why: load invokes _router_settings while performing selectors selectors; the call advances that operation through its result or side effect.
            _router_settings(raw.get("router", {}), profiles),
            # What: supply selectors to cls; why: load binds this selectors value to cls's selectors input.
            selectors=selectors,
            # What: supply routing profiles to cls; why: load binds this routing profiles value to cls's routing profiles input.
            routing_profiles=routing_profiles,
            # What: supply path to cls; why: load binds this path value to cls's path input.
            path=path,
        # What: complete the cls call with selectors and routing profiles and path; why: ModelCatalog.load groups the supplied clauses as one cls call before its value is consumed.
        )

    # What: define get around name; why: its direct callers call get for get and rely on this exact input and result contract.
    def get(self, name: str) -> ModelProfile:
        # What: establish the handler boundary for the protected operation; why: ModelCatalog.get routes failures to key error while preserving cleanup and success flow.
        try:
            # What: return profiles and get and name and aliases from get; why: get exposes profiles and get and name and aliases so its caller can continue with the function\'s computed outcome.
            return self._profiles[self._aliases.get(name, name)]
        # What: handle key error by raise catalog error f unknown model profile name; why: ModelCatalog.get converts that failure into this concrete recovery, response, or cleanup behavior.
        except KeyError as exc:
            # What: raise CatalogError for the caller; why: ModelCatalog.get stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError(f"unknown model profile {name!r}") from exc

    # What: define public around the current object state; why:  its direct callers call public for public and rely on this exact input and result contract.
    def public(self) -> list[dict[str, Any]]:
        # What: return public and name and sorted and profiles from public; why: public exposes public and name and sorted and profiles so its caller can continue with the function\'s computed outcome.
        return [self._profiles[name].public() for name in sorted(self._profiles)]

    # What: define public_selectors around the current object state; why: its direct callers call public_selectors for public selectors and rely on this exact input and result contract.
    def public_selectors(self) -> list[dict[str, Any]]:
        # What: return public and name and sorted and selectors from public_selectors; why: public_selectors exposes public and name and sorted and selectors so its caller can continue with the function\'s computed outcome.
        return [self._selectors[name].public() for name in sorted(self._selectors)]

    # What: define public_routing_profiles around the current object state; why: its direct callers call public_routing_profiles for public routing profiles and rely on this exact input and result contract.
    def public_routing_profiles(self) -> list[dict[str, Any]]:
        # What: return public and name and sorted and routing profiles from public_routing_profiles; why: public_routing_profiles exposes public and name and sorted and routing profiles so its caller can continue with the function\'s computed outcome.
        return [
            # What: call self._routing_profiles.public with the declared inputs; why: public_routing_profiles consumes the self._routing_profiles.public return value while evaluating self._routing_profiles[name].public() for name in sorted(self._routing_p.
            self._routing_profiles[name].public() for name in sorted(self._routing_profiles)
        # What: complete the public_routing_profiles signature with self; why: ModelCatalog.public_routing_profiles groups the supplied clauses as one public_routing_profiles signature before its value is consumed.
        ]

    # What: define profiles around the current object state; why: its direct callers call profiles for profiles and rely on this exact input and result contract.
    def profiles(self) -> tuple[ModelProfile, ...]:
        """Return immutable profile values for internal identity matching."""
        # What: document return immutable profile values for internal in the profiles docstring; why: introspection and maintainers read this exact docstring fragment to understand profiles behavior without executing it.
        # What: return tuple and profiles and name and sorted from profiles; why: profiles exposes tuple and profiles and name and sorted so its caller can continue with the function\'s computed outcome.
        return tuple(self._profiles[name] for name in sorted(self._profiles))

    # What: define selector around name; why: its direct callers call selector for selector and rely on this exact input and result contract.
    def selector(self, name: str) -> ModelSelector | None:
        # What: return get and name and selectors from selector; why: selector exposes get and name and selectors so its caller can continue with the function\'s computed outcome.
        return self._selectors.get(name)

    # What: define routing_profile around name; why: its direct callers call routing_profile for routing profile and rely on this exact input and result contract.
    def routing_profile(self, name: str) -> RoutingProfile | None:
        # What: return get and name and routing profiles from routing_profile; why: routing_profile exposes get and name and routing profiles so its caller can continue with the function\'s computed outcome.
        return self._routing_profiles.get(name)

    # What: define has_routable_id around name; why: its direct callers call has_routable_id for has routable id and rely on this exact input and result contract.
    def has_routable_id(self, name: str) -> bool:
        # What: return name and selectors and profiles and aliases from has_routable_id; why: has_routable_id exposes name and selectors and profiles and aliases so its caller can continue with the function\'s computed outcome.
        return name in self._selectors or name in self._profiles or name in self._aliases

    # What: define listed_model_ids around the current object state; why: its direct callers call listed_model_ids for listed model ids and rely on this exact input and result contract.
    def listed_model_ids(self) -> tuple[str, ...]:
        """Return the OpenAI-visible IDs without exposing hidden canonical profiles."""
        # What: document return the open ai visible ids without exposing in the listed_model_ids docstring; why: introspection and maintainers read this exact docstring fragment to understand listed model ids behavior without executing it.
        # What: initialize result as an empty runtime accumulator; why: ModelCatalog.listed_model_ids appends or maps entries into it during result append name before consuming the aggregate.
        result: list[str] = []
        # What: iterate across sorted and profiles to perform profile and profiles and name; why: listed_model_ids repeats the body only while or for the loop header admits an iteration.
        for name in sorted(self._profiles):
            # What: compute profile from profiles and name; why: if profile unlisted later reads profile, so listed_model_ids must retain the computed value under that name.
            profile = self._profiles[name]
            # What: gate on unlisted and profile before the computed value; why: listed_model_ids admits the computed value only for this predicate and excludes the opposite state.
            if profile.unlisted:
                # What: apply the continue portion of the enclosing predicate; why: this clause remains in listed_model_ids\'s enclosing expression so its grouping and evaluation order stay intact.
                continue
            # What: call result.append with name; why: listed_model_ids invokes result.append while performing if self settings include aliases in list; the call advances that operation through its result or side effect.
            result.append(name)
            # What: gate on include aliases in list and settings before extend and aliases and result and profile; why: listed_model_ids admits extend and aliases and result and profile only for this predicate and excludes the opposite state.
            if self.settings.include_aliases_in_list:
                # What: call result.extend with aliases and profile; why: listed_model_ids invokes result.extend while performing result extend; the call advances that operation through its result or side effect.
                result.extend(profile.aliases)
        # What: call result.extend with name and sorted and selectors and unlisted; why: listed_model_ids invokes result.extend while performing name for name in sorted self selectors; the call advances that operation through its result or side effect.
        result.extend(
            # What: call sorted with selectors; why: listed_model_ids consumes the sorted return value while evaluating name for name in sorted(self._selectors) if not self._selectors[name].un.
            name for name in sorted(self._selectors) if not self._selectors[name].unlisted
        # What: complete the result.extend call with name; why: ModelCatalog.listed_model_ids groups the supplied clauses as one result.extend call before its value is consumed.
        )
        # What: return tuple and result from listed_model_ids; why: listed_model_ids exposes tuple and result so its caller can continue with the function\'s computed outcome.
        return tuple(result)

    # What: define resolve_upstream_path around path; why: its direct callers call resolve_upstream_path for resolve upstream path and rely on this exact input and result contract.
    def resolve_upstream_path(self, path: str) -> tuple[str, ModelProfile, str]:
        """Resolve the longest configured model-ID prefix from a decoded path."""
        # What: document resolve the longest configured model id prefix in the resolve_upstream_path docstring; why: introspection and maintainers read this exact docstring fragment to understand resolve upstream path behavior without executing it.
        # What: compute parts from split and strip and path and value and value; why: for index in range len parts later reads parts, so resolve_upstream_path must retain the computed value under that name.
        parts = path.strip("/").split("/")
        # What: compute match from the named fixture input; why: match candidate profile join parts index later reads match, so resolve_upstream_path must retain the computed value under that name.
        match: tuple[str, ModelProfile, str] | None = None
        # What: iterate across range and len and parts to perform candidate and join and parts and index; why: resolve_upstream_path repeats the body only while or for the loop header admits an iteration.
        for index in range(1, len(parts) + 1):
            # What: compute candidate from join and parts and index and value; why: canonical self aliases get candidate candidate later reads candidate, so resolve_upstream_path must retain the computed value under that name.
            candidate = "/".join(parts[:index])
            # What: compute canonical from get and candidate and aliases; why: profile self profiles get canonical later reads canonical, so resolve_upstream_path must retain the computed value under that name.
            canonical = self._aliases.get(candidate, candidate)
            # What: compute profile from get and canonical and profiles; why: if profile is not later reads profile, so resolve_upstream_path must retain the computed value under that name.
            profile = self._profiles.get(canonical)
            # What: gate on profile before match and candidate and profile and join and parts; why: resolve_upstream_path admits match and candidate and profile and join and parts only for this predicate and excludes the opposite state.
            if profile is not None:
                # What: compute match from candidate and profile and join and parts; why: if match is later reads match, so resolve_upstream_path must retain the computed value under that name.
                match = candidate, profile, "/" + "/".join(parts[index:])
        # What: gate on match before catalog error; why: resolve_upstream_path admits catalog error only for this predicate and excludes the opposite state.
        if match is None:
            # What: raise CatalogError for the caller; why: ModelCatalog.resolve_upstream_path stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError("upstream path does not begin with a configured model ID")
        # What: return match from resolve_upstream_path; why: resolve_upstream_path exposes match so its caller can continue with the function\'s computed outcome.
        return match

    # What: define group_for around name; why: its direct callers call group_for for group for and rely on this exact input and result contract.
    def group_for(self, name: str) -> RoutingGroup | None:
        # What: iterate across groups and settings to perform name and members and group; why: group_for repeats the body only while or for the loop header admits an iteration.
        for group in self.settings.groups:
            # What: gate on name and members and group before group; why: group_for admits group only for this predicate and excludes the opposite state.
            if name in group.members:
                # What: return group from group_for; why: group_for exposes group so its caller can continue with the function\'s computed outcome.
                return group
        # What: return no value from group_for; why: group_for returns no value to callers that depend on its completed result.
        return None


# What: define _finite_seconds around value and field and minimum and maximum; why: its direct callers call _finite_seconds for finite seconds and rely on this exact input and result contract.
def _finite_seconds(value: object, field: str, *, minimum: float, maximum: float) -> float:
    # What: gate on isinstance and value and bool and minimum and maximum before catalog error and field and minimum and maximum; why: _finite_seconds admits catalog error and field and minimum and maximum only for this predicate and excludes the opposite state.
    if (not isinstance(value, (int, float)) or isinstance(value, bool)
            # What: apply the or not minimum value maximum portion of the enclosing predicate; why: this clause remains in _finite_seconds\'s enclosing expression so its grouping and evaluation order stay intact.
            or not minimum <= value <= maximum):
        # What: raise CatalogError for the caller; why: _finite_seconds stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field} must be from {minimum:g} through {maximum:g} seconds")
    # What: return float and value from _finite_seconds; why: _finite_seconds exposes float and value so its caller can continue with the function\'s computed outcome.
    return float(value)


# What: define _router_settings around value and profiles; why: its direct callers call _router_settings for router settings and rely on this exact input and result contract.
def _router_settings(value: object, profiles: dict[str, ModelProfile]) -> RouterSettings:
    # What: gate on value before value; why: _router_settings admits value only for this predicate and excludes the opposite state.
    if value is None:
        # What: initialize value as an empty runtime accumulator; why: _router_settings appends or maps entries into it during if not isinstance value dict before consuming the aggregate.
        value = {}
    # What: gate on isinstance and value and dict before catalog error; why: _router_settings admits catalog error only for this predicate and excludes the opposite state.
    if not isinstance(value, dict):
        # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError("router must be a table")
    # What: compute allowed from api keys and default ttl s and unload timeout s and upstream timeout s and scheduler; why: unknown sorted set value allowed later reads allowed, so _router_settings must retain the computed value under that name.
    allowed = {
        # What: apply the api keys default ttl s unload timeout s upstream timeout s portion of allowed; why: _router_settings uses this clause to evaluate allowed as one grouped value.
        "api_keys", "default_ttl_s", "unload_timeout_s", "upstream_timeout_s",
        # What: apply the scheduler groups include aliases in list global concurrency limit portion of allowed; why: _router_settings uses this clause to evaluate allowed as one grouped value.
        "scheduler", "groups", "include_aliases_in_list", "global_concurrency_limit",
        # What: apply the send loading state preload model startup routing profile portion of allowed; why: _router_settings uses this clause to evaluate allowed as one grouped value.
        "send_loading_state", "preload_model", "startup_routing_profile",
        # What: apply the upstream no activation suffixes portion of allowed; why: _router_settings uses this clause to evaluate allowed as one grouped value.
        "upstream_no_activation_suffixes",
        # What: apply the activity max entries capture buffer mb portion of allowed; why: _router_settings uses this clause to evaluate allowed as one grouped value.
        "activity_max_entries", "capture_buffer_mb",
        # What: apply the activity session headers portion of allowed; why: _router_settings uses this clause to evaluate allowed as one grouped value.
        "activity_session_headers",
        # What: apply the performance disabled performance every s portion of allowed; why: _router_settings uses this clause to evaluate allowed as one grouped value.
        "performance_disabled", "performance_every_s",
    # What: complete the allowed collection with api keys and default ttl s and unload timeout s and upstream timeout s; why: _router_settings groups the supplied clauses as one allowed collection before its value is consumed.
    }
    # What: compute unknown from sorted and allowed and set and value; why: if unknown later reads unknown, so _router_settings must retain the computed value under that name.
    unknown = sorted(set(value) - allowed)
    # What: gate on unknown before catalog error and join and unknown; why: _router_settings admits catalog error and join and unknown only for this predicate and excludes the opposite state.
    if unknown:
        # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"router: unsupported keys: {', '.join(unknown)}")
    # What: compute raw keys from get and value and api keys; why: if not isinstance raw keys list or later reads raw keys, so _router_settings must retain the computed value under that name.
    raw_keys = value.get("api_keys", [])
    # What: gate on isinstance and raw keys and list and all and key before catalog error; why: _router_settings admits catalog error only for this predicate and excludes the opposite state.
    if (not isinstance(raw_keys, list) or not all(isinstance(key, str) and key and "\x00" not in key
                                                    # What: apply the for key in raw keys portion of the enclosing predicate; why: this clause remains in _router_settings\'s enclosing expression so its grouping and evaluation order stay intact.
                                                    for key in raw_keys)):
        # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError("router.api_keys must be non-empty strings without NUL")
    # What: gate on len and raw keys and set before catalog error; why: _router_settings admits catalog error only for this predicate and excludes the opposite state.
    if len(set(raw_keys)) != len(raw_keys):
        # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError("router.api_keys must not contain duplicates")
    # What: compute scheduler from get and value and scheduler and fifo; why: if scheduler fifo later reads scheduler, so _router_settings must retain the computed value under that name.
    scheduler = value.get("scheduler", "fifo")
    # What: gate on scheduler before catalog error; why: _router_settings admits catalog error only for this predicate and excludes the opposite state.
    if scheduler != "fifo":
        # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError("router.scheduler currently supports only fifo")
    # What: compute include aliases in list from get and value and include aliases in list and false; why: if not isinstance include aliases in list bool later reads include aliases in list, so _router_settings must retain the computed value under that name.
    include_aliases_in_list = value.get("include_aliases_in_list", False)
    # What: gate on isinstance and include aliases in list and bool before catalog error; why: _router_settings admits catalog error only for this predicate and excludes the opposite state.
    if not isinstance(include_aliases_in_list, bool):
        # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError("router.include_aliases_in_list must be a boolean")
    # What: compute global concurrency limit from get and value and global concurrency limit and 0; why: not isinstance global concurrency limit int later reads global concurrency limit, so _router_settings must retain the computed value under that name.
    global_concurrency_limit = value.get("global_concurrency_limit", 0)
    # What: gate on isinstance and global concurrency limit and bool and int before catalog error; why: _router_settings admits catalog error only for this predicate and excludes the opposite state.
    if (
        # What: call isinstance with global concurrency limit and int; why: _router_settings invokes isinstance while performing or isinstance global concurrency limit bool; the call advances that operation through its result or side effect.
        not isinstance(global_concurrency_limit, int)
        # What: call isinstance with global concurrency limit and bool; why: _router_settings invokes isinstance while performing or not global concurrency limit 000 000; the call advances that operation through its result or side effect.
        or isinstance(global_concurrency_limit, bool)
        # What: apply the or not global concurrency limit 000 000 portion of the enclosing predicate; why: this clause remains in _router_settings\'s enclosing expression so its grouping and evaluation order stay intact.
        or not 0 <= global_concurrency_limit <= 1_000_000
    # What: complete the enclosing predicate with if not isinstance global concurrency limit int or isinstance global concurrency limit bool; why: _router_settings groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError("router.global_concurrency_limit must be an integer from 0 through 1000000")
    # What: compute send loading state from get and value and send loading state and false; why: if not isinstance send loading state bool later reads send loading state, so _router_settings must retain the computed value under that name.
    send_loading_state = value.get("send_loading_state", False)
    # What: gate on isinstance and send loading state and bool before catalog error; why: _router_settings admits catalog error only for this predicate and excludes the opposite state.
    if not isinstance(send_loading_state, bool):
        # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError("router.send_loading_state must be a boolean")
    # What: compute preload model from get and value and preload model; why: if preload model is not later reads preload model, so _router_settings must retain the computed value under that name.
    preload_model = value.get("preload_model")
    # What: gate on preload model before preload model and model id; why: _router_settings admits preload model and model id only for this predicate and excludes the opposite state.
    if preload_model is not None:
        # What: compute preload model from model id and preload model; why: preload model preload model later reads preload model, so _router_settings must retain the computed value under that name.
        preload_model = _model_id(preload_model)
    # What: compute startup routing profile from get and value and startup routing profile; why: if startup routing profile is not later reads startup routing profile, so _router_settings must retain the computed value under that name.
    startup_routing_profile = value.get("startup_routing_profile")
    # What: gate on startup routing profile before startup routing profile and simple name; why: _router_settings admits startup routing profile and simple name only for this predicate and excludes the opposite state.
    if startup_routing_profile is not None:
        # What: compute startup routing profile from simple name and startup routing profile and router and startup routing profile; why: startup routing profile router startup routing profile later reads startup routing profile, so _router_settings must retain the computed value under that name.
        startup_routing_profile = _simple_name(
            # What: apply the startup routing profile router startup routing profile portion of startup routing profile; why: _router_settings uses this clause to evaluate startup routing profile as one grouped value.
            startup_routing_profile, "router.startup_routing_profile"
        # What: complete the _simple_name call with startup routing profile; why: _router_settings groups the supplied clauses as one _simple_name call before its value is consumed.
        )
    # What: evaluate and capture upstream no activation suffixes value get; why: the enclosing qualifier uses the captured result in its next validation or artifact step.
    upstream_no_activation_suffixes = value.get(
        # What: call list with default upstream no activation suffixes; why: _router_settings consumes the list return value while evaluating "upstream_no_activation_suffixes", list(DEFAULT_UPSTREAM_NO_ACTIVATION_S.
        "upstream_no_activation_suffixes", list(DEFAULT_UPSTREAM_NO_ACTIVATION_SUFFIXES)
    # What: complete the value.get call with list; why: _router_settings groups the supplied clauses as one value.get call before its value is consumed.
    )
    # What: gate on isinstance and upstream no activation suffixes and list and len and all before catalog error; why: _router_settings admits catalog error only for this predicate and excludes the opposite state.
    if (
        # What: call isinstance with upstream no activation suffixes and list; why: _router_settings invokes isinstance while performing or len upstream no activation suffixes; the call advances that operation through its result or side effect.
        not isinstance(upstream_no_activation_suffixes, list)
        # What: call len with upstream no activation suffixes; why: _router_settings invokes len while performing or not all; the call advances that operation through its result or side effect.
        or len(upstream_no_activation_suffixes) > 64
        # What: call all with suffix and upstream no activation suffixes and isinstance and str; why: _router_settings invokes all while performing isinstance suffix str and upstream suffix fullmatch suffix; the call advances that operation through its result or side effect.
        or not all(
            # What: call isinstance with suffix and str; why: _router_settings invokes isinstance while performing for suffix in upstream no activation suffixes; the call advances that operation through its result or side effect.
            isinstance(suffix, str) and _UPSTREAM_SUFFIX.fullmatch(suffix)
            # What: apply the for suffix in upstream no activation suffixes portion of the enclosing predicate; why: this clause remains in _router_settings\'s enclosing expression so its grouping and evaluation order stay intact.
            for suffix in upstream_no_activation_suffixes
        # What: complete the all call with suffix; why: _router_settings groups the supplied clauses as one all call before its value is consumed.
        )
    # What: complete the enclosing predicate with if not isinstance upstream no activation suffixes list or len upstream no activation suffixes 64; why: _router_settings groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(
            # What: apply the router upstream no activation suffixes must contain at most safe portion of the enclosing predicate; why: this clause remains in _router_settings\'s enclosing expression so its grouping and evaluation order stay intact.
            "router.upstream_no_activation_suffixes must contain at most 64 safe dot suffixes"
        # What: complete the CatalogError call with ordered positional inputs; why: _router_settings groups the supplied clauses as one CatalogError call before its value is consumed.
        )
    # What: gate on len and upstream no activation suffixes and set before catalog error; why: _router_settings admits catalog error only for this predicate and excludes the opposite state.
    if len(set(upstream_no_activation_suffixes)) != len(upstream_no_activation_suffixes):
        # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError("router.upstream_no_activation_suffixes must not contain duplicates")
    # What: compute activity max entries from get and value and activity max entries and 1000; why: if not isinstance activity max entries int or later reads activity max entries, so _router_settings must retain the computed value under that name.
    activity_max_entries = value.get("activity_max_entries", 1000)
    # What: gate on isinstance and activity max entries and bool and int before catalog error; why: _router_settings admits catalog error only for this predicate and excludes the opposite state.
    if (not isinstance(activity_max_entries, int) or isinstance(activity_max_entries, bool)
            # What: apply the or not activity max entries 000 portion of the enclosing predicate; why: this clause remains in _router_settings\'s enclosing expression so its grouping and evaluation order stay intact.
            or not 1 <= activity_max_entries <= 100_000):
        # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError("router.activity_max_entries must be an integer from 1 through 100000")
    # What: compute capture buffer mb from get and value and capture buffer mb and 0; why: if not isinstance capture buffer mb int or later reads capture buffer mb, so _router_settings must retain the computed value under that name.
    capture_buffer_mb = value.get("capture_buffer_mb", 0)
    # What: gate on isinstance and capture buffer mb and bool and int before catalog error; why: _router_settings admits catalog error only for this predicate and excludes the opposite state.
    if (not isinstance(capture_buffer_mb, int) or isinstance(capture_buffer_mb, bool)
            # What: apply the or not capture buffer mb portion of the enclosing predicate; why: this clause remains in _router_settings\'s enclosing expression so its grouping and evaluation order stay intact.
            or not 0 <= capture_buffer_mb <= 256):
        # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError("router.capture_buffer_mb must be an integer from 0 through 256")
    # What: evaluate and capture activity session headers value get; why: the enclosing qualifier uses the captured result in its next validation or artifact step.
    activity_session_headers = value.get(
        # What: call list with default activity session headers; why: _router_settings consumes the list return value while evaluating "activity_session_headers", list(DEFAULT_ACTIVITY_SESSION_HEADERS).
        "activity_session_headers", list(DEFAULT_ACTIVITY_SESSION_HEADERS)
    # What: complete the value.get call with list; why: _router_settings groups the supplied clauses as one value.get call before its value is consumed.
    )
    # What: gate on isinstance and activity session headers and list and len and all before catalog error; why: _router_settings admits catalog error only for this predicate and excludes the opposite state.
    if (
        # What: call isinstance with activity session headers and list; why: _router_settings invokes isinstance while performing or len activity session headers; the call advances that operation through its result or side effect.
        not isinstance(activity_session_headers, list)
        # What: call len with activity session headers; why: _router_settings invokes len while performing or not all; the call advances that operation through its result or side effect.
        or len(activity_session_headers) > 16
        # What: call all with header and activity session headers and isinstance and str; why: _router_settings invokes all while performing isinstance header str and http header name fullmatch header; the call advances that operation through its result or side effect.
        or not all(
            # What: call isinstance with header and str; why: _router_settings invokes isinstance while performing for header in activity session headers; the call advances that operation through its result or side effect.
            isinstance(header, str) and _HTTP_HEADER_NAME.fullmatch(header)
            # What: apply the for header in activity session headers portion of the enclosing predicate; why: this clause remains in _router_settings\'s enclosing expression so its grouping and evaluation order stay intact.
            for header in activity_session_headers
        # What: complete the all call with header; why: _router_settings groups the supplied clauses as one all call before its value is consumed.
        )
    # What: complete the enclosing predicate with if not isinstance activity session headers list or len activity session headers 16; why: _router_settings groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(
            # What: apply the router activity session headers must contain at most safe portion of the enclosing predicate; why: this clause remains in _router_settings\'s enclosing expression so its grouping and evaluation order stay intact.
            "router.activity_session_headers must contain at most 16 safe HTTP header names"
        # What: complete the CatalogError call with ordered positional inputs; why: _router_settings groups the supplied clauses as one CatalogError call before its value is consumed.
        )
    # What: compute normalized session headers from tuple and lower and header and activity session headers; why: if len set normalized session headers len normalized session headers later reads normalized session headers, so _router_settings must retain the computed value under that name.
    normalized_session_headers = tuple(header.lower() for header in activity_session_headers)
    # What: gate on len and normalized session headers and set before catalog error; why: _router_settings admits catalog error only for this predicate and excludes the opposite state.
    if len(set(normalized_session_headers)) != len(normalized_session_headers):
        # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError("router.activity_session_headers must not contain duplicates")
    # What: gate on any and header and normalized session headers and split before catalog error; why: _router_settings admits catalog error only for this predicate and excludes the opposite state.
    if any(
        # What: apply the authorization in header or token in portion of the enclosing predicate; why: this clause remains in _router_settings\'s enclosing expression so its grouping and evaluation order stay intact.
        "authorization" in header or "token" in header or "secret" in header
        # What: call header.split with value; why: _router_settings invokes header.split while performing for header in normalized session headers; the call advances that operation through its result or side effect.
        or ("api" in header.split("-") and "key" in header.split("-"))
        # What: apply the for header in normalized session headers portion of the enclosing predicate; why: this clause remains in _router_settings\'s enclosing expression so its grouping and evaluation order stay intact.
        for header in normalized_session_headers
    # What: complete the any call with header; why: _router_settings groups the supplied clauses as one any call before its value is consumed.
    ):
        # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError("router.activity_session_headers must not name credential headers")
    # What: compute performance disabled from get and value and performance disabled and false; why: if not isinstance performance disabled bool later reads performance disabled, so _router_settings must retain the computed value under that name.
    performance_disabled = value.get("performance_disabled", False)
    # What: gate on isinstance and performance disabled and bool before catalog error; why: _router_settings admits catalog error only for this predicate and excludes the opposite state.
    if not isinstance(performance_disabled, bool):
        # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError("router.performance_disabled must be a boolean")
    # What: compute performance every s from finite seconds and get and value and router and performance every s; why: value get performance every s later reads performance every s, so _router_settings must retain the computed value under that name.
    performance_every_s = _finite_seconds(
        # What: call value.get with performance every s and 5; why: _router_settings invokes value.get while performing router performance every s minimum maximum; the call advances that operation through its result or side effect.
        value.get("performance_every_s", 5),
        # What: supply minimum to _finite_seconds; why: _router_settings binds this 5 value to _finite_seconds's minimum input.
        "router.performance_every_s", minimum=5, maximum=3600,
    # What: complete the _finite_seconds call with minimum and maximum; why: _router_settings groups the supplied clauses as one _finite_seconds call before its value is consumed.
    )
    # What: compute raw groups from get and value and groups; why: if not isinstance raw groups dict later reads raw groups, so _router_settings must retain the computed value under that name.
    raw_groups = value.get("groups", {})
    # What: gate on isinstance and raw groups and dict before catalog error; why: _router_settings admits catalog error only for this predicate and excludes the opposite state.
    if not isinstance(raw_groups, dict):
        # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError("router.groups must be a table")
    # What: initialize groups as an empty runtime accumulator; why: _router_settings appends or maps entries into it during raise catalog error f router groups name must be before consuming the aggregate.
    groups: list[RoutingGroup] = []
    # What: compute claimed from set; why: if len set members len members later reads claimed, so _router_settings must retain the computed value under that name.
    claimed: set[str] = set()
    # What: iterate across items and raw groups to perform name and simple name and raw name; why: _router_settings repeats the body only while or for the loop header admits an iteration.
    for raw_name, raw_group in raw_groups.items():
        # What: compute name from simple name and raw name and router and group and names; why: raise catalog error f router groups name must later reads name, so _router_settings must retain the computed value under that name.
        name = _simple_name(raw_name, "router group names")
        # What: gate on isinstance and raw group and dict before catalog error and name; why: _router_settings admits catalog error and name only for this predicate and excludes the opposite state.
        if not isinstance(raw_group, dict):
            # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError(f"router.groups.{name} must be a table")
        # What: compute unknown from sorted and set and raw group and members and swap; why: if unknown later reads unknown, so _router_settings must retain the computed value under that name.
        unknown = sorted(set(raw_group) - {"members", "swap", "exclusive", "persistent"})
        # What: gate on unknown before catalog error and name and join and unknown; why: _router_settings admits catalog error and name and join and unknown only for this predicate and excludes the opposite state.
        if unknown:
            # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError(f"router.groups.{name}: unsupported keys: {', '.join(unknown)}")
        # What: compute members from get and raw group and members; why: if not isinstance members list or later reads members, so _router_settings must retain the computed value under that name.
        members = raw_group.get("members")
        # What: gate on members and isinstance and list and all and member before catalog error and name; why: _router_settings admits catalog error and name only for this predicate and excludes the opposite state.
        if (not isinstance(members, list) or not members
                # What: call all with member and members and isinstance and str; why: _router_settings invokes all while performing raise catalog error f router groups name members; the call advances that operation through its result or side effect.
                or not all(isinstance(member, str) and member in profiles for member in members)):
            # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError(f"router.groups.{name}.members must name configured models")
        # What: gate on intersection and members and len and claimed and set before catalog error; why: _router_settings admits catalog error only for this predicate and excludes the opposite state.
        if len(set(members)) != len(members) or claimed.intersection(members):
            # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError("a model can belong to only one router group")
        # What: call claimed.update with members; why: _router_settings invokes claimed.update while performing flags key raw group get key default for; the call advances that operation through its result or side effect.
        claimed.update(members)
        # What: compute flags from key and get and default and raw group and swap; why: if not all isinstance flag bool later reads flags, so _router_settings must retain the computed value under that name.
        flags = {key: raw_group.get(key, default) for key, default in
                 # What: apply the swap exclusive persistent portion of flags; why: _router_settings uses this clause to evaluate flags as one grouped value.
                 (("swap", True), ("exclusive", True), ("persistent", False))}
        # What: gate on all and isinstance and flag and bool and values before catalog error and name; why: _router_settings admits catalog error and name only for this predicate and excludes the opposite state.
        if not all(isinstance(flag, bool) for flag in flags.values()):
            # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError(f"router.groups.{name} flags must be booleans")
        # The native coordinator deliberately owns exactly one resident child.
        # Accepting llama-swap's coexistence flags here would silently promise
        # a scheduling policy we cannot implement. Fail atomically at reload
        # time instead; an operator can express the supported policy as an
        # exclusive swapping group, or a singleton persistent protected slot.
        # What: gate on flags before catalog error and name; why:  _router_settings admits catalog error and name only for this predicate and excludes the opposite state.
        if not flags["exclusive"]:
            # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError(
                # What: apply the f router groups name single resident native routing portion of the enclosing predicate; why: this clause remains in _router_settings\'s enclosing expression so its grouping and evaluation order stay intact.
                f"router.groups.{name}: single-resident native routing requires exclusive = true"
            # What: complete the CatalogError call with name; why: _router_settings groups the supplied clauses as one CatalogError call before its value is consumed.
            )
        # What: gate on flags before catalog error and name; why:  _router_settings admits catalog error and name only for this predicate and excludes the opposite state.
        if flags["persistent"] and flags["swap"]:
            # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError(f"router.groups.{name}: persistent groups must set swap = false")
        # What: gate on flags before catalog error and name; why:  _router_settings admits catalog error and name only for this predicate and excludes the opposite state.
        if not flags["persistent"] and not flags["swap"]:
            # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError(
                # What: apply the f router groups name swap false requires portion of the enclosing predicate; why: this clause remains in _router_settings\'s enclosing expression so its grouping and evaluation order stay intact.
                f"router.groups.{name}: swap = false requires multi-resident routing and is unsupported"
            # What: complete the CatalogError call with name; why: _router_settings groups the supplied clauses as one CatalogError call before its value is consumed.
            )
        # What: gate on flags and len and members before catalog error and name; why: _router_settings admits catalog error and name only for this predicate and excludes the opposite state.
        if flags["persistent"] and len(members) != 1:
            # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError(
                # What: apply the f router groups name a persistent group portion of the enclosing predicate; why: this clause remains in _router_settings\'s enclosing expression so its grouping and evaluation order stay intact.
                f"router.groups.{name}: a persistent group needs exactly one member under single-resident routing"
            # What: complete the CatalogError call with name; why: _router_settings groups the supplied clauses as one CatalogError call before its value is consumed.
            )
        # What: supply expanded arguments to groups.append; why: _router_settings binds this flags value to groups.append's expanded input.
        groups.append(RoutingGroup(name, tuple(members), **flags))
    # What: compute membership from member and name and group and groups; why: if profile group is not and membership get later reads membership, so _router_settings must retain the computed value under that name.
    membership = {member: group.name for group in groups for member in group.members}
    # What: iterate across items and profiles to perform group and catalog error and profile and get and name; why: _router_settings repeats the body only while or for the loop header admits an iteration.
    for name, profile in profiles.items():
        # What: gate on group and profile and get and name and membership before catalog error and name; why: _router_settings admits catalog error and name only for this predicate and excludes the opposite state.
        if profile.group is not None and membership.get(name) != profile.group:
            # What: raise CatalogError for the caller; why:  _router_settings stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError(f"models.{name}.group must match router group membership")
    # What: return router settings and scheduler and include aliases in list and global concurrency limit from _router_settings; why: _router_settings exposes router settings and scheduler and include aliases in list and global concurrency limit so its caller can continue with the function\'s computed outcome.
    return RouterSettings(
        # What: supply api keys to tuple; why: _router_settings binds this tuple and raw keys value to tuple's api keys input.
        api_keys=tuple(raw_keys),
        # What: supply default ttl s to _finite_seconds; why: _router_settings binds this finite seconds and get and value and router and default ttl s value to _finite_seconds's default ttl s input.
        default_ttl_s=_finite_seconds(value.get("default_ttl_s", 0), "router.default_ttl_s", minimum=0, maximum=86400),
        # What: supply unload timeout s to _finite_seconds; why: _router_settings binds this finite seconds and get and value and router and unload timeout s value to _finite_seconds's unload timeout s input.
        unload_timeout_s=_finite_seconds(value.get("unload_timeout_s", 30), "router.unload_timeout_s", minimum=1, maximum=900),
        # What: supply upstream timeout s to _finite_seconds; why: _router_settings binds this finite seconds and get and value and router and upstream timeout s value to _finite_seconds's upstream timeout s input.
        upstream_timeout_s=_finite_seconds(value.get("upstream_timeout_s", 900), "router.upstream_timeout_s", minimum=1, maximum=7200),
        # What: supply scheduler to RouterSettings; why: _router_settings binds this scheduler value to RouterSettings's scheduler input.
        scheduler=scheduler,
        # What: supply groups to tuple; why: _router_settings binds this tuple and groups value to tuple's groups input.
        groups=tuple(groups),
        # What: supply include aliases in list to RouterSettings; why: _router_settings binds this include aliases in list value to RouterSettings's include aliases in list input.
        include_aliases_in_list=include_aliases_in_list,
        # What: supply global concurrency limit to RouterSettings; why: _router_settings binds this global concurrency limit value to RouterSettings's global concurrency limit input.
        global_concurrency_limit=global_concurrency_limit,
        # What: supply send loading state to RouterSettings; why: _router_settings binds this send loading state value to RouterSettings's send loading state input.
        send_loading_state=send_loading_state,
        # What: supply preload model to RouterSettings; why: _router_settings binds this preload model value to RouterSettings's preload model input.
        preload_model=preload_model,
        # What: supply startup routing profile to RouterSettings; why: _router_settings binds this startup routing profile value to RouterSettings's startup routing profile input.
        startup_routing_profile=startup_routing_profile,
        # What: supply upstream no activation suffixes to tuple; why: _router_settings binds this tuple and upstream no activation suffixes value to tuple's upstream no activation suffixes input.
        upstream_no_activation_suffixes=tuple(upstream_no_activation_suffixes),
        # What: supply activity max entries to RouterSettings; why: _router_settings binds this activity max entries value to RouterSettings's activity max entries input.
        activity_max_entries=activity_max_entries,
        # What: supply capture buffer mb to RouterSettings; why: _router_settings binds this capture buffer mb value to RouterSettings's capture buffer mb input.
        capture_buffer_mb=capture_buffer_mb,
        # What: supply activity session headers to RouterSettings; why: _router_settings binds this normalized session headers value to RouterSettings's activity session headers input.
        activity_session_headers=normalized_session_headers,
        # What: supply performance disabled to RouterSettings; why: _router_settings binds this performance disabled value to RouterSettings's performance disabled input.
        performance_disabled=performance_disabled,
        # What: supply performance every s to RouterSettings; why: _router_settings binds this performance every s value to RouterSettings's performance every s input.
        performance_every_s=performance_every_s,
    # What: complete the RouterSettings call with api keys and default ttl s and unload timeout s and upstream timeout s and scheduler; why: _router_settings groups the supplied clauses as one RouterSettings call before its value is consumed.
    )


# What: define _simple_name around name and label; why: its direct callers call _simple_name for simple name and rely on this exact input and result contract.
def _simple_name(name: object, label: str = "names") -> str:
    # What: gate on isinstance and name and str and fullmatch and simple name before catalog error and label; why: _simple_name admits catalog error and label only for this predicate and excludes the opposite state.
    if not isinstance(name, str) or not _SIMPLE_NAME.fullmatch(name):
        # What: raise CatalogError for the caller; why: _simple_name stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{label} must match [A-Za-z0-9][A-Za-z0-9._-]{{0,127}}")
    # What: return name from _simple_name; why: _simple_name exposes name so its caller can continue with the function\'s computed outcome.
    return name


# What: define _valid_model_id around name; why: its direct callers call _valid_model_id for valid model id and rely on this exact input and result contract.
def _valid_model_id(name: object) -> bool:
    # What: return bool and isinstance and name and str from _valid_model_id; why: _valid_model_id exposes bool and isinstance and name and str so its caller can continue with the function\'s computed outcome.
    return bool(
        # What: call isinstance with name and str; why: _valid_model_id invokes isinstance while performing and len name; the call advances that operation through its result or side effect.
        isinstance(name, str)
        # What: call len with name; why: _valid_model_id invokes len while performing and all model segment fullmatch segment for segment; the call advances that operation through its result or side effect.
        and len(name) <= 128
        # What: call all with fullmatch and segment and model segment and split; why: _valid_model_id consumes the all return value while evaluating and all(_MODEL_SEGMENT.fullmatch(segment) for segment in name.split("/").
        and all(_MODEL_SEGMENT.fullmatch(segment) for segment in name.split("/"))
    # What: complete the bool call with isinstance; why: _valid_model_id groups the supplied clauses as one bool call before its value is consumed.
    )


# What: define _model_id around name; why: its direct callers call _model_id for model id and rely on this exact input and result contract.
def _model_id(name: object) -> str:
    # What: gate on valid model id and name before catalog error; why: _model_id admits catalog error only for this predicate and excludes the opposite state.
    if not _valid_model_id(name):
        # What: raise CatalogError for the caller; why: _model_id stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(
            # What: preserve the exact model ids must be slash separated a za z0 9 literal fragment; why: _model_id passes this fragment verbatim through "model IDs must be slash-separated [A-Za-z0-9][A-Za-z0-9._:-] segments ", because changing it would alter a protocol payload, serialized fixture, or public message.
            # What: preserve the exact with at most characters total literal fragment; why: _model_id passes this fragment verbatim through "model IDs must be slash-separated [A-Za-z0-9][A-Za-z0-9._:-] segments ", because changing it would alter a protocol payload, serialized fixture, or public message.
            "model IDs must be slash-separated [A-Za-z0-9][A-Za-z0-9._:-] segments "
            "with at most 128 characters total"
        # What: complete the CatalogError call with ordered positional inputs; why: _model_id groups the supplied clauses as one CatalogError call before its value is consumed.
        )
    # What: return name from _model_id; why: _model_id exposes name so its caller can continue with the function\'s computed outcome.
    return name


# What: define _profile around name and value; why: its direct callers call _profile for profile and rely on this exact input and result contract.
def _profile(name: str, value: object) -> ModelProfile:
    # What: gate on isinstance and value and dict before catalog error and name; why: _profile admits catalog error and name only for this predicate and excludes the opposite state.
    if not isinstance(value, dict):
        # What: raise CatalogError for the caller; why:  _profile stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"models.{name} must be a table")
    # What: compute allowed from model and args and port and description and ready timeout s; why: unknown sorted set value allowed later reads allowed, so _profile must retain the computed value under that name.
    allowed = {
        # What: apply the model args port description ready timeout s ttl s portion of allowed; why: _profile uses this clause to evaluate allowed as one grouped value.
        "model", "args", "port", "description", "ready_timeout_s", "ttl_s",
        # What: apply the unload timeout s priority group drop fields aliases unlisted portion of allowed; why: _profile uses this clause to evaluate allowed as one grouped value.
        "unload_timeout_s", "priority", "group", "drop_fields", "aliases", "unlisted",
        # What: apply the concurrency limit send loading state capabilities set fields portion of allowed; why: _profile uses this clause to evaluate allowed as one grouped value.
        "concurrency_limit", "send_loading_state", "capabilities", "set_fields",
        # What: apply the set fields by id check endpoint proxy use model name name metadata portion of allowed; why: _profile uses this clause to evaluate allowed as one grouped value.
        "set_fields_by_id", "check_endpoint", "proxy", "use_model_name", "name", "metadata",
        # What: apply the upstream timeout s portion of allowed; why: _profile uses this clause to evaluate allowed as one grouped value.
        "upstream_timeout_s",
    # What: complete the allowed collection with model and args and port and description; why: _profile groups the supplied clauses as one allowed collection before its value is consumed.
    }
    # What: compute unknown from sorted and allowed and set and value; why: if unknown later reads unknown, so _profile must retain the computed value under that name.
    unknown = sorted(set(value) - allowed)
    # What: gate on unknown before catalog error and name and join and unknown; why: _profile admits catalog error and name and join and unknown only for this predicate and excludes the opposite state.
    if unknown:
        # What: raise CatalogError for the caller; why:  _profile stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"models.{name}: unsupported keys: {', '.join(unknown)}")
    # What: compute model from get and value and model; why: if not isinstance model str or later reads model, so _profile must retain the computed value under that name.
    model = value.get("model")
    # What: gate on model and isinstance and str and strip before catalog error and name; why: _profile admits catalog error and name only for this predicate and excludes the opposite state.
    if not isinstance(model, str) or not model.strip() or "\x00" in model:
        # What: raise CatalogError for the caller; why:  _profile stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"models.{name}.model must be a non-empty string without NUL")
    # What: compute raw args from get and value and args; why: if not isinstance raw args list or later reads raw args, so _profile must retain the computed value under that name.
    raw_args = value.get("args", [])
    # What: gate on isinstance and raw args and list and all and arg before catalog error and name; why: _profile admits catalog error and name only for this predicate and excludes the opposite state.
    if not isinstance(raw_args, list) or not all(isinstance(arg, str) and "\x00" not in arg for arg in raw_args):
        # What: raise CatalogError for the caller; why:  _profile stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"models.{name}.args must be an array of strings without NUL")
    # The daemon owns these two options.  Letting a profile smuggle them through
    # produces ambiguous process state and defeats the lifecycle conflict guard.
    # What: iterate across raw args to perform option and split and arg; why: _profile repeats the body only while or for the loop header admits an iteration.
    for arg in raw_args:
        # What: compute option from split and arg and 0 and value and 1; why: if arg or option p or later reads option, so _profile must retain the computed value under that name.
        option = arg.split("=", 1)[0]
        # What: compute reserved from model and model path and port; why: option startswith and any flag startswith option for later reads reserved, so _profile must retain the computed value under that name.
        reserved = ("--model", "--model-path", "--port")
        # What: gate on arg and option and startswith and any and flag before catalog error and name; why: _profile admits catalog error and name only for this predicate and excludes the opposite state.
        if arg == "--" or option == "-p" or (
            # What: call option.startswith with value; why: _profile consumes the option.startswith return value while evaluating option.startswith("--") and any(flag.startswith(option) for flag in rese.
            option.startswith("--") and any(flag.startswith(option) for flag in reserved)
        # What: complete the enclosing predicate with arg equals or option equals p or option startswith and; why: _profile groups the supplied clauses as one enclosing predicate expression before its value is consumed.
        ):
            # What: raise CatalogError for the caller; why:  _profile stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError(f"models.{name}.args must not set --model or --port")
    # What: compute port from get and value and port; why: if port is not and not later reads port, so _profile must retain the computed value under that name.
    port = value.get("port")
    # Port zero is an explicit request for a fresh loopback port on each
    # activation. It is not passed through to uvicorn: the native router
    # reserves an OS-selected candidate and records that concrete target for
    # readiness, proxying, accounting, and re-adoption. ``None`` keeps the
    # daemon-wide fixed default for backwards-compatible catalogs.
    # What: gate on port and isinstance and bool and int before catalog error and name; why: _profile admits catalog error and name only for this predicate and excludes the opposite state.
    if port is not None and (not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535):
        # What: raise CatalogError for the caller; why:  _profile stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"models.{name}.port must be an integer from 0 through 65535")
    # What: compute description from public text and get and value and name and description; why: value get description f models name description later reads description, so _profile must retain the computed value under that name.
    description = _public_text(
        # What: call value.get with description; why: _profile consumes the value.get return value while evaluating value.get("description"), f"models.{name}.description".
        value.get("description"), f"models.{name}.description"
    # What: complete the _public_text call with get and name; why: _profile groups the supplied clauses as one _public_text call before its value is consumed.
    )
    # What: compute display name from public text and get and value and name and name; why: check endpoint proxy use model name display name metadata json later reads display name, so _profile must retain the computed value under that name.
    display_name = _public_text(value.get("name"), f"models.{name}.name")
    # What: compute metadata json from metadata json and get and value and name and metadata; why: check endpoint proxy use model name display name metadata json later reads metadata json, so _profile must retain the computed value under that name.
    metadata_json = _metadata_json(
        # What: call value.get with metadata and the named fixture input; why: _profile consumes the value.get return value while evaluating value.get("metadata", {}), f"models.{name}.metadata".
        value.get("metadata", {}), f"models.{name}.metadata"
    # What: complete the _metadata_json call with get and name; why: _profile groups the supplied clauses as one _metadata_json call before its value is consumed.
    )
    # What: compute upstream timeout s from get and value and upstream timeout s; why: if upstream timeout s is not later reads upstream timeout s, so _profile must retain the computed value under that name.
    upstream_timeout_s = value.get("upstream_timeout_s")
    # What: gate on upstream timeout s before upstream timeout s and finite seconds and name; why: _profile admits upstream timeout s and finite seconds and name only for this predicate and excludes the opposite state.
    if upstream_timeout_s is not None:
        # What: compute upstream timeout s from finite seconds and upstream timeout s and name and models and upstream timeout s; why: upstream timeout s f models name upstream timeout s later reads upstream timeout s, so _profile must retain the computed value under that name.
        upstream_timeout_s = _finite_seconds(
            # What: apply the upstream timeout s f models name upstream timeout s portion of upstream timeout s; why: _profile uses this clause to evaluate upstream timeout s as one grouped value.
            upstream_timeout_s, f"models.{name}.upstream_timeout_s",
            # What: supply minimum to _finite_seconds; why: _profile binds this 1 value to _finite_seconds's minimum input.
            minimum=1, maximum=7200,
        # What: complete the _finite_seconds call with minimum and maximum; why: _profile groups the supplied clauses as one _finite_seconds call before its value is consumed.
        )
    # What: compute ready timeout s from finite seconds and get and value and name and ready timeout s; why: name model tuple raw args port description later reads ready timeout s, so _profile must retain the computed value under that name.
    ready_timeout_s = _finite_seconds(value.get("ready_timeout_s", 120), f"models.{name}.ready_timeout_s", minimum=1, maximum=900)
    # What: compute ttl s from get and value and ttl s; why: if ttl s is not later reads ttl s, so _profile must retain the computed value under that name.
    ttl_s = value.get("ttl_s")
    # What: gate on ttl s before ttl s and finite seconds and name; why: _profile admits ttl s and finite seconds and name only for this predicate and excludes the opposite state.
    if ttl_s is not None:
        # What: compute ttl s from finite seconds and ttl s and name and models and ttl s; why: ttl s unload timeout s priority group later reads ttl s, so _profile must retain the computed value under that name.
        ttl_s = _finite_seconds(ttl_s, f"models.{name}.ttl_s", minimum=0, maximum=86400)
    # What: compute unload timeout s from get and value and unload timeout s; why: if unload timeout s is not later reads unload timeout s, so _profile must retain the computed value under that name.
    unload_timeout_s = value.get("unload_timeout_s")
    # What: gate on unload timeout s before unload timeout s and finite seconds and name; why: _profile admits unload timeout s and finite seconds and name only for this predicate and excludes the opposite state.
    if unload_timeout_s is not None:
        # What: compute unload timeout s from finite seconds and unload timeout s and name and models and unload timeout s; why: ttl s unload timeout s priority group later reads unload timeout s, so _profile must retain the computed value under that name.
        unload_timeout_s = _finite_seconds(unload_timeout_s, f"models.{name}.unload_timeout_s", minimum=1, maximum=900)
    # What: compute priority from get and value and priority and 0; why: if not isinstance priority int or later reads priority, so _profile must retain the computed value under that name.
    priority = value.get("priority", 0)
    # What: gate on isinstance and priority and bool and int before catalog error and name; why: _profile admits catalog error and name only for this predicate and excludes the opposite state.
    if not isinstance(priority, int) or isinstance(priority, bool) or not -1000 <= priority <= 1000:
        # What: raise CatalogError for the caller; why:  _profile stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"models.{name}.priority must be an integer from -1000 through 1000")
    # What: compute group from get and value and group; why: if group is not later reads group, so _profile must retain the computed value under that name.
    group = value.get("group")
    # What: gate on group before group and simple name and name; why: _profile admits group and simple name and name only for this predicate and excludes the opposite state.
    if group is not None:
        # What: compute group from simple name and group and name and models and group; why: ttl s unload timeout s priority group later reads group, so _profile must retain the computed value under that name.
        group = _simple_name(group, f"models.{name}.group")
    # What: compute drop fields from get and value and drop fields; why: if not isinstance drop fields list or later reads drop fields, so _profile must retain the computed value under that name.
    drop_fields = value.get("drop_fields", [])
    # What: gate on isinstance and drop fields and list and len before catalog error and name; why: _profile admits catalog error and name only for this predicate and excludes the opposite state.
    if not isinstance(drop_fields, list) or len(drop_fields) > 64:
        # What: raise CatalogError for the caller; why:  _profile stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(
            # What: apply the f models name drop fields must be portion of the enclosing predicate; why: this clause remains in _profile\'s enclosing expression so its grouping and evaluation order stay intact.
            f"models.{name}.drop_fields must be at most 64 safe JSON field paths"
        # What: complete the CatalogError call with name; why: _profile groups the supplied clauses as one CatalogError call before its value is consumed.
        )
    # What: compute normalized drop fields from tuple and request field path and field and drop fields; why: if len set normalized drop fields len normalized drop fields later reads normalized drop fields, so _profile must retain the computed value under that name.
    normalized_drop_fields = tuple(
        # What: call _request_field_path with field and name and models and drop fields; why: _profile consumes the _request_field_path return value while evaluating _request_field_path(field, f"models.{name}.drop_fields") for field in dr.
        _request_field_path(field, f"models.{name}.drop_fields") for field in drop_fields
    # What: complete the tuple call with request field path; why: _profile groups the supplied clauses as one tuple call before its value is consumed.
    )
    # What: gate on len and normalized drop fields and set before catalog error and name; why: _profile admits catalog error and name only for this predicate and excludes the opposite state.
    if len(set(normalized_drop_fields)) != len(normalized_drop_fields):
        # What: raise CatalogError for the caller; why:  _profile stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"models.{name}.drop_fields must not contain duplicates")
    # What: gate on normalized drop fields before catalog error and name; why: _profile admits catalog error and name only for this predicate and excludes the opposite state.
    if ("model",) in normalized_drop_fields:
        # What: raise CatalogError for the caller; why:  _profile stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"models.{name}.drop_fields must not remove model")
    # What: compute aliases from get and value and aliases; why: not isinstance aliases list later reads aliases, so _profile must retain the computed value under that name.
    aliases = value.get("aliases", [])
    # What: gate on isinstance and aliases and list and all and len before catalog error and name; why: _profile admits catalog error and name only for this predicate and excludes the opposite state.
    if (
        # What: call isinstance with aliases and list; why: _profile invokes isinstance while performing or not all valid model id alias for; the call advances that operation through its result or side effect.
        not isinstance(aliases, list)
        # What: call all with valid model id and alias and aliases; why: _profile invokes all while performing or len set aliases len aliases; the call advances that operation through its result or side effect.
        or not all(_valid_model_id(alias) for alias in aliases)
        # What: call len with set and aliases; why: _profile consumes the len return value while evaluating or len(set(aliases)) != len(aliases).
        or len(set(aliases)) != len(aliases)
    # What: complete the enclosing predicate with if not isinstance aliases list or not all valid model id; why: _profile groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise CatalogError for the caller; why:  _profile stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"models.{name}.aliases must be distinct valid profile names")
    # What: compute unlisted from get and value and unlisted and false; why: if not isinstance unlisted bool later reads unlisted, so _profile must retain the computed value under that name.
    unlisted = value.get("unlisted", False)
    # What: gate on isinstance and unlisted and bool before catalog error and name; why: _profile admits catalog error and name only for this predicate and excludes the opposite state.
    if not isinstance(unlisted, bool):
        # What: raise CatalogError for the caller; why:  _profile stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"models.{name}.unlisted must be a boolean")
    # What: compute concurrency limit from get and value and concurrency limit and 0; why: not isinstance concurrency limit int later reads concurrency limit, so _profile must retain the computed value under that name.
    concurrency_limit = value.get("concurrency_limit", 0)
    # What: gate on isinstance and concurrency limit and bool and int before catalog error and name; why: _profile admits catalog error and name only for this predicate and excludes the opposite state.
    if (
        # What: call isinstance with concurrency limit and int; why: _profile invokes isinstance while performing or isinstance concurrency limit bool; the call advances that operation through its result or side effect.
        not isinstance(concurrency_limit, int)
        # What: call isinstance with concurrency limit and bool; why: _profile invokes isinstance while performing or not concurrency limit 000 000; the call advances that operation through its result or side effect.
        or isinstance(concurrency_limit, bool)
        # What: apply the or not concurrency limit 000 000 portion of the enclosing predicate; why: this clause remains in _profile\'s enclosing expression so its grouping and evaluation order stay intact.
        or not 0 <= concurrency_limit <= 1_000_000
    # What: complete the enclosing predicate with if not isinstance concurrency limit int or isinstance concurrency limit bool; why: _profile groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise CatalogError for the caller; why:  _profile stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(
            # What: apply the f models name concurrency limit must be portion of the enclosing predicate; why: this clause remains in _profile\'s enclosing expression so its grouping and evaluation order stay intact.
            f"models.{name}.concurrency_limit must be an integer from 0 through 1000000"
        # What: complete the CatalogError call with name; why: _profile groups the supplied clauses as one CatalogError call before its value is consumed.
        )
    # What: compute send loading state from get and value and send loading state; why: if send loading state is not and not later reads send loading state, so _profile must retain the computed value under that name.
    send_loading_state = value.get("send_loading_state")
    # What: gate on send loading state and isinstance and bool before catalog error and name; why: _profile admits catalog error and name only for this predicate and excludes the opposite state.
    if send_loading_state is not None and not isinstance(send_loading_state, bool):
        # What: raise CatalogError for the caller; why:  _profile stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"models.{name}.send_loading_state must be a boolean")
    # What: compute capabilities from capabilities and name and get and value and capabilities; why: concurrency limit send loading state capabilities set fields set fields by id later reads capabilities, so _profile must retain the computed value under that name.
    capabilities = _capabilities(name, value.get("capabilities", {}))
    # What: compute set fields from request fields and name and get and value and set fields; why: concurrency limit send loading state capabilities set fields set fields by id later reads set fields, so _profile must retain the computed value under that name.
    set_fields = _request_fields(name, "set_fields", value.get("set_fields", {}))
    # What: compute set fields by id from request fields by id and name and get and value and set fields by id; why: name value get set fields by id later reads set fields by id, so _profile must retain the computed value under that name.
    set_fields_by_id = _request_fields_by_id(
        # What: call value.get with set fields by id and the named fixture input; why: _profile consumes the value.get return value while evaluating name, value.get("set_fields_by_id", {}).
        name, value.get("set_fields_by_id", {})
    # What: complete the _request_fields_by_id call with name and get; why: _profile groups the supplied clauses as one _request_fields_by_id call before its value is consumed.
    )
    # What: compute check endpoint from check endpoint and get and default check endpoint and value; why: value get check endpoint default check endpoint later reads check endpoint, so _profile must retain the computed value under that name.
    check_endpoint = _check_endpoint(
        # What: call value.get with check endpoint and default check endpoint; why: _profile invokes value.get while performing f models name check endpoint; the call advances that operation through its result or side effect.
        value.get("check_endpoint", DEFAULT_CHECK_ENDPOINT),
        # What: apply the f models name check endpoint portion of check endpoint; why: _profile uses this clause to evaluate check endpoint as one grouped value.
        f"models.{name}.check_endpoint",
    # What: complete the _check_endpoint call with get and name; why: _profile groups the supplied clauses as one _check_endpoint call before its value is consumed.
    )
    # What: compute proxy from proxy template and get and default proxy and value; why: value get proxy default proxy f models name later reads proxy, so _profile must retain the computed value under that name.
    proxy = _proxy_template(
        # What: call value.get with proxy and default proxy; why: _profile consumes the value.get return value while evaluating value.get("proxy", DEFAULT_PROXY), f"models.{name}.proxy".
        value.get("proxy", DEFAULT_PROXY), f"models.{name}.proxy"
    # What: complete the _proxy_template call with get and name; why: _profile groups the supplied clauses as one _proxy_template call before its value is consumed.
    )
    # What: compute use model name from upstream model name and get and value and name and use model name; why: value get use model name f models name use model name later reads use model name, so _profile must retain the computed value under that name.
    use_model_name = _upstream_model_name(
        # What: call value.get with use model name; why: _profile consumes the value.get return value while evaluating value.get("use_model_name"), f"models.{name}.use_model_name".
        value.get("use_model_name"), f"models.{name}.use_model_name"
    # What: complete the _upstream_model_name call with get and name; why: _profile groups the supplied clauses as one _upstream_model_name call before its value is consumed.
    )
    # What: compute aliases from list and fromkeys and dict and aliases; why: aliases later reads aliases, so _profile must retain the computed value under that name.
    aliases = list(dict.fromkeys([
        # What: apply the aliases portion of aliases; why: _profile uses this clause to evaluate aliases as one grouped value.
        *aliases,
        # What: apply the model id for model id value in set fields by id portion of aliases; why: _profile uses this clause to evaluate aliases as one grouped value.
        *(model_id for model_id, _ in set_fields_by_id if model_id != name),
    # What: complete the list call with fromkeys; why: _profile groups the supplied clauses as one list call before its value is consumed.
    ]))
    # What: return model profile and name and model and port from _profile; why: _profile exposes model profile and name and model and port so its caller can continue with the function\'s computed outcome.
    return ModelProfile(
        # What: call tuple with raw args; why: _profile invokes tuple while performing ttl s unload timeout s priority group; the call advances that operation through its result or side effect.
        name, model, tuple(raw_args), port, description, ready_timeout_s,
        # What: apply the ttl s unload timeout s priority group portion of the enclosing predicate; why: this clause remains in _profile\'s enclosing expression so its grouping and evaluation order stay intact.
        ttl_s, unload_timeout_s, priority, group,
        # What: call tuple with join and path and normalized drop fields and value; why: _profile invokes tuple while performing concurrency limit send loading state capabilities set fields set fields by id; the call advances that operation through its result or side effect.
        tuple(".".join(path) for path in normalized_drop_fields), tuple(aliases), unlisted,
        # What: apply the concurrency limit send loading state capabilities set fields set fields by id portion of the enclosing predicate; why: this clause remains in _profile\'s enclosing expression so its grouping and evaluation order stay intact.
        concurrency_limit, send_loading_state, capabilities, set_fields, set_fields_by_id,
        # What: apply the check endpoint proxy use model name display name metadata json portion of the enclosing predicate; why: this clause remains in _profile\'s enclosing expression so its grouping and evaluation order stay intact.
        check_endpoint, proxy, use_model_name, display_name, metadata_json,
        # What: apply the upstream timeout s portion of the enclosing predicate; why: this clause remains in _profile\'s enclosing expression so its grouping and evaluation order stay intact.
        upstream_timeout_s,
    # What: complete the ModelProfile call with name and model and tuple and port and description; why: _profile groups the supplied clauses as one ModelProfile call before its value is consumed.
    )


# What: define _check_endpoint around value and field; why: its direct callers call _check_endpoint for check endpoint and rely on this exact input and result contract.
def _check_endpoint(value: object, field: str) -> str:
    # What: gate on any and isinstance and value and str and len before catalog error and field; why: _check_endpoint admits catalog error and field only for this predicate and excludes the opposite state.
    if (
        # What: call isinstance with value and str; why: _check_endpoint invokes isinstance while performing or len value; the call advances that operation through its result or side effect.
        not isinstance(value, str)
        # What: call len with value; why: _check_endpoint invokes len while performing or not safe http path fullmatch value; the call advances that operation through its result or side effect.
        or len(value) > 256
        # What: call _SAFE_HTTP_PATH.fullmatch with value; why: _check_endpoint invokes _SAFE_HTTP_PATH.fullmatch while performing or any segment in for segment; the call advances that operation through its result or side effect.
        or not _SAFE_HTTP_PATH.fullmatch(value)
        # What: call any with segment and split and value and value and value; why: _check_endpoint consumes the any return value while evaluating or any(segment in {".", ".."} for segment in value.split("/")).
        or any(segment in {".", ".."} for segment in value.split("/"))
    # What: complete the enclosing predicate with if not isinstance value str or len value 256; why: _check_endpoint groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise CatalogError for the caller; why: _check_endpoint stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(
            # What: apply the f field must be an absolute portion of the enclosing predicate; why: this clause remains in _check_endpoint\'s enclosing expression so its grouping and evaluation order stay intact.
            f"{field} must be an absolute ASCII path without query, fragment, or traversal"
        # What: complete the CatalogError call with field; why: _check_endpoint groups the supplied clauses as one CatalogError call before its value is consumed.
        )
    # What: return value from _check_endpoint; why: _check_endpoint exposes value so its caller can continue with the function\'s computed outcome.
    return value


# What: define _proxy_template around value and field; why: its direct callers call _proxy_template for proxy template and rely on this exact input and result contract.
def _proxy_template(value: object, field: str) -> str:
    # What: gate on isinstance and value and str and len before catalog error and field; why: _proxy_template admits catalog error and field only for this predicate and excludes the opposite state.
    if not isinstance(value, str) or len(value) > 512:
        # What: raise CatalogError for the caller; why:  _proxy_template stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field} must be a safe loopback HTTP URL template")
    # What: compute match from fullmatch and value and proxy template; why: if match is later reads match, so _proxy_template must retain the computed value under that name.
    match = _PROXY_TEMPLATE.fullmatch(value)
    # What: gate on match before catalog error and field; why: _proxy_template admits catalog error and field only for this predicate and excludes the opposite state.
    if match is None:
        # What: raise CatalogError for the caller; why:  _proxy_template stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(
            # What: apply the f field must be http port portion of the enclosing predicate; why: this clause remains in _proxy_template\'s enclosing expression so its grouping and evaluation order stay intact.
            f"{field} must be http://127.0.0.1:${{PORT}} with an optional safe path prefix"
        # What: complete the CatalogError call with field; why: _proxy_template groups the supplied clauses as one CatalogError call before its value is consumed.
        )
    # What: compute prefix from group and match and value and prefix; why: if any segment in for segment later reads prefix, so _proxy_template must retain the computed value under that name.
    prefix = match.group("prefix") or ""
    # What: gate on any and segment and split and prefix before catalog error and field; why: _proxy_template admits catalog error and field only for this predicate and excludes the opposite state.
    if any(segment in {".", ".."} for segment in prefix.split("/")):
        # What: raise CatalogError for the caller; why:  _proxy_template stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(
            # What: apply the f field must be http port portion of the enclosing predicate; why: this clause remains in _proxy_template\'s enclosing expression so its grouping and evaluation order stay intact.
            f"{field} must be http://127.0.0.1:${{PORT}} with an optional safe path prefix"
        # What: complete the CatalogError call with field; why: _proxy_template groups the supplied clauses as one CatalogError call before its value is consumed.
        )
    # What: gate on prefix before prefix; why: _proxy_template admits prefix only for this predicate and excludes the opposite state.
    if prefix == "/":
        # What: compute prefix from value; why: return default proxy prefix later reads prefix, so _proxy_template must retain the computed value under that name.
        prefix = ""
    # What: return default proxy and prefix from _proxy_template; why: _proxy_template exposes default proxy and prefix so its caller can continue with the function\'s computed outcome.
    return DEFAULT_PROXY + prefix


# What: define _upstream_model_name around value and field; why: its direct callers call _upstream_model_name for upstream model name and rely on this exact input and result contract.
def _upstream_model_name(value: object, field: str) -> str | None:
    # What: gate on value before the computed value; why: _upstream_model_name admits the computed value only for this predicate and excludes the opposite state.
    if value is None:
        # What: return no value from _upstream_model_name; why: _upstream_model_name returns no value to callers that depend on its completed result.
        return None
    # What: gate on value and any and isinstance and str and len before catalog error and field; why: _upstream_model_name admits catalog error and field only for this predicate and excludes the opposite state.
    if (
        # What: call isinstance with value and str; why: _upstream_model_name invokes isinstance while performing or not value; the call advances that operation through its result or side effect.
        not isinstance(value, str)
        # What: apply the or not value portion of the enclosing predicate; why: this clause remains in _upstream_model_name\'s enclosing expression so its grouping and evaluation order stay intact.
        or not value
        # What: call len with value; why: _upstream_model_name invokes len while performing or value value strip; the call advances that operation through its result or side effect.
        or len(value) > 256
        # What: call value.strip with the declared inputs; why: _upstream_model_name invokes value.strip while performing or any ord character or ord; the call advances that operation through its result or side effect.
        or value != value.strip()
        # What: call any with character and value and ord and 32 and 127; why: _upstream_model_name consumes the any return value while evaluating or any(ord(character) < 32 or ord(character) == 127 for character in val.
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    # What: complete the enclosing predicate with if not isinstance value str or not value or; why: _upstream_model_name groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise CatalogError for the caller; why: _upstream_model_name stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(
            # What: apply the f field must be a non empty portion of the enclosing predicate; why: this clause remains in _upstream_model_name\'s enclosing expression so its grouping and evaluation order stay intact.
            f"{field} must be a non-empty trimmed string without control characters"
        # What: complete the CatalogError call with field; why: _upstream_model_name groups the supplied clauses as one CatalogError call before its value is consumed.
        )
    # What: return value from _upstream_model_name; why: _upstream_model_name exposes value so its caller can continue with the function\'s computed outcome.
    return value


# What: define _metadata_json around value and field; why: its direct callers call _metadata_json for metadata json and rely on this exact input and result contract.
def _metadata_json(value: object, field: str) -> str:
    # What: gate on isinstance and value and dict and all and key before catalog error and field; why: _metadata_json admits catalog error and field only for this predicate and excludes the opposite state.
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        # What: raise CatalogError for the caller; why:  _metadata_json stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field} must be a table with string keys")
    # What: establish the handler boundary for the protected operation; why: _metadata_json routes failures to type error and value error while preserving cleanup and success flow.
    try:
        # What: return dumps and value and json and false and false from _metadata_json; why: _metadata_json exposes dumps and value and json and false and false so its caller can continue with the function\'s computed outcome.
        return json.dumps(
            # What: supply ensure ascii to json.dumps; why: _metadata_json binds this false value to json.dumps's ensure ascii input.
            value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True
        # What: complete the json.dumps call with ensure ascii and allow nan and separators and sort keys; why: _metadata_json groups the supplied clauses as one json.dumps call before its value is consumed.
        )
    # What: handle type error and value error by raise catalog error f field must be json compatible; why: _metadata_json converts that failure into this concrete recovery, response, or cleanup behavior.
    except (TypeError, ValueError) as exc:
        # What: raise CatalogError for the caller; why:  _metadata_json stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field} must be JSON-compatible") from exc


# What: define _public_text around value and field; why: its direct callers call _public_text for public text and rely on this exact input and result contract.
def _public_text(value: object, field: str) -> str | None:
    # What: gate on value before the computed value; why: _public_text admits the computed value only for this predicate and excludes the opposite state.
    if value is None:
        # What: return no value from _public_text; why: _public_text returns no value to callers that depend on its completed result.
        return None
    # What: gate on value and isinstance and str before catalog error and field; why: _public_text admits catalog error and field only for this predicate and excludes the opposite state.
    if not isinstance(value, str) or "\x00" in value:
        # What: raise CatalogError for the caller; why: _public_text stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field} must be a string without NUL")
    # What: return strip and value from _public_text; why: _public_text exposes strip and value so its caller can continue with the function\'s computed outcome.
    return value.strip() or None


# What: define _request_field_path around value and field; why: its direct callers call _request_field_path for request field path and rely on this exact input and result contract.
def _request_field_path(value: object, field: str) -> tuple[str, ...]:
    # What: gate on isinstance and value and str and len before catalog error and field; why: _request_field_path admits catalog error and field only for this predicate and excludes the opposite state.
    if not isinstance(value, str) or len(value) > 128:
        # What: raise CatalogError for the caller; why: _request_field_path stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field} must use safe dot-delimited JSON object paths")
    # What: compute path from tuple and split and value and value; why: if not path or len path later reads path, so _request_field_path must retain the computed value under that name.
    path = tuple(value.split("."))
    # What: gate on path and len and all and fullmatch and part before catalog error and field; why: _request_field_path admits catalog error and field only for this predicate and excludes the opposite state.
    if not path or len(path) > 16 or not all(_SIMPLE_NAME.fullmatch(part) for part in path):
        # What: raise CatalogError for the caller; why: _request_field_path stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field} must use safe dot-delimited JSON object paths")
    # What: return path from _request_field_path; why: _request_field_path exposes path so its caller can continue with the function\'s computed outcome.
    return path


# What: define _request_fields around name and key and value; why: its direct callers call _request_fields for request fields and rely on this exact input and result contract.
def _request_fields(name: str, key: str, value: object) -> tuple[RequestField, ...]:
    # What: compute field from name and key and models and value; why: raise catalog error f field must be later reads field, so _request_fields must retain the computed value under that name.
    field = f"models.{name}.{key}"
    # What: gate on isinstance and value and dict and len before catalog error and field; why: _request_fields admits catalog error and field only for this predicate and excludes the opposite state.
    if not isinstance(value, dict) or len(value) > 64:
        # What: raise CatalogError for the caller; why:  _request_fields stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field} must be a table with at most 64 JSON field assignments")
    # What: initialize hard as an empty runtime accumulator; why: _request_fields appends or maps entries into it during soft if is soft else hard path operation before consuming the aggregate.
    hard: dict[tuple[str, ...], RequestField] = {}
    # What: initialize soft as an empty runtime accumulator; why: _request_fields appends or maps entries into it during soft if is soft else hard path operation before consuming the aggregate.
    soft: dict[tuple[str, ...], RequestField] = {}
    # What: iterate across items and value to perform is soft and isinstance and raw key and str and endswith; why: _request_fields repeats the body only while or for the loop header admits an iteration.
    for raw_key, raw_value in value.items():
        # What: compute is soft from isinstance and raw key and str and endswith and value; why: raw key if is soft else raw key later reads is soft, so _request_fields must retain the computed value under that name.
        is_soft = isinstance(raw_key, str) and raw_key.endswith("?")
        # What: compute path from request field path and field and is soft and raw key and 1; why: if path model later reads path, so _request_fields must retain the computed value under that name.
        path = _request_field_path(
            # What: apply the raw key if is soft else raw key portion of path; why: _request_fields uses this clause to evaluate path as one grouped value.
            raw_key[:-1] if is_soft else raw_key,
            # What: apply the field portion of path; why: _request_fields uses this clause to evaluate path as one grouped value.
            field,
        # What: complete the _request_field_path call with is soft and field; why: _request_fields groups the supplied clauses as one _request_field_path call before its value is consumed.
        )
        # What: gate on path before catalog error and field; why: _request_fields admits catalog error and field only for this predicate and excludes the opposite state.
        if path == ("model",):
            # What: raise CatalogError for the caller; why:  _request_fields stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError(f"{field} must not set model")
        # What: establish the handler boundary for the protected operation; why: _request_fields routes failures to type error and value error while preserving cleanup and success flow.
        try:
            # What: compute value json from dumps and raw value and json and false and false; why: if len value json encode utf 8 536 later reads value json, so _request_fields must retain the computed value under that name.
            value_json = json.dumps(
                # What: apply the raw value portion of value json; why: _request_fields uses this clause to evaluate value json as one grouped value.
                raw_value,
                # What: supply allow nan to json.dumps; why: _request_fields binds this false value to json.dumps's allow nan input.
                allow_nan=False,
                # What: supply ensure ascii to json.dumps; why: _request_fields binds this false value to json.dumps's ensure ascii input.
                ensure_ascii=False,
                # What: supply separators to json.dumps; why: _request_fields binds this value and value value to json.dumps's separators input.
                separators=(",", ":"),
                # What: supply sort keys to json.dumps; why: _request_fields binds this true value to json.dumps's sort keys input.
                sort_keys=True,
            # What: complete the json.dumps call with allow nan and ensure ascii and separators and sort keys; why: _request_fields groups the supplied clauses as one json.dumps call before its value is consumed.
            )
        # What: handle type error and value error by raise catalog error f field raw key must be; why: _request_fields converts that failure into this concrete recovery, response, or cleanup behavior.
        except (TypeError, ValueError) as exc:
            # What: raise CatalogError for the caller; why:  _request_fields stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError(f"{field}.{raw_key} must be JSON-compatible") from exc
        # What: gate on len and encode and value json before catalog error and field and raw key; why: _request_fields admits catalog error and field and raw key only for this predicate and excludes the opposite state.
        if len(value_json.encode("utf-8")) > 65_536:
            # What: raise CatalogError for the caller; why:  _request_fields stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError(f"{field}.{raw_key} exceeds the 65536-byte value limit")
        # What: compute operation from request field and path and value json and is soft; why: soft if is soft else hard path later reads operation, so _request_fields must retain the computed value under that name.
        operation = RequestField(path, value_json, is_soft)
        # What: compute result entry from operation; why: the enclosing return or state update later reads result entry, so _request_fields must retain the computed value under that name.
        (soft if is_soft else hard)[path] = operation
    # What: iterate across intersection and soft and set and hard to perform pop and path and soft; why: _request_fields repeats the body only while or for the loop header admits an iteration.
    for path in set(hard).intersection(soft):
        # What: call soft.pop with path; why: _request_fields invokes soft.pop while performing return tuple hard path for path; the call advances that operation through its result or side effect.
        soft.pop(path)
    # What: return tuple and hard and path and soft from _request_fields; why: _request_fields exposes tuple and hard and path and soft so its caller can continue with the function\'s computed outcome.
    return tuple(hard[path] for path in sorted(hard)) + tuple(
        # What: call sorted with soft; why: _request_fields consumes the sorted return value while evaluating soft[path] for path in sorted(soft).
        soft[path] for path in sorted(soft)
    # What: complete the tuple call with soft; why: _request_fields groups the supplied clauses as one tuple call before its value is consumed.
    )


# What: define _request_fields_by_id around name and value; why: its direct callers call _request_fields_by_id for request fields by id and rely on this exact input and result contract.
def _request_fields_by_id(
    # What: declare the name input for _request_fields_by_id; why: _request_fields_by_id consumes name during field f models name set fields by id, so callers must bind it with the other signature inputs.
    name: str, value: object
# What: complete the enclosing predicate collection with tuple and str and request field and the named fixture input; why: _request_fields_by_id groups the supplied clauses as one enclosing predicate collection collection before its value is consumed.
) -> tuple[tuple[str, tuple[RequestField, ...]], ...]:
    # What: compute field from name and models and set fields by id; why: raise catalog error f field must be later reads field, so _request_fields_by_id must retain the computed value under that name.
    field = f"models.{name}.set_fields_by_id"
    # What: gate on isinstance and value and dict and len before catalog error and field; why: _request_fields_by_id admits catalog error and field only for this predicate and excludes the opposite state.
    if not isinstance(value, dict) or len(value) > 64:
        # What: raise CatalogError for the caller; why: _request_fields_by_id stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field} must be a table with at most 64 model IDs")
    # What: initialize result as an empty runtime accumulator; why: _request_fields_by_id appends or maps entries into it during result append model id request fields name f set fields by id model id before consuming the aggregate.
    result = []
    # What: iterate across items and value to perform model id and model id; why: _request_fields_by_id repeats the body only while or for the loop header admits an iteration.
    for model_id, fields in value.items():
        # What: compute model id from model id and model id; why: result append model id request fields name f set fields by id later reads model id, so _request_fields_by_id must retain the computed value under that name.
        model_id = _model_id(model_id)
        # What: preserve the exact result append model id request fields name f set fields by id literal fragment; why: _request_fields_by_id passes this fragment verbatim through result.append((model_id, _request_fields(name, f"set_fields_by_id.{model, because changing it would alter a protocol payload, serialized fi.
        result.append((model_id, _request_fields(name, f"set_fields_by_id.{model_id}", fields)))
    # What: return tuple and sorted and result from _request_fields_by_id; why: _request_fields_by_id exposes tuple and sorted and result so its caller can continue with the function\'s computed outcome.
    return tuple(sorted(result))


# What: define _capabilities around name and value; why: its direct callers call _capabilities for capabilities and rely on this exact input and result contract.
def _capabilities(name: str, value: object) -> ModelCapabilities:
    # What: compute field from name and models and capabilities; why: raise catalog error f field must be later reads field, so _capabilities must retain the computed value under that name.
    field = f"models.{name}.capabilities"
    # What: gate on isinstance and value and dict before catalog error and field; why: _capabilities admits catalog error and field only for this predicate and excludes the opposite state.
    if not isinstance(value, dict):
        # What: raise CatalogError for the caller; why:  _capabilities stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field} must be a table")
    # What: compute unknown from sorted and set and value and in and out; why: if unknown later reads unknown, so _capabilities must retain the computed value under that name.
    unknown = sorted(set(value) - {"in", "out", "tools", "context"})
    # What: gate on unknown before catalog error and field and join and unknown; why: _capabilities admits catalog error and field and join and unknown only for this predicate and excludes the opposite state.
    if unknown:
        # What: raise CatalogError for the caller; why:  _capabilities stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field}: unsupported keys: {', '.join(unknown)}")

    # What: define modalities around key; why: its direct callers call modalities for modalities and rely on this exact input and result contract.
    def modalities(key: str) -> tuple[str, ...]:
        # What: compute raw from get and key and value; why: if not isinstance raw list or later reads raw, so modalities must retain the computed value under that name.
        raw = value.get(key, [])
        # What: gate on isinstance and raw and list and all and item before catalog error and field and key; why: modalities admits catalog error and field and key only for this predicate and excludes the opposite state.
        if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
            # What: raise CatalogError for the caller; why:  modalities stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError(f"{field}.{key} must be an array of supported modalities")
        # What: gate on len and raw and set before catalog error and field and key; why: modalities admits catalog error and field and key only for this predicate and excludes the opposite state.
        if len(set(raw)) != len(raw):
            # What: raise CatalogError for the caller; why:  modalities stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError(f"{field}.{key} must not contain duplicates")
        # What: compute unsupported from sorted and set and raw and text; why: if unsupported later reads unsupported, so modalities must retain the computed value under that name.
        unsupported = sorted(set(raw) - {"text"})
        # What: gate on unsupported before catalog error and field and key and join and unsupported; why: modalities admits catalog error and field and key and join and unsupported only for this predicate and excludes the opposite state.
        if unsupported:
            # What: raise CatalogError for the caller; why:  modalities stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError(
                # What: call operation.join with unsupported; why: modalities consumes the operation.join return value while evaluating f"{field}.{key} contains unsupported modalities: {', '.join(unsupported).
                f"{field}.{key} contains unsupported modalities: {', '.join(unsupported)}"
            # What: complete the CatalogError call with field; why: modalities groups the supplied clauses as one CatalogError call before its value is consumed.
            )
        # What: return tuple and raw from modalities; why: modalities exposes tuple and raw so its caller can continue with the function\'s computed outcome.
        return tuple(raw)

    # What: compute tools from get and value and tools and false; why: if not isinstance tools bool later reads tools, so _capabilities must retain the computed value under that name.
    tools = value.get("tools", False)
    # What: gate on isinstance and tools and bool before catalog error and field; why: _capabilities admits catalog error and field only for this predicate and excludes the opposite state.
    if not isinstance(tools, bool):
        # What: raise CatalogError for the caller; why:  _capabilities stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field}.tools must be a boolean")
    # What: compute context from get and value and context and 0; why: not isinstance context int later reads context, so _capabilities must retain the computed value under that name.
    context = value.get("context", 0)
    # What: gate on isinstance and context and bool and int before catalog error and field; why: _capabilities admits catalog error and field only for this predicate and excludes the opposite state.
    if (
        # What: call isinstance with context and int; why: _capabilities invokes isinstance while performing or isinstance context bool; the call advances that operation through its result or side effect.
        not isinstance(context, int)
        # What: call isinstance with context and bool; why: _capabilities invokes isinstance while performing or context; the call advances that operation through its result or side effect.
        or isinstance(context, bool)
        # What: apply the or context portion of the enclosing predicate; why: this clause remains in _capabilities\'s enclosing expression so its grouping and evaluation order stay intact.
        or context < 0
    # What: complete the enclosing predicate with if not isinstance context int or isinstance context bool; why: _capabilities groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise CatalogError for the caller; why:  _capabilities stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field}.context must be a nonnegative integer")
    # What: return model capabilities and tools and context and modalities and in from _capabilities; why: _capabilities exposes model capabilities and tools and context and modalities and in so its caller can continue with the function\'s computed outcome.
    return ModelCapabilities(modalities("in"), modalities("out"), tools, context)


# What: define _routing_profile around name and value; why: its direct callers call _routing_profile for routing profile and rely on this exact input and result contract.
def _routing_profile(name: str, value: object) -> RoutingProfile:
    # What: compute field from name and profiles; why: raise catalog error f field must be later reads field, so _routing_profile must retain the computed value under that name.
    field = f"profiles.{name}"
    # What: gate on isinstance and value and dict before catalog error and field; why: _routing_profile admits catalog error and field only for this predicate and excludes the opposite state.
    if not isinstance(value, dict):
        # What: raise CatalogError for the caller; why:  _routing_profile stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field} must be a table with description and pins")
    # What: compute unknown from sorted and set and value and description and pins; why: if unknown later reads unknown, so _routing_profile must retain the computed value under that name.
    unknown = sorted(set(value) - {"description", "pins"})
    # What: gate on unknown before catalog error and field and join and unknown; why: _routing_profile admits catalog error and field and join and unknown only for this predicate and excludes the opposite state.
    if unknown:
        # What: raise CatalogError for the caller; why:  _routing_profile stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field}: unsupported keys: {', '.join(unknown)}")
    # What: compute description from get and value and description; why: if description is not and later reads description, so _routing_profile must retain the computed value under that name.
    description = value.get("description")
    # What: gate on description and isinstance and str before catalog error and field; why: _routing_profile admits catalog error and field only for this predicate and excludes the opposite state.
    if description is not None and (
        # What: call isinstance with description and str; why: _routing_profile consumes the isinstance return value while evaluating not isinstance(description, str) or "\x00" in description.
        not isinstance(description, str) or "\x00" in description
    # What: complete the enclosing predicate with description is not and not isinstance description str or; why: _routing_profile groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise CatalogError for the caller; why:  _routing_profile stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field}.description must be a string without NUL")
    # What: compute raw pins from get and value and pins; why: if not isinstance raw pins dict or later reads raw pins, so _routing_profile must retain the computed value under that name.
    raw_pins = value.get("pins")
    # What: gate on raw pins and isinstance and dict before catalog error and field; why: _routing_profile admits catalog error and field only for this predicate and excludes the opposite state.
    if not isinstance(raw_pins, dict) or not raw_pins:
        # What: raise CatalogError for the caller; why:  _routing_profile stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field}.pins must contain at least one entry")
    # What: initialize pins as an empty runtime accumulator; why: _routing_profile appends or maps entries into it during raise catalog error f field pins pin must before consuming the aggregate.
    pins: list[tuple[str, str | None]] = []
    # What: iterate across items and raw pins to perform pin and model id and raw pin; why: _routing_profile repeats the body only while or for the loop header admits an iteration.
    for raw_pin, raw_target in raw_pins.items():
        # What: compute pin from model id and raw pin; why: raise catalog error f field pins pin later reads pin, so _routing_profile must retain the computed value under that name.
        pin = _model_id(raw_pin)
        # What: gate on isinstance and raw target and str before catalog error and field and pin; why: _routing_profile admits catalog error and field and pin only for this predicate and excludes the opposite state.
        if not isinstance(raw_target, str):
            # What: raise CatalogError for the caller; why:  _routing_profile stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError(f"{field}.pins.{pin} must be a model ID or empty string")
        # What: compute target from raw target and model id; why: pins append pin target later reads target, so _routing_profile must retain the computed value under that name.
        target = _model_id(raw_target) if raw_target else None
        # What: call pins.append with pin and target; why: _routing_profile invokes pins.append while performing return routing profile name tuple sorted pins; the call advances that operation through its result or side effect.
        pins.append((pin, target))
    # What: return routing profile and name and tuple and description from _routing_profile; why: _routing_profile exposes routing profile and name and tuple and description so its caller can continue with the function\'s computed outcome.
    return RoutingProfile(name, tuple(sorted(pins)), description or None)


# What: define _selector around name and value; why: its direct callers call _selector for selector and rely on this exact input and result contract.
def _selector(name: str, value: object) -> ModelSelector:
    # What: compute field from name and selectors; why: raise catalog error f field must be later reads field, so _selector must retain the computed value under that name.
    field = f"selectors.{name}"
    # What: gate on isinstance and value and dict before catalog error and field; why: _selector admits catalog error and field only for this predicate and excludes the opposite state.
    if not isinstance(value, dict):
        # What: raise CatalogError for the caller; why:  _selector stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field} must be a table")
    # What: compute unknown from sorted and set and value and strategy and targets; why: if unknown later reads unknown, so _selector must retain the computed value under that name.
    unknown = sorted(
        # What: call set with value; why: _selector consumes the set return value while evaluating set(value) - {"strategy", "targets", "name", "description", "unlisted",.
        set(value) - {"strategy", "targets", "name", "description", "unlisted", "metadata"}
    # What: complete the sorted call with set; why: _selector groups the supplied clauses as one sorted call before its value is consumed.
    )
    # What: gate on unknown before catalog error and field and join and unknown; why: _selector admits catalog error and field and join and unknown only for this predicate and excludes the opposite state.
    if unknown:
        # What: raise CatalogError for the caller; why:  _selector stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field}: unsupported keys: {', '.join(unknown)}")
    # What: compute strategy from get and value and strategy; why: if strategy spillover later reads strategy, so _selector must retain the computed value under that name.
    strategy = value.get("strategy")
    # What: gate on strategy before catalog error and field; why:  _selector admits catalog error and field only for this predicate and excludes the opposite state.
    if strategy == "spillover":
        # What: raise CatalogError for the caller; why:  _selector stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(
            # What: apply the f field strategy spillover requires multi resident portion of the enclosing predicate; why: this clause remains in _selector\'s enclosing expression so its grouping and evaluation order stay intact.
            f"{field}.strategy spillover requires multi-resident or peer capacity and is unsupported"
        # What: complete the CatalogError call with field; why: _selector groups the supplied clauses as one CatalogError call before its value is consumed.
        )
    # What: gate on strategy before catalog error and field; why:  _selector admits catalog error and field only for this predicate and excludes the opposite state.
    if strategy not in {"pin", "warm"}:
        # What: raise CatalogError for the caller; why:  _selector stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field}.strategy must be pin or warm")
    # What: compute targets from get and value and targets; why: not isinstance targets list later reads targets, so _selector must retain the computed value under that name.
    targets = value.get("targets")
    # What: gate on targets and isinstance and list and len and all before catalog error and field; why: _selector admits catalog error and field only for this predicate and excludes the opposite state.
    if (
        # What: call isinstance with targets and list; why: _selector invokes isinstance while performing or not targets; the call advances that operation through its result or side effect.
        not isinstance(targets, list)
        # What: apply the or not targets portion of the enclosing predicate; why: this clause remains in _selector\'s enclosing expression so its grouping and evaluation order stay intact.
        or not targets
        # What: call len with targets; why: _selector invokes len while performing or not all valid model id target for; the call advances that operation through its result or side effect.
        or len(targets) > 64
        # What: call all with valid model id and target and targets; why: _selector consumes the all return value while evaluating or not all(_valid_model_id(target) for target in targets).
        or not all(_valid_model_id(target) for target in targets)
    # What: complete the enclosing predicate with if not isinstance targets list or not targets or; why: _selector groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise CatalogError for the caller; why:  _selector stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field}.targets must contain 1 to 64 valid model IDs")
    # What: compute display name from get and value and name; why: for key candidate in name display name later reads display name, so _selector must retain the computed value under that name.
    display_name = value.get("name")
    # What: compute description from get and value and description; why: for key candidate in name display name later reads description, so _selector must retain the computed value under that name.
    description = value.get("description")
    # What: iterate across display name and description to perform candidate and catalog error and isinstance and str and field; why: _selector repeats the body only while or for the loop header admits an iteration.
    for key, candidate in (("name", display_name), ("description", description)):
        # What: gate on candidate and isinstance and str before catalog error and field and key; why: _selector admits catalog error and field and key only for this predicate and excludes the opposite state.
        if candidate is not None and (
            # What: call isinstance with candidate and str; why: _selector consumes the isinstance return value while evaluating not isinstance(candidate, str) or "\x00" in candidate.
            not isinstance(candidate, str) or "\x00" in candidate
        # What: complete the enclosing predicate with candidate is not and not isinstance candidate str or; why: _selector groups the supplied clauses as one enclosing predicate expression before its value is consumed.
        ):
            # What: raise CatalogError for the caller; why:  _selector stops this rejected path before it can mutate state, dispatch work, or report success.
            raise CatalogError(f"{field}.{key} must be a string without NUL")
    # What: compute unlisted from get and value and unlisted and false; why: if not isinstance unlisted bool later reads unlisted, so _selector must retain the computed value under that name.
    unlisted = value.get("unlisted", False)
    # What: gate on isinstance and unlisted and bool before catalog error and field; why: _selector admits catalog error and field only for this predicate and excludes the opposite state.
    if not isinstance(unlisted, bool):
        # What: raise CatalogError for the caller; why:  _selector stops this rejected path before it can mutate state, dispatch work, or report success.
        raise CatalogError(f"{field}.unlisted must be a boolean")
    # What: compute metadata json from metadata json and get and value and field and metadata; why: metadata json later reads metadata json, so _selector must retain the computed value under that name.
    metadata_json = _metadata_json(value.get("metadata", {}), f"{field}.metadata")
    # What: return model selector and name and strategy and unlisted from _selector; why: _selector exposes model selector and name and strategy and unlisted so its caller can continue with the function\'s computed outcome.
    return ModelSelector(
        # What: apply the name portion of the enclosing predicate; why: this clause remains in _selector\'s enclosing expression so its grouping and evaluation order stay intact.
        name,
        # What: apply the strategy portion of the enclosing predicate; why: this clause remains in _selector\'s enclosing expression so its grouping and evaluation order stay intact.
        strategy,
        # What: call tuple with targets; why: _selector invokes tuple while performing display name or; the call advances that operation through its result or side effect.
        tuple(targets),
        # What: apply the display name or portion of the enclosing predicate; why: this clause remains in _selector\'s enclosing expression so its grouping and evaluation order stay intact.
        display_name or None,
        # What: apply the description or portion of the enclosing predicate; why: this clause remains in _selector\'s enclosing expression so its grouping and evaluation order stay intact.
        description or None,
        # What: apply the unlisted portion of the enclosing predicate; why: this clause remains in _selector\'s enclosing expression so its grouping and evaluation order stay intact.
        unlisted,
        # What: apply the metadata json portion of the enclosing predicate; why: this clause remains in _selector\'s enclosing expression so its grouping and evaluation order stay intact.
        metadata_json,
    # What: complete the ModelSelector call with name and strategy and tuple and display name and description; why: _selector groups the supplied clauses as one ModelSelector call before its value is consumed.
    )
