"""Controlled fixture-only adapter for Freqtrade-like backtest outputs.

This module reads already-produced JSON/zip reports and normalizes them into
the internal backtest result contract. It never executes Freqtrade commands.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from bollinger_evolver.backtest_adapter import (
    NormalizedBacktestResult,
    validate_normalized_backtest_result,
)
from bollinger_evolver.freqtrade_backtest_normalizer import (
    load_freqtrade_backtest_report_from_zip_fixture,
    load_freqtrade_backtest_report_json,
    normalize_freqtrade_backtest_report,
)


def _stable_genome_hash(genome: Mapping[str, Any]) -> str:
    payload = json.dumps(dict(genome), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_report_fixture(report_path: str | Path) -> tuple[Mapping[str, Any], str]:
    path = Path(report_path)
    if path.suffix.lower() == ".zip":
        return load_freqtrade_backtest_report_from_zip_fixture(path), "zip_fixture"
    return load_freqtrade_backtest_report_json(path), "json_fixture"


class ControlledFreqtradeBacktestAdapter:
    """BacktestAdapter-compatible parser for controlled fixture reports."""

    def __init__(
        self,
        report_path: str | Path,
        *,
        strategy_name: str | None = None,
        default_leverage: float = 1.0,
        default_risk_per_trade: float = 0.01,
    ) -> None:
        self.report, self.report_kind = _load_report_fixture(report_path)
        self.strategy_name = strategy_name
        self.default_leverage = default_leverage
        self.default_risk_per_trade = default_risk_per_trade

    def run_backtest(self, genome: Mapping[str, Any]) -> NormalizedBacktestResult:
        result = normalize_freqtrade_backtest_report(
            self.report,
            strategy_name=self.strategy_name,
            default_leverage=self.default_leverage,
            default_risk_per_trade=self.default_risk_per_trade,
        )
        metadata = dict(result.metadata)
        metadata.update(
            {
                "source": "controlled_dryrun_adapter",
                "adapter": "ControlledFreqtradeBacktestAdapter",
                "report_kind": self.report_kind,
                "report_path": f"<redacted:{self.report_kind}>",
                "genome_hash": _stable_genome_hash(genome),
                "genome_id": str(genome.get("genome_id", "unknown")) if genome else "unknown",
                "execution": "fixture_only",
            }
        )
        return validate_normalized_backtest_result(
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
        )
