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

  it('renders confidence badge', () => {
    render(<EventCard event={mockEvent} onClick={vi.fn()} />);
    expect(screen.getByText('confirmed')).toBeInTheDocument();
  });

  it('renders corroborating sources count', () => {
    render(<EventCard event={mockEvent} onClick={vi.fn()} />);
    expect(screen.getByText(/3 sources/i)).toBeInTheDocument();
  });

  it('renders pool spread', () => {
    render(<EventCard event={mockEvent} onClick={vi.fn()} />);
    expect(screen.getByText(/2 pools/i)).toBeInTheDocument();
  });

  it('shows dispute warning when dispute_count > 0', () => {
    render(<EventCard event={mockEventWithDisputes} onClick={vi.fn()} />);
    expect(screen.getByText(/2 disputes/i)).toBeInTheDocument();
  });

  it('does not show dispute warning when no disputes', () => {
    render(<EventCard event={mockEvent} onClick={vi.fn()} />);
    expect(screen.queryByText(/dispute/i)).not.toBeInTheDocument();
  });

  it('shows reviewed badge when human_reviewed is true', () => {
    render(<EventCard event={mockEventWithDisputes} onClick={vi.fn()} />);
    expect(screen.getByText(/Reviewed/i)).toBeInTheDocument();
  });

  it('does not show reviewed badge when not reviewed', () => {
    render(<EventCard event={mockEvent} onClick={vi.fn()} />);
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

  it('applies confirmed badge class for confirmed confidence', () => {
    render(<EventCard event={mockEvent} onClick={vi.fn()} />);
    const badge = screen.getByText('confirmed');
    expect(badge).toHaveClass('badge-green');
  });

  it('applies disputed badge class for disputed confidence', () => {
    render(<EventCard event={mockEventWithDisputes} onClick={vi.fn()} />);
    const badge = screen.getByText('disputed');
    expect(badge).toHaveClass('badge-yellow');
  });

  it('renders singular "dispute" label for exactly 1 dispute', () => {
    const event = { ...mockEvent, dispute_count: 1 };
    render(<EventCard event={event} onClick={vi.fn()} />);
    expect(screen.getByText(/1 dispute$/i)).toBeInTheDocument();
  });
});
