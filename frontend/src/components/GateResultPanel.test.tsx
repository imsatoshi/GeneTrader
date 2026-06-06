import { render, screen } from '@testing-library/react';
import GateResultPanel from './GateResultPanel';
import { mockGateResult } from '../mocks/offlineData';

describe('GateResultPanel', () => {
  it('renders ready state and counts', () => {
    render(<GateResultPanel gate={mockGateResult} />);

    expect(screen.getByText('READY')).toBeInTheDocument();
    expect(screen.getByText('Errors: 0')).toBeInTheDocument();
    expect(screen.getByText('Warnings: 1')).toBeInTheDocument();
  });
});
