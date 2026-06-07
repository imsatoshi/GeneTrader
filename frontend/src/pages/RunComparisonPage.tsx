import { useMemo, useState } from 'react';
import { comparableRuns, comparisonMetrics, type ComparableRun } from '../mocks/runComparison';

function formatMetric(value: number) {
  return value.toFixed(3);
}

function findRun(runId: string): ComparableRun {
  return comparableRuns.find((run) => run.run_id === runId) ?? comparableRuns[0];
}

function diffClass(diff: number, lowerIsBetter: boolean) {
  if (diff === 0) {
    return 'metric-neutral';
  }
  const improved = lowerIsBetter ? diff < 0 : diff > 0;
  return improved ? 'metric-good' : 'metric-risk';
}

export default function RunComparisonPage() {
  const [leftRunId, setLeftRunId] = useState(comparableRuns[0]?.run_id ?? '');
  const [rightRunId, setRightRunId] = useState(comparableRuns[1]?.run_id ?? '');
  const leftRun = findRun(leftRunId);
  const rightRun = findRun(rightRunId);
  const rows = useMemo(
    () =>
      comparisonMetrics.map((metric) => {
        const leftValue = leftRun[metric.key];
        const rightValue = rightRun[metric.key];
        return {
          ...metric,
          leftValue,
          rightValue,
          diff: rightValue - leftValue,
        };
      }),
    [leftRun, rightRun],
  );

  return (
    <section className="page-stack">
      <div className="section-heading">
        <p className="eyebrow">Comparison</p>
        <h2>Run Comparison</h2>
        <p>Read-only mock comparison across custom GA run metrics.</p>
      </div>

      <div className="panel editor-grid">
        <label>
          Run A
          <select aria-label="Run A" value={leftRunId} onChange={(event) => setLeftRunId(event.target.value)}>
            {comparableRuns.map((run) => (
              <option key={run.run_id} value={run.run_id}>
                {run.run_id}
              </option>
            ))}
          </select>
        </label>
        <label>
          Run B
          <select aria-label="Run B" value={rightRunId} onChange={(event) => setRightRunId(event.target.value)}>
            {comparableRuns.map((run) => (
              <option key={run.run_id} value={run.run_id}>
                {run.run_id}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="table-shell">
        <table>
          <thead>
            <tr>
              <th>metric</th>
              <th>{leftRun.run_id}</th>
              <th>{rightRun.run_id}</th>
              <th>difference</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key}>
                <td>{row.label}</td>
                <td>{formatMetric(row.leftValue)}</td>
                <td>{formatMetric(row.rightValue)}</td>
                <td className={diffClass(row.diff, row.lowerIsBetter)}>{formatMetric(row.diff)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
