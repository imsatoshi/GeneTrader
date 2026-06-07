import { monteCarloSummaries, type MonteCarloSummary } from '../mocks/monteCarloFixtures';

function formatMetric(value: number) {
  return value.toFixed(3);
}

function failureClass(summary: MonteCarloSummary) {
  if (summary.failure_rate >= 0.15 || summary.drawdown_p95 >= 0.2) {
    return 'risk-critical';
  }
  if (summary.failure_rate >= 0.1 || summary.drawdown_p95 >= 0.12) {
    return 'risk-warning';
  }
  return 'risk-ok';
}

export default function MonteCarloPanelPage() {
  const highestFailureRate = Math.max(...monteCarloSummaries.map((summary) => summary.failure_rate));
  const worstDrawdown = Math.max(...monteCarloSummaries.map((summary) => summary.drawdown_p95));
  const warningCount = monteCarloSummaries.filter((summary) => failureClass(summary) !== 'risk-ok').length;

  return (
    <section className="page-stack">
      <div className="section-heading">
        <p className="eyebrow">Stress test</p>
        <h2>Monte Carlo Summary</h2>
        <p>Fixture-only perturbation summary for custom strategy robustness checks.</p>
      </div>

      <div className="status-grid">
        <div className="status-card status-card-success">
          <span>Mock runs</span>
          <strong>{monteCarloSummaries[0]?.runs ?? 0}</strong>
          <small>per fixture</small>
        </div>
        <div className="status-card status-card-warning">
          <span>Warnings</span>
          <strong>{warningCount}</strong>
          <small>runs need review</small>
        </div>
        <div className="status-card status-card-danger">
          <span>Failure rate</span>
          <strong>{formatMetric(highestFailureRate)}</strong>
          <small>highest fixture rate</small>
        </div>
        <div className="status-card">
          <span>Drawdown p95</span>
          <strong>{formatMetric(worstDrawdown)}</strong>
          <small>worst fixture drawdown</small>
        </div>
      </div>

      <div className="table-shell">
        <table>
          <thead>
            <tr>
              <th>run_id</th>
              <th>runs</th>
              <th>profit_p05</th>
              <th>profit_median</th>
              <th>profit_p95</th>
              <th>drawdown_p95</th>
              <th>failure_rate</th>
              <th>worst_case_summary</th>
            </tr>
          </thead>
          <tbody>
            {monteCarloSummaries.map((summary) => (
              <tr key={summary.run_id}>
                <td>{summary.run_id}</td>
                <td>{summary.runs}</td>
                <td>{formatMetric(summary.profit_p05)}</td>
                <td>{formatMetric(summary.profit_median)}</td>
                <td>{formatMetric(summary.profit_p95)}</td>
                <td>{formatMetric(summary.drawdown_p95)}</td>
                <td>
                  <span className={`risk-pill ${failureClass(summary)}`}>{formatMetric(summary.failure_rate)}</span>
                </td>
                <td>{summary.worst_case_summary}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
