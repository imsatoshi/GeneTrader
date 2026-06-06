import { render, screen } from '@testing-library/react';
import OverviewPage from './OverviewPage';

describe('OverviewPage', () => {
  it('renders summary cards', () => {
    render(<OverviewPage />);

    expect(screen.getByText('Preflight')).toBeInTheDocument();
    expect(screen.getByText('Best fitness')).toBeInTheDocument();
  });
});
