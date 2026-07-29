# GeneTrader

Parameter search for Freqtrade strategies. A genetic algorithm (or Optuna)
proposes strategy parameters and trading pairs, runs each candidate through a
Freqtrade backtest, and scores the result with a fitness function tuned against
overfitting.

**This repository does not trade.** It produces candidate strategy files and
scores; deploying anything to a live bot is a manual step taken outside it.
There is no monitoring, no auto-deployment, and no rollback here by design —
that layer was removed once it became clear the live bot is curated by hand.

## Running a search

```bash
cp ga.json.example ga.json          # then edit paths and search settings
python main.py                       # genetic algorithm (default)
python main.py --optimizer optuna    # TPE search, better for high dimensions
python main.py --download --start-date 20240101
python main.py --resume              # continue from the latest checkpoint
```

Results land in `results_dir`, the best individual per generation in
`best_generations_dir`, and checkpoints in `checkpoint_dir`. A completed run
clears its checkpoint; a crashed one leaves it for `--resume`.

`--config` sets `GENETRADER_CONFIG` for the worker processes, so a custom
config applies to the backtests as well as the search loop.

## Reading the output

Two numbers matter more than the raw winner.

**Selection bar.** Evaluating N candidates and reporting the best means running
N experiments and publishing the winner; part of that score is the luck of
being luckiest of N. Each generation logs what the best of N zero-skill
candidates would have been expected to reach, given the spread the search
actually produced:

```bash
python scripts/selection_bar.py --per-generation
```

A winner below its own bar has not beaten noise. Clearing it is necessary, not
sufficient — evaluations inside a GA are not independent trials, and fitness is
not normally distributed. Treat it as a screen.

**Walk-forward.** Set `enable_walk_forward: true` to train each fold on its own
historical window and score it on the following out-of-sample window. This is
the real test for curve-fitting and the reason to prefer it over a single
recent-window search. It costs one full GA run per fold.

## Fitness

`strategy/evaluation.py` scores a backtest on seven weighted components
(profit, risk-adjusted return, drawdown, win rate, trade frequency, statistical
confidence, duration) and applies a complexity penalty.

Candidates are disqualified outright — before scoring — when they trade too
little for the result to mean anything, exceed `max_drawdown_limit`, fall below
`min_profit_factor`, or fall below `min_win_rate`. Those three thresholds come
from the config, so tightening them in `ga.json` changes which candidates
survive.

Watch for backtests reporting max drawdown 0 **and** profit factor 0 **and** a
perfect win rate. Freqtrade prints that when it has no losing trade to divide
by, which usually means the strategy never closes a loser and the risk is
sitting in open positions the summary cannot see. The profit-factor
disqualification rejects them; `scripts/selection_bar.py` filters them out of
its statistics and reports how many it dropped.

## Layout

```
main.py                  entry point
optimization/            GA and Optuna drivers, checkpointing, walk-forward folds
genetic_algorithm/       individuals, population, crossover/mutation/selection
strategy/
  backtest.py            renders a candidate and shells out to Freqtrade
  evaluation.py          parses backtest output, computes fitness
  gen_template.py        builds a strategy file from the base template
  walk_forward.py        fold generation
  selection_bar.py       expected best-of-N under no skill
  robustness.py          parameter sensitivity, Monte Carlo
scripts/
  selection_bar.py       report the bar from fitness logs
  workflow.py            end-to-end run: optimize, compare, notify
  get_pairs.py           refresh the pair whitelist from Binance
  monitor_delistings.py  watch for delisting announcements
config/settings.py       config loading and validation
```

## When helping with this repository

- Backtests shell out to Freqtrade and take minutes each. A default search is
  hundreds of them. Never launch a full run to test a change; patch
  `run_backtest` instead, as `tests/test_ga_core.py` does.
- `tests/` runs without a `ga.json` — `conftest.py` falls back to
  `ga.json.example`. Keep it that way.
- The strategy file in `strategies/` is generated. The source of truth is
  `base_strategy_file` in the config, which lives outside this repository.
