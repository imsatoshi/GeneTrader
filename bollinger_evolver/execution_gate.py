"""Fail-closed execution gate for future real Freqtrade backtests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


REAL_FREQTRADE_BACKTEST_ENV = "GENETRADER_ENABLE_REAL_FREQTRADE_BACKTEST"
FORBIDDEN_COMMANDS = frozenset({"trade", "live", "hyperopt", "download-data", "download_data"})
SECRET_MARKERS = frozenset(
    {
        ".env",
        "api_key",
        "apikey",
        "credential",
        "credentials",
        "password",
        "private_key",
        "secret",
        "token",
    }
)


def _read_field(source: object, field_name: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(field_name, default)
    return getattr(source, field_name, default)


def _is_truthy_approval(approval: object | None) -> bool:
    if approval is None:
        return False
    if isinstance(approval, bool):
        return approval
    return bool(_read_field(approval, "execution_allowed", False)) and not bool(
        _read_field(approval, "rejected_by_policy", False)
    )


def _secret_hits(value: object, *, path: str = "value") -> list[str]:
    hits: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key).lower()
            next_path = f"{path}.{key}"
            if any(marker in key_text for marker in SECRET_MARKERS):
                hits.append(next_path)
            hits.extend(_secret_hits(item, path=next_path))
        return hits
    if isinstance(value, (str, bytes)):
        text = value.decode("utf-8", errors="ignore") if isinstance(value, bytes) else value
        lowered = text.lower()
        if any(marker in lowered for marker in SECRET_MARKERS):
            hits.append(path)
        return hits
    if hasattr(value, "__dict__"):
        hits.extend(_secret_hits(vars(value), path=path))
        return hits
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            hits.extend(_secret_hits(item, path=f"{path}[{index}]"))
    return hits


def _command_tokens(request: object | None) -> tuple[str, ...]:
    if request is None:
        return ()
    raw = _read_field(request, "argv", None) or _read_field(request, "command", None)
    if raw is None:
        return ()
    if isinstance(raw, str):
        return tuple(raw.split())
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
        return tuple(str(token) for token in raw)
    return (str(raw),)


def validate_real_backtest_execution_gate(
    request: object | None = None,
    *,
    env: Mapping[str, str] | None = None,
    approval: object | None = None,
) -> dict[str, object]:
    """Validate real backtest preconditions without enabling execution.

    The default is deliberately fail-closed: omitted env, approval, dry-run flag,
    or output root all produce ``ok=False``.
    """

    active_env = dict(env or {})
    errors: list[str] = []
    warnings: list[str] = []

    if active_env.get(REAL_FREQTRADE_BACKTEST_ENV) != "1":
        errors.append("real_freqtrade_backtest_env_not_enabled")
    if any(_secret_hits({key: value}, path="env") for key, value in active_env.items()):
        errors.append("secret_like_env_not_allowed")
    if not _is_truthy_approval(approval or _read_field(request, "approval", None)):
        errors.append("explicit_approval_required")
    if _read_field(request, "dry_run_only", False) is not True:
        errors.append("dry_run_only_required")

    output_root = _read_field(request, "output_root", None)
    if not isinstance(output_root, str) or not output_root.strip():
        errors.append("allowed_output_root_required")
    elif _secret_hits(output_root, path="output_root"):
        errors.append("secret_like_output_root_not_allowed")

    tokens = tuple(token.lower() for token in _command_tokens(request))
    if any(token in FORBIDDEN_COMMANDS for token in tokens):
        errors.append("forbidden_freqtrade_command")
    if _secret_hits(request, path="request"):
        errors.append("secret_like_request_field_not_allowed")

    return {
        "ok": not errors,
        "errors": sorted(set(errors)),
        "warnings": warnings,
    }
