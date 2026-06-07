import { render, screen } from '@testing-library/react';
import RiskDashboardPage from './RiskDashboardPage';

describe('RiskDashboardPage', () => {
  it('renders risk dashboard metrics', () => {
    render(<RiskDashboardPage />);

    expect(screen.getByRole('heading', { name: 'Risk Dashboard' })).toBeInTheDocument();
    expect(screen.getByText('max_drawdown')).toBeInTheDocument();
    expect(screen.getByText('loss_streak')).toBeInTheDocument();
    expect(screen.getByText('portfolio_exposure')).toBeInTheDocument();
    expect(screen.getByText('risk_per_trade')).toBeInTheDocument();
    expect(screen.getByText('leverage')).toBeInTheDocument();
    expect(screen.getByText('failure_rate')).toBeInTheDocument();
  });

  it('marks high risk items clearly', () => {
    render(<RiskDashboardPage />);

    expect(screen.getByText('custom-loss-streak-review')).toBeInTheDocument();
    expect(screen.getAllByText('risk-critical').length).toBeGreaterThan(0);
    expect(screen.getAllByText('risk-warning').length).toBeGreaterThan(0);
  });

  it('shows circuit breaker status and Monte Carlo failure rate', () => {
    render(<RiskDashboardPage />);

    expect(screen.getByText('pause_trading')).toBeInTheDocument();
    expect(screen.getByText('reduce_risk')).toBeInTheDocument();
    expect(screen.getAllByText('0.160').length).toBeGreaterThan(0);
  });

  it('has accessible table column names', () => {
    render(<RiskDashboardPage />);

    expect(screen.getByRole('columnheader', { name: 'run_id' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'circuit breaker status' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'risk level' })).toBeInTheDocument();
  });
});
