import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import RunExplorerPage from './RunExplorerPage';

describe('RunExplorerPage', () => {
  it('renders mock experiment registry rows', () => {
    render(<RunExplorerPage />);

    expect(screen.getByText('Mock Experiment Registry')).toBeInTheDocument();
    expect(screen.getAllByText('mock-ga-seed-42').length).toBeGreaterThan(0);
    expect(screen.getAllByText('portfolio-smoke-001').length).toBeGreaterThan(0);
    expect(screen.getAllByText('walk-forward-robustness-003').length).toBeGreaterThan(0);
    expect(screen.getByText('best_fitness')).toBeInTheDocument();
    expect(screen.getByText('population_size')).toBeInTheDocument();
    expect(screen.getAllByText('completed').length).toBeGreaterThan(0);
  });

  it('opens run details from the mock fixture', async () => {
    render(<RunExplorerPage />);

    await userEvent.click(screen.getAllByText('open details')[0]);

    expect(screen.getByText(/Source: mock-ga-cli/i)).toBeInTheDocument();
    expect(screen.getByText(/Artifact dir: artifacts\/mock-ga-seed-42/i)).toBeInTheDocument();
    expect(screen.getByText(/baseline mock session/i)).toBeInTheDocument();
  });
});
