import { render, screen } from '@testing-library/react';
import MockDashboardPage from './MockDashboardPage';

describe('MockDashboardPage', () => {
  it('renders session summary sections', async () => {
    render(<MockDashboardPage />);

    expect(screen.getByText('Session Summary Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Offline Data Inventory')).toBeInTheDocument();
    expect(screen.getByText('Requirements Gate')).toBeInTheDocument();
    expect(screen.getByText('GA Run Summary')).toBeInTheDocument();
    expect(screen.getByText(/session-summary\/v1/i)).toBeInTheDocument();
    expect(screen.getByText(/Source: mock/i)).toBeInTheDocument();
    expect(screen.getByText(/Inventory count: 2/i)).toBeInTheDocument();
    expect(screen.getByText(/Gate error count: 2/i)).toBeInTheDocument();
    expect(screen.getByText(/Run ID: mock-run-001/i)).toBeInTheDocument();
    expect(screen.getByText(/Best fitness/i)).toBeInTheDocument();
    expect(await screen.findByText(/Artifact run ID: mock-ga-seed-2026/i)).toBeInTheDocument();
    expect(screen.getByText('GA Leaderboard')).toBeInTheDocument();
    expect(screen.getByText('Best Genome Detail')).toBeInTheDocument();
    expect(screen.getByText('Risk Components')).toBeInTheDocument();
    expect(screen.getByText(/Max loss streak: 2/i)).toBeInTheDocument();
    expect(screen.getByText(/Leverage: 2.4/i)).toBeInTheDocument();
    expect(screen.getByText(/Risk per trade: 0.014/i)).toBeInTheDocument();
    expect(screen.getByText('drawdown_penalty')).toBeInTheDocument();
    expect(screen.getAllByText(/gen003-ind002/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/BTC\/USDT/).length).toBeGreaterThan(0);
  });
});
