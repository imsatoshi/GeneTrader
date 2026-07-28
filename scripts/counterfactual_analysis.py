#!/usr/bin/env python3
"""Did re-optimizing actually beat leaving the strategy alone?

The adaptive stack assumes that re-fitting parameters when performance drops
recovers an edge. In financial time series the opposite is also plausible: the
drop is noise, and re-fitting chases it, adding turnover and overfitting. That
assumption has never been tested here, and it decides whether ~6,800 lines of
adaptive code are worth maintaining.

This reads the performance database written by the live monitor and compares
the realised outcome after each deployment against the incumbent's trailing
performance. It uses only recorded history: it places no trades, runs no
backtests, and touches no strategy files.

Usage:
    python scripts/counterfactual_analysis.py --strategy GeneTrader
    python scripts/counterfactual_analysis.py --strategy GeneTrader --window-days 14 --json
"""

import argparse
import json
import os
import statistics
import sys
from dataclasses import dataclass, asdict
from datetime import timedelta
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import Settings  # noqa: E402
from deployment.version_control import StrategyVersionControl  # noqa: E402
from monitoring.performance_db import PerformanceDB  # noqa: E402
from utils.time_utils import to_utc  # noqa: E402


@dataclass
class SwitchOutcome:
    """One deployment, and what happened on either side of it."""
    deployed_at: str
    from_version: Optional[str]
    to_version: str
    before_profit_pct: Optional[float]
    after_profit_pct: Optional[float]
    before_drawdown: Optional[float]
    after_drawdown: Optional[float]
    before_samples: int
    after_samples: int

    @property
    def delta(self) -> Optional[float]:
        if self.before_profit_pct is None or self.after_profit_pct is None:
            return None
        return self.after_profit_pct - self.before_profit_pct

    @property
    def comparable(self) -> bool:
        return self.delta is not None


def _mean(values: List[float]) -> Optional[float]:
    return statistics.mean(values) if values else None


def _window_metrics(db: PerformanceDB, strategy: str, start, end) -> Dict[str, Any]:
    """Average profit and drawdown over [start, end)."""
    snapshots = db.get_snapshots(strategy_name=strategy, since=start, until=end, limit=10000)
    return {
        'profit': _mean([s.total_profit_pct for s in snapshots]),
        'drawdown': _mean([s.max_drawdown for s in snapshots]),
        'samples': len(snapshots),
    }


def analyse(settings: Settings, strategy: str, window_days: int,
            versions_dir: str) -> Dict[str, Any]:
    db = PerformanceDB(getattr(settings, 'performance_db_path', 'data/performance.db'))
    vc = StrategyVersionControl(versions_dir)

    history = vc.get_deployment_history(strategy)
    if not history:
        return {'strategy': strategy, 'error': 'no deployment history recorded'}

    # get_deployment_history returns newest first; walk forward in time.
    ordered = sorted(history, key=lambda h: h['deployed_at'])
    window = timedelta(days=window_days)

    outcomes: List[SwitchOutcome] = []
    for index, event in enumerate(ordered):
        deployed_at = to_utc(
            __import__('datetime').datetime.fromisoformat(event['deployed_at'])
        )
        before = _window_metrics(db, strategy, deployed_at - window, deployed_at)
        after = _window_metrics(db, strategy, deployed_at, deployed_at + window)

        outcomes.append(SwitchOutcome(
            deployed_at=event['deployed_at'],
            from_version=ordered[index - 1]['version_id'] if index else None,
            to_version=event['version_id'],
            before_profit_pct=before['profit'],
            after_profit_pct=after['profit'],
            before_drawdown=before['drawdown'],
            after_drawdown=after['drawdown'],
            before_samples=before['samples'],
            after_samples=after['samples'],
        ))

    comparable = [o for o in outcomes if o.comparable]
    deltas = [o.delta for o in comparable]
    improved = sum(1 for d in deltas if d > 0)

    verdict = 'insufficient data'
    if len(deltas) >= 5:
        mean_delta = statistics.mean(deltas)
        if mean_delta > 0 and improved > len(deltas) / 2:
            verdict = 'reoptimization appears to help'
        elif mean_delta < 0:
            verdict = 'reoptimization appears to hurt: consider disabling auto-reoptimization'
        else:
            verdict = 'no measurable effect: the adaptive loop is not earning its complexity'

    return {
        'strategy': strategy,
        'window_days': window_days,
        'deployments_found': len(outcomes),
        'comparable_deployments': len(comparable),
        'improved_count': improved,
        'mean_profit_delta': statistics.mean(deltas) if deltas else None,
        'median_profit_delta': statistics.median(deltas) if deltas else None,
        'verdict': verdict,
        'caveat': (
            'Each window mixes strategy change with market regime change; '
            'this measures association, not causation. Treat fewer than ~10 '
            'comparable deployments as directional only.'
        ),
        'outcomes': [asdict(o) for o in outcomes],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Compare post-deployment performance against the incumbent'
    )
    parser.add_argument('--config', default='ga.json', help='Config file (default: ga.json)')
    parser.add_argument('--strategy', required=True, help='Strategy name')
    parser.add_argument('--window-days', type=int, default=7,
                        help='Comparison window on each side of a deployment (default: 7)')
    parser.add_argument('--versions-dir', default='data/strategy_versions',
                        help='Strategy version store (default: data/strategy_versions)')
    parser.add_argument('--json', action='store_true', help='Emit JSON instead of a report')
    args = parser.parse_args()

    try:
        settings = Settings(args.config)
    except Exception as e:
        print(f"Failed to load config: {e}", file=sys.stderr)
        return 1

    result = analyse(settings, args.strategy, args.window_days, args.versions_dir)

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    if 'error' in result:
        print(f"{result['strategy']}: {result['error']}")
        return 1

    print(f"Strategy:                {result['strategy']}")
    print(f"Comparison window:       ±{result['window_days']} days")
    print(f"Deployments found:       {result['deployments_found']}")
    print(f"With data on both sides: {result['comparable_deployments']}")
    print(f"Improved after switch:   {result['improved_count']}")
    if result['mean_profit_delta'] is not None:
        print(f"Mean profit delta:       {result['mean_profit_delta']:+.4f}")
        print(f"Median profit delta:     {result['median_profit_delta']:+.4f}")
    print(f"\nVerdict: {result['verdict']}")
    print(f"\nCaveat: {result['caveat']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
