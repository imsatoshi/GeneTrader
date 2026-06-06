import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import RunExplorerCustomPage from './RunExplorerCustomPage';

describe('RunExplorerCustomPage', () => {
  it('renders custom mock registry rows', () => {
    render(<RunExplorerCustomPage />);

    expect(screen.getByText('Custom Run Explorer')).toBeInTheDocument();
    expect(screen.getAllByText('custom-ga-seed-42').length).toBeGreaterThan(0);
    expect(screen.getAllByText('custom-walk-forward-017').length).toBeGreaterThan(0);
    expect(screen.getAllByText('custom-portfolio-088').length).toBeGreaterThan(0);
    expect(screen.getByText('stability_score')).toBeInTheDocument();
    expect(screen.getByText('failure_rate')).toBeInTheDocument();
    expect(screen.getByText('portfolio_drawdown')).toBeInTheDocument();
  });

  it('opens custom run details from fixture data', async () => {
    render(<RunExplorerCustomPage />);

    await userEvent.click(screen.getAllByText('open details')[0]);

    expect(screen.getAllByText(/Artifact dir: artifacts\/custom-ga-seed-42/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/advisory risk governor/i).length).toBeGreaterThan(0);
  });

  it('sorts custom runs by run id', async () => {
    render(<RunExplorerCustomPage />);

    await userEvent.selectOptions(screen.getByLabelText('Sort'), 'run_id');

    expect(screen.getAllByTestId('custom-run-id')[0]).toHaveTextContent('custom-ga-seed-42');
  });

  it('sorts custom runs by generations', async () => {
    render(<RunExplorerCustomPage />);

    await userEvent.selectOptions(screen.getByLabelText('Sort'), 'generations');

    expect(screen.getAllByTestId('custom-run-id')[0]).toHaveTextContent('custom-portfolio-088');
  });

  it('filters by minimum stability score', async () => {
    render(<RunExplorerCustomPage />);

    const input = screen.getByLabelText('Minimum stability score');
    await userEvent.clear(input);
    await userEvent.type(input, '0.8');

    expect(screen.getAllByTestId('custom-run-id')).toHaveLength(1);
    expect(screen.getAllByTestId('custom-run-id')[0]).toHaveTextContent('custom-ga-seed-42');
  });

  it('filters by maximum portfolio drawdown', async () => {
    render(<RunExplorerCustomPage />);

    const input = screen.getByLabelText('Maximum portfolio drawdown');
    await userEvent.clear(input);
    await userEvent.type(input, '0.08');

    expect(screen.getAllByTestId('custom-run-id')).toHaveLength(1);
    expect(screen.getAllByTestId('custom-run-id')[0]).toHaveTextContent('custom-portfolio-088');
  });

  it('shows selected run details and mock JSON export preview', async () => {
    render(<RunExplorerCustomPage />);

    await userEvent.click(screen.getAllByTestId('custom-run-id')[1]);
    await userEvent.click(screen.getByRole('button', { name: /export json/i }));

    expect(screen.getByRole('heading', { name: 'custom-portfolio-088' })).toBeInTheDocument();
    expect(screen.getByText(/Genome: custom-gen006-ind021/i)).toBeInTheDocument();
    expect(screen.getByLabelText('mock json export')).toHaveTextContent('custom-ga-seed-42');
  });
});
