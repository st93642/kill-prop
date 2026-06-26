import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import EventFeed from '../EventFeed';
import { mockEvent, mockEventWithDisputes } from '../../test/fixtures';

const defaultFilter = { pool: '', min_confidence: '', topic: '' };

describe('EventFeed', () => {
  it('shows loading spinner when loading', () => {
    render(
      <EventFeed
        events={[]}
        loading={true}
        filter={defaultFilter}
        onFilterChange={vi.fn()}
        onSelectEvent={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.getByText(/loading stories/i)).toBeInTheDocument();
  });

  it('shows empty state when not loading and no events', () => {
    render(
      <EventFeed
        events={[]}
        loading={false}
        filter={defaultFilter}
        onFilterChange={vi.fn()}
        onSelectEvent={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.getByText(/no stories yet/i)).toBeInTheDocument();
  });

  it('renders event cards for each event', () => {
    render(
      <EventFeed
        events={[mockEvent, mockEventWithDisputes]}
        loading={false}
        filter={defaultFilter}
        onFilterChange={vi.fn()}
        onSelectEvent={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.getByText('Drone strike hits fuel depot near Dnipro')).toBeInTheDocument();
  });

  it('shows stats row when events are present', () => {
    render(
      <EventFeed
        events={[mockEvent]}
        loading={false}
        filter={defaultFilter}
        onFilterChange={vi.fn()}
        onSelectEvent={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.getByText('Stories')).toBeInTheDocument();
    expect(screen.getAllByText('Confirmed').length).toBeGreaterThan(0);
    // "Conflicting reports" appears as both a stat label and a filter option
    expect(screen.getAllByText('Conflicting reports').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Regions covered')).toBeInTheDocument();
  });

  it('shows correct confirmed count', () => {
    render(
      <EventFeed
        events={[mockEvent, mockEventWithDisputes]}
        loading={false}
        filter={defaultFilter}
        onFilterChange={vi.fn()}
        onSelectEvent={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );
    // mockEvent is confirmed, mockEventWithDisputes is disputed → 1 confirmed
    const confirmedCount = screen.getAllByText('1').find(
      el => el.nextElementSibling?.textContent === 'Confirmed',
    );
    expect(confirmedCount).toBeInTheDocument();
  });

  it('renders region filter select', () => {
    render(
      <EventFeed
        events={[]}
        loading={false}
        filter={defaultFilter}
        onFilterChange={vi.fn()}
        onSelectEvent={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.getByDisplayValue('All regions')).toBeInTheDocument();
  });

  it('renders reliability filter select', () => {
    render(
      <EventFeed
        events={[]}
        loading={false}
        filter={defaultFilter}
        onFilterChange={vi.fn()}
        onSelectEvent={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.getByDisplayValue('All reliability')).toBeInTheDocument();
  });

  it('renders search input', () => {
    render(
      <EventFeed
        events={[]}
        loading={false}
        filter={defaultFilter}
        onFilterChange={vi.fn()}
        onSelectEvent={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.getByPlaceholderText(/search stories/i)).toBeInTheDocument();
  });

  it('calls onFilterChange when region filter changes', async () => {
    const user = userEvent.setup();
    const onFilterChange = vi.fn();
    render(
      <EventFeed
        events={[]}
        loading={false}
        filter={defaultFilter}
        onFilterChange={onFilterChange}
        onSelectEvent={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );
    await user.selectOptions(screen.getByDisplayValue('All regions'), 'western_mainstream');
    expect(onFilterChange).toHaveBeenCalledWith({
      ...defaultFilter,
      pool: 'western_mainstream',
    });
  });

  it('calls onFilterChange when search input changes', async () => {
    const user = userEvent.setup();
    const onFilterChange = vi.fn();
    render(
      <EventFeed
        events={[]}
        loading={false}
        filter={defaultFilter}
        onFilterChange={onFilterChange}
        onSelectEvent={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );
    await user.type(screen.getByPlaceholderText(/search stories/i), 'military');
    expect(onFilterChange).toHaveBeenCalled();
  });

  it('calls onRefresh when refresh button is clicked', async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn();
    render(
      <EventFeed
        events={[]}
        loading={false}
        filter={defaultFilter}
        onFilterChange={vi.fn()}
        onSelectEvent={vi.fn()}
        onRefresh={onRefresh}
      />,
    );
    await user.click(screen.getByText('↻'));
    expect(onRefresh).toHaveBeenCalledOnce();
  });

  it('calls onSelectEvent when an event card is clicked', async () => {
    const user = userEvent.setup();
    const onSelectEvent = vi.fn();
    render(
      <EventFeed
        events={[mockEvent]}
        loading={false}
        filter={defaultFilter}
        onFilterChange={vi.fn()}
        onSelectEvent={onSelectEvent}
        onRefresh={vi.fn()}
      />,
    );
    await user.click(screen.getByText('Drone strike hits fuel depot near Dnipro'));
    expect(onSelectEvent).toHaveBeenCalledWith(mockEvent.event_id);
  });
});
