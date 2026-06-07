export type ComparableRun = {
  run_id: string;
  best_fitness: number;
  max_drawdown: number;
  stability_score: number;
  portfolio_drawdown: number;
  leverage: number;
  risk_per_trade: number;
};

export const comparableRuns: ComparableRun[] = [
  {
    run_id: 'custom-ga-seed-42',
    best_fitness: 0.864,
    max_drawdown: 0.09,
    stability_score: 0.82,
    portfolio_drawdown: 0.09,
    leverage: 2,
    risk_per_trade: 0.012,
  },
  {
    run_id: 'custom-walk-forward-017',
    best_fitness: 0.799,
    max_drawdown: 0.18,
    stability_score: 0.76,
    portfolio_drawdown: 0.13,
    leverage: 3,
    risk_per_trade: 0.02,
  },
  {
    run_id: 'custom-portfolio-088',
    best_fitness: 0.812,
    max_drawdown: 0.08,
    stability_score: 0.79,
    portfolio_drawdown: 0.08,
    leverage: 2,
    risk_per_trade: 0.012,
  },
];

export type ComparisonMetric = {
  key: keyof Omit<ComparableRun, 'run_id'>;
  label: string;
  lowerIsBetter: boolean;
};

export const comparisonMetrics: ComparisonMetric[] = [
  { key: 'best_fitness', label: 'best_fitness', lowerIsBetter: false },
  { key: 'max_drawdown', label: 'max_drawdown', lowerIsBetter: true },
  { key: 'stability_score', label: 'stability_score', lowerIsBetter: false },
  { key: 'portfolio_drawdown', label: 'portfolio_drawdown', lowerIsBetter: true },
  { key: 'leverage', label: 'leverage', lowerIsBetter: true },
  { key: 'risk_per_trade', label: 'risk_per_trade', lowerIsBetter: true },
];
