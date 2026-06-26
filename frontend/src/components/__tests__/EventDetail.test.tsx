import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import EventDetailView from '../EventDetail';
import { mockEventDetail, mockEventDetailWithDisputes } from '../../test/fixtures';

// The component fetches cross-pool analysis on mount; stub the network call.
vi.mock('../../api/client', () => ({
  getCrossPoolAnalysis: vi.fn().mockResolvedValue({
    event_id: 'e_test001',
    title: 'Drone strike hits fuel depot near Dnipro',
    pool_count: 2,
    pools_represented: ['western_mainstream', 'neutral_wire'],
    fields_analysis: [],
    llm_comparison: null,
    dispute_layer: { contradictions: [] },
  }),
}));

import * as api from '../../api/client';
const mockGetCrossPool = api.getCrossPoolAnalysis as ReturnType<typeof vi.fn>;

describe('EventDetailView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetCrossPool.mockResolvedValue({
      event_id: 'e_test001',
      title: 'Drone strike hits fuel depot near Dnipro',
      pool_count: 2,
      pools_represented: ['western_mainstream', 'neutral_wire'],
      fields_analysis: [],
      llm_comparison: null,
      dispute_layer: { contradictions: [] },
    });
  });

  it('renders event title', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} />);
    expect(screen.getByText('Drone strike hits fuel depot near Dnipro')).toBeInTheDocument();
  });

  it('renders plain-language reliability badge', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} />);
    expect(screen.getByText('Confirmed')).toBeInTheDocument();
  });

  it('renders "How different sources report this" section', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} />);
    expect(screen.getByText(/how different sources report this/i)).toBeInTheDocument();
  });

  it('renders "Full coverage" section', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} />);
    expect(screen.getByText('Full coverage')).toBeInTheDocument();
  });

  it('renders region labels in plain language', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} />);
    expect(screen.getAllByText('Western media').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Wire services').length).toBeGreaterThanOrEqual(1);
  });

  it('renders claim text', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} />);
    const elements = screen.getAllByText(/A drone struck a fuel depot near the Dnipro river/i);
    expect(elements.length).toBeGreaterThanOrEqual(1);
  });

  it('renders plain claim-type labels (Fact / Quote)', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} />);
    expect(screen.getAllByText('Fact').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Quote').length).toBeGreaterThanOrEqual(1);
  });

  it('does NOT render the analyst review panel', () => {
    render(<EventDetailView event={mockEventDetail} onBack={vi.fn()} />);
    expect(screen.queryByPlaceholderText(/add review notes/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/save notes/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/approve/i)).not.toBeInTheDocument();
  });

  it('does NOT render the analyst "Reviewed" badge even when human_reviewed is true', () => {
    const reviewed = { ...mockEventDetail, human_reviewed: true };
    render(<EventDetailView event={reviewed} onBack={vi.fn()} />);
    expect(screen.queryByText(/✓ Reviewed/i)).not.toBeInTheDocument();
  });

  it('shows conflicting-reports warning when contradiction state is disputed_detail', () => {
    render(<EventDetailView event={mockEventDetailWithDisputes} onBack={vi.fn()} />);
    expect(screen.getByText(/⚠ Conflicting reports/i)).toBeInTheDocument();
  });

  it('renders Bias & loaded language section when claims have propaganda flags', async () => {
    const withFlags: typeof mockEventDetail = {
      ...mockEventDetail,
      source_claims_layer: [
        {
          ...mockEventDetail.source_claims_layer[0],
          propaganda_flags: ['loaded_language'],
        },
      ],
    };
    mockGetCrossPool.mockResolvedValue({
      event_id: 'e_test001',
      title: 'Drone strike hits fuel depot near Dnipro',
      pool_count: 1,
      pools_represented: ['western_mainstream'],
      fields_analysis: [],
      llm_comparison: null,
      dispute_layer: { contradictions: [] },
    });
    render(<EventDetailView event={withFlags} onBack={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByText(/Bias & loaded language/i)).toBeInTheDocument();
    });
    expect(screen.getByText('Emotional language')).toBeInTheDocument();
  });
});
