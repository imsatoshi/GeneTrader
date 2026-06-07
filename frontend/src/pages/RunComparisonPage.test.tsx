import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import RunComparisonPage from './RunComparisonPage';

describe('RunComparisonPage', () => {
  it('renders run comparison controls and metrics', () => {
    render(<RunComparisonPage />);

    expect(screen.getByRole('heading', { name: 'Run Comparison' })).toBeInTheDocument();
    expect(screen.getByLabelText('Run A')).toBeInTheDocument();
    expect(screen.getByLabelText('Run B')).toBeInTheDocument();
    expect(screen.getByText('best_fitness')).toBeInTheDocument();
    expect(screen.getByText('max_drawdown')).toBeInTheDocument();
    expect(screen.getByText('stability_score')).toBeInTheDocument();
    expect(screen.getByText('portfolio_drawdown')).toBeInTheDocument();
    expect(screen.getByText('leverage')).toBeInTheDocument();
    expect(screen.getByText('risk_per_trade')).toBeInTheDocument();
  });

  it('allows selecting run A and run B', async () => {
    render(<RunComparisonPage />);

    await userEvent.selectOptions(screen.getByLabelText('Run A'), 'custom-portfolio-088');
    await userEvent.selectOptions(screen.getByLabelText('Run B'), 'custom-walk-forward-017');

    expect(screen.getByLabelText('Run A')).toHaveValue('custom-portfolio-088');
    expect(screen.getByLabelText('Run B')).toHaveValue('custom-walk-forward-017');
  });

  it('shows metric differences between selected mock runs', () => {
    render(<RunComparisonPage />);

    expect(screen.getByText('-0.065')).toBeInTheDocument();
    expect(screen.getAllByText('0.090').length).toBeGreaterThan(0);
    expect(screen.getAllByText('3.000').length).toBeGreaterThan(0);
  });

  it('has accessible table column names', () => {
    render(<RunComparisonPage />);

    expect(screen.getByRole('columnheader', { name: 'metric' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'difference' })).toBeInTheDocument();
  });
});
