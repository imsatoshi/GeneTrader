import { riskGovernorAdjustments, type RiskGovernorAdjustment } from '../mocks/riskGovernorFixtures';

function formatMetric(value: number) {
  return value.toFixed(3);
}

function adjustmentClass(adjustment: RiskGovernorAdjustment) {
  if (adjustment.actions.includes('cooldown_applied') || adjustment.actions.includes('leverage_clamped')) {
    return 'risk-warning';
  }
  return 'risk-ok';
}

export default function RiskGovernorPanelPage() {
  const adjustedCount = riskGovernorAdjustments.filter((item) => item.actions.some((action) => action !== 'no_adjustment')).length;
  const maxCooldown = Math.max(...riskGovernorAdjustments.map((item) => item.cooldown_candles));
  const maxOriginalLeverage = Math.max(...riskGovernorAdjustments.map((item) => item.original_leverage));

  return (
    <section className="page-stack">
      <div className="section-heading">
        <p className="eyebrow">Risk governor</p>
        <h2>RiskGovernor Feedback</h2>
        <p>Mock-only review of leverage, risk, and cooldown adjustments.</p>
      </div>

      <div className="status-grid">
        <div className="status-card status-card-success">
          <span>Fixtures</span>
          <strong>{riskGovernorAdjustments.length}</strong>
          <small>mock strategies</small>
        </div>
        <div className="status-card status-card-warning">
          <span>Adjusted</span>
          <strong>{adjustedCount}</strong>
          <small>risk governor actions</small>
        </div>
        <div className="status-card status-card-danger">
          <span>Max leverage</span>
          <strong>{formatMetric(maxOriginalLeverage)}</strong>
          <small>original leverage</small>
        </div>
        <div className="status-card">
          <span>Cooldown</span>
          <strong>{maxCooldown}</strong>
          <small>max cooldown_candles</small>
        </div>
      </div>

      <div className="table-shell">
        <table>
          <thead>
            <tr>
              <th>fixture_id</th>
              <th>original leverage</th>
              <th>adjusted leverage</th>
              <th>original risk_per_trade</th>
              <th>adjusted risk_per_trade</th>
              <th>cooldown_candles</th>
              <th>actions</th>
              <th>warnings</th>
            </tr>
          </thead>
          <tbody>
            {riskGovernorAdjustments.map((adjustment) => (
              <tr key={adjustment.fixture_id}>
                <td>{adjustment.fixture_id}</td>
                <td>{formatMetric(adjustment.original_leverage)}</td>
                <td className={adjustment.adjusted_leverage < adjustment.original_leverage ? 'metric-good' : 'metric-neutral'}>
                  {formatMetric(adjustment.adjusted_leverage)}
                </td>
                <td>{formatMetric(adjustment.original_risk_per_trade)}</td>
                <td className={adjustment.adjusted_risk_per_trade < adjustment.original_risk_per_trade ? 'metric-good' : 'metric-neutral'}>
                  {formatMetric(adjustment.adjusted_risk_per_trade)}
                </td>
                <td>{adjustment.cooldown_candles}</td>
                <td>
                  <ul className="warning-list">
                    {adjustment.actions.map((action) => (
                      <li className={adjustmentClass(adjustment)} key={action}>
                        {action}
                      </li>
                    ))}
                  </ul>
                </td>
                <td>
                  {adjustment.warnings.length > 0 ? (
                    <ul className="warning-list">
                      {adjustment.warnings.map((warning) => (
                        <li key={warning}>{warning}</li>
                      ))}
                    </ul>
                  ) : (
                    <span className="risk-pill risk-ok">none</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
