import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PipelineRunner from '../PipelineRunner';

// Mock the api/client module
vi.mock('../../api/client', () => ({
  ingestArticles: vi.fn(),
  clusterEvents: vi.fn(),
  runPipeline: vi.fn(),
}));

import * as api from '../../api/client';

const mockIngest = api.ingestArticles as ReturnType<typeof vi.fn>;
const mockCluster = api.clusterEvents as ReturnType<typeof vi.fn>;
const mockRun = api.runPipeline as ReturnType<typeof vi.fn>;

describe('PipelineRunner', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIngest.mockResolvedValue({
      message: 'Ingested 5 articles',
      article_ids: ['a1', 'a2'],
      total_claims: 20,
    });
    mockCluster.mockResolvedValue({
      message: 'Clustered into 2 events',
      event_ids: ['e1', 'e2'],
    });
    mockRun.mockResolvedValue({
      stages: {
        source_intake: { articles_ingested: 5, claims_extracted: 20 },
        event_clustering: { events_created: 2 },
      },
      summary: 'Ingested 5 articles, extracted 20 claims, clustered into 2 events.',
    });
  });

  it('renders pipeline stage indicator', () => {
    render(<PipelineRunner onComplete={vi.fn()} />);
    // Steps render as "○ Source Intake" etc. — use getAllByText or a partial match
    expect(screen.getAllByText(/source intake/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/normalization/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/clustering/i).length).toBeGreaterThan(0);
  });

  it('renders Run Full Pipeline button', () => {
    render(<PipelineRunner onComplete={vi.fn()} />);
    // Button text is "▶ Run Full Pipeline"
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
      expect(screen.getByText(/ingesting articles/i)).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText(/pipeline complete/i)).toBeInTheDocument();
    });
  });

  it('disables button while running', async () => {
    // Make the pipeline hang until we check the button
    let resolveIngest!: (v: unknown) => void;
    mockIngest.mockReturnValue(new Promise(r => { resolveIngest = r; }));

    const user = userEvent.setup();
    render(<PipelineRunner onComplete={vi.fn()} />);
    await user.click(screen.getByRole('button', { name: /run full pipeline/i }));

    expect(screen.getByText(/running/i)).toBeDisabled();
    resolveIngest({ message: 'done', article_ids: [], total_claims: 0 });
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
      expect(screen.getByText(/ingested 5 articles/i)).toBeInTheDocument();
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
    mockIngest.mockRejectedValue(new Error('Network error'));
    const user = userEvent.setup();
    render(<PipelineRunner onComplete={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: /run full pipeline/i }));

    await waitFor(() => {
      expect(screen.getByText(/❌ error: network error/i)).toBeInTheDocument();
    });
  });

  it('re-enables button after error', async () => {
    mockIngest.mockRejectedValue(new Error('Fail'));
    const user = userEvent.setup();
    render(<PipelineRunner onComplete={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: /run full pipeline/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /run full pipeline/i })).not.toBeDisabled();
    });
  });
});
