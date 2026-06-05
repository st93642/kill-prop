import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ReviewConsole from '../ReviewConsole';
import { mockEvent, mockEventWithDisputes, mockStats } from '../../test/fixtures';

describe('ReviewConsole', () => {
  it('shows loading spinner when loading', () => {
    render(
      <ReviewConsole
        events={[]}
        stats={null}
        loading={true}
        onSelectEvent={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.getByText(/loading events/i)).toBeInTheDocument();
  });

  it('shows all-reviewed empty state when no unreviewed events', () => {
    const reviewed = { ...mockEvent, human_reviewed: true };
    render(
      <ReviewConsole
        events={[reviewed]}
        stats={null}
        loading={false}
        onSelectEvent={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.getByText(/all events have been reviewed/i)).toBeInTheDocument();
  });

  it('shows unreviewed events', () => {
    render(
      <ReviewConsole
        events={[mockEvent]}
        stats={null}
        loading={false}
        onSelectEvent={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.getByText('Drone strike hits fuel depot near Dnipro')).toBeInTheDocument();
  });

  it('shows pending review count in filter bar', () => {
    render(
      <ReviewConsole
        events={[mockEvent, mockEventWithDisputes]}
        stats={null}
        loading={false}
        onSelectEvent={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );
    // mockEventWithDisputes has human_reviewed: true → 1 pending (mockEvent)
    expect(screen.getByText(/pending review/i)).toBeInTheDocument();
  });

  it('renders stats row when stats provided', () => {
    render(
      <ReviewConsole
        events={[]}
        stats={mockStats}
        loading={false}
        onSelectEvent={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.getByText('Total Events')).toBeInTheDocument();
    expect(screen.getByText('Reviewed')).toBeInTheDocument();
    expect(screen.getByText('Pending Review')).toBeInTheDocument();
    expect(screen.getByText('With Disputes')).toBeInTheDocument();
    expect(screen.getByText('Review Completion')).toBeInTheDocument();
  });

  it('shows correct stat values', () => {
    render(
      <ReviewConsole
        events={[]}
        stats={mockStats}
        loading={false}
        onSelectEvent={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.getByText('5')).toBeInTheDocument(); // total
    expect(screen.getByText('2')).toBeInTheDocument(); // reviewed
    expect(screen.getByText('40%')).toBeInTheDocument(); // completion
  });

  it('does not show stats row when stats is null', () => {
    render(
      <ReviewConsole
        events={[]}
        stats={null}
        loading={false}
        onSelectEvent={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.queryByText('Total Events')).not.toBeInTheDocument();
  });

  it('shows unconfirmed events section when unconfirmed events exist', () => {
    render(
      <ReviewConsole
        events={[mockEventWithDisputes]}
        stats={null}
        loading={false}
        onSelectEvent={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.getByText(/unconfirmed events/i)).toBeInTheDocument();
  });

  it('calls onRefresh when refresh button clicked', async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn();
    render(
      <ReviewConsole
        events={[]}
        stats={null}
        loading={false}
        onSelectEvent={vi.fn()}
        onRefresh={onRefresh}
      />,
    );
    await user.click(screen.getByText(/↻ refresh/i));
    expect(onRefresh).toHaveBeenCalledOnce();
  });

  it('calls onSelectEvent when an event card is clicked', async () => {
    const user = userEvent.setup();
    const onSelectEvent = vi.fn();
    render(
      <ReviewConsole
        events={[mockEvent]}
        stats={null}
        loading={false}
        onSelectEvent={onSelectEvent}
        onRefresh={vi.fn()}
      />,
    );
    await user.click(screen.getByText('Drone strike hits fuel depot near Dnipro'));
    expect(onSelectEvent).toHaveBeenCalledWith(mockEvent.event_id);
  });
});
