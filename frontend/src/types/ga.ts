export interface GenerationMetric {
  generation: number;
  bestFitness: number;
  avgFitness: number;
  worstFitness: number;
}

export interface ResultCandidate {
  rank: number;
  fitness: number;
  profit: number;
  sharpe: number;
  drawdown: number;
  parameters: Record<string, string | number>;
}
