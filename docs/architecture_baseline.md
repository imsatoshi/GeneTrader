# Architecture Baseline

## 0. Baseline Recovery Note

- Previous state: this workspace was an empty Git repository with only `.git`
  and a local `docs/architecture_baseline.md`.
- Recovery action: remote `origin` was added as
  `https://github.com/imsatoshi/GeneTrader.git`, remote branches were fetched,
  and local branch `main` was checked out to track `origin/main`.
- Current audit time: `2026-05-30 13:09:46 +08:00`.
- Current source status: restored GeneTrader source is present on
  `main...origin/main`.
- Current source commit: `9e687a2 Merge pull request #16 from
  imsatoshi/claude/review-project-strategy-cGpAx`.
- Current local change status: `docs/architecture_baseline.md` is local and
  untracked relative to upstream.
- This report is based on the restored source tree, not the earlier empty
  repository state.

## 1. Repository Overview

GeneTrader is a Python project for optimizing Freqtrade strategies. The standard
flow generates strategy variants, runs Freqtrade backtests, parses result text,
and uses a fitness score to drive optimization.

Main directories and files:

- `main.py`: standard CLI entry point for optimization.
- `config/`: configuration loading and derived global settings.
- `genetic_algorithm/`: core GA primitives: `Individual`, `Population`,
  `crossover`, `mutate`, selection, and diversity helpers.
- `optimization/`: optimizer interface plus `GeneticOptimizer` and
  `OptunaOptimizer`.
- `strategy/`: strategy template parsing, strategy rendering, Freqtrade
  backtest wrapper, result parsing, walk-forward validation, and robustness
  helpers.
- `user_data/`: Freqtrade user directory; tracked example/config data is sparse,
  while generated strategies, temp configs, and data are mostly ignored.
- `tests/`: unittest-style tests collected through pytest.
- `scripts/`: operational scripts for workflow automation, analysis,
  benchmarking, pair updates, monitoring, cron/systemd, and Freqtrade restart.
- `adaptive/`, `monitoring/`, `deployment/`, `agent_api/`: adaptive
  optimization, performance monitoring, deployment/rollback, and agent API
  layers.
- `ga.json.example`: example runtime config copied to an ignored local `ga.json`.
- `README.md`: setup, config, usage, and high-level flow documentation.
- `daily_results/20241223/gen10/`: tracked sample generated strategy/result
  artifacts.

## 2. Main Entry Flow

`main.py` is the standard optimizer entry point.

Startup flow:

- Argument parsing uses `argparse` and supports `--config`, `--download`,
  `--start-date`, `--end-date`, `--resume`, and `--optimizer`.
- Configuration loading creates `Settings(args.config)`.
- Strategy parameter discovery calls
  `generate_dynamic_template(settings.base_strategy_file)` and stores the
  returned parameter list on `settings.parameters`.
- Directory setup calls `create_directories()` for `settings.results_dir`,
  `settings.best_generations_dir`, `settings.checkpoint_dir`, and `logs/`.
- Optional data download calls `download_data(start_date)` when `--download` is
  set.
- Optimizer selection defaults to CLI `--optimizer`, but if CLI is still
  `genetic`, `settings.optimizer_type` can override it.
- `run_optimization()` loads trading pairs from
  `settings.config_file -> exchange.pair_whitelist`, then instantiates either
  `GeneticOptimizer` or `OptunaOptimizer`.
- The main optimization entry is `optimizer.optimize(initial_individuals)`.
- Returned best individuals are saved by `save_best_individual()`.
- Overall best generation, fitness, and trading pairs are logged.

Error handling:

- `main()` wraps the whole flow in `try/except Exception` and logs failures via
  `logger.exception()`.
- `--resume` is parsed, but no checkpoint load/resume behavior was found in
  `main.py` or the inspected standard GA optimizer path.

## 3. Configuration Loading

Runtime config is loaded by `config/settings.py`.

Where config lives:

- Default runtime config path is `ga.json`.
- `ga.json` is ignored by `.gitignore`.
- `ga.json.example` is the tracked example file.
- `Settings(config_file)` can load any JSON path passed from `main.py --config`.
- `_SettingsProxy` uses `GENETRADER_CONFIG` or `ga.json` for modules that import
  global `settings`.

How config is read:

- `Settings.__init__()` checks file existence, parses JSON, validates required
  fields and numeric constraints, then maps values to instance attributes.
