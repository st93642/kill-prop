import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import EventCard from '../EventCard';
import { mockEvent, mockEventWithDisputes } from '../../test/fixtures';

describe('EventCard', () => {
  it('renders event title', () => {
    render(<EventCard event={mockEvent} onClick={vi.fn()} />);
    expect(screen.getByText('Drone strike hits fuel depot near Dnipro')).toBeInTheDocument();
  });

  it('renders fact summary', () => {
    render(<EventCard event={mockEvent} onClick={vi.fn()} />);
    expect(screen.getByText(/Strike involving drone/i)).toBeInTheDocument();
  });

  it('renders plain-language reliability badge', () => {
    render(<EventCard event={mockEvent} onClick={vi.fn()} />);
    expect(screen.getByText('Confirmed')).toBeInTheDocument();
  });

  it('renders sources and regions count in plain language', () => {
    render(<EventCard event={mockEvent} onClick={vi.fn()} />);
    expect(screen.getByText(/3 sources · 3 regions/i)).toBeInTheDocument();
  });

  it('shows conflict warning when dispute_count > 0', () => {
    render(<EventCard event={mockEventWithDisputes} onClick={vi.fn()} />);
    expect(screen.getByText(/2 conflicting points/i)).toBeInTheDocument();
  });

  it('does not show conflict warning when no disputes', () => {
    render(<EventCard event={mockEvent} onClick={vi.fn()} />);
    expect(screen.queryByText(/conflicting points/i)).not.toBeInTheDocument();
  });

  it('does not show reviewed badge on card', () => {
    render(<EventCard event={mockEventWithDisputes} onClick={vi.fn()} />);
    expect(screen.queryByText(/Reviewed/i)).not.toBeInTheDocument();
  });

  it('renders pool dots for each pool', () => {
    render(<EventCard event={mockEvent} onClick={vi.fn()} />);
    const poolDots = document.querySelectorAll('.pool-dot');
    expect(poolDots.length).toBe(mockEvent.pools.length);
  });

  it('calls onClick when card is clicked', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    render(<EventCard event={mockEvent} onClick={handleClick} />);
    await user.click(screen.getByText('Drone strike hits fuel depot near Dnipro'));
    expect(handleClick).toHaveBeenCalledOnce();
  });

  it('applies confirmed badge class for confirmed reliability', () => {
    render(<EventCard event={mockEvent} onClick={vi.fn()} />);
    const badge = screen.getByText('Confirmed');
    expect(badge).toHaveClass('badge-green');
  });

  it('applies disputed badge class for conflicting reports', () => {
    render(<EventCard event={mockEventWithDisputes} onClick={vi.fn()} />);
    const badge = screen.getByText('Conflicting reports');
    expect(badge).toHaveClass('badge-yellow');
  });
});
