import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import HyperparamSweepPage from './HyperparamSweepPage';

describe('HyperparamSweepPage', () => {
  it('renders mock sweep rows and accessible controls', () => {
    render(<HyperparamSweepPage />);

    expect(screen.getByRole('heading', { name: 'Hyperparameter Sweep' })).toBeInTheDocument();
    expect(screen.getByLabelText('Sort metric')).toBeInTheDocument();
    expect(screen.getByLabelText('Minimum stability')).toBeInTheDocument();
    expect(screen.getByText('sweep-safe-001')).toBeInTheDocument();
    expect(screen.getByText('bb_period=24, stddev=2.1, stoploss=0.035')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'run_id' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'fitness' })).toBeInTheDocument();
  });

  it('sorts rows by max drawdown when the column button is used', async () => {
    render(<HyperparamSweepPage />);

    await userEvent.click(screen.getByRole('button', { name: 'max_drawdown' }));

    const firstDataRow = screen.getAllByRole('row')[1];
    expect(within(firstDataRow).getByText('sweep-stable-044')).toBeInTheDocument();
  });

  it('sorts rows by fitness through the select control', async () => {
    render(<HyperparamSweepPage />);

    await userEvent.selectOptions(screen.getByLabelText('Sort metric'), 'fitness');

    const firstDataRow = screen.getAllByRole('row')[1];
    expect(within(firstDataRow).getByText('sweep-safe-001')).toBeInTheDocument();
  });

  it('filters rows by minimum stability without reading backend data', async () => {
    render(<HyperparamSweepPage />);

    await userEvent.clear(screen.getByLabelText('Minimum stability'));
    await userEvent.type(screen.getByLabelText('Minimum stability'), '0.9');

    expect(screen.getByText('sweep-safe-001')).toBeInTheDocument();
    expect(screen.getByText('sweep-stable-044')).toBeInTheDocument();
    expect(screen.queryByText('sweep-high-risk-063')).not.toBeInTheDocument();
  });
});
