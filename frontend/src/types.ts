export type SourcePool = 
  | 'western_mainstream'
  | 'russian_state'
  | 'russian_independent'
  | 'chinese_state'
  | 'neutral_wire';

export type ConfidenceClass =
  | 'confirmed'
  | 'probable'
  | 'single_source'
  | 'disputed'
  | 'unknown';

export type FieldResolutionStatus =
  | 'confirmed'
  | 'abstracted'
  | 'disputed'
  | 'unknown'
  | 'single_source';

export type ContradictionState =
  | 'reported'
  | 'corroborated'
  | 'disputed_detail'
  | 'resolved'
  | 'corrected';

export interface ArticleSummary {
  article_id: string;
  title: string;
  source: string;
  source_pool: string;
  language: string;
  claim_count: number;
}

export interface EventSummary {
  event_id: string;
  title: string;
  topic: string;
  fact_summary: string;
  overall_confidence: string;
  contradiction_state: string;
  corroborating_sources: number;
  pool_spread: number;
  pool_count: number;
  pools: string[];
  dispute_count: number;
  contradiction_count: number;
  source_claim_count: number;
  updated_at: string;
  human_reviewed: boolean;
}

export interface FactLayer {
  summary: string;
  fields: Record<string, string>;
  confidence: string;
  corroborating_sources: number;
  pool_spread: number;
}

export interface TopSupport {
  value: string;
  score: number;
  pool_count: number;
  source_names: string[];
}

export interface FieldResolution {
  status: string;
  value: string | null;
  disputed_values: string[];
  top_support: TopSupport | null;
}

export interface ContradictionInfo {
  type: string;
  outcome: string | null;
  field: string;
  description: string;
  state: string;
}

export interface SourceClaim {
  source: string;
  source_pool: string;
  claim: string;
  attribution: string | null;
  bucket: string;
  score: number;
  claim_id?: string;
}

export interface EventDetail {
  event_id: string;
  title: string;
  topic: string;
  created_at: string;
  updated_at: string;
  overall_confidence: string;
  contradiction_state: string;
  human_reviewed: boolean;
  source_pools: string[];
  fact_layer: FactLayer;
  dispute_layer: {
    fields: Record<string, FieldResolution>;
    contradictions: ContradictionInfo[];
  };
  source_claims_layer: SourceClaim[];
}

export interface DashboardStats {
  total_events: number;
  reviewed: number;
  pending_review: number;
  with_disputes: number;
  unconfirmed: number;
  review_completion: number;
}

export interface PipelineResult {
  stages: Record<string, any>;
  summary: string;
}

export interface ClaimDetail {
  claim_id: string;
  text_original: string;
  text_normalized: string | null;
  bucket: string;
  arguments: Record<string, {value: string; normalized: string | null; attributed: boolean}>;
  evidence: Record<string, boolean>;
  attribution: {status: string; speaker: string | null; phrase: string | null};
  propaganda_flags: string[];
  confidence: number;
}