import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as client from '../client';

// Mock global fetch
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

function mockOk(body: unknown) {
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(''),
  } as Response);
}

function mockError(status: number, text: string) {
  return Promise.resolve({
    ok: false,
    status,
    json: () => Promise.resolve({}),
    text: () => Promise.resolve(text),
  } as Response);
}

describe('API client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('healthCheck', () => {
    it('calls /api/health', async () => {
      mockFetch.mockReturnValue(mockOk({ status: 'healthy' }));
      const result = await client.healthCheck();
      expect(mockFetch).toHaveBeenCalledWith('/api/health', expect.any(Object));
      expect(result).toEqual({ status: 'healthy' });
    });
  });

  describe('runPipeline', () => {
    it('calls GET /api/pipeline/run', async () => {
      mockFetch.mockReturnValue(mockOk({ stages: {}, summary: 'done' }));
      await client.runPipeline();
      expect(mockFetch).toHaveBeenCalledWith('/api/pipeline/run', expect.any(Object));
    });
  });

  describe('ingestArticles', () => {
    it('calls POST /api/articles/ingest', async () => {
      mockFetch.mockReturnValue(mockOk({ message: 'done', article_ids: [], total_claims: 0 }));
      await client.ingestArticles();
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/articles/ingest',
        expect.objectContaining({ method: 'POST' }),
      );
    });

    it('returns ingest result', async () => {
      const data = { message: 'Ingested 5 articles', article_ids: ['a1'], total_claims: 10 };
      mockFetch.mockReturnValue(mockOk(data));
      const result = await client.ingestArticles();
      expect(result).toEqual(data);
    });
  });

  describe('listArticles', () => {
    it('calls GET /api/articles', async () => {
      mockFetch.mockReturnValue(mockOk([]));
      await client.listArticles();
      expect(mockFetch).toHaveBeenCalledWith('/api/articles', expect.any(Object));
    });
  });

  describe('getArticle', () => {
    it('calls GET /api/articles/:id', async () => {
      mockFetch.mockReturnValue(mockOk({ article_id: 'a1' }));
      await client.getArticle('a1');
      expect(mockFetch).toHaveBeenCalledWith('/api/articles/a1', expect.any(Object));
    });
  });

  describe('clusterEvents', () => {
    it('calls POST /api/events/cluster', async () => {
      mockFetch.mockReturnValue(mockOk({ message: 'done', event_ids: [] }));
      await client.clusterEvents();
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/events/cluster',
        expect.objectContaining({ method: 'POST' }),
      );
    });
  });

  describe('listEvents', () => {
    it('calls GET /api/events with no params', async () => {
      mockFetch.mockReturnValue(mockOk([]));
      await client.listEvents();
      expect(mockFetch).toHaveBeenCalledWith('/api/events', expect.any(Object));
    });

    it('appends pool query param when provided', async () => {
      mockFetch.mockReturnValue(mockOk([]));
      await client.listEvents({ pool: 'western_mainstream' });
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/events?pool=western_mainstream',
        expect.any(Object),
      );
    });

    it('appends min_confidence query param', async () => {
      mockFetch.mockReturnValue(mockOk([]));
      await client.listEvents({ min_confidence: 'confirmed' });
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/events?min_confidence=confirmed',
        expect.any(Object),
      );
    });

    it('appends topic query param', async () => {
      mockFetch.mockReturnValue(mockOk([]));
      await client.listEvents({ topic: 'military' });
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/events?topic=military',
        expect.any(Object),
      );
    });

    it('appends multiple query params', async () => {
      mockFetch.mockReturnValue(mockOk([]));
      await client.listEvents({ pool: 'western_mainstream', topic: 'military' });
      const url = mockFetch.mock.calls[0][0] as string;
      expect(url).toContain('pool=western_mainstream');
      expect(url).toContain('topic=military');
    });

    it('omits empty string params', async () => {
      mockFetch.mockReturnValue(mockOk([]));
      await client.listEvents({ pool: '', min_confidence: '', topic: '' });
      expect(mockFetch).toHaveBeenCalledWith('/api/events', expect.any(Object));
    });
  });

  describe('getEventDetail', () => {
    it('calls GET /api/events/:id', async () => {
      mockFetch.mockReturnValue(mockOk({ event_id: 'e1' }));
      await client.getEventDetail('e1');
      expect(mockFetch).toHaveBeenCalledWith('/api/events/e1', expect.any(Object));
    });
  });

  describe('updateReview', () => {
    it('calls PUT /api/events/:id/review', async () => {
      mockFetch.mockReturnValue(mockOk({ message: 'saved', event_id: 'e1', human_reviewed: true }));
      await client.updateReview('e1', 'notes');
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/events/e1/review',
        expect.objectContaining({ method: 'PUT' }),
      );
    });

    it('sends notes in body', async () => {
      mockFetch.mockReturnValue(mockOk({ message: 'saved', event_id: 'e1', human_reviewed: true }));
      await client.updateReview('e1', 'test notes');
      const [, options] = mockFetch.mock.calls[0];
      expect(JSON.parse(options.body)).toMatchObject({ notes: 'test notes' });
    });
  });

  describe('getReviewDashboard', () => {
    it('calls GET /api/review/dashboard', async () => {
      mockFetch.mockReturnValue(mockOk({ total_events: 0 }));
      await client.getReviewDashboard();
      expect(mockFetch).toHaveBeenCalledWith('/api/review/dashboard', expect.any(Object));
    });
  });

  describe('overrideField', () => {
    it('calls POST /api/review/:id/override', async () => {
      mockFetch.mockReturnValue(mockOk({ message: 'done', event_id: 'e1' }));
      await client.overrideField('e1', 'weapon_type', 'drone', 'Correction');
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/review/e1/override',
        expect.objectContaining({ method: 'POST' }),
      );
    });

    it('sends field/value/reason in body', async () => {
      mockFetch.mockReturnValue(mockOk({ message: 'done', event_id: 'e1' }));
      await client.overrideField('e1', 'weapon_type', 'drone', 'reason');
      const [, options] = mockFetch.mock.calls[0];
      expect(JSON.parse(options.body)).toEqual({
        field: 'weapon_type',
        override_value: 'drone',
        reason: 'reason',
      });
    });
  });

  describe('approveEvent', () => {
    it('calls POST /api/review/:id/approve', async () => {
      mockFetch.mockReturnValue(mockOk({ message: 'approved', event_id: 'e1' }));
      await client.approveEvent('e1');
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/review/e1/approve',
        expect.objectContaining({ method: 'POST' }),
      );
    });
  });

  describe('error handling', () => {
    it('throws an error when response is not ok', async () => {
      mockFetch.mockReturnValue(mockError(404, 'Not found'));
      await expect(client.getEventDetail('bad_id')).rejects.toThrow('API error 404: Not found');
    });

    it('throws an error for 500 responses', async () => {
      mockFetch.mockReturnValue(mockError(500, 'Internal Server Error'));
      await expect(client.healthCheck()).rejects.toThrow('API error 500');
    });
  });
});
