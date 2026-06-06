"""Plan-only Freqtrade backtest command manifest builder.

This module builds a future execution plan as JSON-safe metadata. It does not
execute commands, load external trading libraries, scan directories, or create
backtest output.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any


SAFE_TIMEFRAMES = frozenset({"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "1d"})
SAFE_EXPORT_VALUES = frozenset({"none", "trades", "signals"})
SAFE_CACHE_VALUES = frozenset({"none", "day", "week", "month"})
PATH_FIELDS = (
    "config_path",
    "userdir_path",
    "datadir_path",
    "strategy_path",
    "backtest_directory",
)
SHELL_META_CHARS = frozenset(";|&<>`$\\")
SECRET_PATH_MARKERS = frozenset(
    {
        ".env",
        "api_key",
        "apikey",
        "secret",
        "token",
        "password",
        "private_key",
    }
)
SECRET_METADATA_KEYS = SECRET_PATH_MARKERS


@dataclass(frozen=True)
class BacktestCommandPlan:
    strategy_name: str
    config_path: Path | None = None
    userdir_path: Path | None = None
    datadir_path: Path | None = None
    strategy_path: Path | None = None
    backtest_directory: Path | None = None
    timeframe: str | None = None
    timerange: str | None = None
    pairs: tuple[str, ...] = ()
    export: str = "trades"
    dry_run_wallet: float | None = None
    stake_amount: float | None = None
    fee: float | None = None
    max_open_trades: int | None = None
    enable_protections: bool = False
    timeframe_detail: str | None = None
    cache: str | None = "none"
    notes: str | None = None
    allowed_roots: tuple[Path, ...] = ()
    extra_metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class BacktestCommandManifest:
    source_type: str
    execution_mode: str
    argv: tuple[str, ...]
    redacted_argv: tuple[str, ...]
    strategy_name: str
    redacted_paths: Mapping[str, str]
    parameter_summary: Mapping[str, object]
    safety_flags: Mapping[str, bool]
    warnings: tuple[str, ...] = ()


def _has_shell_meta(value: str) -> bool:
    return any(character in value for character in SHELL_META_CHARS)


def _has_glob(value: str) -> bool:
    return any(character in value for character in "*?[]")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return redact_path(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, set):
        return sorted(_json_safe(item) for item in value)
    return value


def _redacted_metadata(metadata: Mapping[str, object]) -> dict[str, object]:
    redacted: dict[str, object] = {}
    for key, value in metadata.items():
        key_text = str(key)
        if any(marker in key_text.lower() for marker in SECRET_METADATA_KEYS):
            redacted[key_text] = "<redacted>"
        else:
            redacted[key_text] = _json_safe(value)
    return redacted


def _validate_simple_token(value: str, *, field_name: str, allow_slash: bool = False) -> None:
    if not value or value.strip() != value:
        raise ValueError(f"{field_name}_invalid")
    if any(character.isspace() for character in value):
        raise ValueError(f"{field_name}_must_not_contain_whitespace")
    if _has_shell_meta(value):
        raise ValueError(f"{field_name}_must_not_contain_shell_meta")
    allowed_extra = "/_:-." if allow_slash else "_:.-"
    if not all(character.isalnum() or character in allowed_extra for character in value):
        raise ValueError(f"{field_name}_contains_unsupported_character")


def _validate_positive_number(value: float | None, *, field_name: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{field_name}_must_be_finite_number")
    if float(value) <= 0.0:
        raise ValueError(f"{field_name}_must_be_positive")


def _validate_non_negative_number(value: float | None, *, field_name: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{field_name}_must_be_finite_number")
    if float(value) < 0.0:
        raise ValueError(f"{field_name}_must_be_non_negative")


def _validate_path_is_allowed(path: Path, allowed_roots: tuple[Path, ...], *, field_name: str) -> Path:
    path_text = str(path)
    if _has_glob(path_text):
        raise ValueError(f"{field_name}_glob_not_allowed")
    lowered_name = path.name.lower()
    if any(marker in lowered_name for marker in SECRET_PATH_MARKERS):
        raise ValueError(f"{field_name}_secret_like_path_not_allowed")

    resolved = path.resolve()
    if not any(_is_relative_to(resolved, root) for root in allowed_roots):
        raise ValueError(f"{field_name}_outside_allowed_roots")
    return resolved


def validate_command_plan_paths(plan: BacktestCommandPlan) -> Mapping[str, Path]:
    """Validate plan paths without scanning directories or creating outputs."""

    if not plan.allowed_roots:
        raise ValueError("allowed_roots_required")
    resolved_roots = tuple(Path(root).resolve() for root in plan.allowed_roots)
    resolved: dict[str, Path] = {}

    if plan.config_path is not None:
        path = _validate_path_is_allowed(plan.config_path, resolved_roots, field_name="config_path")
        if path.suffix.lower() != ".json" or not path.is_file():
            raise ValueError("config_path_must_be_json_file")
        resolved["config_path"] = path

    for field_name in ("userdir_path", "datadir_path"):
        raw_path = getattr(plan, field_name)
        if raw_path is None:
            continue
        path = _validate_path_is_allowed(raw_path, resolved_roots, field_name=field_name)
        if not path.is_dir():
            raise ValueError(f"{field_name}_must_be_directory")
        resolved[field_name] = path

    if plan.strategy_path is not None:
        path = _validate_path_is_allowed(plan.strategy_path, resolved_roots, field_name="strategy_path")
        if not (path.is_dir() or (path.is_file() and path.suffix.lower() == ".py")):
            raise ValueError("strategy_path_must_be_directory_or_py_file")
        resolved["strategy_path"] = path

    if plan.backtest_directory is not None:
        path_text = str(plan.backtest_directory)
        if _has_glob(path_text):
            raise ValueError("backtest_directory_glob_not_allowed")
        lowered_name = plan.backtest_directory.name.lower()
        if any(marker in lowered_name for marker in SECRET_PATH_MARKERS):
            raise ValueError("backtest_directory_secret_like_path_not_allowed")
        path = plan.backtest_directory.resolve()
        parent = path.parent
        if not any(_is_relative_to(path, root) or _is_relative_to(parent, root) for root in resolved_roots):
            raise ValueError("backtest_directory_outside_allowed_roots")
        if path.exists() and not path.is_dir():
            raise ValueError("backtest_directory_must_be_directory_or_future_directory")
        resolved["backtest_directory"] = path

    return resolved


def validate_backtest_plan_parameters(plan: BacktestCommandPlan) -> None:
    """Validate the safe subset of Freqtrade backtesting parameters."""

    _validate_simple_token(plan.strategy_name, field_name="strategy_name")
    if plan.timeframe is not None:
        _validate_simple_token(plan.timeframe, field_name="timeframe")
        if plan.timeframe not in SAFE_TIMEFRAMES:
            raise ValueError("timeframe_not_allowed")
    if plan.timeframe_detail is not None:
        _validate_simple_token(plan.timeframe_detail, field_name="timeframe_detail")
        if plan.timeframe_detail not in SAFE_TIMEFRAMES:
            raise ValueError("timeframe_detail_not_allowed")
    if plan.timerange is not None:
        _validate_simple_token(plan.timerange, field_name="timerange")
    if plan.export not in SAFE_EXPORT_VALUES:
        raise ValueError("export_not_allowed")
    if plan.cache is not None and plan.cache not in SAFE_CACHE_VALUES:
        raise ValueError("cache_not_allowed")
    for pair in plan.pairs:
        _validate_simple_token(pair, field_name="pair", allow_slash=True)
        if "/" not in pair:
            raise ValueError("pair_must_contain_separator")
    _validate_positive_number(plan.dry_run_wallet, field_name="dry_run_wallet")
    _validate_positive_number(plan.stake_amount, field_name="stake_amount")
    _validate_non_negative_number(plan.fee, field_name="fee")
    if plan.max_open_trades is not None:
        if (
            isinstance(plan.max_open_trades, bool)
            or not isinstance(plan.max_open_trades, int)
            or plan.max_open_trades <= 0
        ):
            raise ValueError("max_open_trades_must_be_positive_int")
    if plan.notes is not None and _has_shell_meta(plan.notes):
        raise ValueError("notes_must_not_contain_shell_meta")


def redact_path(path: Path) -> str:
    return f"<redacted:{Path(path).name}>"


def _append_path_arg(
    argv: list[str],
    redacted_argv: list[str],
    redacted_paths: dict[str, str],
    *,
    option: str,
    field_name: str,
    resolved_paths: Mapping[str, Path],
) -> None:
    if field_name not in resolved_paths:
        return
    redacted = redact_path(resolved_paths[field_name])
    argv.extend([option, redacted])
    redacted_argv.extend([option, redacted])
    redacted_paths[field_name] = redacted


def _safety_flags() -> dict[str, bool]:
    return {
        "freqtrade_executed": False,
        "subprocess_used": False,
        "shell_used": False,
        "exchange_api_used": False,
        "network_used": False,
        "secrets_loaded": False,
        "real_backtest_result_created": False,
    }


def build_freqtrade_backtest_command_manifest(
    plan: BacktestCommandPlan,
) -> BacktestCommandManifest:
    """Build a redacted argv manifest for future manual execution review."""

    validate_backtest_plan_parameters(plan)
    resolved_paths = validate_command_plan_paths(plan)
    argv = ["freqtrade", "backtesting", "--strategy", plan.strategy_name]
    redacted_argv = list(argv)
    redacted_paths: dict[str, str] = {}

    _append_path_arg(
        argv,
        redacted_argv,
        redacted_paths,
        option="--config",
        field_name="config_path",
        resolved_paths=resolved_paths,
    )
    _append_path_arg(
        argv,
        redacted_argv,
        redacted_paths,
        option="--userdir",
        field_name="userdir_path",
        resolved_paths=resolved_paths,
    )
    _append_path_arg(
        argv,
        redacted_argv,
        redacted_paths,
        option="--datadir",
        field_name="datadir_path",
        resolved_paths=resolved_paths,
    )
    _append_path_arg(
        argv,
        redacted_argv,
        redacted_paths,
        option="--strategy-path",
        field_name="strategy_path",
        resolved_paths=resolved_paths,
    )
    _append_path_arg(
        argv,
        redacted_argv,
        redacted_paths,
        option="--backtest-directory",
        field_name="backtest_directory",
        resolved_paths=resolved_paths,
    )

    scalar_options: list[tuple[str, Any]] = [
        ("--timeframe", plan.timeframe),
        ("--timerange", plan.timerange),
        ("--export", plan.export),
        ("--dry-run-wallet", plan.dry_run_wallet),
        ("--stake-amount", plan.stake_amount),
        ("--fee", plan.fee),
        ("--max-open-trades", plan.max_open_trades),
        ("--timeframe-detail", plan.timeframe_detail),
        ("--cache", plan.cache),
    ]
    for option, value in scalar_options:
        if value is None:
            continue
        argv.extend([option, str(value)])
        redacted_argv.extend([option, str(value)])
    if plan.pairs:
        argv.append("--pairs")
        redacted_argv.append("--pairs")
        argv.extend(plan.pairs)
        redacted_argv.extend(plan.pairs)
    if plan.enable_protections:
        argv.append("--enable-protections")
        redacted_argv.append("--enable-protections")

    parameter_summary = {
        "strategy_name": plan.strategy_name,
        "timeframe": plan.timeframe,
        "timerange": plan.timerange,
        "pairs": list(plan.pairs),
        "export": plan.export,
        "dry_run_wallet": plan.dry_run_wallet,
        "stake_amount": plan.stake_amount,
        "fee": plan.fee,
        "max_open_trades": plan.max_open_trades,
        "enable_protections": plan.enable_protections,
        "timeframe_detail": plan.timeframe_detail,
        "cache": plan.cache,
        "notes_present": plan.notes is not None,
        "extra_metadata": _redacted_metadata(plan.extra_metadata),
    }
    return BacktestCommandManifest(
        source_type="freqtrade_backtest_command_manifest",
        execution_mode="plan_only_no_execution",
        argv=tuple(argv),
        redacted_argv=tuple(redacted_argv),
        strategy_name=plan.strategy_name,
        redacted_paths=redacted_paths,
        parameter_summary=parameter_summary,
        safety_flags=_safety_flags(),
        warnings=("plan_only_not_executed",),
    )


def _stable_genome_hash(genome: Mapping[str, object]) -> str:
    payload = json.dumps(_json_safe(dict(genome)), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_backtest_plan_from_genome(
    genome: Mapping[str, object],
    *,
    strategy_name: str,
    allowed_roots: tuple[Path, ...],
    base_plan: BacktestCommandPlan | None = None,
) -> BacktestCommandPlan:
    """Build a command plan bridge without writing genome data to config files."""

    redacted_keys = sorted(
        str(key) for key in genome if any(marker in str(key).lower() for marker in SECRET_METADATA_KEYS)
    )
    metadata = {
        **dict(base_plan.extra_metadata if base_plan else {}),
        "genome_received": True,
        "genome_param_keys": sorted(str(key) for key in genome),
        "genome_hash": _stable_genome_hash(genome),
        "redacted_genome_keys": redacted_keys,
    }
    if base_plan is None:
        return BacktestCommandPlan(
            strategy_name=strategy_name,
            allowed_roots=allowed_roots,
            extra_metadata=metadata,
        )
    return replace(
        base_plan,
        strategy_name=strategy_name,
        allowed_roots=allowed_roots,
        extra_metadata=metadata,
    )


def command_manifest_to_json_safe_dict(
    manifest: BacktestCommandManifest,
) -> dict[str, object]:
    data = asdict(manifest)
    json.dumps(data, sort_keys=True)
    return data


def write_backtest_command_manifest(
    manifest: BacktestCommandManifest,
    output_path: Path,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(command_manifest_to_json_safe_dict(manifest), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output
