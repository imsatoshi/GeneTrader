import { portfolioSummaries, type PortfolioSummary } from '../mocks/portfolioFixtures';

function formatMetric(value: number) {
  return value.toFixed(3);
}

function exposureClass(summary: PortfolioSummary) {
  if (summary.total_exposure > 0.5 || summary.portfolio_drawdown >= 0.18) {
    return 'risk-critical';
  }
  if (summary.total_exposure > 0.3 || summary.violations.length > 0) {
    return 'risk-warning';
  }
  return 'risk-ok';
}

export default function PortfolioSummaryPage() {
  const maxDrawdown = Math.max(...portfolioSummaries.map((summary) => summary.portfolio_drawdown));
  const maxExposure = Math.max(...portfolioSummaries.map((summary) => summary.total_exposure));
  const breachCount = portfolioSummaries.filter((summary) => summary.violations.length > 0).length;

  return (
    <section className="page-stack">
      <div className="section-heading">
        <p className="eyebrow">Portfolio</p>
        <h2>Portfolio Exposure</h2>
        <p>Mock-only multi-pair exposure review for custom strategy runs.</p>
      </div>

      <div className="status-grid">
        <div className="status-card status-card-success">
          <span>Portfolios</span>
          <strong>{portfolioSummaries.length}</strong>
          <small>fixture groups</small>
        </div>
        <div className="status-card status-card-danger">
          <span>Exposure breach</span>
          <strong>{breachCount}</strong>
          <small>mock portfolios flagged</small>
        </div>
        <div className="status-card">
          <span>Total exposure</span>
          <strong>{formatMetric(maxExposure)}</strong>
          <small>highest fixture exposure</small>
        </div>
        <div className="status-card status-card-warning">
          <span>Drawdown</span>
          <strong>{formatMetric(maxDrawdown)}</strong>
          <small>portfolio_drawdown max</small>
        </div>
      </div>

      {portfolioSummaries.map((summary) => (
        <section className="panel" key={summary.run_id}>
          <div className="section-heading">
            <h3>{summary.run_id}</h3>
            <p>
              portfolio_profit {formatMetric(summary.portfolio_profit)} / portfolio_drawdown{' '}
              {formatMetric(summary.portfolio_drawdown)} / correlation_penalty{' '}
              {formatMetric(summary.correlation_penalty)}
            </p>
            <span className={`risk-pill ${exposureClass(summary)}`}>total_exposure {formatMetric(summary.total_exposure)}</span>
          </div>

          <div className="table-shell compact-table">
            <table>
              <thead>
                <tr>
                  <th>pair</th>
                  <th>exposure</th>
                  <th>profit</th>
                  <th>drawdown</th>
                </tr>
              </thead>
              <tbody>
                {summary.pair_exposures.map((pair) => (
                  <tr key={pair.pair}>
                    <td>{pair.pair}</td>
                    <td className={pair.exposure > 0.15 ? 'metric-risk' : 'metric-neutral'}>{formatMetric(pair.exposure)}</td>
                    <td>{formatMetric(pair.profit)}</td>
                    <td>{formatMetric(pair.drawdown)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="detail-grid">
            <section>
              <h4>violations</h4>
              {summary.violations.length > 0 ? (
                <ul className="warning-list">
                  {summary.violations.map((violation) => (
                    <li key={violation}>{violation}</li>
                  ))}
                </ul>
              ) : (
                <p className="muted-text">none</p>
              )}
            </section>
            <section>
              <h4>recommendations</h4>
              <ul className="insight-list">
                {summary.recommendations.map((recommendation) => (
                  <li key={recommendation}>{recommendation}</li>
                ))}
              </ul>
            </section>
          </div>
        </section>
      ))}
    </section>
  );
}
