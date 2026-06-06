import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ArticleViewer from '../ArticleViewer';
import { mockArticles } from '../../test/fixtures';

vi.mock('../../api/client', () => ({
  getArticle: vi.fn(),
}));

import * as api from '../../api/client';
const mockGetArticle = api.getArticle as ReturnType<typeof vi.fn>;

const mockArticleDetail = {
  article_id: 'a_001',
  title: 'Russian drone strike hits key bridge near Kyiv',
  source: 'Western Herald',
  source_pool: 'western_mainstream',
  full_text: 'A Russian Shahed drone struck a fuel depot near the Dnipro river early Friday.',
  claims: [
    {
      claim_id: 'c_001',
      text_original: 'A drone struck a fuel depot.',
      text_normalized: '[shahed_drone] struck a [fuel_depot].',
      bucket: 'verified_fact',
      arguments: {
        weapon_type: { value: 'shahed-136', normalized: 'shahed_drone', attributed: false },
      },
      evidence: {
        quote: false,
        official_statement: true,
        primary_media: false,
        document_link: false,
        eyewitness: false,
        satellite_imagery: false,
        timestamp_geolocation: false,
      },
      attribution: { status: 'on_record', speaker: null, phrase: null },
      propaganda_flags: [],
      confidence: 0.75,
    },
  ],
};

describe('ArticleViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetArticle.mockResolvedValue(mockArticleDetail);
  });

  it('shows empty state when no articles', () => {
    render(<ArticleViewer articles={[]} />);
    expect(screen.getByText(/no articles ingested yet/i)).toBeInTheDocument();
  });

  it('renders article list', () => {
    render(<ArticleViewer articles={mockArticles} />);
    expect(screen.getByText('Russian drone strike hits key bridge near Kyiv')).toBeInTheDocument();
    expect(screen.getByText('Ukrainian drone hits military fuel depot')).toBeInTheDocument();
  });

  it('shows article count in heading', () => {
    render(<ArticleViewer articles={mockArticles} />);
    expect(screen.getByText(`Articles (${mockArticles.length})`)).toBeInTheDocument();
  });

  it('shows article source and pool', () => {
    render(<ArticleViewer articles={mockArticles} />);
    expect(screen.getByText(/western herald/i)).toBeInTheDocument();
    expect(screen.getByText(/western mainstream/i)).toBeInTheDocument();
  });

  it('shows claim count per article', () => {
    render(<ArticleViewer articles={mockArticles} />);
    expect(screen.getByText('6 claims')).toBeInTheDocument();
    expect(screen.getByText('5 claims')).toBeInTheDocument();
  });

  it('shows select-an-article placeholder when none selected', () => {
    render(<ArticleViewer articles={mockArticles} />);
    expect(screen.getByText(/select an article/i)).toBeInTheDocument();
  });

  it('loads and shows article detail when an article is clicked', async () => {
    const user = userEvent.setup();
    render(<ArticleViewer articles={mockArticles} />);

    await user.click(screen.getByText('Russian drone strike hits key bridge near Kyiv'));

    await waitFor(() => {
      expect(mockGetArticle).toHaveBeenCalledWith('a_001');
    });
    await waitFor(() => {
      expect(screen.getByText(/A Russian Shahed drone struck/i)).toBeInTheDocument();
    });
  });

  it('shows full text pane after article is loaded', async () => {
    const user = userEvent.setup();
    render(<ArticleViewer articles={mockArticles} />);
    await user.click(screen.getByText('Russian drone strike hits key bridge near Kyiv'));

    await waitFor(() => {
      expect(screen.getByText('Full Text')).toBeInTheDocument();
    });
  });

  it('shows extracted claims pane after article is loaded', async () => {
    const user = userEvent.setup();
    render(<ArticleViewer articles={mockArticles} />);
    await user.click(screen.getByText('Russian drone strike hits key bridge near Kyiv'));

    await waitFor(() => {
      expect(screen.getByText(/extracted claims/i)).toBeInTheDocument();
    });
  });

  it('shows claim text in claims table', async () => {
    const user = userEvent.setup();
    render(<ArticleViewer articles={mockArticles} />);
    await user.click(screen.getByText('Russian drone strike hits key bridge near Kyiv'));

    await waitFor(() => {
      expect(screen.getByText(/A drone struck a fuel depot/i)).toBeInTheDocument();
    });
  });

  it('shows claim bucket in claims table', async () => {
    const user = userEvent.setup();
    render(<ArticleViewer articles={mockArticles} />);
    await user.click(screen.getByText('Russian drone strike hits key bridge near Kyiv'));

    await waitFor(() => {
      expect(screen.getByText('verified fact')).toBeInTheDocument();
    });
  });

  it('shows loading indicator while fetching', async () => {
    let resolve!: (v: unknown) => void;
    mockGetArticle.mockReturnValue(new Promise(r => { resolve = r; }));

    const user = userEvent.setup();
    render(<ArticleViewer articles={mockArticles} />);
    await user.click(screen.getByText('Russian drone strike hits key bridge near Kyiv'));

    expect(screen.getByText(/loading article/i)).toBeInTheDocument();
    await act(async () => { resolve(mockArticleDetail); });
  });

  it('shows claim arguments in table', async () => {
    const user = userEvent.setup();
    render(<ArticleViewer articles={mockArticles} />);
    await user.click(screen.getByText('Russian drone strike hits key bridge near Kyiv'));

    await waitFor(() => {
      expect(screen.getAllByText(/shahed_drone/i).length).toBeGreaterThan(0);
    });
  });
});
