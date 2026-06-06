import StatusCard from '../components/StatusCard';
import { mockPreflightSummary } from '../mocks/preflight';

export default function OverviewPage() {
  const summary = mockPreflightSummary;
  return (
    <section className="page-stack">
      <div className="hero-panel">
        <p className="eyebrow">Overview</p>
        <h2>Offline readiness and GA signal at a glance.</h2>
        <p>Mock data drives this dashboard until the FastAPI/REST bridge is explicitly introduced.</p>
      </div>
      <div className="status-grid">
        <StatusCard label="Preflight" value={summary.preflightOk ? 'OK' : 'Blocked'} tone="success" detail="read-only gate" />
        <StatusCard label="Errors" value={summary.errorsCount} tone="neutral" />
        <StatusCard label="Warnings" value={summary.warningsCount} tone="warning" />
        <StatusCard label="Best fitness" value={summary.latestGaRun.bestFitness.toFixed(2)} tone="success" />
      </div>
      <div className="quick-actions">
        <a href="/offline-data">Review Offline Data</a>
        <a href="/requirements">Edit Requirements</a>
        <a href="/ga-runs">Inspect GA Runs</a>
      </div>
    </section>
  );
}
