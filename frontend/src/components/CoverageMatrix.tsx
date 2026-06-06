import type { CoverageMatrix as CoverageMatrixType } from '../types/offlineData';

export default function CoverageMatrix({ matrix }: { matrix: CoverageMatrixType }) {
  return (
    <div className="panel">
      <h3>Coverage Matrix</h3>
      <div className="coverage-grid" style={{ gridTemplateColumns: `160px repeat(${matrix.timeframes.length}, 1fr)` }}>
        <strong>Pair</strong>
        {matrix.timeframes.map((timeframe) => (
          <strong key={timeframe}>{timeframe}</strong>
        ))}
        {matrix.matrix.map((row) => (
          <div className="coverage-row" key={row.pair}>
            <span>{row.pair}</span>
            {row.cells.map((cell) => (
              <span key={`${row.pair}-${cell.timeframe}`} className={`coverage-cell ${cell.status}`}>
                {cell.status}
              </span>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
