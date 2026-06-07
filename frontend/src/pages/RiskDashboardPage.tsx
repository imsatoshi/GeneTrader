import { riskDashboardRows, type RiskDashboardRow } from '../mocks/riskDashboard';

function formatMetric(value: number) {
  return value.toFixed(3);
}

function riskClass(row: RiskDashboardRow) {
  if (row.circuit_breaker_status === 'pause_trading' || row.failure_rate >= 0.12 || row.max_drawdown >= 0.2) {
    return 'risk-critical';
  }
  if (
    row.circuit_breaker_status === 'reduce_risk' ||
    row.loss_streak >= 4 ||
    row.portfolio_exposure > 0.3 ||
    row.leverage >= 3
  ) {
    return 'risk-warning';
  }
  return 'risk-ok';
}

export default function RiskDashboardPage() {
  const highestFailureRate = Math.max(...riskDashboardRows.map((row) => row.failure_rate));
  const breakerCount = riskDashboardRows.filter((row) => row.circuit_breaker_status !== 'none').length;
  const highRiskCount = riskDashboardRows.filter((row) => riskClass(row) !== 'risk-ok').length;

  return (
    <section className="page-stack">
      <div className="section-heading">
        <p className="eyebrow">Risk</p>
        <h2>Risk Dashboard</h2>
        <p>Read-only mock risk view for custom strategy runs.</p>
      </div>

      <div className="status-grid">
        <div className="status-card status-card-danger">
          <span>High risk</span>
          <strong>{highRiskCount}</strong>
          <small>mock runs flagged</small>
        </div>
        <div className="status-card status-card-warning">
          <span>Circuit breakers</span>
          <strong>{breakerCount}</strong>
          <small>reduce or pause states</small>
        </div>
        <div className="status-card">
          <span>Failure rate</span>
          <strong>{formatMetric(highestFailureRate)}</strong>
          <small>Monte Carlo worst case</small>
        </div>
        <div className="status-card status-card-success">
          <span>Runs</span>
          <strong>{riskDashboardRows.length}</strong>
          <small>fixture-only rows</small>
        </div>
      </div>

      <div className="table-shell">
        <table>
          <thead>
            <tr>
              <th>run_id</th>
              <th>max_drawdown</th>
              <th>loss_streak</th>
              <th>portfolio_exposure</th>
              <th>risk_per_trade</th>
              <th>leverage</th>
              <th>circuit breaker status</th>
              <th>failure_rate</th>
              <th>risk level</th>
            </tr>
          </thead>
          <tbody>
            {riskDashboardRows.map((row) => (
              <tr key={row.run_id}>
                <td>{row.run_id}</td>
                <td>{formatMetric(row.max_drawdown)}</td>
                <td>{row.loss_streak}</td>
                <td>{formatMetric(row.portfolio_exposure)}</td>
                <td>{formatMetric(row.risk_per_trade)}</td>
                <td>{formatMetric(row.leverage)}</td>
                <td>{row.circuit_breaker_status}</td>
                <td>{formatMetric(row.failure_rate)}</td>
                <td>
                  <span className={`risk-pill ${riskClass(row)}`}>{riskClass(row)}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
