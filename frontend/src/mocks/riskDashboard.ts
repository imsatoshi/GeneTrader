export type RiskDashboardRow = {
  run_id: string;
  max_drawdown: number;
  loss_streak: number;
  portfolio_exposure: number;
  risk_per_trade: number;
  leverage: number;
  circuit_breaker_status: 'none' | 'reduce_risk' | 'pause_trading';
  failure_rate: number;
};

export const riskDashboardRows: RiskDashboardRow[] = [
  {
    run_id: 'custom-ga-seed-42',
    max_drawdown: 0.09,
    loss_streak: 2,
    portfolio_exposure: 0.3,
    risk_per_trade: 0.012,
    leverage: 2,
    circuit_breaker_status: 'none',
    failure_rate: 0.06,
  },
  {
    run_id: 'custom-walk-forward-017',
    max_drawdown: 0.18,
    loss_streak: 7,
    portfolio_exposure: 0.55,
    risk_per_trade: 0.02,
    leverage: 3,
    circuit_breaker_status: 'reduce_risk',
    failure_rate: 0.09,
  },
  {
    run_id: 'custom-loss-streak-review',
    max_drawdown: 0.24,
    loss_streak: 9,
    portfolio_exposure: 0.48,
    risk_per_trade: 0.018,
    leverage: 2.5,
    circuit_breaker_status: 'pause_trading',
    failure_rate: 0.16,
  },
];
