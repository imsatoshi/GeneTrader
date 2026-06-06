import { useMemo, useState } from 'react';
import { customRunRegistry, type CustomExperimentRun } from '../mocks/runRegistryCustom';

type SortKey = 'best_fitness' | 'generations' | 'run_id';

function formatMetric(value: number, digits = 3) {
  return value.toFixed(digits);
}

function latestRun(runs: CustomExperimentRun[]) {
  return [...runs].sort((left, right) => right.created_at.localeCompare(left.created_at))[0];
}

function previewJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}

export default function RunExplorerCustomPage() {
  const runs = customRunRegistry;
  const [sortKey, setSortKey] = useState<SortKey>('best_fitness');
  const [minStability, setMinStability] = useState(0);
  const [maxPortfolioDrawdown, setMaxPortfolioDrawdown] = useState(1);
  const [selectedRunId, setSelectedRunId] = useState(runs[0]?.run_id ?? '');
  const [showJsonExport, setShowJsonExport] = useState(false);
  const latest = latestRun(runs);
  const bestFitness = Math.max(...runs.map((run) => run.best_fitness));
  const averageStability = runs.reduce((total, run) => total + run.stability_score, 0) / runs.length;
  const visibleRuns = useMemo(() => {
    return runs
      .filter((run) => run.stability_score >= minStability)
      .filter((run) => run.portfolio_drawdown <= maxPortfolioDrawdown)
      .sort((left, right) => {
        if (sortKey === 'run_id') {
          return left.run_id.localeCompare(right.run_id);
        }
        return Number(right[sortKey]) - Number(left[sortKey]);
      });
  }, [runs, sortKey, minStability, maxPortfolioDrawdown]);
  const selectedRun = visibleRuns.find((run) => run.run_id === selectedRunId) ?? visibleRuns[0];

  return (
    <section className="page-stack">
      <div className="section-heading">
        <p className="eyebrow">Custom Strategy</p>
        <h2>Custom Run Explorer</h2>
        <p>Read-only fixture view of custom GA sessions, robustness checks, and portfolio reviews.</p>
      </div>

      <div className="status-grid">
        <div className="status-card status-card-success">
          <span>Runs</span>
          <strong>{runs.length}</strong>
          <small>custom registry rows</small>
        </div>
        <div className="status-card">
          <span>Best fitness</span>
          <strong>{formatMetric(bestFitness)}</strong>
          <small>top custom score</small>
        </div>
        <div className="status-card status-card-warning">
          <span>Stability</span>
          <strong>{formatMetric(averageStability)}</strong>
          <small>average walk-forward score</small>
        </div>
        <div className="status-card">
          <span>Latest</span>
          <strong>{latest?.seed ?? 'N/A'}</strong>
          <small>{latest?.run_id ?? 'no run'}</small>
        </div>
      </div>

      <div className="panel editor-grid">
        <label>
          Sort
          <select value={sortKey} onChange={(event) => setSortKey(event.target.value as SortKey)}>
            <option value="best_fitness">best_fitness</option>
            <option value="generations">generations</option>
            <option value="run_id">run_id</option>
          </select>
        </label>
        <label>
          Min stability
          <input
            aria-label="Minimum stability score"
            max="1"
            min="0"
            step="0.01"
            type="number"
            value={minStability}
            onChange={(event) => setMinStability(Number(event.target.value || 0))}
          />
        </label>
        <label>
          Max portfolio drawdown
          <input
            aria-label="Maximum portfolio drawdown"
            max="1"
            min="0"
            step="0.01"
            type="number"
            value={maxPortfolioDrawdown}
            onChange={(event) => setMaxPortfolioDrawdown(Number(event.target.value || 0))}
          />
        </label>
        <button type="button" onClick={() => setShowJsonExport((value) => !value)}>
          Export JSON
        </button>
      </div>

      <div className="table-shell">
        <table>
          <thead>
            <tr>
              <th>run_id</th>
              <th>source</th>
              <th>best_fitness</th>
              <th>stability_score</th>
              <th>failure_rate</th>
              <th>portfolio_profit</th>
              <th>portfolio_drawdown</th>
              <th>best_genome_id</th>
              <th>status</th>
            </tr>
          </thead>
          <tbody>
            {visibleRuns.map((run) => (
              <tr key={run.run_id} onClick={() => setSelectedRunId(run.run_id)}>
                <td data-testid="custom-run-id">{run.run_id}</td>
                <td>{run.source}</td>
                <td>{formatMetric(run.best_fitness)}</td>
                <td>{formatMetric(run.stability_score)}</td>
                <td>{formatMetric(run.failure_rate)}</td>
                <td>{formatMetric(run.portfolio_profit)}</td>
                <td>{formatMetric(run.portfolio_drawdown)}</td>
                <td>{run.best_genome_id}</td>
                <td>{run.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selectedRun ? (
        <div className="panel custom-detail-view">
          <div className="section-heading">
            <p className="eyebrow">Selected Run</p>
            <h2>{selectedRun.run_id}</h2>
          </div>
          <div className="summary-grid">
            <span>Source: {selectedRun.source}</span>
            <span>Genome: {selectedRun.best_genome_id}</span>
            <span>Portfolio drawdown: {formatMetric(selectedRun.portfolio_drawdown)}</span>
            <span>Artifact dir: {selectedRun.artifact_dir}</span>
          </div>
          <p>{selectedRun.notes}</p>
          <div className="detail-grid">
            <section>
              <h3>Genome Parameters</h3>
              <pre className="json-preview">{previewJson(selectedRun.genome)}</pre>
            </section>
            <section>
              <h3>StrategyConfig</h3>
              <pre className="json-preview">{previewJson(selectedRun.strategy_config)}</pre>
            </section>
            <section>
              <h3>RiskGovernor Adjustments</h3>
              <div className="summary-grid">
                <span>Adjusted leverage: {formatMetric(selectedRun.risk_governor.adjusted_leverage, 2)}</span>
                <span>
                  Adjusted risk per trade: {formatMetric(selectedRun.risk_governor.adjusted_risk_per_trade, 3)}
                </span>
                <span>Actions: {selectedRun.risk_governor.actions.join(', ')}</span>
              </div>
            </section>
            <section>
              <h3>TradingSystemConfig Preview</h3>
              <pre className="json-preview">{previewJson(selectedRun.trading_system_config)}</pre>
            </section>
            <section>
              <h3>Fitness Components</h3>
              <pre className="json-preview">{previewJson(selectedRun.fitness_components)}</pre>
            </section>
            <section>
              <h3>Walk-forward Stability</h3>
              <div className="summary-grid">
                <span>
                  Stability: {formatMetric(selectedRun.robustness_summary.walk_forward.stability_score)}
                </span>
                <span>
                  Train/validation gap:{' '}
                  {formatMetric(selectedRun.robustness_summary.walk_forward.train_validation_gap)}
                </span>
                <span>
                  Validation/test gap:{' '}
                  {formatMetric(selectedRun.robustness_summary.walk_forward.validation_test_gap)}
                </span>
              </div>
            </section>
            <section>
              <h3>Monte Carlo Summary</h3>
              <div className="summary-grid">
                <span>Runs: {selectedRun.robustness_summary.monte_carlo.runs}</span>
                <span>Profit p05: {formatMetric(selectedRun.robustness_summary.monte_carlo.profit_p05)}</span>
                <span>
                  Drawdown p95: {formatMetric(selectedRun.robustness_summary.monte_carlo.drawdown_p95)}
                </span>
                <span>Failure rate: {formatMetric(selectedRun.robustness_summary.monte_carlo.failure_rate)}</span>
              </div>
            </section>
            <section>
              <h3>Portfolio Summary</h3>
              <div className="summary-grid">
                <span>Profit: {formatMetric(selectedRun.robustness_summary.portfolio.portfolio_profit)}</span>
                <span>Drawdown: {formatMetric(selectedRun.robustness_summary.portfolio.portfolio_drawdown)}</span>
                <span>
                  Correlation penalty:{' '}
                  {formatMetric(selectedRun.robustness_summary.portfolio.correlation_penalty)}
                </span>
              </div>
            </section>
          </div>
        </div>
      ) : null}

      {showJsonExport ? (
        <pre aria-label="mock json export" className="json-preview">
          {JSON.stringify(visibleRuns, null, 2)}
        </pre>
      ) : null}

      <div className="manifest-list">
        {visibleRuns.map((run) => (
          <details className="batch-job-card" key={`${run.run_id}-details`}>
            <summary>
              <span>open details</span>
              <span>{run.run_id}</span>
              <span>{run.strategy_family}</span>
            </summary>
            <div className="batch-job-detail">
              <div className="summary-grid">
                <span>Created: {run.created_at}</span>
                <span>Population: {run.population_size}</span>
                <span>Generations: {run.generations}</span>
                <span>Artifact dir: {run.artifact_dir}</span>
              </div>
              <p>{run.notes}</p>
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}
