import { render, screen } from '@testing-library/react';
import MockBatchDashboardPage from './MockBatchDashboardPage';

describe('MockBatchDashboardPage', () => {
  it('renders batch summary and failure-aware job states', async () => {
    render(<MockBatchDashboardPage />);

    expect(await screen.findByText('Batch Result Dashboard')).toBeInTheDocument();
    expect(screen.getByText(/Batch ID: small-batch-mock-001/i)).toBeInTheDocument();
    expect(screen.getByText(/Status: Partial success/i)).toBeInTheDocument();
    expect(screen.getByText(/Total jobs: 5/i)).toBeInTheDocument();
    expect(screen.getByText(/Mock-first: true/i)).toBeInTheDocument();
    expect(screen.getByText('Per-Genome Results')).toBeInTheDocument();

    expect(screen.getByText('job-success-001')).toBeInTheDocument();
    expect(screen.getByText('Success')).toBeInTheDocument();
    expect(screen.getByText('job-failed-002')).toBeInTheDocument();
    expect(screen.getAllByText('Failed').length).toBeGreaterThan(0);
    expect(screen.getByText('job-skipped-003')).toBeInTheDocument();
    expect(screen.getAllByText('Skipped').length).toBeGreaterThan(0);
    expect(screen.getByText('job-timeout-004')).toBeInTheDocument();
    expect(screen.getByText('Timeout')).toBeInTheDocument();
    expect(screen.getByText('job-policy-005')).toBeInTheDocument();
    expect(screen.getByText('Policy rejected')).toBeInTheDocument();
  });

  it('renders success metrics and risk-aware fitness components', async () => {
    render(<MockBatchDashboardPage />);

    expect(await screen.findByText(/Profit: 21.00%/i)).toBeInTheDocument();
    expect(screen.getByText(/Sharpe: 1.52/i)).toBeInTheDocument();
    expect(screen.getByText(/Win rate: 61.00%/i)).toBeInTheDocument();
    expect(screen.getByText(/Max drawdown: 7.00%/i)).toBeInTheDocument();
    expect(screen.getByText(/Total trades: 42/i)).toBeInTheDocument();
    expect(screen.getByText(/Max loss streak: 2/i)).toBeInTheDocument();
    expect(screen.getByText(/Leverage: 2.4/i)).toBeInTheDocument();
    expect(screen.getByText(/Risk per trade: 0.014/i)).toBeInTheDocument();
    expect(screen.getByText('drawdown_penalty')).toBeInTheDocument();
    expect(screen.getByText('final_fitness')).toBeInTheDocument();
  });

  it('renders redacted failure messages without exposing sensitive strings', async () => {
    render(<MockBatchDashboardPage />);

    expect(await screen.findByText('ValueError')).toBeInTheDocument();
    expect(screen.getByText(/<redacted:path>/i)).toBeInTheDocument();
    expect(screen.getByText(/<redacted:secret-key>/i)).toBeInTheDocument();
    expect(screen.getByText(/small_batch_real_execution_requires_dual_env_opt_in/i)).toBeInTheDocument();
    expect(document.body.textContent).not.toContain('C:/Users');
    expect(document.body.textContent).not.toContain('.env');
  });
});
