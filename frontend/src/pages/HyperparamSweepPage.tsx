import { useMemo, useState } from 'react';
import { hyperparamSweepResults, type HyperparamSweepResult } from '../mocks/hyperparamSweepFixtures';

type SortKey = keyof Pick<
  HyperparamSweepResult,
  'rank' | 'fitness' | 'max_drawdown' | 'stability_score' | 'risk_per_trade' | 'leverage'
>;

const sortableColumns: Array<{ key: SortKey; label: string; lowerIsBetter?: boolean }> = [
  { key: 'rank', label: 'rank', lowerIsBetter: true },
  { key: 'fitness', label: 'fitness' },
  { key: 'max_drawdown', label: 'max_drawdown', lowerIsBetter: true },
  { key: 'stability_score', label: 'stability_score' },
  { key: 'risk_per_trade', label: 'risk_per_trade', lowerIsBetter: true },
  { key: 'leverage', label: 'leverage', lowerIsBetter: true },
];

function formatMetric(value: number) {
  return value.toFixed(3);
}

function sortResults(results: HyperparamSweepResult[], sortKey: SortKey) {
  const lowerIsBetter = sortableColumns.find((column) => column.key === sortKey)?.lowerIsBetter ?? false;
  return [...results].sort((left, right) => {
    const diff = left[sortKey] - right[sortKey];
    return lowerIsBetter ? diff : -diff;
  });
}

export default function HyperparamSweepPage() {
  const [sortKey, setSortKey] = useState<SortKey>('rank');
  const [minimumStability, setMinimumStability] = useState('0.00');
  const filteredRows = useMemo(() => {
    const threshold = Number.parseFloat(minimumStability) || 0;
    return sortResults(
      hyperparamSweepResults.filter((result) => result.stability_score >= threshold),
      sortKey,
    );
  }, [minimumStability, sortKey]);

  return (
    <section className="page-stack">
      <div className="section-heading">
        <p className="eyebrow">Mock sweep</p>
        <h2>Hyperparameter Sweep</h2>
        <p>Read-only fixture view for custom strategy parameter search results.</p>
      </div>

      <div className="panel editor-grid">
        <label>
          Sort metric
          <select aria-label="Sort metric" value={sortKey} onChange={(event) => setSortKey(event.target.value as SortKey)}>
            {sortableColumns.map((column) => (
              <option key={column.key} value={column.key}>
                {column.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Minimum stability
          <input
            aria-label="Minimum stability"
            inputMode="decimal"
            onChange={(event) => setMinimumStability(event.target.value)}
            type="number"
            value={minimumStability}
          />
        </label>
      </div>

      <div className="table-shell">
        <table>
          <thead>
            <tr>
              <th>run_id</th>
              <th>parameter set</th>
              {sortableColumns.map((column) => (
                <th key={column.key}>
                  <button type="button" onClick={() => setSortKey(column.key)}>
                    {column.label}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredRows.map((result) => (
              <tr key={result.run_id}>
                <td>{result.run_id}</td>
                <td>{result.parameter_set}</td>
                <td>{result.rank}</td>
                <td>{formatMetric(result.fitness)}</td>
                <td className={result.max_drawdown > 0.1 ? 'metric-risk' : 'metric-good'}>
                  {formatMetric(result.max_drawdown)}
                </td>
                <td className={result.stability_score >= 0.85 ? 'metric-good' : 'metric-risk'}>
                  {formatMetric(result.stability_score)}
                </td>
                <td>{formatMetric(result.risk_per_trade)}</td>
                <td className={result.leverage > 3 ? 'metric-risk' : 'metric-neutral'}>{formatMetric(result.leverage)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
