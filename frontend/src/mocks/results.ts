import type { ResultCandidate } from '../types/ga';

export const mockResults: ResultCandidate[] = [
  {
    rank: 1,
    fitness: 0.68,
    profit: 14.2,
    sharpe: 1.42,
    drawdown: 6.1,
    parameters: { bbPeriod: 24, bbStd: 2.4, mode: 'hybrid' },
  },
  {
    rank: 2,
    fitness: 0.61,
    profit: 11.7,
    sharpe: 1.2,
    drawdown: 8.3,
    parameters: { bbPeriod: 20, bbStd: 2.2, mode: 'breakout' },
  },
  {
    rank: 3,
    fitness: 0.53,
    profit: 9.4,
    sharpe: 1.06,
    drawdown: 9.8,
    parameters: { bbPeriod: 30, bbStd: 2.8, mode: 'mean_reversion' },
  },
];
