export interface PreflightSummary {
  preflightOk: boolean;
  errorsCount: number;
  warningsCount: number;
  latestGaRun: {
    bestFitness: number;
    avgFitness: number;
  };
}
