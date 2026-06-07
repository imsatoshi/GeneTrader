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
    expect(screen.getByText('max_drawdown')).toBeInTheDocument();
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

  it('filters by maximum max drawdown', async () => {
    render(<RunExplorerCustomPage />);

    const input = screen.getByLabelText('Maximum max drawdown');
    await userEvent.clear(input);
    await userEvent.type(input, '0.085');

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

  it('renders genome detail', () => {
    render(<RunExplorerCustomPage />);

    expect(screen.getByText('Genome Parameters')).toBeInTheDocument();
    expect(screen.getByText(/entry_bb_window/i)).toBeInTheDocument();
  });

  it('renders risk governor adjustments', () => {
    render(<RunExplorerCustomPage />);

    expect(screen.getByText('RiskGovernor Adjustments')).toBeInTheDocument();
    expect(screen.getByText(/Adjusted leverage:/i)).toBeInTheDocument();
    expect(screen.getByText(/Adjusted risk per trade:/i)).toBeInTheDocument();
  });

  it('renders trading system config preview', () => {
    render(<RunExplorerCustomPage />);

    expect(screen.getByText('TradingSystemConfig Preview')).toBeInTheDocument();
    expect(screen.getByText(/custom-trading-system-config\/v1/i)).toBeInTheDocument();
  });

  it('renders fitness components', () => {
    render(<RunExplorerCustomPage />);

    expect(screen.getByText('Fitness Components')).toBeInTheDocument();
    expect(screen.getAllByText(/final_fitness/i).length).toBeGreaterThan(0);
  });

  it('renders robustness summary', () => {
    render(<RunExplorerCustomPage />);

    expect(screen.getByText('Walk-forward Stability')).toBeInTheDocument();
    expect(screen.getByText('Monte Carlo Summary')).toBeInTheDocument();
    expect(screen.getByText('Portfolio Summary')).toBeInTheDocument();
  });

  it('renders strategy explainability and position sizing preview', () => {
    render(<RunExplorerCustomPage />);

    expect(screen.getByText('Strategy explanation')).toBeInTheDocument();
    expect(screen.getByText('Risk warnings')).toBeInTheDocument();
    expect(screen.getByText('Fitness explanation')).toBeInTheDocument();
    expect(screen.getByText('Position sizing preview')).toBeInTheDocument();
    expect(screen.getByText(/final_fitness=0.864/i)).toBeInTheDocument();
  });

  it('shows high leverage warning from selected mock run', async () => {
    render(<RunExplorerCustomPage />);

    await userEvent.click(screen.getAllByText('custom-walk-forward-017')[0]);

    expect(screen.getByRole('heading', { name: 'custom-walk-forward-017' })).toBeInTheDocument();
    expect(screen.getByText('high_leverage_strategy')).toBeInTheDocument();
    expect(screen.getByText('risk_governor:reduced_risk_after_drawdown')).toBeInTheDocument();
    expect(screen.getByText('risk_governor_action=reduced_risk_after_drawdown')).toBeInTheDocument();
  });

  it('has accessibility smoke coverage for controls and table columns', () => {
    render(<RunExplorerCustomPage />);

    expect(screen.getByRole('heading', { name: 'Custom Run Explorer' })).toBeInTheDocument();
    expect(screen.getByLabelText('Sort')).toBeInTheDocument();
    expect(screen.getByLabelText('Minimum stability score')).toBeInTheDocument();
    expect(screen.getByLabelText('Maximum portfolio drawdown')).toBeInTheDocument();
    expect(screen.getByLabelText('Maximum max drawdown')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /export json/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'run_id' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'best_fitness' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'max_drawdown' })).toBeInTheDocument();
  });
});
