export type HyperparamSweepResult = {
  run_id: string;
  parameter_set: string;
  fitness: number;
  max_drawdown: number;
  stability_score: number;
  risk_per_trade: number;
  leverage: number;
  rank: number;
};

export const hyperparamSweepResults: HyperparamSweepResult[] = [
  {
    run_id: 'sweep-safe-001',
    parameter_set: 'bb_period=24, stddev=2.1, stoploss=0.035',
    fitness: 0.842,
    max_drawdown: 0.061,
    stability_score: 0.91,
    risk_per_trade: 0.014,
    leverage: 2.0,
    rank: 1,
  },
  {
    run_id: 'sweep-balanced-017',
    parameter_set: 'bb_period=32, stddev=2.4, stoploss=0.045',
    fitness: 0.801,
    max_drawdown: 0.074,
    stability_score: 0.86,
    risk_per_trade: 0.018,
    leverage: 2.5,
    rank: 2,
  },
  {
    run_id: 'sweep-stable-044',
    parameter_set: 'bb_period=40, stddev=2.8, stoploss=0.050',
    fitness: 0.764,
    max_drawdown: 0.052,
    stability_score: 0.94,
    risk_per_trade: 0.012,
    leverage: 1.8,
    rank: 3,
  },
  {
    run_id: 'sweep-high-risk-063',
    parameter_set: 'bb_period=18, stddev=1.8, stoploss=0.025',
    fitness: 0.733,
    max_drawdown: 0.142,
    stability_score: 0.63,
    risk_per_trade: 0.028,
    leverage: 4.0,
    rank: 4,
  },
];
