import { mockRunRegistry, type MockExperimentRun } from '../mocks/runRegistry';

function formatFitness(value: number) {
  return value.toFixed(3);
}

function latestRun(runs: MockExperimentRun[]) {
  return [...runs].sort((left, right) => right.created_at.localeCompare(left.created_at))[0];
}

export default function RunExplorerPage() {
  const runs = mockRunRegistry;
  const completed = runs.filter((run) => run.status === 'completed').length;
  const latest = latestRun(runs);

  return (
    <section className="page-stack">
      <div className="section-heading">
        <p className="eyebrow">Run Explorer</p>
        <h2>Mock Experiment Registry</h2>
        <p>Read-only fixture view of GA experiment runs and generated artifact metadata.</p>
      </div>

      <div className="status-grid">
        <div className="status-card status-card-success">
          <span>Runs</span>
          <strong>{runs.length}</strong>
          <small>mock registry records</small>
        </div>
        <div className="status-card">
          <span>Completed</span>
          <strong>{completed}</strong>
          <small>ready for review</small>
        </div>
        <div className="status-card status-card-warning">
          <span>Latest</span>
          <strong>{latest?.seed ?? 'N/A'}</strong>
          <small>{latest?.run_id ?? 'no run'}</small>
        </div>
        <div className="status-card">
          <span>Best fitness</span>
          <strong>{formatFitness(Math.max(...runs.map((run) => run.best_fitness)))}</strong>
          <small>top mock score</small>
        </div>
      </div>

      <div className="table-shell">
        <table>
          <thead>
            <tr>
              <th>run_id</th>
              <th>created_at</th>
              <th>best_fitness</th>
              <th>generations</th>
              <th>population_size</th>
              <th>status</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.run_id}>
                <td>{run.run_id}</td>
                <td>{run.created_at}</td>
                <td>{formatFitness(run.best_fitness)}</td>
                <td>{run.generations}</td>
                <td>{run.population_size}</td>
                <td>{run.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="manifest-list">
        {runs.map((run) => (
          <details className="batch-job-card" key={`${run.run_id}-details`}>
            <summary>
              <span>open details</span>
              <span>{run.run_id}</span>
              <span>{run.status}</span>
            </summary>
            <div className="batch-job-detail">
              <div className="summary-grid">
                <span>Source: {run.source}</span>
                <span>Seed: {run.seed}</span>
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
