import { describe, expect, it } from 'vitest';
import riskAwareArtifact from './__fixtures__/gaSessionArtifact.riskAware.json';
import { adaptGaSessionArtifact, fetchGaSessionSummary } from './gaSessionAdapter';

describe('gaSessionAdapter', () => {
  it('returns a typed GA session summary', async () => {
    const summary = await fetchGaSessionSummary();

    expect(summary.schemaVersion).toBe('ga-session-summary/v1');
    expect(summary.source).toBe('mock-ga-execution');
    expect(summary.runId).toBe('mock-ga-seed-2026');
    expect(summary.leaderboard[0].genomeId).toBe('gen003-ind002');
  });

  it('maps leaderboard entries in rank order', async () => {
    const summary = await fetchGaSessionSummary();

    expect(summary.leaderboard.map((item) => item.rank)).toEqual([1, 2, 3]);
    expect(summary.leaderboard.map((item) => item.fitness)).toEqual([0.472481, 0.331902, 0.118012]);
  });

  it('preserves risk-aware fields from Python GA artifact leaderboard entries', () => {
    const summary = adaptGaSessionArtifact(riskAwareArtifact);
    const entry = summary.leaderboard[0];

    expect(entry.fitnessComponents).toMatchObject({
      profit_component: 0.18,
      sharpe_component: 0.35,
      win_rate_component: 0.057,
      drawdown_penalty: 0.16,
      leverage_penalty: 0,
      risk_per_trade_penalty: 0,
      loss_streak_penalty: 0.45,
      final_fitness: 1.23,
    });
    expect(entry.maxLossStreak).toBe(3);
    expect(entry.leverage).toBe(2.0);
    expect(entry.riskPerTrade).toBe(0.015);
  });

  it('handles legacy leaderboard entries without risk-aware fields', () => {
    const summary = adaptGaSessionArtifact({
      schema_version: 'ga-session-summary/v1',
      source: 'mock-ga-execution',
      run_id: 'legacy-run',
      generation: 1,
      population_size: 1,
      best_fitness: 0.1,
      average_fitness: 0.1,
      diversity: 1,
      best_genome: {},
      fitness_series: [{ generation: 1, best_fitness: 0.1, average_fitness: 0.1, diversity: 1 }],
      leaderboard: [
        {
          rank: 1,
          genome_id: 'legacy-genome',
          fitness: 0.1,
          profit: 0.2,
          drawdown: 0.05,
          sharpe: 1.1,
          win_rate: 0.5,
          genome: {},
        },
      ],
    });
    const entry = summary.leaderboard[0];

    expect(entry.fitnessComponents).toEqual({});
    expect(entry.maxLossStreak).toBeNull();
    expect(entry.leverage).toBeNull();
    expect(entry.riskPerTrade).toBeNull();
  });

  it('maps fitness series to camelCase fields', async () => {
    const summary = await fetchGaSessionSummary();

    expect(summary.fitnessSeries[0]).toEqual({
      generation: 1,
      bestFitness: 0.251044,
      averageFitness: 0.103117,
      diversity: 1,
    });
  });

  it('can select a different mock run id', async () => {
    const summary = await fetchGaSessionSummary('mock-ga-seed-88');

    expect(summary.runId).toBe('mock-ga-seed-88');
    expect(summary.generation).toBe(2);
  });

  it('falls back to the default artifact for unknown run ids', async () => {
    const summary = await fetchGaSessionSummary('missing-run');

    expect(summary.runId).toBe('mock-ga-seed-2026');
  });
});
