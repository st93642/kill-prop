import { useState, useMemo, useEffect } from 'react';
import type { EventDetail, SourceClaim } from '../types';
import * as api from '../api/client';
import type { CrossPoolAnalysis, FieldAnalysis } from '../api/client';

interface Props {
  event: EventDetail;
  onBack: () => void;
  onUpdate: (eventId: string) => void;
}

const POOL_LABELS: Record<string, string> = {
  western_mainstream: 'Western',
  russian_state: 'Russian State',
  russian_independent: 'Russian Ind.',
  chinese_state: 'Chinese State',
  neutral_wire: 'Wire',
  middle_eastern: 'Middle East',
  latin_american: 'Latin America',
  african: 'African',
  south_asian: 'South Asia',
  east_asian: 'East Asia',
};

const POOL_ORDER = [
  'western_mainstream', 'russian_state', 'russian_independent', 'chinese_state',
  'neutral_wire', 'middle_eastern', 'latin_american', 'african', 'south_asian', 'east_asian',
];

const FIELD_LABELS: Record<string, string> = {
  actor: 'Who did it?',
  weapon_type: 'What weapon?',
  location: 'Where?',
  casualties: 'Casualties',
  target: 'What was hit?',
  event_type: 'Type of event',
  time: 'When?',
};

export default function EventDetailView({ event, onBack, onUpdate }: Props) {
  const [reviewNotes, setReviewNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());
  const [crossPool, setCrossPool] = useState<CrossPoolAnalysis | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoadingAnalysis(true);
      try {
        const result = await api.getCrossPoolAnalysis(event.event_id);
        if (!cancelled) setCrossPool(result);
      } catch {
        if (!cancelled) setCrossPool(null);
      } finally {
        if (!cancelled) setLoadingAnalysis(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [event.event_id]);

  const handleSaveReview = async () => {
    setSaving(true);
    try {
      await api.updateReview(event.event_id, reviewNotes);
      onUpdate(event.event_id);
    } finally {
      setSaving(false);
    }
  };

  const handleApprove = async () => {
    setSaving(true);
    try {
      await api.approveEvent(event.event_id);
      onUpdate(event.event_id);
    } finally {
      setSaving(false);
    }
  };

  // ── Pool-by-pool claim analysis ──────────────────────────────────
  const poolAnalysis = useMemo(() => {
    const pools: Record<string, { claims: SourceClaim[]; sources: Set<string> }> = {};
    for (const sc of event.source_claims_layer) {
      if (!pools[sc.source_pool]) {
        pools[sc.source_pool] = { claims: [], sources: new Set() };
      }
      pools[sc.source_pool].claims.push(sc);
      pools[sc.source_pool].sources.add(sc.source);
    }
    return pools;
  }, [event.source_claims_layer]);

  // ── Cross-pool claim overlap detection ───────────────────────────
  const crossPoolAnalysis = useMemo(() => {
    type ClaimGroup = {
      key: string;
      claims: SourceClaim[];
      pools: Set<string>;
      allAgree: boolean;
    };
    const groups: ClaimGroup[] = [];
    const seen = new Set<string>();

    for (const sc of event.source_claims_layer) {
      if (seen.has(sc.claim_id || sc.claim)) continue;
      
      // Find similar claims across pools (simple word overlap)
      const similar = event.source_claims_layer.filter(other => {
        if (other === sc) return false;
        if (seen.has(other.claim_id || other.claim)) return false;
        const words1 = new Set(sc.claim.toLowerCase().split(/\s+/).filter(w => w.length > 3));
        const words2 = new Set(other.claim.toLowerCase().split(/\s+/).filter(w => w.length > 3));
        if (words1.size === 0 || words2.size === 0) return false;
        const intersection = [...words1].filter(w => words2.has(w));
        return intersection.length / Math.min(words1.size, words2.size) > 0.5;
      });

      const group: ClaimGroup = {
        key: sc.claim_id || sc.claim.slice(0, 40),
        claims: [sc, ...similar],
        pools: new Set([sc.source_pool, ...similar.map(s => s.source_pool)]),
        allAgree: false,
      };
      
      // Mark all as seen
      seen.add(sc.claim_id || sc.claim);
      for (const s of similar) seen.add(s.claim_id || s.claim);
      
      // Check if all pools represented agree (identical or near-identical wording)
      const poolCount = new Set(event.source_pools).size;
      group.allAgree = group.pools.size >= Math.min(poolCount, 2) && 
        group.claims.every(c => c.bucket !== 'opinionated_framing');
      
      groups.push(group);
    }
    
    return groups;
  }, [event.source_claims_layer, event.source_pools]);

  const toggleSource = (id: string) => {
    setExpandedSources(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  return (
    <div className="event-detail">
      <div className="event-detail-header">
        <div>
          <h2>{event.title}</h2>
          <div className="event-meta">
            <span className={`badge ${
              event.overall_confidence === 'confirmed' ? 'badge-green' :
              event.overall_confidence === 'probable' ? 'badge-blue' :
              event.overall_confidence === 'disputed' ? 'badge-yellow' : 'badge-gray'
            }`}>{event.overall_confidence}</span>
            <span>{event.fact_layer.corroborating_sources} sources</span>
            <span>{event.fact_layer.pool_spread} pools</span>
            <div className="pool-dots">
              {event.source_pools.map(p => (
                <span key={p} className={`pool-dot ${p}`} title={POOL_LABELS[p] || p} />
              ))}
            </div>
            {event.contradiction_state === 'disputed_detail' && (
              <span style={{ color: 'var(--accent-yellow)' }}>⚠ Disputed</span>
            )}
            {event.human_reviewed && (
              <span style={{ color: 'var(--accent-green)' }}>✓ Reviewed</span>
            )}
          </div>
        </div>
        <button className="btn btn-sm" onClick={onBack} style={{ whiteSpace: 'nowrap' }}>← Back</button>
      </div>

      {/* ── Cross-Pool Claim Analysis ─────────────────────────── */}
      <div className="pane" style={{ marginBottom: 16 }}>
        <div className="pane-header">
          <span className="pane-icon">🔬</span>
          <h3 style={{ fontSize: 18 }}>Cross-Pool Claim Analysis</h3>
        </div>
        <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 16, lineHeight: 1.5 }}>
          Claims that appear across multiple pools with similar wording are more likely to be factual.
          Single-pool claims may reflect editorial bias or selective omission.
        </p>

        {loadingAnalysis && (
          <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: 14 }}>
            ⏳ Analyzing cross-pool patterns...
          </div>
        )}

        {/* LLM-powered qualitative comparison */}
        {crossPool?.llm_comparison && (
          <div style={{
            padding: '14px 16px',
            borderRadius: 8,
            border: '1px solid rgba(167,139,250,0.3)',
            background: 'rgba(167,139,250,0.04)',
            marginBottom: 20,
          }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-purple)', marginBottom: 8 }}>
              🤖 LLM Analysis
            </div>
            <div style={{ fontSize: 14, lineHeight: 1.6, color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>
              {crossPool.llm_comparison}
            </div>
          </div>
        )}

        {/* Field-by-field comparison */}
        {crossPool && crossPool.fields_analysis.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {crossPool.fields_analysis.map(field => (
              <CrossPoolField key={field.field} field={field} />
            ))}
          </div>
        )}

        {/* Fallback: simple claim list if no cross-pool data */}
        {!crossPool && !loadingAnalysis && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {crossPoolAnalysis.map(group => {
              const poolNames = [...group.pools].map((p: string) => POOL_LABELS[p] || p);
              const isFact = group.allAgree && group.pools.size >= 2;
              return (
                <div key={group.key} style={{
                  padding: '12px 14px',
                  borderRadius: 8,
                  border: `1px solid ${isFact ? 'rgba(52,211,153,0.3)' : group.pools.size >= 2 ? 'rgba(251,191,36,0.2)' : 'var(--border)'}`,
                  background: isFact ? 'rgba(52,211,153,0.04)' : 'var(--bg-card)',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    {isFact && <span className="badge badge-green" style={{ fontSize: 11 }}>AGREED</span>}
                    {!isFact && group.pools.size >= 2 && <span className="badge badge-yellow" style={{ fontSize: 11 }}>VARIANT</span>}
                    {group.pools.size === 1 && <span className="badge badge-gray" style={{ fontSize: 11 }}>SINGLE</span>}
                    <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                      {group.pools.size} pool{group.pools.size > 1 ? 's' : ''}: {poolNames.join(', ')}
                    </span>
                  </div>
                  <div style={{ fontSize: 14, lineHeight: 1.6, color: 'var(--text-primary)' }}>
                    {group.claims.map((c: SourceClaim, i: number) => (
                      <div key={i} style={{
                        padding: '4px 0',
                        borderLeft: `4px solid ${getPoolColor(c.source_pool)}`,
                        paddingLeft: 10,
                        marginBottom: i < group.claims.length - 1 ? 6 : 0,
                      }}>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginRight: 6, fontWeight: 600 }}>
                          [{POOL_LABELS[c.source_pool] || c.source_pool}]
                        </span>
                        <span>{c.claim}</span>
                        {c.propaganda_flags && c.propaganda_flags.length > 0 && (
                          <span style={{ marginLeft: 6, fontSize: 10, color: 'var(--accent-red)' }}>
                            🚩{c.propaganda_flags.join(',')}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Pool-by-Pool Breakdown ──────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(Object.keys(poolAnalysis).length, 3)}, 1fr)`, gap: 12, marginBottom: 12 }}>
        {POOL_ORDER.filter(p => poolAnalysis[p]).map(pool => {
          const data = poolAnalysis[pool];
          const totalClaims = data.claims.length;
          const framingCount = data.claims.filter(c => c.bucket === 'opinionated_framing').length;
          const propagandaCount = data.claims.reduce((s, c) => s + (c.propaganda_flags?.length || 0), 0);
          
          return (
            <div key={pool} className="pane" style={{ 
              borderTop: `3px solid ${getPoolColor(pool)}`,
              padding: 12,
            }}>
              <div className="pane-header" style={{ marginBottom: 8 }}>
                <span className="pane-icon">{getPoolIcon(pool)}</span>
                <h3 style={{ fontSize: 14 }}>{POOL_LABELS[pool] || pool}</h3>
                <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-muted)' }}>
                  {[...data.sources].join(', ')}
                </span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>
                {totalClaims} claims · {framingCount} framing · {propagandaCount} propaganda
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {data.claims.map((c, i) => (
                  <div key={i} style={{
                    fontSize: 13,
                    lineHeight: 1.5,
                    padding: '6px 8px',
                    borderRadius: 4,
                    background: c.bucket === 'opinionated_framing' ? 'rgba(248,113,113,0.06)' : 'transparent',
                    borderLeft: `2px solid ${c.bucket === 'opinionated_framing' ? 'var(--accent-red)' : 'transparent'}`,
                  }}>
                    <div style={{ color: 'var(--text-primary)' }}>{c.claim}</div>
                    <div style={{ display: 'flex', gap: 6, marginTop: 4, flexWrap: 'wrap' }}>
                      <span style={{ 
                        fontSize: 10, 
                        padding: '2px 6px', 
                        borderRadius: 3,
                        background: c.bucket === 'verified_fact' ? 'rgba(52,211,153,0.15)' :
                                   c.bucket === 'attributed_statement' ? 'rgba(96,165,250,0.15)' :
                                   c.bucket === 'inference' ? 'rgba(251,191,36,0.15)' :
                                   'rgba(248,113,113,0.15)',
                        color: c.bucket === 'verified_fact' ? 'var(--accent-green)' :
                               c.bucket === 'attributed_statement' ? 'var(--accent-blue)' :
                               c.bucket === 'inference' ? 'var(--accent-yellow)' : 'var(--accent-red)',
                      }}>
                        {c.bucket.replace(/_/g, ' ')}
                      </span>
                      {c.propaganda_flags && c.propaganda_flags.map(f => (
                        <span key={f} style={{ fontSize: 10, color: 'var(--accent-red)' }}>🚩{f}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Propaganda & Framing Analysis ────────────────────────── */}
      <PropagandaAnalysis sourceClaims={event.source_claims_layer} />

      {/* ── Article Sources ──────────────────────────── */}
      <div className="pane" style={{ marginTop: 12 }}>
        <div className="pane-header">
          <span className="pane-icon">📄</span>
          <h3>Source Articles</h3>
          <span style={{ marginLeft: 'auto', fontSize: 13, color: 'var(--text-muted)' }}>
            {event.source_claims_layer.length} claims from {event.fact_layer.corroborating_sources} sources
          </span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {Object.entries(poolAnalysis).map(([pool, data]) => (
            <div key={pool}>
              <div style={{ 
                fontSize: 13, 
                fontWeight: 600, 
                color: getPoolColor(pool),
                marginBottom: 6,
                marginTop: 10,
              }}>
                {POOL_LABELS[pool] || pool} ({data.claims.length} claims)
              </div>
              {[...data.sources].map(source => {
                const sourceClaims = data.claims.filter(c => c.source === source);
                const isExpanded = expandedSources.has(`${pool}-${source}`);
                const articleUrl = sourceClaims.find(c => c.article_url)?.article_url;
                return (
                  <div key={source} style={{
                    fontSize: 13,
                    padding: '6px 10px',
                    background: 'var(--bg-card)',
                    borderRadius: 6,
                    border: '1px solid var(--border)',
                    marginBottom: 4,
                  }}>
                    <div 
                      onClick={() => toggleSource(`${pool}-${source}`)}
                      style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                    >
                      <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                        {source}
                        {articleUrl && articleUrl.startsWith('http') && (
                          <a 
                            href={articleUrl} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            onClick={e => e.stopPropagation()}
                            style={{ 
                              marginLeft: 8, 
                              fontSize: 11, 
                              color: 'var(--accent-blue)',
                              textDecoration: 'none',
                            }}
                          >
                            🔗 view
                          </a>
                        )}
                      </span>
                      <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                        {sourceClaims.length} claims {isExpanded ? '▲' : '▼'}
                      </span>
                    </div>
                    {isExpanded && (
                      <div style={{ marginTop: 6, paddingLeft: 10, borderLeft: '2px solid var(--border)' }}>
                        {sourceClaims.map((c, i) => (
                          <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '3px 0', lineHeight: 1.5 }}>
                            [{c.bucket.replace(/_/g, ' ')}] {c.claim.slice(0, 150)}{c.claim.length > 150 ? '…' : ''}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* ── Review panel ─────────────────────────────────────────── */}
      <div className="review-panel" style={{ marginTop: 16 }}>
        <h4>✏️ Human Review</h4>
        <textarea
          placeholder="Add review notes..."
          value={reviewNotes}
          onChange={e => setReviewNotes(e.target.value)}
        />
        <div className="review-actions">
          <button className="btn btn-success btn-sm" onClick={handleApprove} disabled={saving}>
            {saving ? 'Saving...' : '✓ Approve'}
          </button>
          <button className="btn btn-sm" onClick={handleSaveReview} disabled={saving || !reviewNotes}>
            {saving ? 'Saving...' : '💾 Save Notes'}
          </button>
        </div>
        {event.human_reviewed && event.human_review_notes && (
          <div style={{ marginTop: 10, padding: 8, background: 'rgba(167,139,250,0.08)', borderRadius: 6, fontSize: 12, color: 'var(--text-secondary)' }}>
            <strong style={{ color: 'var(--accent-purple)' }}>Notes:</strong>
            <p style={{ marginTop: 4 }}>{event.human_review_notes}</p>
          </div>
        )}
      </div>
    </div>
  );
}

function getPoolColor(pool: string): string {
  switch (pool) {
    case 'western_mainstream': return '#60a5fa';
    case 'russian_state': return '#f87171';
    case 'russian_independent': return '#a78bfa';
    case 'chinese_state': return '#fb923c';
    case 'neutral_wire': return '#34d399';
    case 'middle_eastern': return '#fbbf24';
    case 'latin_american': return '#34d399';
    case 'african': return '#f97316';
    case 'south_asian': return '#818cf8';
    case 'east_asian': return '#fb7185';
    default: return '#6b7280';
  }
}

function getPoolIcon(pool: string): string {
  switch (pool) {
    case 'western_mainstream': return '🌍';
    case 'russian_state': return '🇷🇺';
    case 'russian_independent': return '🗣️';
    case 'chinese_state': return '🇨🇳';
    case 'neutral_wire': return '📡';
    case 'middle_eastern': return '🕌';
    case 'latin_american': return '🌎';
    case 'african': return '🌍';
    case 'south_asian': return '🛕';
    case 'east_asian': return '⛩️';
    default: return '📰';
  }
}

/** Field-by-field cross-pool comparison card */
function CrossPoolField({ field }: { field: FieldAnalysis }) {
  const poolKeys = Object.keys(field.values_by_pool);
  const label = FIELD_LABELS[field.field] || field.field;
  const isDisputed = field.agreement_level === 'disputed';
  const isAgreed = field.agreement_level === 'agreed';
  const isSingle = field.agreement_level === 'single_source';

  return (
    <div style={{
      padding: '14px 16px',
      borderRadius: 8,
      border: `1px solid ${isDisputed ? 'rgba(248,113,113,0.4)' : isAgreed ? 'rgba(52,211,153,0.3)' : 'var(--border)'}`,
      background: isDisputed ? 'rgba(248,113,113,0.03)' : isAgreed ? 'rgba(52,211,153,0.03)' : 'var(--bg-card)',
    }}>
      {/* Field header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>
          {label}
        </span>
        {isAgreed && <span className="badge badge-green" style={{ fontSize: 11 }}>✓ AGREED</span>}
        {!isAgreed && !isDisputed && !isSingle && <span className="badge badge-yellow" style={{ fontSize: 11 }}>~ VARIANT</span>}
        {isDisputed && <span className="badge" style={{ fontSize: 11, background: 'rgba(248,113,113,0.15)', color: 'var(--accent-red)' }}>⚠ DISPUTED</span>}
        {isSingle && <span className="badge badge-gray" style={{ fontSize: 11 }}>SINGLE SOURCE</span>}
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          {poolKeys.length} pool{poolKeys.length > 1 ? 's' : ''}
        </span>
      </div>

      {/* Analysis text */}
      <div style={{
        fontSize: 14,
        lineHeight: 1.5,
        color: isDisputed ? 'var(--accent-red)' : 'var(--text-secondary)',
        marginBottom: 12,
        padding: '8px 12px',
        background: 'var(--bg-surface)',
        borderRadius: 6,
      }}>
        {field.analysis}
      </div>

      {/* Pool-by-pool values */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {poolKeys.map(poolKey => {
          const values = field.values_by_pool[poolKey];
          return (
            <div key={poolKey} style={{
              padding: '8px 12px',
              borderRadius: 6,
              borderLeft: `4px solid ${getPoolColor(poolKey)}`,
              background: 'var(--bg-surface)',
            }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: getPoolColor(poolKey), marginBottom: 4 }}>
                {POOL_LABELS[poolKey] || poolKey}
              </div>
              {values.map((v, i) => (
                <div key={i} style={{ fontSize: 14, lineHeight: 1.5, color: 'var(--text-primary)' }}>
                  "{v.claim}"
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                    — {v.source}
                  </div>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function getBucketBadgeColor(bucket: string): string {
  switch (bucket) {
    case 'verified_fact': return 'green';
    case 'attributed_statement': return 'blue';
    case 'inference': return 'yellow';
    case 'opinionated_framing': return 'red';
    default: return 'gray';
  }
}
function PropagandaAnalysis({ sourceClaims }: { sourceClaims: SourceClaim[] }) {
  // Aggregate propaganda flags across all claims
  const flagCounts: Record<string, { count: number; sources: Set<string>; examples: string[] }> = {};
  const framingClaims: SourceClaim[] = [];
  
  for (const sc of sourceClaims) {
    if (sc.bucket === 'opinionated_framing') {
      framingClaims.push(sc);
    }
    for (const flag of (sc.propaganda_flags || [])) {
      if (!flagCounts[flag]) {
        flagCounts[flag] = { count: 0, sources: new Set(), examples: [] };
      }
      flagCounts[flag].count++;
      flagCounts[flag].sources.add(sc.source);
      if (flagCounts[flag].examples.length < 3) {
        flagCounts[flag].examples.push(sc.claim.slice(0, 100) + '…');
      }
    }
  }

  const hasPropaganda = Object.keys(flagCounts).length > 0 || framingClaims.length > 0;
  if (!hasPropaganda) return null;

  const flagLabels: Record<string, { label: string; desc: string }> = {
    loaded_language: { label: 'Loaded Language', desc: 'Emotionally charged terms designed to provoke a reaction' },
    us_vs_them: { label: 'Us vs. Them', desc: 'Framing that divides groups into opposing camps' },
    certainty_without_evidence: { label: 'Certainty Without Evidence', desc: 'Absolute claims presented without supporting proof' },
  };

  return (
    <div className="pane" style={{ marginTop: 16, borderColor: 'rgba(248,113,113,0.3)', background: 'rgba(248,113,113,0.02)' }}>
      <div className="pane-header">
        <span className="pane-icon">🚩</span>
        <h3>Propaganda & Framing Analysis</h3>
        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--accent-red)' }}>
          {Object.values(flagCounts).reduce((s, f) => s + f.count, 0)} signals · {framingClaims.length} framing claims
        </span>
      </div>

      {Object.keys(flagCounts).length > 0 && (
        <div style={{ marginBottom: 12 }}>
          {Object.entries(flagCounts).map(([flag, data]) => {
            const info = flagLabels[flag] || { label: flag, desc: '' };
            return (
              <div key={flag} style={{
                marginBottom: 8,
                padding: '8px 12px',
                background: 'rgba(248,113,113,0.06)',
                borderRadius: 6,
                border: '1px solid rgba(248,113,113,0.15)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <span className="badge badge-red" style={{ fontSize: 10 }}>{info.label}</span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {data.count} occurrence{data.count > 1 ? 's' : ''} · {data.sources.size} source{data.sources.size > 1 ? 's' : ''}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>{info.desc}</div>
                {data.examples.slice(0, 2).map((ex, i) => (
                  <div key={i} style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic', paddingLeft: 8, borderLeft: '2px solid rgba(248,113,113,0.2)' }}>
                    "{ex}"
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      )}

      {framingClaims.length > 0 && (
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-red)', marginBottom: 6 }}>
            Opinionated Framing Claims ({framingClaims.length})
          </div>
          {framingClaims.slice(0, 5).map((fc, i) => (
            <div key={i} style={{
              fontSize: 11,
              color: 'var(--text-secondary)',
              padding: '4px 8px',
              marginBottom: 4,
              background: 'rgba(248,113,113,0.04)',
              borderRadius: 4,
              borderLeft: '3px solid var(--accent-red)',
            }}>
              <span style={{ color: 'var(--text-muted)' }}>{fc.source}:</span> "{fc.claim.slice(0, 120)}{fc.claim.length > 120 ? '…' : ''}"
            </div>
          ))}
        </div>
      )}
    </div>
  );
}