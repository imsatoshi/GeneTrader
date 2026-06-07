import { render, screen } from '@testing-library/react';
import RiskGovernorPanelPage from './RiskGovernorPanelPage';

describe('RiskGovernorPanelPage', () => {
  it('renders risk governor adjustment columns', () => {
    render(<RiskGovernorPanelPage />);

    expect(screen.getByRole('heading', { name: 'RiskGovernor Feedback' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'fixture_id' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'original leverage' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'adjusted leverage' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'original risk_per_trade' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'adjusted risk_per_trade' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'cooldown_candles' })).toBeInTheDocument();
  });

  it('shows leverage_clamped for the high leverage fixture', () => {
    render(<RiskGovernorPanelPage />);

    expect(screen.getByText('high-leverage-review')).toBeInTheDocument();
    expect(screen.getByText('leverage_clamped')).toBeInTheDocument();
    expect(screen.getByText('leverage above owner review default')).toBeInTheDocument();
  });

  it('shows cooldown_applied for the loss streak fixture', () => {
    render(<RiskGovernorPanelPage />);

    expect(screen.getByText('loss-streak-cooldown')).toBeInTheDocument();
    expect(screen.getByText('cooldown_applied')).toBeInTheDocument();
    expect(screen.getByText('loss streak exceeded cutoff')).toBeInTheDocument();
  });

  it('keeps safe fixture visible without warnings', () => {
    render(<RiskGovernorPanelPage />);

    expect(screen.getByText('safe-default')).toBeInTheDocument();
    expect(screen.getByText('no_adjustment')).toBeInTheDocument();
    expect(screen.getByText('none')).toBeInTheDocument();
  });
});
