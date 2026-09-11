import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBadge } from '../../../shared/components/StatusBadge';

describe('StatusBadge Unit Component Tests', () => {
  it('renders status text correctly', () => {
    render(<StatusBadge status="Online" />);
    expect(screen.getByText('Online')).toBeInTheDocument();
  });

  it('applies green success styles for online status', () => {
    const { container } = render(<StatusBadge status="Online" />);
    const badge = container.querySelector('span');
    expect(badge).toHaveClass('bg-success/15');
  });

  it('applies red danger styles for offline status', () => {
    const { container } = render(<StatusBadge status="Offline" />);
    const badge = container.querySelector('span');
    expect(badge).toHaveClass('bg-danger/15');
  });

  it('applies yellow warning styles for degraded status', () => {
    const { container } = render(<StatusBadge status="Degraded" />);
    const badge = container.querySelector('span');
    expect(badge).toHaveClass('bg-warning/15');
  });
});