- `config/config.py` imports the lazy global `settings` and derives
  `PROJECT_ROOT`, `LOG_CONFIG`, `REMOTE_SERVER`, `BARK_ENDPOINT`, and
  `BARK_KEY`.

Key GA fields:

- `population_size`
- `generations`
- `crossover_prob`
- `mutation_prob`
- `tournament_size`
- `pool_processes`
- `fix_pairs`
- `num_pairs`
- `diversity_threshold`
- `max_mutation_prob`
- `enable_diversity_selection`
- `diversity_selection_weight`
- `optimizer_type`
- `optuna_n_trials`, `optuna_sampler`, `optuna_n_startup_trials`,
  `optuna_pruning`, `optuna_n_jobs`

Key Freqtrade fields:

- `freqtrade_path`
- `config_file`
- `user_dir`
- `data_dir`
- `strategy_dir`
- `backtest_timerange_weeks`
- `max_retries`
- `retry_delay`
- `api_url`
- `freqtrade_username`
- `freqtrade_password`

Key strategy generation fields:

- `base_strategy_file`
- `strategy_dir`
- `add_max_open_trades`
- `add_dynamic_timeframes`
- `fix_pairs`
- `num_pairs`

Operational/deployment fields:

- `project_dir`, `results_dir`, `best_generations_dir`, `checkpoint_dir`
- SSH/SCP fields: `hostname`, `username`, `port`, `key_path`,
  `remote_datadir`, `remote_strategydir`
- Adaptive/agent fields such as `adaptive_optimization_enabled`,
  `performance_db_path`, `agent_api_enabled`, and `agent_api_key`

Important boundary:

- `main.py` passes a concrete `Settings(args.config)` into optimizers, while
  `strategy/backtest.py`, `data/downloader.py`, `config/config.py`, and some
  scripts import the global lazy `settings`. This means subprocess worker code
  may depend on `ga.json` or `GENETRADER_CONFIG` even when `main.py --config`
  uses another path.

## 4. Genetic Optimizer Flow

The main GA implementation is `optimization/genetic_optimizer.py`, backed by
types in `genetic_algorithm/`.

Population initialization:

- `GeneticOptimizer._create_population()` calls `Population.create_random()`.
- `Population.create_random()` creates a list of random `Individual` objects.
- Initial individuals, when provided, are appended to the generated population.

Individual and genes:

- `Individual` stores `genes`, `trading_pairs`, `fitness`, and `param_types`.
- `genes` are generated from parsed strategy parameters.
- Supported parameter types are `Int`, `Decimal`, `Categorical`, and `Boolean`.
- `trading_pairs` is either all pairs or a random sample, depending on
  `fix_pairs` and `num_pairs`.

Selection:

- Standard selection uses `select_tournament(population, tournament_size)`.
- If diversity selection is enabled, `select_with_diversity()` combines fitness
  and genetic distance from a reference individual.

Crossover:

- `crossover(parent1, parent2, with_pair=True)` performs single-point gene
  crossover.
- If pair crossover is enabled and both parents have pairs, it shuffles the
  union of parent pairs and assigns pair slices to children.

Mutation:

- `mutate(individual, mutation_rate)` mutates each gene independently.
- Boolean genes flip.
- Categorical genes pick a random option.
- Numeric genes use one of `noise`, `reset`, or `scale`, then clamp to the
  configured range.
- `Individual.after_genetic_operation()` constrains genes after crossover or
  mutation.
- `maintain_diversity()` can apply extra mutations when population diversity is
  below `diversity_threshold`.

Fitness:

- Each generation evaluates individuals in a multiprocessing pool.
- Fitness is produced by `strategy.backtest.run_backtest()`.
- `run_backtest()` renders a strategy, writes a temp config, invokes Freqtrade,
  parses the output, and calls `fitness_function()`.
- `fitness_function()` combines profit, win rate, Sharpe/Sortino/profit factor,
  drawdown, trade frequency, duration, trade confidence, and complexity penalty.

Generation advancement:

- Evaluate all individuals.
- Keep positive-fitness individuals; if none, fall back to all non-`None`
  fitness values.
- Pick best individual before reproduction.
- Build offspring through tournament/diversity selection.
- Preserve elite individual at the first offspring slot.
- Apply crossover, mutation, optional diversity maintenance.
- Replace the population with offspring.
- Append `(generation_number, best_individual)` to the return list.

