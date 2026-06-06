import { render, screen } from '@testing-library/react';
import CoverageMatrix from './CoverageMatrix';
import { mockCoverageMatrix } from '../mocks/offlineData';

describe('CoverageMatrix', () => {
  it('renders pair and timeframe coverage', () => {
    render(<CoverageMatrix matrix={mockCoverageMatrix} />);

    expect(screen.getByText('BTC/USDT')).toBeInTheDocument();
    expect(screen.getByText('15m')).toBeInTheDocument();
    expect(screen.getAllByText('present')).toHaveLength(3);
  });
});
