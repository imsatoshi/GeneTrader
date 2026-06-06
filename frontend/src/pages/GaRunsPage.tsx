import FitnessChart from '../components/FitnessChart';
import { mockGenerationMetrics } from '../mocks/gaRuns';

export default function GaRunsPage() {
  return (
    <section className="page-stack">
      <div className="section-heading">
        <p className="eyebrow">GA Runs</p>
        <h2>Mock-first genetic optimization monitor.</h2>
      </div>
      <div className="panel">
        <FitnessChart data={mockGenerationMetrics} />
      </div>
      <div className="manifest-list">
        {mockGenerationMetrics.map((item) => (
          <div className="manifest-row" key={item.generation}>
            <span>Generation {item.generation}</span>
            <span>Best {item.bestFitness.toFixed(2)}</span>
            <span>Avg {item.avgFitness.toFixed(2)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
