import { mockDelay } from './client';
import { mockGenerationMetrics } from '../mocks/gaRuns';
import { mockResults } from '../mocks/results';

export async function fetchGaRuns() {
  return mockDelay(mockGenerationMetrics);
}

export async function fetchResults() {
  return mockDelay(mockResults);
}
