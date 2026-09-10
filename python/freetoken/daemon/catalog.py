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
class ModelProfile:
    name: str
    model: str
    args: tuple[str, ...]
    port: int | None = None
    description: str | None = None

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
        return doc


class ModelCatalog:
    def __init__(self, profiles: dict[str, ModelProfile]):
        self._profiles = profiles

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
        return cls(profiles)

    def get(self, name: str) -> ModelProfile:
        try:
            return self._profiles[name]
        except KeyError as exc:
            raise CatalogError(f"unknown model profile {name!r}") from exc

    def public(self) -> list[dict[str, Any]]:
        return [self._profiles[name].public() for name in sorted(self._profiles)]


def _profile_name(name: object) -> str:
    if not isinstance(name, str) or not _NAME.fullmatch(name):
        raise CatalogError("profile names must match [A-Za-z0-9][A-Za-z0-9._-]{0,127}")
    return name


def _profile(name: str, value: object) -> ModelProfile:
    if not isinstance(value, dict):
        raise CatalogError(f"models.{name} must be a table")
    allowed = {"model", "args", "port", "description"}
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
        if arg in {"--model", "--port", "-p"} or arg.startswith(("--model=", "--port=")):
            raise CatalogError(f"models.{name}.args must not set --model or --port")
    port = value.get("port")
    if port is not None and (not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535):
        raise CatalogError(f"models.{name}.port must be an integer from 1 through 65535")
    description = value.get("description")
    if description is not None and (not isinstance(description, str) or "\x00" in description):
        raise CatalogError(f"models.{name}.description must be a string without NUL")
    return ModelProfile(name, model, tuple(raw_args), port, description)
