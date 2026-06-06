import { mockDelay } from './client';
import { mockCoverageMatrix, mockGateResult, mockInventoryFiles, mockInventorySummary } from '../mocks/offlineData';

export async function fetchOfflineInventory() {
  return mockDelay({ files: mockInventoryFiles, summary: mockInventorySummary });
}

export async function fetchCoverageMatrix() {
  return mockDelay(mockCoverageMatrix);
}

export async function fetchGateResult() {
  return mockDelay(mockGateResult);
}
