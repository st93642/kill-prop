import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PipelineRunner from '../PipelineRunner';

// Mock the api/client module
vi.mock('../../api/client', () => ({
  runPipeline: vi.fn(),
}));

import * as api from '../../api/client';

const mockRun = api.runPipeline as ReturnType<typeof vi.fn>;

describe('PipelineRunner', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRun.mockResolvedValue({
      stages: {
        source_intake: { articles_ingested: 5, claims_extracted: 20 },
        event_clustering: { events_created: 2 },
        consensus: { events_resolved: 2 },
        scoring: { events_scored: 2 },
      },
      summary: 'Ingested 5 articles, extracted 20 claims, clustered into 2 events.',
    });
  });

  it('renders pipeline stage indicator', () => {
    render(<PipelineRunner onComplete={vi.fn()} />);
    expect(screen.getAllByText(/source intake/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/normalization/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/clustering/i).length).toBeGreaterThan(0);
  });

  it('renders Run Full Pipeline button', () => {
    render(<PipelineRunner onComplete={vi.fn()} />);
    expect(screen.getByRole('button', { name: /run full pipeline/i })).toBeInTheDocument();
  });

  it('shows idle console placeholder initially', () => {
    render(<PipelineRunner onComplete={vi.fn()} />);
    expect(screen.getByText(/click "run full pipeline"/i)).toBeInTheDocument();
  });

  it('button is enabled initially', () => {
    render(<PipelineRunner onComplete={vi.fn()} />);
    expect(screen.getByRole('button', { name: /run full pipeline/i })).not.toBeDisabled();
  });

  it('shows stats cards', () => {
    render(<PipelineRunner onComplete={vi.fn()} />);
    expect(screen.getByText('Pipeline Stages')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
  });

  it('shows "Ready" status initially', () => {
    render(<PipelineRunner onComplete={vi.fn()} />);
    expect(screen.getByText('Ready')).toBeInTheDocument();
  });

  it('runs pipeline and logs stages on click', async () => {
    const user = userEvent.setup();
    render(<PipelineRunner onComplete={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: /run full pipeline/i }));

    await waitFor(() => {
      expect(screen.getByText(/ingesting/i)).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText(/pipeline complete/i)).toBeInTheDocument();
    });
  });

  it('disables button while running', async () => {
    let resolveRun!: (v: unknown) => void;
    mockRun.mockReturnValue(new Promise(r => { resolveRun = r; }));

    const user = userEvent.setup();
    render(<PipelineRunner onComplete={vi.fn()} />);
    await user.click(screen.getByRole('button', { name: /run full pipeline/i }));

    expect(screen.getByRole('button', { name: /running/i })).toBeDisabled();
    await act(async () => { resolveRun({ stages: {}, summary: 'done' }); });
  });

  it('shows Complete status and results pane after success', async () => {
    const user = userEvent.setup();
    render(<PipelineRunner onComplete={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: /run full pipeline/i }));

    await waitFor(() => {
      expect(screen.getByText('Complete')).toBeInTheDocument();
    });
    expect(screen.getByText('Pipeline Results')).toBeInTheDocument();
  });

  it('shows summary text in results', async () => {
    const user = userEvent.setup();
    render(<PipelineRunner onComplete={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: /run full pipeline/i }));

    await waitFor(() => {
      // The summary text appears in both the console log and the results pane
      const elements = screen.getAllByText(/ingested 5 articles, extracted 20 claims, clustered into 2 events/i);
      expect(elements.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('calls onComplete when "View Event Feed" is clicked', async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    render(<PipelineRunner onComplete={onComplete} />);

    await user.click(screen.getByRole('button', { name: /run full pipeline/i }));

    await waitFor(() => {
      expect(screen.getByText(/view event feed/i)).toBeInTheDocument();
    });

    await user.click(screen.getByText(/view event feed/i));
    expect(onComplete).toHaveBeenCalledOnce();
  });

  it('shows error message when API fails', async () => {
    mockRun.mockRejectedValue(new Error('Network error'));
    const user = userEvent.setup();
    render(<PipelineRunner onComplete={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: /run full pipeline/i }));

    await waitFor(() => {
      expect(screen.getByText(/❌ error: network error/i)).toBeInTheDocument();
    });
  });

  it('re-enables button after error', async () => {
    mockRun.mockRejectedValue(new Error('Fail'));
    const user = userEvent.setup();
    render(<PipelineRunner onComplete={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: /run full pipeline/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /run full pipeline/i })).not.toBeDisabled();
    });
  });
});
