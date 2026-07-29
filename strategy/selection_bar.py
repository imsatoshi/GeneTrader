"""How good would the best of N random strategies have looked anyway?

A GA that evaluates 900 candidates and reports the best one has run 900
experiments and published the winner. Some of that winner's score is skill and
some is the luck of being the luckiest of 900 draws. This module estimates the
luck component: given the spread of fitness actually observed in the
population, what score would the best of N zero-skill candidates be expected to
reach? That value is the search's own selection bar, and a winner that does not
clear it has not demonstrated anything the search couldn't have produced from
noise.

The estimator is the Bailey / Lopez de Prado false-strategy benchmark used for
the Deflated Sharpe Ratio, applied to the quantity this project actually
selects on -- Final Fitness -- rather than to Sharpe. Sharpe is one weighted
input to fitness (see strategy/evaluation.py); deflating it would measure
selection pressure that was never applied.

Read the output as a screening diagnostic, not a verdict. Two assumptions are
knowingly violated:

  * Independence. Generation N+1 descends from generation N by selection,
    crossover, and mutation, so evaluations are not independent trials. Using
    the full evaluation count overstates the number of independent draws, which
    raises the bar -- the test is therefore conservative on that axis.
  * Normality. Fitness is a bounded weighted sum, not a normal variate.

The real answer to "is this curve-fitted" is out-of-sample performance. Set
enable_walk_forward and compare train against test folds. This number is a
cheap in-sample screen that runs on data you already have.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Sequence

EULER_MASCHERONI = 0.5772156649015329

# fitness_function returns -1.0 .. -4.0 as disqualification codes and
# run_backtest returns -inf when a backtest produced nothing. Neither is a
# sample from the distribution of strategy performance.
DISQUALIFIED_ABOVE = -0.999


def _probit(p: float) -> float:
    """Inverse standard normal CDF (Acklam's rational approximation)."""
    if not 0.0 < p < 1.0:
        raise ValueError("probit needs 0 < p < 1")
    a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00)
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return ((((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])
                / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1))
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -((((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])
                 / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1))
    q = p - 0.5
    r = q * q
    return ((((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q
            / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1))


def expected_max(n_trials: int, dispersion: float) -> float:
    """Expected maximum of ``n_trials`` iid draws from N(0, dispersion^2).

    This is the increment above the mean that the luckiest of n zero-skill
    candidates is expected to reach.
    """
    if dispersion <= 0 or n_trials < 2:
        return 0.0
    z1 = _probit(1 - 1.0 / n_trials)
    z2 = _probit(1 - 1.0 / (n_trials * math.e))
    return dispersion * ((1 - EULER_MASCHERONI) * z1 + EULER_MASCHERONI * z2)


@dataclass
class SelectionBar:
    """Winner versus the score the search could have reached by luck."""
    n_evaluated: int
    n_scored: int          # after dropping disqualified / degenerate entries
    n_dropped: int
    mean: float
    dispersion: float
    winner: float
    bar: float             # mean + expected_max(n_scored, dispersion)
    edge: float            # winner - bar
    clears_bar: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def summary(self) -> str:
        verdict = "above" if self.clears_bar else "BELOW"
        return (f"selection bar: winner={self.winner:.4f} {verdict} "
                f"chance-bar={self.bar:.4f} (edge {self.edge:+.4f}) from "
                f"n={self.n_scored} scored candidates, spread={self.dispersion:.4f}")


def is_degenerate(record: Dict[str, float]) -> bool:
    """True for backtests whose metrics cannot be what they claim.

    Freqtrade reports profit factor 0 and max drawdown 0 when it has no losing
    trade to divide by. Combined with a perfect win rate that means no loss was
    ever realised -- typically a strategy that simply never closes a losing
    position, leaving the risk in open trades where the summary cannot see it.
    Such a candidate scores maximum drawdown-penalty and win-rate points, so it
    outranks real strategies. Current fitness_function rejects it on the profit
    factor check, but historical logs predate that guard.
    """
    return (record.get('max_drawdown', 1.0) == 0.0
            and record.get('profit_factor', 1.0) == 0.0
            and record.get('win_rate', 0.0) >= 0.999)


def scoreable(records: Sequence[Dict[str, float]],
              drop_degenerate: bool = True) -> List[Dict[str, float]]:
    """Keep only entries that represent a real evaluated strategy."""
    kept = []
    for r in records:
        fitness = r.get('fitness')
        if fitness is None or not math.isfinite(fitness):
            continue
        if fitness <= DISQUALIFIED_ABOVE:
            continue
        if drop_degenerate and is_degenerate(r):
            continue
        kept.append(r)
    return kept


def compute(records: Sequence[Dict[str, float]],
            n_trials: Optional[int] = None,
            drop_degenerate: bool = True) -> Optional[SelectionBar]:
    """Compute the selection bar for a pool of evaluated candidates.

    Args:
        records: dicts with at least ``fitness``; ``max_drawdown``,
            ``profit_factor`` and ``win_rate`` enable degenerate filtering.
        n_trials: override the trial count. Defaults to the number of scoreable
            candidates. Pass the full search size when the pool is a sample of
            a larger search, so the bar reflects everything that was tried.
        drop_degenerate: exclude backtests that reported no losing trade. Set
            False only to show what including them would do.

    Returns None when fewer than two candidates survive filtering.
    """
    kept = scoreable(records, drop_degenerate=drop_degenerate)
    if len(kept) < 2:
        return None

    values = [r['fitness'] for r in kept]
    mean = statistics.mean(values)
    dispersion = statistics.pstdev(values)
    winner = max(values)
    trials = n_trials if n_trials is not None else len(values)
    bar = mean + expected_max(trials, dispersion)

    return SelectionBar(
        n_evaluated=len(records),
        n_scored=len(kept),
        n_dropped=len(records) - len(kept),
        mean=mean,
        dispersion=dispersion,
        winner=winner,
        bar=bar,
        edge=winner - bar,
        clears_bar=winner > bar,
    )


def from_fitnesses(fitnesses: Sequence[float],
                   n_trials: Optional[int] = None) -> Optional[SelectionBar]:
    """Convenience wrapper when only fitness values are available."""
    return compute([{'fitness': f} for f in fitnesses], n_trials=n_trials)
