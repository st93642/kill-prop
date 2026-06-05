import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import EventDetailView from '../EventDetail';
import { mockEventDetail, mockEventDetailWithDisputes } from '../../test/fixtures';

vi.mock('../../api/client', () => ({
  updateReview: vi.fn(),
  approveEvent: vi.fn(),
}));

import * as api from '../../api/client';
const mockUpdateReview = api.updateReview as ReturnType<typeof vi.fn>;
const mockApproveEvent = api.approveEvent as ReturnType<typeof vi.fn>;

describe('EventDetailView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUpdateReview.mockResolvedValue({
      message: 'Review saved',
      event_id: 'e_test001',
      human_reviewed: true,
    });
    mockApproveEvent.mockResolvedValue({
      message: 'Event approved',
      event_id: 'e_test001',
    });
  });

  it('renders event title', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} onUpdate={vi.fn()} />);
    expect(screen.getByText('Drone strike hits fuel depot near Dnipro')).toBeInTheDocument();
  });

  it('renders confidence badge', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} onUpdate={vi.fn()} />);
    // confidence badge appears in the header metadata
    const badge = document.querySelector('.badge-green');
    expect(badge).toBeInTheDocument();
    expect(badge?.textContent).toBe('confirmed');
  });

  it('renders fact layer summary', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} onUpdate={vi.fn()} />);
    expect(screen.getByText(/Strike involving drone/i)).toBeInTheDocument();
  });

  it('renders Facts Agreed pane header', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} onUpdate={vi.fn()} />);
    expect(screen.getByText('Facts Agreed Across Sources')).toBeInTheDocument();
  });

  it('renders Disputed Details pane header', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} onUpdate={vi.fn()} />);
    expect(screen.getByText('Disputed Details')).toBeInTheDocument();
  });

  it('renders Source Claims pane header', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} onUpdate={vi.fn()} />);
    expect(screen.getByText('Source Claims & Evidence Trail')).toBeInTheDocument();
  });

  it('renders source claims in table', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} onUpdate={vi.fn()} />);
    expect(screen.getByText('Reuters')).toBeInTheDocument();
    expect(screen.getAllByText('Wire Service').length).toBeGreaterThan(0);
    expect(screen.getByText(/A drone struck a fuel depot/i)).toBeInTheDocument();
  });

  it('shows "no disputes" message when no dispute fields', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} onUpdate={vi.fn()} />);
    expect(screen.getByText(/no field-level disputes/i)).toBeInTheDocument();
  });

  it('shows dispute fields when disputes exist', () => {
    render(<EventDetailView event={mockEventDetailWithDisputes} onBack={vi.fn()} onUpdate={vi.fn()} />);
    // The dispute field label renders in the dispute pane with " — disputed" suffix
    expect(screen.getByText(/weapon type — disputed/i)).toBeInTheDocument();
  });

  it('shows contradictions when present', () => {
    render(<EventDetailView event={mockEventDetailWithDisputes} onBack={vi.fn()} onUpdate={vi.fn()} />);
    expect(screen.getByText('Contradictions')).toBeInTheDocument();
    expect(screen.getByText(/sources disagree on weapon type/i)).toBeInTheDocument();
  });

  it('renders review panel with textarea', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} onUpdate={vi.fn()} />);
    expect(screen.getByPlaceholderText(/add review notes/i)).toBeInTheDocument();
  });

  it('Approve button is enabled', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} onUpdate={vi.fn()} />);
    expect(screen.getByText(/approve event/i)).not.toBeDisabled();
  });

  it('Save Notes button is disabled when textarea is empty', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} onUpdate={vi.fn()} />);
    expect(screen.getByText(/save notes/i)).toBeDisabled();
  });

  it('Save Notes button is enabled when textarea has text', async () => {
    const user = userEvent.setup();
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} onUpdate={vi.fn()} />);
    await user.type(screen.getByPlaceholderText(/add review notes/i), 'Some notes');
    expect(screen.getByText(/save notes/i)).not.toBeDisabled();
  });

  it('calls approveEvent and onUpdate when Approve is clicked', async () => {
    const user = userEvent.setup();
    const onUpdate = vi.fn();
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} onUpdate={onUpdate} />);
    await user.click(screen.getByText(/approve event/i));
    await waitFor(() => {
      expect(mockApproveEvent).toHaveBeenCalledWith('e_test001');
      expect(onUpdate).toHaveBeenCalledWith('e_test001');
    });
  });

  it('calls updateReview and onUpdate when Save Notes is clicked', async () => {
    const user = userEvent.setup();
    const onUpdate = vi.fn();
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} onUpdate={onUpdate} />);
    await user.type(screen.getByPlaceholderText(/add review notes/i), 'Test note');
    await user.click(screen.getByText(/save notes/i));
    await waitFor(() => {
      expect(mockUpdateReview).toHaveBeenCalledWith('e_test001', 'Test note');
      expect(onUpdate).toHaveBeenCalledWith('e_test001');
    });
  });

  it('shows "Reviewed" badge when human_reviewed is true', () => {
    const reviewed = { ...mockEventDetail, human_reviewed: true };
    render(<EventDetailView event={reviewed} onBack={vi.fn()} onUpdate={vi.fn()} />);
    expect(screen.getByText(/✓ Reviewed/i)).toBeInTheDocument();
  });

  it('shows disputed fields warning badge when contradiction state is disputed_detail', () => {
    render(<EventDetailView event={mockEventDetailWithDisputes} onBack={vi.fn()} onUpdate={vi.fn()} />);
    expect(screen.getByText(/has disputed fields/i)).toBeInTheDocument();
  });

  it('renders fact layer field tags', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} onUpdate={vi.fn()} />);
    expect(screen.getByText(/event type: strike/i)).toBeInTheDocument();
  });

  it('renders source pool labels in claims table', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} onUpdate={vi.fn()} />);
    expect(screen.getByText('Western')).toBeInTheDocument();
    expect(screen.getByText('Wire')).toBeInTheDocument();
  });

  it('renders claim scores in table', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} onUpdate={vi.fn()} />);
    expect(screen.getByText('0.750')).toBeInTheDocument();
    expect(screen.getByText('0.650')).toBeInTheDocument();
  });
});
