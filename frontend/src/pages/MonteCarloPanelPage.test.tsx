import { render, screen } from '@testing-library/react';
import MonteCarloPanelPage from './MonteCarloPanelPage';

describe('MonteCarloPanelPage', () => {
  it('renders Monte Carlo summary metrics from mock fixtures', () => {
    render(<MonteCarloPanelPage />);

    expect(screen.getByRole('heading', { name: 'Monte Carlo Summary' })).toBeInTheDocument();
    expect(screen.getByText('runs')).toBeInTheDocument();
    expect(screen.getByText('profit_p05')).toBeInTheDocument();
    expect(screen.getByText('profit_median')).toBeInTheDocument();
    expect(screen.getByText('profit_p95')).toBeInTheDocument();
    expect(screen.getByText('drawdown_p95')).toBeInTheDocument();
    expect(screen.getByText('failure_rate')).toBeInTheDocument();
    expect(screen.getByText('worst_case_summary')).toBeInTheDocument();
  });

  it('shows failure rate and warning markers for high risk fixtures', () => {
    render(<MonteCarloPanelPage />);

    expect(screen.getByText('custom-loss-streak-review')).toBeInTheDocument();
    expect(screen.getAllByText('0.184').length).toBeGreaterThan(0);
    expect(document.querySelectorAll('.risk-critical').length).toBeGreaterThan(0);
    expect(document.querySelectorAll('.risk-warning').length).toBeGreaterThan(0);
  });

  it('displays worst case summary text without backend access', () => {
    render(<MonteCarloPanelPage />);

    expect(screen.getByText('Loss streak perturbation triggers drawdown circuit breaker review.')).toBeInTheDocument();
    expect(screen.getByText('Small profit erosion under shuffled late-cycle losses.')).toBeInTheDocument();
  });

  it('has accessible table column names', () => {
    render(<MonteCarloPanelPage />);

    expect(screen.getByRole('columnheader', { name: 'run_id' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'failure_rate' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'worst_case_summary' })).toBeInTheDocument();
  });
});
