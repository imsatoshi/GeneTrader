import ResultsTable from '../components/ResultsTable';
import { mockResults } from '../mocks/results';

export default function ResultsPage() {
  return (
    <section className="page-stack">
      <div className="section-heading">
        <p className="eyebrow">Results</p>
        <h2>Leaderboard of optimized mock candidates.</h2>
      </div>
      <ResultsTable results={mockResults} />
    </section>
  );
}