Saving best individuals:

- `GeneticOptimizer.optimize()` returns generation bests.
- `main.py::save_best_individual()` writes JSON files named
  `best_individual_gen{generation}.json` into `settings.best_generations_dir`.

## 5. Strategy Generation Flow

Template and parameter extraction:

- `strategy/gen_template.py` reads `settings.base_strategy_file`.
- `parse_parameters()` uses regex to extract Freqtrade `IntParameter`,
  `DecimalParameter`, `BooleanParameter`, and `CategoricalParameter`
  definitions.
- `generate_dynamic_template()` can append synthetic `max_open_trades` and
  `dynamic_timeframes` parameters.
- `replace_parameters()` replaces the Freqtrade strategy class name with
  `${strategy_name}` and optimized defaults with `${parameter_name}`
  placeholders.

Strategy file generation:

- `strategy/backtest.py::render_strategy()` builds a `string.Template` from the
  generated template.
- Genes are mapped by parameter order into placeholder values.
- Decimal genes are rounded by configured `decimal_places`.
- Int genes are cast to integers.
- `run_backtest()` creates names like
  `GeneTrader_gen{generation}_{timestamp}_{random_id}`.
- Generated strategy files are written to
  `{settings.strategy_dir}/{strategy_name}.py`.

Generated file destination:

- In `ga.json.example`, `strategy_dir` is `user_data/strategies`.
- `.gitignore` ignores `user_data/strategies/*` except `.gitkeep`.

Overwrite and collision risk:

- Standard generated strategy names include generation, Unix timestamp, and a
  random four-digit suffix, so ordinary collisions are unlikely.
- There is still a theoretical collision if two workers generate the same
  timestamp and random suffix.
- Generated temp configs follow
  `user_data/temp_config_{timestamp}_{random_id}.json` and have the same
  theoretical collision risk.
- `scripts/workflow.py::rename_strategy_class()` writes into
  `strategies/GeneStrategy.py`; that is a deliberate deployment-style overwrite
  path and should be treated separately from standard generated strategy output.

## 6. Freqtrade Integration

GeneTrader calls Freqtrade through subprocesses, not through a Python-internal
Freqtrade API in the standard optimization path.

Backtesting:

- `strategy/backtest.py::run_backtest()` builds a list command:
  `settings.freqtrade_path backtesting --strategy <strategy_name> -c
  <temp_config> --timerange <timerange> -d <data_dir> --userdir <user_dir>
  --timeframe-detail 1m --enable-protections --cache none`.
- It redirects stdout and stderr into a result text file under `results/`.
- It retries up to `settings.max_retries`.
- It uses `timeout=600`.
- It then parses the output file with `parse_backtest_results()`.

Data download:

- `data/downloader.py::DataDownloader.download_data()` calls
  `freqtrade download-data` with `--config`, `--datadir`, `--timerange`, and a
  fixed timeframe list.

Hyperopt boundary:

- No direct `freqtrade hyperopt` subprocess call was found in the inspected
  standard path.
- `optimization/optuna_optimizer.py` is an internal Optuna optimizer that still
  evaluates trials via `run_backtest()`.

Dry-run/live boundary:

- `main.py` and `strategy/backtest.py` are backtest-oriented.
- `scripts/workflow.py` contains remote upload, SSH/API restart, and comparison
  backtest logic.
- `monitoring/`, `deployment/`, and `adaptive/` contain operational support for
  monitoring, deployment, shadow trading, rollback, and adaptive optimization.
- No dry-run trading command was executed during this audit.

Output parsing:

- `strategy/evaluation.py::parse_backtest_results()` reads the captured
  Freqtrade text output.
- It returns empty metric defaults when `SUMMARY METRICS` is absent.
- `fitness_function()` appends detailed fitness logs to
  `logs/fitness_log.txt`.

## 7. Results and Artifacts

Known artifact paths:

- `bestgenerations/`: configured by `best_generations_dir`; stores
  `best_individual_gen{generation}.json` from `main.py`.
- `results/`: configured by `results_dir`; stores
  `backtest_results_gen{generation}_{timestamp}_{random_id}.txt` from
  `strategy/backtest.py`.
