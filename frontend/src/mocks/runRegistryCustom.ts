export type CustomRunRobustnessSummary = {
  walk_forward: {
    stability_score: number;
    train_validation_gap: number;
    validation_test_gap: number;
  };
  monte_carlo: {
    runs: number;
    profit_p05: number;
    profit_median: number;
    drawdown_p95: number;
    failure_rate: number;
  };
  portfolio: {
    portfolio_profit: number;
    portfolio_drawdown: number;
    correlation_penalty: number;
  };
};

export type CustomExperimentRun = {
  run_id: string;
  created_at: string;
  source: string;
  seed: number;
  generations: number;
  population_size: number;
  best_fitness: number;
  artifact_dir: string;
  status: 'completed' | 'review' | 'failed';
  strategy_family: string;
  stability_score: number;
  failure_rate: number;
  portfolio_profit: number;
  portfolio_drawdown: number;
  best_genome_id: string;
  genome: Record<string, number | string>;
  strategy_config: Record<string, unknown>;
  trading_system_config: Record<string, unknown>;
  risk_governor: {
    adjusted_leverage: number;
    adjusted_risk_per_trade: number;
    actions: string[];
  };
  fitness_components: Record<string, number>;
  robustness_summary: CustomRunRobustnessSummary;
  notes: string;
};

const baselineGenome = {
  genome_id: 'custom-gen004-ind017',
  entry_bb_window: 30,
  entry_bb_stddev: 2.1,
  entry_rsi_period: 14,
  entry_rsi_max: 34,
  exit_take_profit_pct: 0.08,
  exit_stop_loss_pct: 0.03,
  trailing_stop_pct: 0.02,
  add_position_threshold_pct: 0.025,
  reduce_position_threshold_pct: 0.04,
  max_additions: 1,
  leverage: 2,
  risk_per_trade: 0.012,
  max_portfolio_exposure: 0.3,
  cooldown_candles: 6,
};

const baselineStrategyConfig = {
  schema_version: 'custom-strategy/v1',
  genome_id: baselineGenome.genome_id,
  entry: {
    bollinger_window: 30,
    bollinger_stddev: 2.1,
    rsi_period: 14,
    rsi_max: 34,
  },
  exit: {
    take_profit_pct: 0.08,
    stop_loss_pct: 0.03,
    trailing_stop_pct: 0.02,
  },
  position_sizing: {
    leverage: 2,
    risk_per_trade: 0.012,
    max_portfolio_exposure: 0.3,
    max_additions: 1,
  },
  execution_controls: {
    dry_run_only: true,
    real_execution_enabled: false,
  },
};

const baselineTradingSystemConfig = {
  schema_version: 'custom-trading-system-config/v1',
  strategy_id: baselineGenome.genome_id,
  entry: {
    bollinger: { window: 30, stddev: 2.1 },
    rsi: { period: 14, max: 34 },
  },
  exit: {
    stoploss_pct: 0.03,
    takeprofit_pct: 0.08,
    trailing_stop_pct: 0.02,
  },
  position: {
    base_leverage: 2,
    max_leverage: 2,
    risk_per_trade: 0.012,
    max_open_positions: 2,
  },
  risk_control: {
    max_portfolio_exposure: 0.3,
    drawdown_cutoff: 0.1,
    loss_streak_cutoff: 4,
    cooldown_candles: 6,
  },
  execution: {
    dry_run_only: true,
    real_trading_enabled: false,
  },
};

