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

export type PositionSizingPreview = {
  schema_version: string;
  position_value: number;
  margin_required: number;
  risk_amount: number;
  leverage: number;
  warnings: string[];
  source?: string;
  max_portfolio_exposure?: number;
  max_position_value?: number;
};

export type StrategyExplanation = {
  schema_version: string;
  summary: string;
  entry_logic: string[];
  exit_logic: string[];
  risk_logic: string[];
  warnings: string[];
  fitness_explanation: string[];
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
  max_drawdown: number;
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
  position_sizing_preview: PositionSizingPreview;
  strategy_explanation: StrategyExplanation;
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

const baselinePositionSizingPreview = {
  schema_version: 'position-sizing/v1',
  position_value: 3000,
  margin_required: 1500,
  risk_amount: 90,
  leverage: 2,
  warnings: ['max_position_value_applied'],
  source: 'trading-system-config',
  max_portfolio_exposure: 0.3,
  max_position_value: 3000,
};

const baselineStrategyExplanation = {
  schema_version: 'strategy-explainability/v1',
  summary: 'Balanced custom strategy profile for mock-first evaluation.',
  entry_logic: ['bollinger_window=30', 'bollinger_stddev=2.1', 'rsi_max=34'],
  exit_logic: ['stoploss_pct=0.03', 'takeprofit_pct=0.08', 'trailing_stop_pct=0.02'],
  risk_logic: ['leverage=2', 'risk_per_trade=0.012', 'max_portfolio_exposure=0.3'],
  warnings: ['max_position_value_applied'],
  fitness_explanation: [
    'final_fitness=0.864',
    'drawdown_penalty_applied',
    'overfit_penalty_applied',
    'stability_component_rewards_walk_forward_consistency',
  ],
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
    max_drawdown: 0.09,
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
    position_sizing_preview: baselinePositionSizingPreview,
    strategy_explanation: baselineStrategyExplanation,
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
    max_drawdown: 0.18,
    failure_rate: 0.09,
    portfolio_profit: 0.14,
    portfolio_drawdown: 0.13,
    best_genome_id: 'custom-gen003-ind009',
    genome: {
      ...baselineGenome,
      genome_id: 'custom-gen003-ind009',
      entry_bb_window: 26,
      leverage: 3,
      risk_per_trade: 0.02,
      max_portfolio_exposure: 0.55,
      cooldown_candles: 12,
    },
    strategy_config: {
      ...baselineStrategyConfig,
      genome_id: 'custom-gen003-ind009',
    },
    trading_system_config: {
      ...baselineTradingSystemConfig,
      strategy_id: 'custom-gen003-ind009',
      position: {
        ...baselineTradingSystemConfig.position,
        base_leverage: 3,
        max_leverage: 3,
        risk_per_trade: 0.02,
      },
      risk_control: {
        ...baselineTradingSystemConfig.risk_control,
        max_portfolio_exposure: 0.55,
        cooldown_candles: 12,
      },
    },
    risk_governor: {
      adjusted_leverage: 3,
      adjusted_risk_per_trade: 0.01,
      actions: ['reduced_risk_after_drawdown'],
    },
    position_sizing_preview: {
      schema_version: 'position-sizing/v1',
      position_value: 5500,
      margin_required: 1833.3333333333,
      risk_amount: 165,
      leverage: 3,
      warnings: [
        'high_leverage',
        'high_leverage_config',
        'high_portfolio_exposure',
        'max_position_value_applied',
        'risk_per_trade_near_upper_bound',
      ],
      source: 'trading-system-config',
      max_portfolio_exposure: 0.55,
      max_position_value: 5500,
    },
    strategy_explanation: {
      schema_version: 'strategy-explainability/v1',
      summary: 'Strategy profile requires risk review before any real backtest gate.',
      entry_logic: ['bollinger_window=26', 'bollinger_stddev=2.1', 'rsi_max=34'],
      exit_logic: ['stoploss_pct=0.03', 'takeprofit_pct=0.08', 'trailing_stop_pct=0.02'],
      risk_logic: [
        'leverage=3',
        'risk_per_trade=0.02',
        'max_portfolio_exposure=0.55',
        'risk_governor_action=reduced_risk_after_drawdown',
      ],
      warnings: [
        'drawdown_requires_risk_review',
        'high_leverage_strategy',
        'high_portfolio_exposure',
        'risk_governor:reduced_risk_after_drawdown',
        'risk_per_trade_near_limit',
      ],
      fitness_explanation: [
        'final_fitness=0.799',
        'drawdown_penalty_applied',
        'overfit_penalty_applied',
        'stability_component_rewards_walk_forward_consistency',
      ],
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
    max_drawdown: 0.08,
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
    position_sizing_preview: {
      ...baselinePositionSizingPreview,
      position_value: 3500,
      margin_required: 1750,
      risk_amount: 105,
      max_portfolio_exposure: 0.35,
      max_position_value: 3500,
      warnings: ['max_position_value_applied', 'portfolio_exposure_review'],
    },
    strategy_explanation: {
      ...baselineStrategyExplanation,
      summary: 'Portfolio-focused mock strategy with controlled drawdown and reviewable exposure.',
      warnings: ['portfolio_exposure_review'],
      fitness_explanation: [
        'final_fitness=0.812',
        'drawdown_penalty_applied',
        'overfit_penalty_applied',
        'stability_component_rewards_walk_forward_consistency',
      ],
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
