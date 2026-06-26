import type { EventSummary, EventDetail, ArticleSummary, DashboardStats } from '../types';

export const mockEvent: EventSummary = {
  event_id: 'e_test001',
  title: 'Drone strike hits fuel depot near Dnipro',
  topic: 'geopolitics, military',
  fact_summary: 'Strike involving drone at fuel depot in dnipro',
  overall_confidence: 'confirmed',
  contradiction_state: 'corroborated',
  corroborating_sources: 3,
  pool_spread: 2,
  pool_count: 3,
  pools: ['western_mainstream', 'neutral_wire', 'russian_state'],
  dispute_count: 0,
  contradiction_count: 0,
  source_claim_count: 5,
  updated_at: '2026-06-05T03:10:00Z',
  human_reviewed: false,
};

export const mockEventWithDisputes: EventSummary = {
  ...mockEvent,
  event_id: 'e_test002',
  title: 'Casualties dispute near Dnipro region',
  overall_confidence: 'disputed',
  contradiction_state: 'disputed_detail',
  dispute_count: 2,
  contradiction_count: 1,
  human_reviewed: true,
};

export const mockEventDetail: EventDetail = {
  event_id: 'e_test001',
  title: 'Drone strike hits fuel depot near Dnipro',
  topic: 'geopolitics, military',
  created_at: '2026-06-05T00:00:00Z',
  updated_at: '2026-06-05T03:10:00Z',
  overall_confidence: 'confirmed',
  contradiction_state: 'corroborated',
  human_reviewed: false,
  source_pools: ['western_mainstream', 'neutral_wire'],
  fact_layer: {
    summary: 'Strike involving drone at fuel depot in dnipro',
    fields: { event_type: 'strike', weapon_type: 'drone', target: 'fuel_depot' },
    confidence: 'confirmed',
    corroborating_sources: 3,
    pool_spread: 2,
  },
  dispute_layer: {
    fields: {},
    contradictions: [],
  },
  source_claims_layer: [
    {
      source: 'Reuters',
      source_pool: 'western_mainstream',
      claim: 'A drone struck a fuel depot near the Dnipro river.',
      attribution: null,
      bucket: 'verified_fact',
      score: 0.75,
    },
    {
      source: 'Wire Service',
      source_pool: 'neutral_wire',
      claim: 'A drone strike was confirmed by wire service.',
      attribution: 'Wire Service',
      bucket: 'attributed_statement',
      score: 0.65,
    },
  ],
};

export const mockEventDetailWithDisputes: EventDetail = {
  ...mockEventDetail,
  event_id: 'e_test002',
  overall_confidence: 'disputed',
  contradiction_state: 'disputed_detail',
  dispute_layer: {
    fields: {
      weapon_type: {
        status: 'disputed',
        value: null,
        disputed_values: ['drone', 'artillery'],
        top_support: {
          value: 'drone',
          score: 0.45,
          pool_count: 2,
          source_names: ['Reuters', 'Wire Service'],
        },
      },
    },
    contradictions: [
      {
        type: 'field_level',
        outcome: 'unresolved',
        field: 'weapon_type',
        description: 'Sources disagree on weapon type',
        state: 'disputed_detail',
      },
    ],
  },
};

export const mockArticles: ArticleSummary[] = [
  {
    article_id: 'a_001',
    title: 'Russian drone strike hits key bridge near Kyiv',
    source: 'Western Herald',
    source_pool: 'western_mainstream',
    language: 'en',
    claim_count: 6,
  },
  {
    article_id: 'a_002',
    title: 'Ukrainian drone hits military fuel depot',
    source: 'Eastern Times',
    source_pool: 'russian_state',
    language: 'en',
    claim_count: 5,
  },
];

export const mockStats: DashboardStats = {
  total_events: 5,
  reviewed: 2,
  pending_review: 3,
  with_disputes: 1,
  unconfirmed: 1,
  review_completion: 40.0,
};