- `logs/`: configured in `config/config.py`; `fitness_log.txt` is written by
  `strategy/evaluation.py`. `backtest_log.txt` and `diversity_log.csv` are
  named in config but were not found as standard writes in the inspected main
  flow.
- `reports/`: does not exist and no first-class report writer was found in the
  inspected standard source path.
- Generated strategies: normally `user_data/strategies/*.py`, ignored by Git.
- Temp Freqtrade configs: `user_data/temp_config_*.json`, ignored by Git.
- `checkpoints/`: configured and created by `main.py`, but no checkpoint write
  or resume implementation was found in the inspected standard optimizer path.
- `user_data/backtest_results/`: ignored and cleaned by scripts, but the
  standard `run_backtest()` writes output to `results/`.
- `daily_results/{YYYYMMDD}/{generation}/`: `scripts/workflow.py` archives best
  strategy, config, result text, and fitness info here.
- `scripts/outputs/`: benchmark output target in `scripts/benchmark.py`.
- `data/shadow_results/`: shadow trading result target in
  `deployment/shadow_trader.py`.

Cleanup paths:

- `clean.sh` removes content from `results/`, `bestgenerations/`,
  `user_data/backtest_results/`, `user_data/temp_config_*.json`,
  `checkpoints/check*`, and `logs/`.

## 8. Test Structure

`tests/` contains unittest-style modules.

Visible coverage:

- `test_individual.py`: individual creation, gene constraints, copy behavior,
  trading-pair mutation, edge cases.
- `test_population.py`: population creation, best selection, length/iteration,
  edge cases.
- `test_operators.py`: crossover, mutation, tournament selection.
- `test_backtest.py`: `render_strategy()` with mocked template generation.
- `test_evaluation.py`: result parsing, duration parsing, regex helpers,
  fitness calculation.
- `test_fitness_helpers.py`: parsing fitness/generation/strategy/win-rate data
  from logs.
- `test_walk_forward.py`: validation periods, rolling/expanding/anchored
  windows, composite fitness, diversity helpers.
- `test_workflow.py`: workflow upload subprocess behavior.
- `test_adaptive.py`: adaptive optimizer, weighted optimizer, scheduler.
- `test_monitoring.py`: Freqtrade API response mapping, performance database,
  performance monitor, degradation detector, alerts.
- `test_deployment.py`: version control, deployer, shadow trader, rollback.
- `test_agent_api.py`: auth, websocket manager, API response, agent API
  approval flow.

Key gaps and collection risk:

- No full test collection succeeds without a runtime config.
- Tests importing `strategy.evaluation`, `strategy.backtest`, or
  `scripts.workflow` can indirectly import `config.config`, which forces the
  lazy settings proxy to load `ga.json`.
- `run_backtest()` is central and should remain mocked for architecture/unit
  tests because it triggers subprocess Freqtrade backtests.
- Checkpoint/resume behavior appears configured but not covered in the
  inspected standard optimizer path.
- The future Bollinger path currently has no tests because it does not exist.

`pytest --collect-only` result:

- Plain `pytest --collect-only` failed in PowerShell because `pytest` was not
  recognized as a direct command.
- `python -m pytest --collect-only` ran successfully far enough to collect 184
  tests, then stopped with 3 collection errors.
- The 3 collection errors were in `tests/test_backtest.py`,
  `tests/test_evaluation.py`, and `tests/test_workflow.py`.
- The shared cause was missing local `ga.json`: `_SettingsProxy` raised
  `RuntimeError: Configuration file 'ga.json' not found`.

Additional validation:

- `python -m compileall .` completed successfully.
- `compileall` generated ignored `__pycache__` artifacts.

## 9. Safe Extension Points

Minimal-intrusion mounting points for Bollinger Evolver:

- Add `bollinger_evolver/` as an independent module.
- Add `config/ga_bollinger_resonance.json` as a separate config file for the
  new workflow.
- Add a separate gene-space JSON, for example
  `config/bollinger_resonance_gene_space.json`.
- Add `user_data/strategies/BollingerResonanceStrategy.py` as a new Freqtrade
  strategy file or base template.
- Add a dedicated generated strategy output directory, for example
  `user_data/strategies/generated_bollinger/` or another ignored path.
- Add `reports/bollinger_evolver/` or `results/bollinger_evolver/` for
  Bollinger-specific output.
