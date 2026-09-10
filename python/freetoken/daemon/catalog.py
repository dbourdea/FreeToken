"""Named, validated FreeToken engine profiles for ``ft daemon``.

This intentionally borrows the useful *catalog* idea from llama-swap without
accepting its shell-command model.  A profile describes only FreeToken's native
``--model``, ``--port`` and argument-vector contract, so loading a catalog never
creates a shell injection path and the daemon remains torch-free.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

try:  # tomllib joined the stdlib in Python 3.11; FreeToken supports 3.10 too.
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised in the Python 3.10 package build
    import tomli as tomllib


_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


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

    def request(self) -> dict[str, Any]:
        body: dict[str, Any] = {"model": self.model, "args": list(self.args)}
        if self.port is not None:
            body["port"] = self.port
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
        return doc


class ModelCatalog:
    def __init__(self, profiles: dict[str, ModelProfile], settings: RouterSettings | None = None,
                 *, path: str | None = None):
        self._profiles = profiles
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
            profiles[_profile_name(name)] = _profile(_profile_name(name), value)
        return cls(profiles, _router_settings(raw.get("router", {}), profiles), path=path)

    def get(self, name: str) -> ModelProfile:
        try:
            return self._profiles[name]
        except KeyError as exc:
            raise CatalogError(f"unknown model profile {name!r}") from exc

    def public(self) -> list[dict[str, Any]]:
        return [self._profiles[name].public() for name in sorted(self._profiles)]

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
    allowed = {"api_keys", "default_ttl_s", "unload_timeout_s", "upstream_timeout_s", "scheduler", "groups"}
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
    raw_groups = value.get("groups", {})
    if not isinstance(raw_groups, dict):
        raise CatalogError("router.groups must be a table")
    groups: list[RoutingGroup] = []
    claimed: set[str] = set()
    for raw_name, raw_group in raw_groups.items():
        name = _profile_name(raw_name)
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
        if flags["persistent"] and flags["swap"]:
            raise CatalogError(f"router.groups.{name}: persistent groups must set swap = false")
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
    )


def _profile_name(name: object) -> str:
    if not isinstance(name, str) or not _NAME.fullmatch(name):
        raise CatalogError("profile names must match [A-Za-z0-9][A-Za-z0-9._-]{0,127}")
    return name


def _profile(name: str, value: object) -> ModelProfile:
    if not isinstance(value, dict):
        raise CatalogError(f"models.{name} must be a table")
    allowed = {"model", "args", "port", "description", "ready_timeout_s", "ttl_s", "unload_timeout_s", "priority", "group"}
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
    if port is not None and (not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535):
        raise CatalogError(f"models.{name}.port must be an integer from 1 through 65535")
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
        group = _profile_name(group)
    return ModelProfile(name, model, tuple(raw_args), port, description, ready_timeout_s,
                        ttl_s, unload_timeout_s, priority, group)
