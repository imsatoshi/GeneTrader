export type MonteCarloSummary = {
  run_id: string;
  runs: number;
  profit_p05: number;
  profit_median: number;
  profit_p95: number;
  drawdown_p95: number;
  failure_rate: number;
  worst_case_summary: string;
};

export const monteCarloSummaries: MonteCarloSummary[] = [
  {
    run_id: 'custom-ga-seed-42',
    runs: 250,
    profit_p05: 0.041,
    profit_median: 0.128,
    profit_p95: 0.238,
    drawdown_p95: 0.082,
    failure_rate: 0.032,
    worst_case_summary: 'Small profit erosion under shuffled late-cycle losses.',
  },
  {
    run_id: 'custom-walk-forward-017',
    runs: 250,
    profit_p05: -0.018,
    profit_median: 0.092,
    profit_p95: 0.204,
    drawdown_p95: 0.137,
    failure_rate: 0.112,
    worst_case_summary: 'Validation drift creates clustered losses during volatile windows.',
  },
  {
    run_id: 'custom-loss-streak-review',
    runs: 250,
    profit_p05: -0.074,
    profit_median: 0.044,
    profit_p95: 0.151,
    drawdown_p95: 0.221,
    failure_rate: 0.184,
    worst_case_summary: 'Loss streak perturbation triggers drawdown circuit breaker review.',
  },
];
