import type { PreflightSummary } from '../types/preflight';

export const mockPreflightSummary: PreflightSummary = {
  preflightOk: true,
  errorsCount: 0,
  warningsCount: 1,
  latestGaRun: {
    bestFitness: 0.68,
    avgFitness: 0.52,
  },
};
