"""Externalized API configuration (ADR-001; REQ-SEC-002, REQ-QUA-002).

Configuration is read from explicit ``CONTENTGUARD_*`` values.  This module never
loads dotenv files and never stores plaintext bearer tokens: the configured token map
is keyed by SHA-256 digest.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Literal


class ConfigurationError(ValueError):
    """Raised when trusted service configuration is invalid or unknown."""


@dataclass(frozen=True)
class ActorConfig:
    """Server-side identity resolved from a bearer-token digest (REQ-SEC-003)."""

    actor_id: str
    actor_type: Literal["submitter", "moderator"]
    scopes: frozenset[str]

    def __post_init__(self) -> None:
        if not self.actor_id.strip():
            raise ConfigurationError("actor_id must be non-empty")
        if self.actor_type not in {"submitter", "moderator"}:
            raise ConfigurationError("actor_type must be submitter or moderator")


@dataclass(frozen=True)
class FeatureFlags:
    """Closed MVP flag allowlist (REQ-FUN-007, REQ-INV-001)."""

    reconsideration_enabled: bool = False

    def __post_init__(self) -> None:
        if type(self.reconsideration_enabled) is not bool:
            raise ConfigurationError("analysis.reconsideration_enabled must be a bool")

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> FeatureFlags:
        """Reject unknown/non-boolean flags rather than accepting a runtime bypass."""

        allowed = {"analysis.reconsideration_enabled"}
        unknown = set(raw) - allowed
        if unknown:
            raise ConfigurationError(f"unknown feature flags: {sorted(unknown)}")
        value = raw.get("analysis.reconsideration_enabled", False)
        if type(value) is not bool:
            raise ConfigurationError("analysis.reconsideration_enabled must be a bool")
        return cls(reconsideration_enabled=value)

    def as_dict(self) -> dict[str, bool]:
        """Return the canonical durable representation of effective flags."""

        return {"analysis.reconsideration_enabled": self.reconsideration_enabled}


@dataclass(frozen=True)
class ApiConfig:
    """Validated runtime settings for the S2 service boundary (REQ-QUA-002)."""

    database_path: Path
    api_tokens: Mapping[str, ActorConfig]
    intake_max_bytes: int = 16_384
    lease_seconds: int = 30
    recovery_interval_seconds: int = 5
    max_attempts: int = 5
    start_recovery_worker: bool = True
    feature_flags: FeatureFlags = field(default_factory=FeatureFlags)

    def __post_init__(self) -> None:
        object.__setattr__(self, "database_path", Path(self.database_path))
        object.__setattr__(self, "api_tokens", MappingProxyType(dict(self.api_tokens)))
        for name in (
            "intake_max_bytes",
            "lease_seconds",
            "recovery_interval_seconds",
            "max_attempts",
        ):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ConfigurationError(f"{name} must be a positive integer")
        for digest in self.api_tokens:
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise ConfigurationError("API token keys must be lowercase SHA-256 digests")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> ApiConfig:
        """Load the approved ``CONTENTGUARD_*`` keys without reading secret files."""

        env = os.environ if environ is None else environ
        try:
            raw_actors = json.loads(env.get("CONTENTGUARD_API_TOKENS", "{}"))
            raw_flags = json.loads(env.get("CONTENTGUARD_FEATURE_FLAGS", "{}"))
        except json.JSONDecodeError as exc:
            raise ConfigurationError("JSON configuration is invalid") from exc
        if not isinstance(raw_actors, dict) or not isinstance(raw_flags, dict):
            raise ConfigurationError("token and flag configuration must be JSON objects")

        actors: dict[str, ActorConfig] = {}
        for digest, raw_actor in raw_actors.items():
            if not isinstance(digest, str) or not isinstance(raw_actor, dict):
                raise ConfigurationError("token entries must map digests to actor objects")
            scopes = raw_actor.get("scopes", [])
            if not isinstance(scopes, list) or not all(isinstance(v, str) for v in scopes):
                raise ConfigurationError("actor scopes must be a list of strings")
            try:
                actors[digest] = ActorConfig(
                    actor_id=str(raw_actor["actor_id"]),
                    actor_type=raw_actor["actor_type"],  # type: ignore[arg-type]
                    scopes=frozenset(scopes),
                )
            except KeyError as exc:
                raise ConfigurationError("actor_id and actor_type are required") from exc

        def positive_int(key: str, default: int) -> int:
            try:
                value = int(env.get(key, str(default)))
            except ValueError as exc:
                raise ConfigurationError(f"{key} must be an integer") from exc
            if value <= 0:
                raise ConfigurationError(f"{key} must be positive")
            return value

        return cls(
            database_path=Path(env.get("CONTENTGUARD_DATABASE_PATH", "contentguard.sqlite3")),
            api_tokens=actors,
            intake_max_bytes=positive_int("CONTENTGUARD_INTAKE_MAX_BYTES", 16_384),
            lease_seconds=positive_int("CONTENTGUARD_LEASE_SECONDS", 30),
            recovery_interval_seconds=positive_int(
                "CONTENTGUARD_RECOVERY_INTERVAL_SECONDS", 5
            ),
            max_attempts=positive_int("CONTENTGUARD_MAX_ATTEMPTS", 5),
            feature_flags=FeatureFlags.from_mapping(raw_flags),
        )


__all__ = [
    "ActorConfig",
    "ApiConfig",
    "ConfigurationError",
    "FeatureFlags",
]
