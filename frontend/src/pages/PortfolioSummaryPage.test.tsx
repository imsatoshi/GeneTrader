import { render, screen } from '@testing-library/react';
import PortfolioSummaryPage from './PortfolioSummaryPage';

describe('PortfolioSummaryPage', () => {
  it('renders portfolio exposure summary metrics', () => {
    render(<PortfolioSummaryPage />);

    expect(screen.getByRole('heading', { name: 'Portfolio Exposure' })).toBeInTheDocument();
    expect(screen.getByText('portfolio-balanced-001')).toBeInTheDocument();
    expect(screen.getByText(/portfolio_drawdown 0.071/)).toBeInTheDocument();
    expect(screen.getByText(/correlation_penalty 0.018/)).toBeInTheDocument();
    expect(screen.getByText('total_exposure 0.280')).toBeInTheDocument();
  });

  it('shows a multi pair table for mock exposure data', () => {
    render(<PortfolioSummaryPage />);

    expect(screen.getAllByRole('columnheader', { name: 'pair' }).length).toBeGreaterThan(0);
    expect(screen.getAllByText('BTC/USDT').length).toBeGreaterThan(0);
    expect(screen.getAllByText('ETH/USDT').length).toBeGreaterThan(0);
    expect(screen.getAllByText('SOL/USDT').length).toBeGreaterThan(0);
  });

  it('marks exposure breach and recommendations clearly', () => {
    render(<PortfolioSummaryPage />);

    expect(screen.getByText('portfolio-exposure-review')).toBeInTheDocument();
    expect(screen.getAllByText('total_exposure_above_limit').length).toBeGreaterThan(0);
    expect(screen.getByText('portfolio_drawdown_above_limit')).toBeInTheDocument();
    expect(screen.getByText('Clamp portfolio exposure below 0.30.')).toBeInTheDocument();
    expect(document.querySelectorAll('.risk-critical').length).toBeGreaterThan(0);
    expect(document.querySelectorAll('.risk-warning').length).toBeGreaterThan(0);
  });

  it('has accessible table column names', () => {
    render(<PortfolioSummaryPage />);

    expect(screen.getAllByRole('columnheader', { name: 'pair' }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole('columnheader', { name: 'exposure' }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole('columnheader', { name: 'drawdown' }).length).toBeGreaterThan(0);
  });
});
