export type PairExposure = {
  pair: string;
  exposure: number;
  profit: number;
  drawdown: number;
};

export type PortfolioSummary = {
  run_id: string;
  portfolio_profit: number;
  portfolio_drawdown: number;
  total_exposure: number;
  pair_exposures: PairExposure[];
  correlation_penalty: number;
  violations: string[];
  recommendations: string[];
};

export const portfolioSummaries: PortfolioSummary[] = [
  {
    run_id: 'portfolio-balanced-001',
    portfolio_profit: 0.164,
    portfolio_drawdown: 0.071,
    total_exposure: 0.28,
    pair_exposures: [
      { pair: 'BTC/USDT', exposure: 0.1, profit: 0.061, drawdown: 0.034 },
      { pair: 'ETH/USDT', exposure: 0.09, profit: 0.053, drawdown: 0.041 },
      { pair: 'SOL/USDT', exposure: 0.09, profit: 0.05, drawdown: 0.052 },
    ],
    correlation_penalty: 0.018,
    violations: [],
    recommendations: ['Maintain current exposure cap.'],
  },
  {
    run_id: 'portfolio-correlated-014',
    portfolio_profit: 0.118,
    portfolio_drawdown: 0.137,
    total_exposure: 0.42,
    pair_exposures: [
      { pair: 'BTC/USDT', exposure: 0.16, profit: 0.052, drawdown: 0.066 },
      { pair: 'ETH/USDT', exposure: 0.14, profit: 0.041, drawdown: 0.071 },
      { pair: 'BNB/USDT', exposure: 0.12, profit: 0.025, drawdown: 0.058 },
    ],
    correlation_penalty: 0.064,
    violations: ['total_exposure_above_limit'],
    recommendations: ['Reduce correlated large-cap exposure before real validation.'],
  },
  {
    run_id: 'portfolio-exposure-review',
    portfolio_profit: 0.086,
    portfolio_drawdown: 0.194,
    total_exposure: 0.58,
    pair_exposures: [
      { pair: 'BTC/USDT', exposure: 0.2, profit: 0.031, drawdown: 0.084 },
      { pair: 'ETH/USDT', exposure: 0.18, profit: 0.019, drawdown: 0.093 },
      { pair: 'SOL/USDT', exposure: 0.12, profit: 0.024, drawdown: 0.102 },
      { pair: 'AVAX/USDT', exposure: 0.08, profit: 0.012, drawdown: 0.077 },
    ],
    correlation_penalty: 0.091,
    violations: ['total_exposure_above_limit', 'portfolio_drawdown_above_limit'],
    recommendations: ['Clamp portfolio exposure below 0.30.', 'Review multi-pair loss streak handling.'],
  },
];