export const customRunRegistry: CustomExperimentRun[] = [
  {
    run_id: 'custom-ga-seed-42',
    created_at: '2026-06-06T12:10:00+00:00',
    source: 'custom-strategy-mock-ga',
    seed: 42,
    generations: 5,
    population_size: 30,
    best_fitness: 0.864,
    artifact_dir: 'artifacts/custom-ga-seed-42',
    status: 'completed',
    strategy_family: 'custom-bollinger-rsi',
    stability_score: 0.82,
    failure_rate: 0.06,
    portfolio_profit: 0.18,
    portfolio_drawdown: 0.09,
    best_genome_id: baselineGenome.genome_id,
    genome: baselineGenome,
    strategy_config: baselineStrategyConfig,
    trading_system_config: baselineTradingSystemConfig,
    risk_governor: {
      adjusted_leverage: 2,
      adjusted_risk_per_trade: 0.012,
      actions: ['advisory_only_no_strategy_mutation'],
    },
    fitness_components: {
      profit_component: 0.18,
      sharpe_component: 0.36,
      win_rate_component: 0.058,
      drawdown_penalty: 0.18,
      stability_component: 0.164,
      overfit_penalty: 0.08,
      final_fitness: 0.864,
    },
    robustness_summary: {
      walk_forward: {
        stability_score: 0.82,
        train_validation_gap: 0.04,
        validation_test_gap: 0.03,
      },
      monte_carlo: {
        runs: 100,
        profit_p05: 0.04,
        profit_median: 0.14,
        drawdown_p95: 0.14,
        failure_rate: 0.06,
      },
      portfolio: {
        portfolio_profit: 0.18,
        portfolio_drawdown: 0.09,
        correlation_penalty: 0.02,
      },
    },
    notes: 'custom schema baseline with advisory risk governor',
  },
  {
    run_id: 'custom-walk-forward-017',
    created_at: '2026-06-06T13:30:00+00:00',
    source: 'custom-walk-forward',
    seed: 17,
    generations: 4,
    population_size: 24,
    best_fitness: 0.799,
    artifact_dir: 'artifacts/custom-walk-forward-017',
    status: 'review',
    strategy_family: 'custom-bollinger-rsi',
    stability_score: 0.76,
    failure_rate: 0.09,
    portfolio_profit: 0.14,
    portfolio_drawdown: 0.13,
    best_genome_id: 'custom-gen003-ind009',
    genome: {
      ...baselineGenome,
      genome_id: 'custom-gen003-ind009',
      entry_bb_window: 26,
      leverage: 2.5,
      risk_per_trade: 0.015,
      cooldown_candles: 12,
    },
    strategy_config: {
      ...baselineStrategyConfig,
      genome_id: 'custom-gen003-ind009',
    },
    trading_system_config: {
      ...baselineTradingSystemConfig,
      strategy_id: 'custom-gen003-ind009',
    },
    risk_governor: {
      adjusted_leverage: 2.5,
      adjusted_risk_per_trade: 0.01,
      actions: ['reduced_risk_after_drawdown'],
    },
    fitness_components: {
      profit_component: 0.14,
      sharpe_component: 0.31,
      win_rate_component: 0.052,
      drawdown_penalty: 0.26,
      stability_component: 0.152,
      overfit_penalty: 0.12,
      final_fitness: 0.799,
    },
    robustness_summary: {
      walk_forward: {
        stability_score: 0.76,
        train_validation_gap: 0.07,
        validation_test_gap: 0.05,
      },
      monte_carlo: {
        runs: 100,
        profit_p05: -0.01,
        profit_median: 0.11,
        drawdown_p95: 0.18,
        failure_rate: 0.09,
      },
      portfolio: {
        portfolio_profit: 0.14,
        portfolio_drawdown: 0.13,
        correlation_penalty: 0.04,
      },
    },
    notes: 'walk-forward stability and overfit penalty review',
  },
  {
    run_id: 'custom-portfolio-088',
    created_at: '2026-06-06T14:05:00+00:00',
    source: 'custom-portfolio',
    seed: 88,
    generations: 6,
    population_size: 28,
    best_fitness: 0.812,
    artifact_dir: 'artifacts/custom-portfolio-088',
    status: 'completed',
    strategy_family: 'custom-bollinger-rsi',
    stability_score: 0.79,
    failure_rate: 0.05,
    portfolio_profit: 0.21,
    portfolio_drawdown: 0.08,
    best_genome_id: 'custom-gen006-ind021',
    genome: {
      ...baselineGenome,
      genome_id: 'custom-gen006-ind021',
      entry_bb_window: 34,
      entry_bb_stddev: 2.3,
      max_portfolio_exposure: 0.35,
    },
    strategy_config: {
      ...baselineStrategyConfig,
      genome_id: 'custom-gen006-ind021',
    },
    trading_system_config: {
      ...baselineTradingSystemConfig,
      strategy_id: 'custom-gen006-ind021',
    },
    risk_governor: {
      adjusted_leverage: 2,
      adjusted_risk_per_trade: 0.012,
      actions: ['advisory_only_no_strategy_mutation'],
    },
    fitness_components: {
      profit_component: 0.21,
      sharpe_component: 0.33,
      win_rate_component: 0.055,
      drawdown_penalty: 0.16,
      stability_component: 0.158,
      overfit_penalty: 0.09,
      final_fitness: 0.812,
    },
    robustness_summary: {
      walk_forward: {
        stability_score: 0.79,
        train_validation_gap: 0.05,
        validation_test_gap: 0.04,
      },
      monte_carlo: {
        runs: 100,
        profit_p05: 0.05,
        profit_median: 0.17,
        drawdown_p95: 0.13,
        failure_rate: 0.05,
      },
      portfolio: {
        portfolio_profit: 0.21,
        portfolio_drawdown: 0.08,
        correlation_penalty: 0.03,
      },
    },
    notes: 'multi-pair portfolio mock validation',
  },
];
