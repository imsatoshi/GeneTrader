import { describe, expect, it } from 'vitest';
import { sessionSummary } from '../mocks/sessionSummary';

describe('sessionSummary contract', () => {
  it('uses schema v1', () => {
    expect(sessionSummary.schemaVersion).toBe('session-summary/v1');
  });

  it('keeps counts aligned with arrays', () => {
    expect(sessionSummary.offlineData.inventoryCount).toBe(sessionSummary.offlineData.inventory.length);
    expect(sessionSummary.offlineData.manifestDatasetCount).toBe(sessionSummary.offlineData.manifestDatasets.length);
    expect(sessionSummary.offlineData.gateErrorCount).toBe(sessionSummary.offlineData.gateErrors.length);
    expect(sessionSummary.offlineData.gateWarningCount).toBe(sessionSummary.offlineData.gateWarnings.length);
  });

  it('keeps missing combinations aligned with the coverage matrix', () => {
    for (const item of sessionSummary.requirementsGate.missingCombinations) {
      expect(sessionSummary.offlineData.coverageMatrix[item.pair]?.[item.timeframe]).toBe('missing');
    }
  });

  it('includes the current generation in the fitness series', () => {
    expect(sessionSummary.gaRunSummary.fitnessSeries).toContainEqual(
      expect.objectContaining({ generation: sessionSummary.gaRunSummary.generation }),
    );
  });

  it('is JSON serializable', () => {
    expect(() => JSON.stringify(sessionSummary)).not.toThrow();
  });
});
