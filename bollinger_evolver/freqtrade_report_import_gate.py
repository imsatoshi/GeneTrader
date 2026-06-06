"""Safety gate for importing externally produced Freqtrade-like reports.

This module validates an explicitly provided JSON/zip report path, records a
redacted provenance manifest, and normalizes the report through the controlled
dry-run adapter. It does not scan result directories or execute commands.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from bollinger_evolver.backtest_adapter import NormalizedBacktestResult, validate_normalized_backtest_result
from bollinger_evolver.freqtrade_dryrun_adapter import ControlledFreqtradeBacktestAdapter


SUPPORTED_REPORT_SUFFIXES = frozenset({".json", ".zip"})


@dataclass(frozen=True)
class ReportImportRequest:
    report_path: Path
    strategy_name: str | None = None
    allowed_roots: tuple[Path, ...] = ()
    default_leverage: float = 1.0
    default_risk_per_trade: float = 0.01
    genome: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ReportImportManifest:
    source_type: str
    redacted_report_path: str
    file_extension: str
    file_size_bytes: int
    strategy_name: str | None
    sha256: str
    execution_mode: str
    safety_flags: Mapping[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def validate_report_import_path(
    report_path: Path,
    *,
    allowed_roots: tuple[Path, ...],
) -> Path:
    """Validate that one explicit report file is inside an allowed root."""

    if not allowed_roots:
        raise ValueError("report_import_allowed_roots_required")
    if any(character in str(report_path) for character in "*?[]"):
        raise ValueError("report_import_glob_not_allowed")

    resolved_path = Path(report_path).resolve()
    if not resolved_path.exists():
        raise FileNotFoundError("report_import_path_not_found")
    if not resolved_path.is_file():
        raise ValueError("report_import_path_must_be_file")
    if resolved_path.suffix.lower() not in SUPPORTED_REPORT_SUFFIXES:
        raise ValueError("report_import_suffix_not_supported")

    resolved_roots = tuple(Path(root).resolve() for root in allowed_roots)
    if not any(_is_relative_to(resolved_path, root) for root in resolved_roots):
        raise ValueError("report_import_path_outside_allowed_roots")
    return resolved_path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_report_import_manifest(
    report_path: Path,
    *,
    strategy_name: str | None = None,
) -> ReportImportManifest:
    """Build a JSON-safe provenance manifest with redacted path details."""

    resolved_path = Path(report_path).resolve()
    suffix = resolved_path.suffix.lower()
    return ReportImportManifest(
        source_type="freqtrade_report_import",
        redacted_report_path=f"<redacted:{resolved_path.name}>",
        file_extension=suffix,
        file_size_bytes=resolved_path.stat().st_size,
        strategy_name=strategy_name,
        sha256=_sha256_file(resolved_path),
        execution_mode="no_execution_import_only",
        safety_flags={
            "freqtrade_executed": False,
            "subprocess_used": False,
            "exchange_api_used": False,
            "secrets_loaded": False,
        },
    )


def import_controlled_freqtrade_report(
    request: ReportImportRequest,
) -> tuple[NormalizedBacktestResult, ReportImportManifest]:
    """Import one external report through the explicit no-execution gate."""

    resolved_path = validate_report_import_path(request.report_path, allowed_roots=request.allowed_roots)
    manifest = build_report_import_manifest(resolved_path, strategy_name=request.strategy_name)
    adapter = ControlledFreqtradeBacktestAdapter(
        resolved_path,
        strategy_name=request.strategy_name,
        default_leverage=request.default_leverage,
        default_risk_per_trade=request.default_risk_per_trade,
    )
    result = adapter.run_backtest(request.genome or {"genome_id": "external-report-import"})
    metadata = dict(result.metadata)
    metadata.update(
        {
            "source": "external_freqtrade_report_import",
            "adapter": "ControlledFreqtradeBacktestAdapter",
            "execution_mode": "no_execution_import_only",
            "report_manifest": manifest.to_dict(),
        }
    )
    return (
        validate_normalized_backtest_result(
            NormalizedBacktestResult(
                profit=result.profit,
                sharpe=result.sharpe,
                win_rate=result.win_rate,
                max_drawdown=result.max_drawdown,
                total_trades=result.total_trades,
                max_consecutive_losses=result.max_consecutive_losses,
                leverage=result.leverage,
                risk_per_trade=result.risk_per_trade,
                metadata=metadata,
            )
        ),
        manifest,
    )
