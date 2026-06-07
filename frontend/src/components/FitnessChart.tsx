import type { GenerationMetric } from '../types/ga';

type Series = {
  name: string;
  color: string;
  values: number[];
};

function buildPath(values: number[], minValue: number, maxValue: number) {
  const width = 320;
  const height = 180;
  const padding = 18;
  const span = Math.max(0.000001, maxValue - minValue);
  return values
    .map((value, index) => {
      const x = padding + (index / Math.max(1, values.length - 1)) * (width - padding * 2);
      const y = height - padding - ((value - minValue) / span) * (height - padding * 2);
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(' ');
}

export default function FitnessChart({ data }: { data: GenerationMetric[] }) {
  if (data.length === 0) {
    return (
      <div className="chart-frame fitness-chart" data-testid="fitness-chart">
        <svg aria-label="Fitness chart" role="img" viewBox="0 0 320 220">
          <line className="chart-axis" x1="18" x2="302" y1="180" y2="180" />
          <line className="chart-axis" x1="18" x2="18" y1="18" y2="180" />
          <text className="chart-label" textAnchor="middle" x="160" y="110">
            No fitness data
          </text>
        </svg>
      </div>
    );
  }

  const series: Series[] = [
    { name: 'Best', color: '#28745d', values: data.map((item) => item.bestFitness) },
    { name: 'Average', color: '#b97d2b', values: data.map((item) => item.avgFitness) },
    { name: 'Worst', color: '#a6402d', values: data.map((item) => item.worstFitness) },
  ];
  const values = series.flatMap((item) => item.values);
  const minValue = Math.min(...values, 0);
  const maxValue = Math.max(...values, 1);

  return (
    <div className="chart-frame fitness-chart" data-testid="fitness-chart">
      <svg aria-label="Fitness chart" role="img" viewBox="0 0 320 220">
        <line className="chart-axis" x1="18" x2="302" y1="180" y2="180" />
        <line className="chart-axis" x1="18" x2="18" y1="18" y2="180" />
        {series.map((item) => (
          <path
            d={buildPath(item.values, minValue, maxValue)}
            fill="none"
            key={item.name}
            stroke={item.color}
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="3"
          />
        ))}
        {data.map((item, index) => {
          const x = 18 + (index / Math.max(1, data.length - 1)) * 284;
          return (
            <text className="chart-label" key={item.generation} textAnchor="middle" x={x} y="205">
              {item.generation}
            </text>
          );
        })}
      </svg>
      <div className="chart-legend" aria-label="Fitness chart legend">
        {series.map((item) => (
          <span key={item.name}>
            <i style={{ background: item.color }} />
            {item.name}
          </span>
        ))}
      </div>
    </div>
  );
}
