import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import RequirementsPage from './RequirementsPage';

describe('RequirementsPage', () => {
  it('renders generated requirements JSON and validation feedback', async () => {
    render(<RequirementsPage />);

    expect(screen.getAllByText(/BTC\/USDT/).length).toBeGreaterThan(0);
    await userEvent.clear(screen.getByLabelText(/Pairs/i));
    await userEvent.type(screen.getByLabelText(/Pairs/i), 'BADPAIR');
    expect(screen.getByText('Requirements format is invalid.')).toBeInTheDocument();
  });
});