- Add an independent runner, for example `scripts/run_bollinger_evolver.py` or
  `bollinger_evolver/runner.py`, instead of rewriting `main.py`.
- Add tests that mock Freqtrade subprocess calls and assert generated command,
  config, strategy output, and fitness parsing contracts.

Preferred boundary:

- Use the existing concepts of `Settings`, generated strategy files,
  Freqtrade backtest subprocesses, and fitness parsing only through explicit
  adapters.
- Keep Bollinger-specific gene definitions, reports, generated strategies, and
  runner logic separate from the current GA core until behavior is proven.

## 10. High Risk Files

Files that should not be casually modified:

- `main.py`: owns CLI startup, config loading, template parameter discovery,
  optimizer choice, output directory creation, and best-individual saving.
- `config/settings.py`: parses and validates runtime config; changes can affect
  GA, Freqtrade, adaptive, deployment, and agent flows.
- `config/config.py`: exposes `LOG_CONFIG`, `REMOTE_SERVER`, Bark config, and
  forces lazy settings access for many imports.
- `genetic_algorithm/individual.py`: defines genome representation and gene
  constraints.
- `genetic_algorithm/population.py`: defines population creation and best
  selection.
- `genetic_algorithm/operators.py`: defines crossover, mutation, selection, and
  diversity behavior.
- `optimization/genetic_optimizer.py`: owns the active GA loop,
  multiprocessing evaluation, elitism, and generation advancement.
- `optimization/base_optimizer.py`: defines the optimizer contract used by GA
  and Optuna.
- `strategy/gen_template.py`: parses strategy parameters and rewrites strategy
  templates.
- `strategy/backtest.py`: writes generated strategies/temp configs, constructs
  the Freqtrade command, executes subprocesses, and returns fitness.
- `strategy/evaluation.py`: parses Freqtrade output, computes fitness, and
  writes fitness logs.
- `scripts/workflow.py`: contains cleanup, upload, remote restart, strategy
  rename, daily archive, and comparison backtest behavior.
- `ga.json.example` and `user_data/example.json`: user-facing config examples;
  accidental changes can alter setup and runtime expectations.

## 11. Minimal-Invasive Integration Plan

Suggested future files:

- `bollinger_evolver/__init__.py`
- `bollinger_evolver/gene_space.py`
- `bollinger_evolver/strategy_renderer.py`
- `bollinger_evolver/fitness_adapter.py`
- `bollinger_evolver/runner.py`
- `config/ga_bollinger_resonance.json`
- `config/bollinger_resonance_gene_space.json`
- `user_data/strategies/BollingerResonanceStrategy.py`
- `reports/bollinger_evolver/README.md` or an ignored report output path
- `tests/test_bollinger_evolver_*.py`

Existing files to avoid touching initially:

- `main.py`
- `genetic_algorithm/individual.py`
- `genetic_algorithm/population.py`
- `genetic_algorithm/operators.py`
- `optimization/genetic_optimizer.py`
- `strategy/backtest.py`
- `strategy/gen_template.py`
- `strategy/evaluation.py`
- `ga.json.example`

If old files must be changed:

- Only add a small, explicit entry point or adapter.
- Do not alter existing optimizer behavior for the standard `main.py` path.
- Do not change existing strategy generation semantics until Bollinger tests are
  in place.
- Do not make `config/settings.py` require Bollinger fields for normal
  GeneTrader runs.

Preferred integration shape:

- Independent Bollinger runner loads its own config and gene-space JSON.
- Bollinger renderer generates strategy files into a dedicated output path.
- A Freqtrade adapter reuses the existing command-building ideas while keeping
  subprocess calls mockable.
- Fitness parsing can reuse `strategy/evaluation.py` through a narrow adapter,
  or call a Bollinger-specific scoring layer after parsed metrics are available.
- Existing GA/optimizer code should be reused only through a stable contract,
  not by mutating core classes for Bollinger-specific assumptions.

## 12. Recommended Next Task

Next task card:

`Task 01: Establish Bollinger Evolver engineering skeleton`

Scope for that task:

- Create only the empty/placeholder project skeleton for Bollinger Evolver.
- Add config and gene-space schema/examples.
- Add a runner stub that does not run Freqtrade.
- Add tests for config loading and gene-space validation.
- Do not implement Bollinger strategy logic.
- Do not invoke real backtests.
- Do not modify `main.py` or current GA core behavior.
