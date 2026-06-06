import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import InventoryTable from './InventoryTable';
import { mockInventoryFiles } from '../mocks/offlineData';

describe('InventoryTable', () => {
  it('renders inventory rows and supports sorting clicks', async () => {
    render(<InventoryTable files={mockInventoryFiles} />);

    expect(screen.getByText('binance/BTC_USDT-15m.csv')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Timeframe/i }));
    expect(screen.getByText('binance/BTC_USDT-1h.json')).toBeInTheDocument();
  });
});
