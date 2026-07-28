#!/usr/bin/env python3
"""Report the GA's own selection bar from fitness logs.

Answers "how good would the best of N candidates have looked anyway?" using the
dispersion of fitness this search actually produced, so the bar is measured
rather than assumed.

Usage:
    python scripts/selection_bar.py
    python scripts/selection_bar.py --log daily_results/20241223/gen10/fitness_info.txt
    python scripts/selection_bar.py --per-generation --json
"""

import argparse
import glob
import json
import os
import re
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from strategy.selection_bar import compute, is_degenerate, scoreable  # noqa: E402

FIELDS = {
    'fitness': 'Final Fitness',
    'sharpe': 'Sharpe Ratio',
    'profit_factor': 'Profit Factor',
    'win_rate': 'Win Rate',
    'max_drawdown': 'Max Drawdown',
    'generation': 'Generation',
}
PATTERNS = {key: re.compile(re.escape(label) + r":\s*(-?[\d.]+)")
            for key, label in FIELDS.items()}
DEFAULT_GLOBS = ('daily_results/**/fitness_info.txt', 'logs/fitness_log.txt')


def parse_log(path: str) -> List[Dict[str, float]]:
    records = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            if FIELDS['fitness'] not in line:
                continue
            record = {}
            for key, pattern in PATTERNS.items():
                m = pattern.search(line)
                if m:
                    record[key] = float(m.group(1))
            if 'fitness' in record:
                records.append(record)
    return records


def collect(paths: List[str]) -> List[Dict[str, float]]:
    records = []
    for path in paths:
        records.extend(parse_log(path))
    return records


def resolve_paths(explicit: List[str]) -> List[str]:
    if explicit:
        return explicit
    for pattern in DEFAULT_GLOBS:
        found = sorted(glob.glob(pattern, recursive=True))
        if found:
            return found
    return []


def report(result, label: str = '') -> None:
    prefix = f"{label}  " if label else ''
    print(f"{prefix}candidates evaluated : {result.n_evaluated}")
    print(f"{prefix}scored (after filter): {result.n_scored}  "
          f"(dropped {result.n_dropped})")
    print(f"{prefix}fitness mean         : {result.mean:.4f}")
    print(f"{prefix}fitness spread (sd)  : {result.dispersion:.4f}")
    print(f"{prefix}winner               : {result.winner:.4f}")
    print(f"{prefix}chance bar           : {result.bar:.4f}")
    print(f"{prefix}edge                 : {result.edge:+.4f}"
          f"   -> winner is {'above' if result.clears_bar else 'BELOW'} the bar")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--log', action='append', default=[],
                        help='Fitness log to read (repeatable). Default: daily_results/**/fitness_info.txt')
    parser.add_argument('--n-trials', type=int, default=None,
                        help='Override trial count, e.g. the full search size when the log is a sample')
    parser.add_argument('--per-generation', action='store_true',
                        help='Also report a bar per generation')
    parser.add_argument('--keep-degenerate', action='store_true',
                        help='Do not filter zero-drawdown / zero-profit-factor entries (for comparison)')
    parser.add_argument('--json', action='store_true', help='Emit JSON')
    args = parser.parse_args()

    paths = resolve_paths(args.log)
    if not paths:
        print('No fitness logs found. Pass --log <path>.', file=sys.stderr)
        return 1

    records = collect(paths)
    if not records:
        print(f'No fitness entries parsed from: {", ".join(paths)}', file=sys.stderr)
        return 1

    result = compute(records, n_trials=args.n_trials,
                     drop_degenerate=not args.keep_degenerate)
    if result is None:
        print('Fewer than two scoreable candidates; nothing to compare.', file=sys.stderr)
        return 1

    payload: Dict[str, Any] = {'files': paths, 'overall': result.to_dict()}

    degenerate = [r for r in records if is_degenerate(r)]
    disqualified = len(records) - len(scoreable(records)) - len(degenerate)
    payload['dropped'] = {'degenerate': len(degenerate), 'disqualified': disqualified}

    if args.per_generation:
        per_gen = {}
        for record in records:
            per_gen.setdefault(int(record.get('generation', 0)), []).append(record)
        payload['per_generation'] = {}
        for gen in sorted(per_gen):
            gen_result = compute(per_gen[gen], drop_degenerate=not args.keep_degenerate)
            if gen_result:
                payload['per_generation'][gen] = gen_result.to_dict()

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"files: {', '.join(paths)}\n")
    report(result)

    if degenerate:
        print(f"\ndropped {len(degenerate)} degenerate entries "
              f"(max drawdown 0 AND profit factor 0 AND win rate 1.0):")
        print("  freqtrade reports these when no losing trade was ever closed, so the")
        print("  summary hides the risk in still-open positions. They score maximum")
        print("  drawdown and win-rate points and outrank real strategies.")
        best_degenerate = max(degenerate, key=lambda r: r['fitness'])
        print(f"  best of them scored {best_degenerate['fitness']:.4f} "
              f"vs {result.winner:.4f} for the best real candidate")
    if disqualified:
        print(f"\ndropped {disqualified} disqualified entries (fitness <= -1, a rejection code)")

    if args.per_generation and payload.get('per_generation'):
        print("\nper generation:")
        print(f"  {'gen':>4} {'n':>5} {'spread':>9} {'winner':>9} {'bar':>9} {'edge':>9}")
        for gen, data in payload['per_generation'].items():
            print(f"  {gen:4d} {data['n_scored']:5d} {data['dispersion']:9.4f} "
                  f"{data['winner']:9.4f} {data['bar']:9.4f} {data['edge']:+9.4f}")

    print("\nHow to read this")
    print("  The bar is what the best of n candidates would be expected to reach with")
    print("  no skill, given the spread this search produced. Clearing it is necessary,")
    print("  not sufficient: evaluations within a GA are not independent trials, and")
    print("  fitness is not normally distributed. Treat it as a screen. The real test")
    print("  of curve-fitting is out-of-sample -- set enable_walk_forward and compare")
    print("  train against test folds.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
