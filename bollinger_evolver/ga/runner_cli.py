"""CLI entrypoint for read-only mock-first Bollinger Evolver sessions."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bollinger_evolver.config_loader import BollingerConfigError, load_bollinger_config
from bollinger_evolver.evaluators import sanitize_mapping
from bollinger_evolver.ga.runner import GASessionConfig, evaluate_session_preflight, run_ga_session
from bollinger_evolver.strategy_factory import GENERATED_ROOT


FORBIDDEN_ARGS = {
    "--allow-real-backtest",
    "--live",
    "--dry-run-live",
    "--exchange",
    "--api-key",
    "--secret",
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a read-only mock-first Bollinger Evolver GA session.",
        allow_abbrev=False,
    )
    parser.add_argument("--config", required=True, help="Path to Bollinger Evolver JSON config.")
    parser.add_argument("--generations", type=int, help="Override generation count.")
    parser.add_argument("--population-size", type=int, help="Override population size.")
    parser.add_argument("--output-root", default=".runtime/bollinger_evolver/sessions")
    parser.add_argument("--seed", type=int, help="Override random seed.")
    parser.add_argument("--run-id", help="Optional session id. Defaults to a timestamped value.")
    parser.add_argument("--data-manifest", help="Optional data coverage manifest JSON path.")
    parser.add_argument("--required-pair", action="append", dest="required_pairs")
    parser.add_argument("--required-timeframe", action="append", dest="required_timeframes")
    parser.add_argument("--min-candles", type=int, default=100)
    parser.add_argument("--max-gap-ratio", type=float, default=0.02)
    parser.add_argument("--dry-run", action="store_true", help="Validate config and data QA only.")
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip session_report.json and session_report.md generation.",
    )
    parser.add_argument(
        "--disable-data-quality-gate",
        action="store_true",
        help="Skip data QA gate. This keeps mock-first mode and marks the summary explicitly.",
    )
    return parser


def _reject_forbidden_args(argv: list[str]) -> str | None:
    for arg in argv:
        option = arg.split("=", 1)[0]
        if option in FORBIDDEN_ARGS:
            return option
    return None


def _load_manifest(path_value: str | None) -> dict[str, Any] | None:
    if not path_value:
        return None
    path = Path(path_value)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("data manifest must be a JSON object")
    return sanitize_mapping(data)


def _session_id(value: str | None) -> str:
    if value:
        return value
    return "cli-session-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _required_timeframes(config: dict[str, Any], cli_values: list[str] | None) -> tuple[str, ...]:
    if cli_values:
        return tuple(cli_values)
    informative = config.get("informative_timeframes", [])
    return tuple([config["base_timeframe"], *informative])


def _required_pairs(config: dict[str, Any], cli_values: list[str] | None) -> tuple[str, ...]:
    if cli_values:
        return tuple(cli_values)
    return (config["market_filter_pair"],)


def _build_session_config(args: argparse.Namespace) -> GASessionConfig:
    config = load_bollinger_config(args.config)
    manifest = _load_manifest(args.data_manifest)
    run_id = _session_id(args.run_id)
    output_root = Path(args.output_root)
    session_root = output_root / run_id
    required_pairs = _required_pairs(config, args.required_pairs)
    required_timeframes = _required_timeframes(config, args.required_timeframes)
    return GASessionConfig(
        generations=args.generations if args.generations is not None else int(config["generations"]),
        population_size=(
            args.population_size if args.population_size is not None else int(config["population_size"])
        ),
        seed=args.seed if args.seed is not None else int(config["random_seed"]),
        run_id=run_id,
        output_root=output_root,
        strategy_output_dir=GENERATED_ROOT / "cli_sessions" / run_id,
        evaluation_mode="mock",
        allow_real_backtest=False,
        data_coverage_manifest=manifest,
        data_quality_gate_enabled=not args.disable_data_quality_gate,
        required_pairs=required_pairs,
        required_timeframes=required_timeframes,
        min_candles_per_pair_timeframe=int(args.min_candles),
        max_gap_ratio=float(args.max_gap_ratio),
        require_explicit_data_manifest=manifest is None and not args.disable_data_quality_gate,
        generate_report=not args.no_report,
    )


def _write_dry_run_summary(config: GASessionConfig, summary: dict[str, Any]) -> str:
    session_root = Path(summary["session_root"])
    session_root.mkdir(parents=True, exist_ok=True)
    summary_path = session_root / "session_summary.json"
    payload = dict(summary)
    payload["dry_run"] = True
    summary_path.write_text(json.dumps(sanitize_mapping(payload), indent=2, sort_keys=True), encoding="utf-8")
    return str(summary_path)


def _print_summary(
    *,
    status: str,
    summary_path: str,
    report_json_path: str | None = None,
    report_markdown_path: str | None = None,
    warning: str | None = None,
) -> None:
    print("Bollinger Evolver session completed")
    print("mock_evaluation: true")
    print("real_backtest: false")
    print(f"session_summary: {summary_path}")
    if report_json_path:
        print(f"session_report: {report_json_path}")
    if report_markdown_path:
        print(f"session_report_md: {report_markdown_path}")
    print(f"status: {status}")
    if warning:
        print(f"warning: {warning}")


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    forbidden = _reject_forbidden_args(raw_argv)
    if forbidden is not None:
        print(f"unsupported_live_or_secret_argument: {forbidden}", file=sys.stderr)
        return 2

    parser = _build_parser()
    try:
        args = parser.parse_args(raw_argv)
        session_config = _build_session_config(args)
    except (BollingerConfigError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except SystemExit as exc:
        return int(exc.code)

    warning = None
    if args.disable_data_quality_gate:
        warning = "dataQualityGateDisabled=true"

    if args.dry_run:
        summary = evaluate_session_preflight(session_config)
        summary["dataQualityGateDisabled"] = bool(args.disable_data_quality_gate)
        summary_path = _write_dry_run_summary(session_config, summary)
        _print_summary(status=summary["status"], summary_path=summary_path, warning=warning)
        return 0 if summary["status"] == "PASS" else 1

    result = run_ga_session(session_config)
    _print_summary(
        status=result.session_summary["status"],
        summary_path=str(result.session_summary_path),
        report_json_path=result.report_json_path,
        report_markdown_path=result.report_markdown_path,
        warning=warning,
    )
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
