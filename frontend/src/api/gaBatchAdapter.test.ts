import { describe, expect, it } from 'vitest';
import batchArtifact from './__fixtures__/gaBatchArtifact.json';
import { adaptSmallBatchArtifactToDashboard, fetchGaBatchSummary } from './gaBatchAdapter';

describe('gaBatchAdapter', () => {
  it('maps the STAGE-093 small-batch artifact to dashboard contract fields', async () => {
    const summary = await fetchGaBatchSummary();

    expect(summary.batchId).toBe('small-batch-mock-001');
    expect(summary.status).toBe('partial_success');
    expect(summary.totalJobs).toBe(5);
    expect(summary.succeeded).toBe(1);
    expect(summary.failed).toBe(1);
    expect(summary.skipped).toBe(1);
    expect(summary.timedOut).toBe(1);
    expect(summary.policyRejected).toBe(1);
  });

  it('maps success job metrics and fitness components', () => {
    const summary = adaptSmallBatchArtifactToDashboard(batchArtifact);
    const success = summary.leaderboard.find((item) => item.status === 'success');

    expect(success?.normalizedMetrics).toMatchObject({
      profit: 0.21,
      sharpe: 1.52,
      winRate: 0.61,
      maxDrawdown: 0.07,
      totalTrades: 42,
      maxConsecutiveLosses: 2,
      leverage: 2.4,
      riskPerTrade: 0.014,
    });
    expect(success?.fitnessComponents).toMatchObject({
      drawdown_penalty: 0.14,
      final_fitness: 0.211,
    });
  });

  it('keeps failure-aware statuses for all job outcomes', () => {
    const summary = adaptSmallBatchArtifactToDashboard(batchArtifact);

    expect(summary.leaderboard.map((item) => item.status)).toEqual([
      'success',
      'failed',
      'skipped',
      'timeout',
      'policy_rejected',
    ]);
  });

  it('redacts paths and secret-like tokens from errors and metadata', () => {
    const summary = adaptSmallBatchArtifactToDashboard({
      batch_id: 'batch-with-sensitive-error',
      status: 'all_failed',
      results: [
        {
          job_id: 'job-sensitive',
          genome_hash: 'hash-sensitive',
          status: 'failed',
          error_type: 'ValueError',
          error_message: 'C:/Users/name/.env api_key=abc password=bad',
          metadata: { api_key: 'abc', nested: { password: 'bad' } },
        },
      ],
      metadata: { secret: 'bad', path: 'C:/Users/name/file.json' },
    });
    const encoded = JSON.stringify(summary);

    expect(encoded).not.toContain('C:/Users');
    expect(encoded).not.toContain('.env');
    expect(encoded.toLowerCase()).not.toContain('api_key');
    expect(encoded.toLowerCase()).not.toContain('password');
  });

  it('handles legacy camelCase artifacts', () => {
    const summary = adaptSmallBatchArtifactToDashboard({
      batchId: 'legacy-batch',
      status: 'all_success',
      totalJobs: 1,
      timedOut: 0,
      policyRejected: 0,
      results: [
        {
          jobId: 'legacy-job',
          genomeHash: 'legacy-hash',
          status: 'success',
          normalizedResult: {
            profit: 0.1,
            sharpe: 1,
            winRate: 0.5,
            maxDrawdown: 0.05,
            totalTrades: 10,
            maxConsecutiveLosses: 1,
            leverage: 2,
            riskPerTrade: 0.01,
            fitnessComponents: { final_fitness: 0.1 },
          },
        },
      ],
    });

    expect(summary.batchId).toBe('legacy-batch');
    expect(summary.leaderboard[0].jobId).toBe('legacy-job');
    expect(summary.leaderboard[0].normalizedMetrics?.winRate).toBe(0.5);
  });
});
