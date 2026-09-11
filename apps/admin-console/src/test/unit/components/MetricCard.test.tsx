import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MetricCard } from '../../../shared/components/MetricCard';
import { Cpu } from 'lucide-react';

describe('MetricCard Unit Component Tests', () => {
  it('renders title and value correctly', () => {
    render(
      <MetricCard
        title="Total Queries"
        value="1,240"
        icon={Cpu}
        iconBg="bg-indigo-500/10"
        iconColor="text-indigo-400"
      />
    );

    expect(screen.getByText('Total Queries')).toBeInTheDocument();
    expect(screen.getByText('1,240')).toBeInTheDocument();
  });
});
