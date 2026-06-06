"""CLI for mock-first GA session artifact generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from bollinger_evolver.artifact_export import build_generation_artifact
from bollinger_evolver.backtest_adapter import AdapterBackedMockEvaluator, MockBacktestAdapter
from bollinger_evolver.ga_execution import GAExecutionConfig, run_ga_execution
from bollinger_evolver.session_summary import build_ga_session_summary


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def validate_mock_output_dir(output: str | Path) -> Path:
    """Validate an explicit mock artifact output directory."""

    if output is None or not str(output).strip():
        raise ValueError("output_dir_required")
    destination = Path(output).resolve()
    root = _repo_root().resolve()
    disallowed_roots = (
        root,
        root / ".runtime",
        root / "user_data" / "data",
    )
    if destination == root:
        raise ValueError("output_dir_must_not_be_repo_root")
    if any(destination == item or _is_relative_to(destination, item) for item in disallowed_roots[1:]):
        raise ValueError("output_dir_disallowed")
    return destination


def run_mock_command(args: argparse.Namespace) -> dict[str, object]:
    output_dir = validate_mock_output_dir(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    config = GAExecutionConfig(
        population_size=int(args.population_size),
        generations=int(args.generations),
        seed=int(args.seed),
    )
    evaluator = AdapterBackedMockEvaluator(
        MockBacktestAdapter(
            seed=int(args.seed),
            trade_count=int(args.trade_count),
            pair=str(args.pair),
            timeframe=str(args.timeframe),
        )
    )
    result = run_ga_execution(config, evaluator=evaluator)
    run_id = str(args.run_id or f"mock-ga-seed-{args.seed}")
    summary = build_ga_session_summary(result, top_n=int(args.top_n), run_id=run_id)
    summary_path = output_dir / "session_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    generation_paths: list[Path] = []
    for generation in result.generations:
        artifact = build_generation_artifact(
            result,
            generation=int(generation.generation),
            top_n=int(args.top_n),
            run_id=run_id,
        )
        path = output_dir / f"generation_{int(generation.generation):03d}.json"
        path.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
        generation_paths.append(path)

    return {
        "output_dir": str(output_dir),
        "session_summary": str(summary_path),
        "generation_artifacts": [str(path) for path in generation_paths],
        "adapter": "MockBacktestAdapter",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m bollinger_evolver.ga_cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_mock = subparsers.add_parser("run-mock")
    run_mock.add_argument("--generations", type=int, default=3)
    run_mock.add_argument("--population-size", type=int, default=12)
    run_mock.add_argument("--seed", type=int, default=0)
    run_mock.add_argument("--output", required=True)
    run_mock.add_argument("--top-n", type=int, default=10)
    run_mock.add_argument("--trade-count", type=int, default=100)
    run_mock.add_argument("--pair", default="BTC/USDT")
    run_mock.add_argument("--timeframe", default="1h")
    run_mock.add_argument("--run-id", default=None)
    run_mock.set_defaults(handler=run_mock_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.handler(args)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
