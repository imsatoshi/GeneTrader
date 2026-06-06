import { useEffect, useState } from 'react';
import { fetchGaBatchSummary, type GaBatchLeaderboardEntry, type GaBatchSummary } from '../api/gaBatchAdapter';

const statusLabels: Record<string, string> = {
  success: 'Success',
  failed: 'Failed',
  skipped: 'Skipped',
  timeout: 'Timeout',
  policy_rejected: 'Policy rejected',
  all_success: 'All success',
  partial_success: 'Partial success',
  all_failed: 'All failed',
};

function formatPercent(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}

function JobDetail({ job }: { job: GaBatchLeaderboardEntry }) {
  if (job.status !== 'success') {
    return (
      <div className="batch-job-detail">
        <strong>{job.errorType ?? 'No error type'}</strong>
        <span>{job.errorMessage ?? 'No error message provided'}</span>
      </div>
    );
  }

  return (
    <div className="batch-job-detail">
      <div className="summary-grid">
        <span>Profit: {formatPercent(job.normalizedMetrics?.profit ?? 0)}</span>
        <span>Sharpe: {job.normalizedMetrics?.sharpe ?? 0}</span>
        <span>Win rate: {formatPercent(job.normalizedMetrics?.winRate ?? 0)}</span>
        <span>Max drawdown: {formatPercent(job.normalizedMetrics?.maxDrawdown ?? 0)}</span>
        <span>Total trades: {job.normalizedMetrics?.totalTrades ?? 0}</span>
        <span>Max loss streak: {job.normalizedMetrics?.maxConsecutiveLosses ?? 0}</span>
        <span>Leverage: {job.normalizedMetrics?.leverage ?? 0}</span>
        <span>Risk per trade: {job.normalizedMetrics?.riskPerTrade ?? 0}</span>
      </div>
      <dl className="summary-grid">
        {Object.entries(job.fitnessComponents ?? {}).map(([key, value]) => (
          <div key={key}>
            <dt>{key}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function BatchJobRow({ job }: { job: GaBatchLeaderboardEntry }) {
  return (
    <details className={`batch-job-card batch-job-card-${job.status}`}>
      <summary>
        <span>{job.jobId}</span>
        <span>{job.genomeHash}</span>
        <strong>{statusLabels[job.status] ?? job.status}</strong>
      </summary>
      <JobDetail job={job} />
    </details>
  );
}

export default function MockBatchDashboardPage() {
  const [summary, setSummary] = useState<GaBatchSummary | null>(null);

  useEffect(() => {
    let active = true;
    fetchGaBatchSummary().then((nextSummary) => {
      if (active) {
        setSummary(nextSummary);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  if (!summary) {
    return <section className="panel">Loading small-batch dashboard...</section>;
  }

  return (
    <section className="page-stack">
      <div className="section-heading">
        <p className="eyebrow">Small Batch Queue</p>
        <h2>Batch Result Dashboard</h2>
        <p>
          Failure-aware read-only view for STAGE-093 small-batch results. This page renders mock
          artifacts only and does not call Freqtrade, exchanges, subprocesses, or external APIs.
        </p>
      </div>

      <div className="panel">
        <h3>Batch Contract</h3>
        <div className="summary-grid">
          <span>Batch ID: {summary.batchId}</span>
          <span>Status: {statusLabels[summary.status] ?? summary.status}</span>
          <span>Total jobs: {summary.totalJobs}</span>
          <span>Mock-first: {String(summary.metadata?.allow_real_execution === false)}</span>
        </div>
      </div>

      <div className="status-grid">
        <div className="status-card status-card-success">
          <span>Succeeded</span>
          <strong>{summary.succeeded}</strong>
          <small>normalized metrics available</small>
        </div>
        <div className="status-card status-card-danger">
          <span>Failed</span>
          <strong>{summary.failed}</strong>
          <small>redacted error shown</small>
        </div>
        <div className="status-card status-card-warning">
          <span>Skipped</span>
          <strong>{summary.skipped}</strong>
          <small>after prior failure or policy</small>
        </div>
        <div className="status-card status-card-danger">
          <span>Timeout / Policy</span>
          <strong>{summary.timedOut + summary.policyRejected}</strong>
          <small>{summary.timedOut} timeout, {summary.policyRejected} policy rejected</small>
        </div>
      </div>

      <div className="panel">
        <h3>Per-Genome Results</h3>
        <div className="batch-job-list">
          {summary.leaderboard.map((job) => (
            <BatchJobRow key={job.jobId} job={job} />
          ))}
        </div>
      </div>
    </section>
  );
}
