import { fetchGateResult, fetchOfflineInventory } from './offline';
import { fetchGaRuns, fetchResults } from './ga';

describe('mock API client', () => {
  it('returns offline mock data promises', async () => {
    await expect(fetchOfflineInventory()).resolves.toHaveProperty('files');
    await expect(fetchGateResult()).resolves.toHaveProperty('ok', true);
  });

  it('returns GA mock data promises', async () => {
    await expect(fetchGaRuns()).resolves.toHaveLength(4);
    await expect(fetchResults()).resolves.toHaveLength(3);
  });
});
