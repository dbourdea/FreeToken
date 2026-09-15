"""Named, validated FreeToken engine profiles for ``ft daemon``.

This intentionally borrows the useful *catalog* idea from llama-swap without
accepting its shell-command model.  A profile describes only FreeToken's native
``--model``, ``--port`` and argument-vector contract, so loading a catalog never
creates a shell injection path and the daemon remains torch-free.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

try:  # tomllib joined the stdlib in Python 3.11; FreeToken supports 3.10 too.
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised in the Python 3.10 package build
    import tomli as tomllib


_SIMPLE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_MODEL_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SAFE_HTTP_PATH = re.compile(r"^/(?:[A-Za-z0-9._~-]+(?:/[A-Za-z0-9._~-]+)*)?$")
_PROXY_TEMPLATE = re.compile(
    r"^http://127\.0\.0\.1:\$\{PORT\}(?P<prefix>/(?:[A-Za-z0-9._~-]+(?:/[A-Za-z0-9._~-]+)*)?)?$"
)

DEFAULT_CHECK_ENDPOINT = "/health"
DEFAULT_PROXY = "http://127.0.0.1:${PORT}"


class CatalogError(ValueError):
    """A catalog is malformed or requests an unsafe/ambiguous profile."""


@dataclass(frozen=True)
class RoutingGroup:
    """An atomically validated native equivalent of a llama-swap group."""

    name: str
    members: tuple[str, ...]
    swap: bool = True
    exclusive: bool = True
    persistent: bool = False


@dataclass(frozen=True)
class RouterSettings:
    """Global router policy, deliberately free of command execution fields."""

    api_keys: tuple[str, ...] = ()
    default_ttl_s: float = 0.0
    unload_timeout_s: float = 30.0
    upstream_timeout_s: float = 900.0
    scheduler: str = "fifo"
    groups: tuple[RoutingGroup, ...] = ()
    include_aliases_in_list: bool = False
    global_concurrency_limit: int = 0
    send_loading_state: bool = False


@dataclass(frozen=True)
class ModelCapabilities:
    """Validated model-list metadata; it never enables inference behavior."""

    input_modalities: tuple[str, ...] = ()
    output_modalities: tuple[str, ...] = ()
    tools: bool = False
    context: int = 0

    def empty(self) -> bool:
        return not (
            self.input_modalities or self.output_modalities or self.tools or self.context
        )

    def public(self) -> dict[str, Any]:
        doc: dict[str, Any] = {}
        if self.input_modalities:
            doc["in"] = list(self.input_modalities)
        if self.output_modalities:
            doc["out"] = list(self.output_modalities)
        if self.tools:
            doc["tools"] = True
        if self.context:
            doc["context"] = self.context
        return doc

    def model_listing_fields(self) -> dict[str, Any]:
        """Render the applicable pinned llama-swap model-list contract."""
        doc: dict[str, Any] = {}
        if self.input_modalities or self.output_modalities:
            architecture: dict[str, Any] = {}
            if self.input_modalities:
                architecture["input_modalities"] = list(self.input_modalities)
            if self.output_modalities:
                architecture["output_modalities"] = list(self.output_modalities)
            if self.input_modalities and self.output_modalities:
                architecture["modality"] = (
                    f"{'+'.join(self.input_modalities)}->{'+'.join(self.output_modalities)}"
                )
            doc["architecture"] = architecture
        if self.tools:
            doc["capabilities"] = {"function_calling": True}
            doc["supported_parameters"] = ["tools", "tool_choice"]
        if self.context:
            doc["context_length"] = self.context
            doc["context_window"] = self.context
            doc["meta"] = {"n_ctx": self.context}
        return doc


@dataclass(frozen=True)
class RequestField:
    """One immutable, validated JSON field assignment."""

    path: tuple[str, ...]
    value_json: str
    soft: bool = False

    @property
    def key(self) -> str:
        return ".".join(self.path)

    def value(self) -> Any:
        return json.loads(self.value_json)


def _request_fields_public(fields: tuple[RequestField, ...]) -> dict[str, Any]:
    return {
        field.key + ("?" if field.soft else ""): field.value()
        for field in fields
    }


@dataclass(frozen=True)
class ModelSelector:
    """A per-request virtual model resolved to one concrete local profile."""

    name: str
    strategy: str
    targets: tuple[str, ...]
    display_name: str | None = None
    description: str | None = None
    unlisted: bool = False
    metadata_json: str = "{}"

    def metadata(self) -> dict[str, Any]:
        return json.loads(self.metadata_json)

    def public(self) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "name": self.name,
            "strategy": self.strategy,
            "targets": list(self.targets),
        }
        if self.display_name:
            doc["displayName"] = self.display_name
        if self.description:
            doc["description"] = self.description
        if self.unlisted:
            doc["unlisted"] = True
        metadata = self.metadata()
        if metadata:
            doc["metadata"] = metadata
        return doc


@dataclass(frozen=True)
class RoutingProfile:
    """A runtime-selectable set of client model-ID replacements."""

    name: str
    pins: tuple[tuple[str, str | None], ...]
    description: str | None = None

    def replacement(self, model_id: str) -> tuple[bool, str | None]:
        for pin, target in self.pins:
            if pin == model_id:
                return True, target
        return False, None

    def public(self) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "name": self.name,
            "pins": {pin: target for pin, target in self.pins},
        }
        if self.description:
            doc["description"] = self.description
        return doc


@dataclass(frozen=True)
class ModelProfile:
    name: str
    model: str
    args: tuple[str, ...]
    port: int | None = None
    description: str | None = None
    ready_timeout_s: float = 120.0
    ttl_s: float | None = None
    unload_timeout_s: float | None = None
    priority: int = 0
    group: str | None = None
    drop_fields: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    unlisted: bool = False
    concurrency_limit: int = 0
    send_loading_state: bool | None = None
    capabilities: ModelCapabilities = ModelCapabilities()
    set_fields: tuple[RequestField, ...] = ()
    set_fields_by_id: tuple[tuple[str, tuple[RequestField, ...]], ...] = ()
    check_endpoint: str = DEFAULT_CHECK_ENDPOINT
    proxy: str = DEFAULT_PROXY

    def proxy_base_url(self, port: int) -> str:
        """Resolve the validated loopback template to this owned child port."""
        return self.proxy.replace("${PORT}", str(port))

    def request(self) -> dict[str, Any]:
        body: dict[str, Any] = {"model": self.model, "args": list(self.args)}
        if self.port is not None:
            body["port"] = self.port
            if self.port == 0:
                body["dynamicPort"] = True
        return body

    def public(self) -> dict[str, Any]:
        doc = self.request()
        doc["name"] = self.name
        if self.description:
            doc["description"] = self.description
        doc["readyTimeoutS"] = self.ready_timeout_s
        if self.ttl_s is not None:
            doc["ttlS"] = self.ttl_s
        if self.unload_timeout_s is not None:
            doc["unloadTimeoutS"] = self.unload_timeout_s
        if self.priority:
            doc["priority"] = self.priority
        if self.group is not None:
            doc["group"] = self.group
        if self.drop_fields:
            doc["dropFields"] = list(self.drop_fields)
        if self.aliases:
            doc["aliases"] = list(self.aliases)
        if self.unlisted:
            doc["unlisted"] = True
        if self.concurrency_limit:
            doc["concurrencyLimit"] = self.concurrency_limit
        if self.send_loading_state is not None:
            doc["sendLoadingState"] = self.send_loading_state
        if not self.capabilities.empty():
            doc["capabilities"] = self.capabilities.public()
        if self.set_fields:
            doc["setFields"] = _request_fields_public(self.set_fields)
        if self.set_fields_by_id:
            doc["setFieldsById"] = {
                model_id: _request_fields_public(fields)
                for model_id, fields in self.set_fields_by_id
            }
        if self.check_endpoint != DEFAULT_CHECK_ENDPOINT:
            doc["checkEndpoint"] = self.check_endpoint
        if self.proxy != DEFAULT_PROXY:
            doc["proxy"] = self.proxy
        return doc


class ModelCatalog:
    def __init__(
        self,
        profiles: dict[str, ModelProfile],
        settings: RouterSettings | None = None,
        *,
        selectors: dict[str, ModelSelector] | None = None,
        routing_profiles: dict[str, RoutingProfile] | None = None,
        path: str | None = None,
    ):
        self._profiles = dict(profiles)
        aliases: dict[str, str] = {}
        canonical = set(self._profiles)
        for name, profile in self._profiles.items():
            _model_id(name)
            _model_id(profile.name)
            if name != profile.name:
                raise CatalogError(f"profile key {name!r} must match profile name {profile.name!r}")
            for alias in profile.aliases:
                alias = _model_id(alias)
                if alias in canonical:
                    raise CatalogError(f"model alias {alias!r} conflicts with a configured profile")
                if alias in aliases:
                    raise CatalogError(
                        f"model alias {alias!r} is assigned to both {aliases[alias]!r} and {name!r}"
                    )
                aliases[alias] = name
        self._aliases = aliases
        self._selectors = dict(selectors or {})
        occupied = canonical | set(aliases)
        for name, selector in self._selectors.items():
            _model_id(name)
            if name != selector.name:
                raise CatalogError(
                    f"selector key {name!r} must match selector name {selector.name!r}"
                )
            if name in occupied:
                raise CatalogError(f"selector {name!r} conflicts with a model ID or alias")
            for target in selector.targets:
                if target in self._selectors:
                    raise CatalogError(
                        f"selector {name!r} target {target!r} cannot reference another selector"
                    )
                try:
                    self.get(target)
                except CatalogError as exc:
                    raise CatalogError(
                        f"selector {name!r} target {target!r} is not a configured model or alias"
                    ) from exc
        self._routing_profiles = dict(routing_profiles or {})
        for name, routing_profile in self._routing_profiles.items():
            _simple_name(name, "profile name")
            if name != routing_profile.name:
                raise CatalogError(
                    f"routing profile key {name!r} must match profile name {routing_profile.name!r}"
                )
            if not routing_profile.pins:
                raise CatalogError(f"profiles.{name}.pins must contain at least one entry")
            for pin, target in routing_profile.pins:
                _model_id(pin)
                if target is not None and not self.has_routable_id(target):
                    raise CatalogError(
                        f"profiles.{name}.pins.{pin} references unknown model {target!r}"
                    )
        self.settings = settings or RouterSettings()
        self.path = path

    @classmethod
    def empty(cls) -> "ModelCatalog":
        return cls({})

    @classmethod
    def load(cls, path: str) -> "ModelCatalog":
        try:
            with open(path, "rb") as source:
                raw = tomllib.load(source)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise CatalogError(f"cannot read catalog {path!r}: {exc}") from exc
        models = raw.get("models")
        if not isinstance(models, dict):
            raise CatalogError("catalog requires a [models] table")
        profiles: dict[str, ModelProfile] = {}
        for name, value in models.items():
            profiles[_model_id(name)] = _profile(_model_id(name), value)
        raw_selectors = raw.get("selectors", {})
        if not isinstance(raw_selectors, dict):
            raise CatalogError("selectors must be a table")
        selectors = {
            _model_id(name): _selector(_model_id(name), value)
            for name, value in raw_selectors.items()
        }
        raw_profiles = raw.get("profiles", {})
        if not isinstance(raw_profiles, dict):
            raise CatalogError("profiles must be a table")
        routing_profiles = {
            _simple_name(name, "profile name"): _routing_profile(
                _simple_name(name, "profile name"), value
            )
            for name, value in raw_profiles.items()
        }
        return cls(
            profiles,
            _router_settings(raw.get("router", {}), profiles),
            selectors=selectors,
            routing_profiles=routing_profiles,
            path=path,
        )

    def get(self, name: str) -> ModelProfile:
        try:
            return self._profiles[self._aliases.get(name, name)]
        except KeyError as exc:
            raise CatalogError(f"unknown model profile {name!r}") from exc

    def public(self) -> list[dict[str, Any]]:
        return [self._profiles[name].public() for name in sorted(self._profiles)]

    def public_selectors(self) -> list[dict[str, Any]]:
        return [self._selectors[name].public() for name in sorted(self._selectors)]

    def public_routing_profiles(self) -> list[dict[str, Any]]:
        return [
            self._routing_profiles[name].public() for name in sorted(self._routing_profiles)
        ]

    def profiles(self) -> tuple[ModelProfile, ...]:
        """Return immutable profile values for internal identity matching."""
        return tuple(self._profiles[name] for name in sorted(self._profiles))

    def selector(self, name: str) -> ModelSelector | None:
        return self._selectors.get(name)

    def routing_profile(self, name: str) -> RoutingProfile | None:
        return self._routing_profiles.get(name)

    def has_routable_id(self, name: str) -> bool:
        return name in self._selectors or name in self._profiles or name in self._aliases

    def listed_model_ids(self) -> tuple[str, ...]:
        """Return the OpenAI-visible IDs without exposing hidden canonical profiles."""
        result: list[str] = []
        for name in sorted(self._profiles):
            profile = self._profiles[name]
            if profile.unlisted:
                continue
            result.append(name)
            if self.settings.include_aliases_in_list:
                result.extend(profile.aliases)
        result.extend(
            name for name in sorted(self._selectors) if not self._selectors[name].unlisted
        )
        return tuple(result)

    def resolve_upstream_path(self, path: str) -> tuple[str, ModelProfile, str]:
        """Resolve the longest configured model-ID prefix from a decoded path."""
        parts = path.strip("/").split("/")
        match: tuple[str, ModelProfile, str] | None = None
        for index in range(1, len(parts) + 1):
            candidate = "/".join(parts[:index])
            canonical = self._aliases.get(candidate, candidate)
            profile = self._profiles.get(canonical)
            if profile is not None:
                match = candidate, profile, "/" + "/".join(parts[index:])
        if match is None:
            raise CatalogError("upstream path does not begin with a configured model ID")
        return match

    def group_for(self, name: str) -> RoutingGroup | None:
        for group in self.settings.groups:
            if name in group.members:
                return group
        return None


def _finite_seconds(value: object, field: str, *, minimum: float, maximum: float) -> float:
    if (not isinstance(value, (int, float)) or isinstance(value, bool)
            or not minimum <= value <= maximum):
        raise CatalogError(f"{field} must be from {minimum:g} through {maximum:g} seconds")
    return float(value)


def _router_settings(value: object, profiles: dict[str, ModelProfile]) -> RouterSettings:
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise CatalogError("router must be a table")
    allowed = {
        "api_keys", "default_ttl_s", "unload_timeout_s", "upstream_timeout_s",
        "scheduler", "groups", "include_aliases_in_list", "global_concurrency_limit",
        "send_loading_state",
    }
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise CatalogError(f"router: unsupported keys: {', '.join(unknown)}")
    raw_keys = value.get("api_keys", [])
    if (not isinstance(raw_keys, list) or not all(isinstance(key, str) and key and "\x00" not in key
                                                    for key in raw_keys)):
        raise CatalogError("router.api_keys must be non-empty strings without NUL")
    if len(set(raw_keys)) != len(raw_keys):
        raise CatalogError("router.api_keys must not contain duplicates")
    scheduler = value.get("scheduler", "fifo")
    if scheduler != "fifo":
        raise CatalogError("router.scheduler currently supports only fifo")
    include_aliases_in_list = value.get("include_aliases_in_list", False)
    if not isinstance(include_aliases_in_list, bool):
        raise CatalogError("router.include_aliases_in_list must be a boolean")
    global_concurrency_limit = value.get("global_concurrency_limit", 0)
    if (
        not isinstance(global_concurrency_limit, int)
        or isinstance(global_concurrency_limit, bool)
        or not 0 <= global_concurrency_limit <= 1_000_000
    ):
        raise CatalogError("router.global_concurrency_limit must be an integer from 0 through 1000000")
    send_loading_state = value.get("send_loading_state", False)
    if not isinstance(send_loading_state, bool):
        raise CatalogError("router.send_loading_state must be a boolean")
    raw_groups = value.get("groups", {})
    if not isinstance(raw_groups, dict):
        raise CatalogError("router.groups must be a table")
    groups: list[RoutingGroup] = []
    claimed: set[str] = set()
    for raw_name, raw_group in raw_groups.items():
        name = _simple_name(raw_name, "router group names")
        if not isinstance(raw_group, dict):
            raise CatalogError(f"router.groups.{name} must be a table")
        unknown = sorted(set(raw_group) - {"members", "swap", "exclusive", "persistent"})
        if unknown:
            raise CatalogError(f"router.groups.{name}: unsupported keys: {', '.join(unknown)}")
        members = raw_group.get("members")
        if (not isinstance(members, list) or not members
                or not all(isinstance(member, str) and member in profiles for member in members)):
            raise CatalogError(f"router.groups.{name}.members must name configured models")
        if len(set(members)) != len(members) or claimed.intersection(members):
            raise CatalogError("a model can belong to only one router group")
        claimed.update(members)
        flags = {key: raw_group.get(key, default) for key, default in
                 (("swap", True), ("exclusive", True), ("persistent", False))}
        if not all(isinstance(flag, bool) for flag in flags.values()):
            raise CatalogError(f"router.groups.{name} flags must be booleans")
        # The native coordinator deliberately owns exactly one resident child.
        # Accepting llama-swap's coexistence flags here would silently promise
        # a scheduling policy we cannot implement. Fail atomically at reload
        # time instead; an operator can express the supported policy as an
        # exclusive swapping group, or a singleton persistent protected slot.
        if not flags["exclusive"]:
            raise CatalogError(
                f"router.groups.{name}: single-resident native routing requires exclusive = true"
            )
        if flags["persistent"] and flags["swap"]:
            raise CatalogError(f"router.groups.{name}: persistent groups must set swap = false")
        if not flags["persistent"] and not flags["swap"]:
            raise CatalogError(
                f"router.groups.{name}: swap = false requires multi-resident routing and is unsupported"
            )
        if flags["persistent"] and len(members) != 1:
            raise CatalogError(
                f"router.groups.{name}: a persistent group needs exactly one member under single-resident routing"
            )
        groups.append(RoutingGroup(name, tuple(members), **flags))
    membership = {member: group.name for group in groups for member in group.members}
    for name, profile in profiles.items():
        if profile.group is not None and membership.get(name) != profile.group:
            raise CatalogError(f"models.{name}.group must match router group membership")
    return RouterSettings(
        api_keys=tuple(raw_keys),
        default_ttl_s=_finite_seconds(value.get("default_ttl_s", 0), "router.default_ttl_s", minimum=0, maximum=86400),
        unload_timeout_s=_finite_seconds(value.get("unload_timeout_s", 30), "router.unload_timeout_s", minimum=1, maximum=900),
        upstream_timeout_s=_finite_seconds(value.get("upstream_timeout_s", 900), "router.upstream_timeout_s", minimum=1, maximum=7200),
        scheduler=scheduler,
        groups=tuple(groups),
        include_aliases_in_list=include_aliases_in_list,
        global_concurrency_limit=global_concurrency_limit,
        send_loading_state=send_loading_state,
    )


def _simple_name(name: object, label: str = "names") -> str:
    if not isinstance(name, str) or not _SIMPLE_NAME.fullmatch(name):
        raise CatalogError(f"{label} must match [A-Za-z0-9][A-Za-z0-9._-]{{0,127}}")
    return name


def _valid_model_id(name: object) -> bool:
    return bool(
        isinstance(name, str)
        and len(name) <= 128
        and all(_MODEL_SEGMENT.fullmatch(segment) for segment in name.split("/"))
    )


def _model_id(name: object) -> str:
    if not _valid_model_id(name):
        raise CatalogError(
            "model IDs must be slash-separated [A-Za-z0-9][A-Za-z0-9._:-] segments "
            "with at most 128 characters total"
        )
    return name


def _profile(name: str, value: object) -> ModelProfile:
    if not isinstance(value, dict):
        raise CatalogError(f"models.{name} must be a table")
    allowed = {
        "model", "args", "port", "description", "ready_timeout_s", "ttl_s",
        "unload_timeout_s", "priority", "group", "drop_fields", "aliases", "unlisted",
        "concurrency_limit", "send_loading_state", "capabilities", "set_fields",
        "set_fields_by_id", "check_endpoint", "proxy",
    }
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise CatalogError(f"models.{name}: unsupported keys: {', '.join(unknown)}")
    model = value.get("model")
    if not isinstance(model, str) or not model.strip() or "\x00" in model:
        raise CatalogError(f"models.{name}.model must be a non-empty string without NUL")
    raw_args = value.get("args", [])
    if not isinstance(raw_args, list) or not all(isinstance(arg, str) and "\x00" not in arg for arg in raw_args):
        raise CatalogError(f"models.{name}.args must be an array of strings without NUL")
    # The daemon owns these two options.  Letting a profile smuggle them through
    # produces ambiguous process state and defeats the lifecycle conflict guard.
    for arg in raw_args:
        option = arg.split("=", 1)[0]
        reserved = ("--model", "--model-path", "--port")
        if arg == "--" or option == "-p" or (
            option.startswith("--") and any(flag.startswith(option) for flag in reserved)
        ):
            raise CatalogError(f"models.{name}.args must not set --model or --port")
    port = value.get("port")
    # Port zero is an explicit request for a fresh loopback port on each
    # activation. It is not passed through to uvicorn: the native router
    # reserves an OS-selected candidate and records that concrete target for
    # readiness, proxying, accounting, and re-adoption. ``None`` keeps the
    # daemon-wide fixed default for backwards-compatible catalogs.
    if port is not None and (not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535):
        raise CatalogError(f"models.{name}.port must be an integer from 0 through 65535")
    description = value.get("description")
    if description is not None and (not isinstance(description, str) or "\x00" in description):
        raise CatalogError(f"models.{name}.description must be a string without NUL")
    ready_timeout_s = _finite_seconds(value.get("ready_timeout_s", 120), f"models.{name}.ready_timeout_s", minimum=1, maximum=900)
    ttl_s = value.get("ttl_s")
    if ttl_s is not None:
        ttl_s = _finite_seconds(ttl_s, f"models.{name}.ttl_s", minimum=0, maximum=86400)
    unload_timeout_s = value.get("unload_timeout_s")
    if unload_timeout_s is not None:
        unload_timeout_s = _finite_seconds(unload_timeout_s, f"models.{name}.unload_timeout_s", minimum=1, maximum=900)
    priority = value.get("priority", 0)
    if not isinstance(priority, int) or isinstance(priority, bool) or not -1000 <= priority <= 1000:
        raise CatalogError(f"models.{name}.priority must be an integer from -1000 through 1000")
    group = value.get("group")
    if group is not None:
        group = _simple_name(group, f"models.{name}.group")
    drop_fields = value.get("drop_fields", [])
    if not isinstance(drop_fields, list) or len(drop_fields) > 64:
        raise CatalogError(
            f"models.{name}.drop_fields must be at most 64 safe JSON field paths"
        )
    normalized_drop_fields = tuple(
        _request_field_path(field, f"models.{name}.drop_fields") for field in drop_fields
    )
    if len(set(normalized_drop_fields)) != len(normalized_drop_fields):
        raise CatalogError(f"models.{name}.drop_fields must not contain duplicates")
    if ("model",) in normalized_drop_fields:
        raise CatalogError(f"models.{name}.drop_fields must not remove model")
    aliases = value.get("aliases", [])
    if (
        not isinstance(aliases, list)
        or not all(_valid_model_id(alias) for alias in aliases)
        or len(set(aliases)) != len(aliases)
    ):
        raise CatalogError(f"models.{name}.aliases must be distinct valid profile names")
    unlisted = value.get("unlisted", False)
    if not isinstance(unlisted, bool):
        raise CatalogError(f"models.{name}.unlisted must be a boolean")
    concurrency_limit = value.get("concurrency_limit", 0)
    if (
        not isinstance(concurrency_limit, int)
        or isinstance(concurrency_limit, bool)
        or not 0 <= concurrency_limit <= 1_000_000
    ):
        raise CatalogError(
            f"models.{name}.concurrency_limit must be an integer from 0 through 1000000"
        )
    send_loading_state = value.get("send_loading_state")
    if send_loading_state is not None and not isinstance(send_loading_state, bool):
        raise CatalogError(f"models.{name}.send_loading_state must be a boolean")
    capabilities = _capabilities(name, value.get("capabilities", {}))
    set_fields = _request_fields(name, "set_fields", value.get("set_fields", {}))
    set_fields_by_id = _request_fields_by_id(
        name, value.get("set_fields_by_id", {})
    )
    check_endpoint = _check_endpoint(
        value.get("check_endpoint", DEFAULT_CHECK_ENDPOINT),
        f"models.{name}.check_endpoint",
    )
    proxy = _proxy_template(
        value.get("proxy", DEFAULT_PROXY), f"models.{name}.proxy"
    )
    aliases = list(dict.fromkeys([
        *aliases,
        *(model_id for model_id, _ in set_fields_by_id if model_id != name),
    ]))
    return ModelProfile(
        name, model, tuple(raw_args), port, description, ready_timeout_s,
        ttl_s, unload_timeout_s, priority, group,
        tuple(".".join(path) for path in normalized_drop_fields), tuple(aliases), unlisted,
        concurrency_limit, send_loading_state, capabilities, set_fields, set_fields_by_id,
        check_endpoint, proxy,
    )


def _check_endpoint(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) > 256
        or not _SAFE_HTTP_PATH.fullmatch(value)
        or any(segment in {".", ".."} for segment in value.split("/"))
    ):
        raise CatalogError(
            f"{field} must be an absolute ASCII path without query, fragment, or traversal"
        )
    return value


def _proxy_template(value: object, field: str) -> str:
    if not isinstance(value, str) or len(value) > 512:
        raise CatalogError(f"{field} must be a safe loopback HTTP URL template")
    match = _PROXY_TEMPLATE.fullmatch(value)
    if match is None:
        raise CatalogError(
            f"{field} must be http://127.0.0.1:${{PORT}} with an optional safe path prefix"
        )
    prefix = match.group("prefix") or ""
    if any(segment in {".", ".."} for segment in prefix.split("/")):
        raise CatalogError(
            f"{field} must be http://127.0.0.1:${{PORT}} with an optional safe path prefix"
        )
    if prefix == "/":
        prefix = ""
    return DEFAULT_PROXY + prefix


def _request_field_path(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, str) or len(value) > 128:
        raise CatalogError(f"{field} must use safe dot-delimited JSON object paths")
    path = tuple(value.split("."))
    if not path or len(path) > 16 or not all(_SIMPLE_NAME.fullmatch(part) for part in path):
        raise CatalogError(f"{field} must use safe dot-delimited JSON object paths")
    return path


def _request_fields(name: str, key: str, value: object) -> tuple[RequestField, ...]:
    field = f"models.{name}.{key}"
    if not isinstance(value, dict) or len(value) > 64:
        raise CatalogError(f"{field} must be a table with at most 64 JSON field assignments")
    hard: dict[tuple[str, ...], RequestField] = {}
    soft: dict[tuple[str, ...], RequestField] = {}
    for raw_key, raw_value in value.items():
        is_soft = isinstance(raw_key, str) and raw_key.endswith("?")
        path = _request_field_path(
            raw_key[:-1] if is_soft else raw_key,
            field,
        )
        if path == ("model",):
            raise CatalogError(f"{field} must not set model")
        try:
            value_json = json.dumps(
                raw_value,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        except (TypeError, ValueError) as exc:
            raise CatalogError(f"{field}.{raw_key} must be JSON-compatible") from exc
        if len(value_json.encode("utf-8")) > 65_536:
            raise CatalogError(f"{field}.{raw_key} exceeds the 65536-byte value limit")
        operation = RequestField(path, value_json, is_soft)
        (soft if is_soft else hard)[path] = operation
    for path in set(hard).intersection(soft):
        soft.pop(path)
    return tuple(hard[path] for path in sorted(hard)) + tuple(
        soft[path] for path in sorted(soft)
    )


def _request_fields_by_id(
    name: str, value: object
) -> tuple[tuple[str, tuple[RequestField, ...]], ...]:
    field = f"models.{name}.set_fields_by_id"
    if not isinstance(value, dict) or len(value) > 64:
        raise CatalogError(f"{field} must be a table with at most 64 model IDs")
    result = []
    for model_id, fields in value.items():
        model_id = _model_id(model_id)
        result.append((model_id, _request_fields(name, f"set_fields_by_id.{model_id}", fields)))
    return tuple(sorted(result))


def _capabilities(name: str, value: object) -> ModelCapabilities:
    field = f"models.{name}.capabilities"
    if not isinstance(value, dict):
        raise CatalogError(f"{field} must be a table")
    unknown = sorted(set(value) - {"in", "out", "tools", "context"})
    if unknown:
        raise CatalogError(f"{field}: unsupported keys: {', '.join(unknown)}")

    def modalities(key: str) -> tuple[str, ...]:
        raw = value.get(key, [])
        if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
            raise CatalogError(f"{field}.{key} must be an array of supported modalities")
        if len(set(raw)) != len(raw):
            raise CatalogError(f"{field}.{key} must not contain duplicates")
        unsupported = sorted(set(raw) - {"text"})
        if unsupported:
            raise CatalogError(
                f"{field}.{key} contains unsupported modalities: {', '.join(unsupported)}"
            )
        return tuple(raw)

    tools = value.get("tools", False)
    if not isinstance(tools, bool):
        raise CatalogError(f"{field}.tools must be a boolean")
    context = value.get("context", 0)
    if (
        not isinstance(context, int)
        or isinstance(context, bool)
        or context < 0
    ):
        raise CatalogError(f"{field}.context must be a nonnegative integer")
    return ModelCapabilities(modalities("in"), modalities("out"), tools, context)


def _routing_profile(name: str, value: object) -> RoutingProfile:
    field = f"profiles.{name}"
    if not isinstance(value, dict):
        raise CatalogError(f"{field} must be a table with description and pins")
    unknown = sorted(set(value) - {"description", "pins"})
    if unknown:
        raise CatalogError(f"{field}: unsupported keys: {', '.join(unknown)}")
    description = value.get("description")
    if description is not None and (
        not isinstance(description, str) or "\x00" in description
    ):
        raise CatalogError(f"{field}.description must be a string without NUL")
    raw_pins = value.get("pins")
    if not isinstance(raw_pins, dict) or not raw_pins:
        raise CatalogError(f"{field}.pins must contain at least one entry")
    pins: list[tuple[str, str | None]] = []
    for raw_pin, raw_target in raw_pins.items():
        pin = _model_id(raw_pin)
        if not isinstance(raw_target, str):
            raise CatalogError(f"{field}.pins.{pin} must be a model ID or empty string")
        target = _model_id(raw_target) if raw_target else None
        pins.append((pin, target))
    return RoutingProfile(name, tuple(sorted(pins)), description or None)


def _selector(name: str, value: object) -> ModelSelector:
    field = f"selectors.{name}"
    if not isinstance(value, dict):
        raise CatalogError(f"{field} must be a table")
    unknown = sorted(
        set(value) - {"strategy", "targets", "name", "description", "unlisted", "metadata"}
    )
    if unknown:
        raise CatalogError(f"{field}: unsupported keys: {', '.join(unknown)}")
    strategy = value.get("strategy")
    if strategy == "spillover":
        raise CatalogError(
            f"{field}.strategy spillover requires multi-resident or peer capacity and is unsupported"
        )
    if strategy not in {"pin", "warm"}:
        raise CatalogError(f"{field}.strategy must be pin or warm")
    targets = value.get("targets")
    if (
        not isinstance(targets, list)
        or not targets
        or len(targets) > 64
        or not all(_valid_model_id(target) for target in targets)
    ):
        raise CatalogError(f"{field}.targets must contain 1 to 64 valid model IDs")
    display_name = value.get("name")
    description = value.get("description")
    for key, candidate in (("name", display_name), ("description", description)):
        if candidate is not None and (
            not isinstance(candidate, str) or "\x00" in candidate
        ):
            raise CatalogError(f"{field}.{key} must be a string without NUL")
    unlisted = value.get("unlisted", False)
    if not isinstance(unlisted, bool):
        raise CatalogError(f"{field}.unlisted must be a boolean")
    metadata = value.get("metadata", {})
    if not isinstance(metadata, dict) or not all(isinstance(key, str) for key in metadata):
        raise CatalogError(f"{field}.metadata must be a table with string keys")
    try:
        metadata_json = json.dumps(
            metadata, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True
        )
    except (TypeError, ValueError) as exc:
        raise CatalogError(f"{field}.metadata must be JSON-compatible") from exc
    return ModelSelector(
        name,
        strategy,
        tuple(targets),
        display_name or None,
        description or None,
        unlisted,
        metadata_json,
    )
