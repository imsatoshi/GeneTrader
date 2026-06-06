import type { GenerationMetric } from '../types/ga';

export const mockGenerationMetrics: GenerationMetric[] = [
  { generation: 1, bestFitness: 0.42, avgFitness: 0.31, worstFitness: 0.12 },
  { generation: 2, bestFitness: 0.49, avgFitness: 0.35, worstFitness: 0.18 },
  { generation: 3, bestFitness: 0.61, avgFitness: 0.44, worstFitness: 0.21 },
  { generation: 4, bestFitness: 0.68, avgFitness: 0.52, worstFitness: 0.29 },
];
