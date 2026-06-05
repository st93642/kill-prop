import type {
  ArticleSummary,
  ClaimDetail,
  DashboardStats,
  EventDetail,
  EventSummary,
  PipelineResult,
} from '../types';

const API_BASE = '/api';

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API error ${res.status}: ${error}`);
  }
  return res.json();
}

export async function healthCheck(): Promise<{status: string}> {
  return fetchJSON('/health');
}

export async function runPipeline(): Promise<PipelineResult> {
  return fetchJSON('/pipeline/run');
}

export async function ingestArticles(): Promise<{message: string; article_ids: string[]; total_claims: number}> {
  return fetchJSON('/articles/ingest', { method: 'POST' });
}

export async function listArticles(): Promise<ArticleSummary[]> {
  return fetchJSON('/articles');
}

export async function getArticle(articleId: string): Promise<{
  article_id: string;
  title: string;
  source: string;
  source_pool: string;
  full_text: string;
  claims: ClaimDetail[];
}> {
  return fetchJSON(`/articles/${articleId}`);
}

export async function clusterEvents(): Promise<{message: string; event_ids: string[]}> {
  return fetchJSON('/events/cluster', { method: 'POST' });
}

export async function listEvents(params?: {
  pool?: string;
  min_confidence?: string;
  topic?: string;
}): Promise<EventSummary[]> {
  const search = new URLSearchParams();
  if (params?.pool) search.set('pool', params.pool);
  if (params?.min_confidence) search.set('min_confidence', params.min_confidence);
  if (params?.topic) search.set('topic', params.topic);
  const qs = search.toString();
  return fetchJSON(`/events${qs ? `?${qs}` : ''}`);
}

export async function getEventDetail(eventId: string): Promise<EventDetail> {
  return fetchJSON(`/events/${eventId}`);
}

export async function updateReview(
  eventId: string,
  notes?: string,
): Promise<{message: string; event_id: string; human_reviewed: boolean}> {
  return fetchJSON(`/review/${eventId}/notes`, {
    method: 'PUT',
    body: JSON.stringify({ notes: notes || '' }),
  });
}

export async function getReviewDashboard(): Promise<DashboardStats> {
  return fetchJSON('/review/dashboard');
}

export async function overrideField(
  eventId: string,
  field: string,
  overrideValue: string,
  reason?: string,
): Promise<{message: string; event_id: string}> {
  return fetchJSON(`/review/${eventId}/override`, {
    method: 'POST',
    body: JSON.stringify({ field, override_value: overrideValue, reason }),
  });
}

export async function approveEvent(eventId: string): Promise<{message: string; event_id: string}> {
  return fetchJSON(`/review/${eventId}/approve`, { method: 'POST' });
}