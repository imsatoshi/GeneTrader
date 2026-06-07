import { render, screen } from '@testing-library/react';
import FitnessChart from './FitnessChart';
import type { GenerationMetric } from '../types/ga';

const mockFitnessSeries: GenerationMetric[] = [
  { generation: 1, bestFitness: 0.24, avgFitness: 0.16, worstFitness: 0.08 },
  { generation: 2, bestFitness: 0.38, avgFitness: 0.22, worstFitness: 0.12 },
  { generation: 3, bestFitness: 0.51, avgFitness: 0.31, worstFitness: 0.17 },
];

describe('FitnessChart', () => {
  it('renders mock session fitness series as accessible SVG paths', () => {
    const { container } = render(<FitnessChart data={mockFitnessSeries} />);

    expect(screen.getByTestId('fitness-chart')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'Fitness chart' })).toBeInTheDocument();
    expect(screen.getByText('Best')).toBeInTheDocument();
    expect(screen.getByText('Average')).toBeInTheDocument();
    expect(screen.getByText('Worst')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();

    const paths = Array.from(container.querySelectorAll('path'));
    expect(paths).toHaveLength(3);
    for (const path of paths) {
      expect(path.getAttribute('d')).toMatch(/^M /);
      expect(path.getAttribute('d')).not.toMatch(/NaN|Infinity/);
    }
  });

  it('renders a clear empty state instead of a blank chart', () => {
    const { container } = render(<FitnessChart data={[]} />);

    expect(screen.getByRole('img', { name: 'Fitness chart' })).toBeInTheDocument();
    expect(screen.getByText('No fitness data')).toBeInTheDocument();
    expect(container.querySelectorAll('path')).toHaveLength(0);
  });
});
