import { useState, useMemo, useEffect } from 'react';
import type { EventDetail, SourceClaim } from '../types';
import * as api from '../api/client';
import type { CrossPoolAnalysis, FieldAnalysis } from '../api/client';
import {
  POOL_LABELS,
  POOL_LABELS_SHORT,
  POOL_ORDER,
  poolColor,
  poolIcon,
  poolLabelShort,
  reliabilityLabel,
  reliabilityBadgeClass,
  claimTypeLabel,
  biasSignalLabel,
  agreementLabel,
  fieldLabel,
} from '../labels';

interface Props {
  event: EventDetail;
  onBack: () => void;
}

export default function EventDetailView({ event, onBack }: Props) {
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
    return () => {
      cancelled = true;
    };
  }, [event.event_id]);

  // Group claims by source region
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

  // Fallback: simple claim grouping when no cross-pool analysis is available.
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

      seen.add(sc.claim_id || sc.claim);
      for (const s of similar) seen.add(s.claim_id || s.claim);

      const poolCount = new Set(event.source_pools).size;
      group.allAgree =
        group.pools.size >= Math.min(poolCount, 2) &&
        group.claims.every(c => c.bucket !== 'opinionated_framing');

      groups.push(group);
    }

    return groups;
  }, [event.source_claims_layer, event.source_pools]);

  const toggleSource = (id: string) => {
    setExpandedSources(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const regionCount = event.source_pools.length;
  const hasConflicts = event.contradiction_state === 'disputed_detail';

  return (
    <div className="event-detail">
      <div className="event-detail-header">
        <div>
          <h2>{event.title}</h2>
          <div className="event-meta">
            <span className={`badge ${reliabilityBadgeClass(event.overall_confidence)}`}>
              {reliabilityLabel(event.overall_confidence)}
            </span>
            <span>
              {event.fact_layer.corroborating_sources} source
              {event.fact_layer.corroborating_sources === 1 ? '' : 's'} · {regionCount} region
              {regionCount === 1 ? '' : 's'}
            </span>
            <div className="pool-dots">
              {event.source_pools.map(p => (
                <span key={p} className={`pool-dot ${p}`} title={POOL_LABELS[p] || p} />
              ))}
            </div>
            {hasConflicts && (
              <span style={{ color: 'var(--accent-yellow)' }}>⚠ Conflicting reports</span>
            )}
          </div>
        </div>
        <button className="btn btn-sm" onClick={onBack} style={{ whiteSpace: 'nowrap' }}>
          ← Back
        </button>
      </div>

      {/* ── How different sources report this story ──────────────── */}
      <div className="pane" style={{ marginBottom: 16 }}>
        <div className="pane-header">
          <span className="pane-icon">�</span>
          <h3 style={{ fontSize: 18 }}>How different sources report this</h3>
        </div>
        <p
          style={{
            fontSize: 14,
            color: 'var(--text-secondary)',
            marginBottom: 16,
            lineHeight: 1.5,
          }}
        >
          Details confirmed by several independent sources are more likely to be accurate.
          Details reported by only one source may reflect that outlet's editorial choice.
        </p>

        {loadingAnalysis && (
          <div
            style={{
              padding: 20,
              textAlign: 'center',
              color: 'var(--text-muted)',
              fontSize: 14,
            }}
          >
            ⏳ Comparing coverage across sources…
          </div>
        )}

        {/* LLM-powered qualitative comparison */}
        {crossPool?.llm_comparison && (
          <div
            style={{
              padding: '14px 16px',
              borderRadius: 8,
              border: '1px solid rgba(167,139,250,0.3)',
              background: 'rgba(167,139,250,0.04)',
              marginBottom: 20,
            }}
          >
            <div
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: 'var(--accent-purple)',
                marginBottom: 8,
              }}
            >
              🤖 AI summary
            </div>
            <div
              style={{
                fontSize: 14,
                lineHeight: 1.6,
                color: 'var(--text-primary)',
                whiteSpace: 'pre-wrap',
              }}
            >
              {crossPool.llm_comparison}
            </div>
          </div>
        )}

        {/* Field-by-field comparison */}
        {crossPool &&
          crossPool.fields_analysis.length > 0 && (
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
                <div
                  key={group.key}
                  style={{
                    padding: '12px 14px',
                    borderRadius: 8,
                    border: `1px solid ${
                      isFact
                        ? 'rgba(52,211,153,0.3)'
                        : group.pools.size >= 2
                        ? 'rgba(251,191,36,0.2)'
                        : 'var(--border)'
                    }`,
                    background: isFact ? 'rgba(52,211,153,0.04)' : 'var(--bg-card)',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      marginBottom: 6,
                    }}
                  >
                    {isFact && (
                      <span className="badge badge-green" style={{ fontSize: 11 }}>
                        ALL AGREE
                      </span>
                    )}
                    {!isFact && group.pools.size >= 2 && (
                      <span className="badge badge-yellow" style={{ fontSize: 11 }}>
                        SOME DIFFERENCES
                      </span>
                    )}
                    {group.pools.size === 1 && (
                      <span className="badge badge-gray" style={{ fontSize: 11 }}>
                        ONE SOURCE
                      </span>
                    )}
                    <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                      {group.pools.size} region{group.pools.size > 1 ? 's' : ''}:{' '}
                      {poolNames.join(', ')}
                    </span>
                  </div>
                  <div style={{ fontSize: 14, lineHeight: 1.6, color: 'var(--text-primary)' }}>
                    {group.claims.map((c: SourceClaim, i: number) => (
                      <div
                        key={i}
                        style={{
                          padding: '4px 0',
                          borderLeft: `4px solid ${poolColor(c.source_pool)}`,
                          paddingLeft: 10,
                          marginBottom: i < group.claims.length - 1 ? 6 : 0,
                        }}
                      >
                        <span
                          style={{
                            fontSize: 11,
                            color: 'var(--text-muted)',
                            marginRight: 6,
                            fontWeight: 600,
                          }}
                        >
                          [{POOL_LABELS_SHORT[c.source_pool] || c.source_pool}]
                        </span>
                        <span>{c.claim}</span>
                        {c.propaganda_flags && c.propaganda_flags.length > 0 && (
                          <span
                            style={{
                              marginLeft: 6,
                              fontSize: 10,
                              color: 'var(--accent-red)',
                            }}
                          >
                            🚩{c.propaganda_flags.map(f => biasSignalLabel(f).label).join(', ')}
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

      {/* ── What each region says ─────────────────────────────────── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${Math.min(Object.keys(poolAnalysis).length, 3)}, 1fr)`,
          gap: 12,
          marginBottom: 12,
        }}
      >
        {POOL_ORDER.filter(p => poolAnalysis[p]).map(pool => {
          const data = poolAnalysis[pool];
          const totalClaims = data.claims.length;
          const opinionCount = data.claims.filter(c => c.bucket === 'opinionated_framing').length;
          const biasCount = data.claims.reduce(
            (s, c) => s + (c.propaganda_flags?.length || 0),
            0,
          );

          return (
            <div
              key={pool}
              className="pane"
              style={{
                borderTop: `3px solid ${poolColor(pool)}`,
                padding: 12,
              }}
            >
              <div className="pane-header" style={{ marginBottom: 8 }}>
                <span className="pane-icon">{poolIcon(pool)}</span>
                <h3 style={{ fontSize: 14 }}>{POOL_LABELS[pool] || pool}</h3>
                <span
                  style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-muted)' }}
                >
                  {[...data.sources].join(', ')}
                </span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>
                {totalClaims} statement{totalClaims === 1 ? '' : 's'}
                {opinionCount > 0 && ` · ${opinionCount} opinion${opinionCount > 1 ? 's' : ''}`}
                {biasCount > 0 && ` · ${biasCount} bias signal${biasCount > 1 ? 's' : ''}`}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {data.claims.map((c, i) => (
                  <div
                    key={i}
                    style={{
                      fontSize: 13,
                      lineHeight: 1.5,
                      padding: '6px 8px',
                      borderRadius: 4,
                      background:
                        c.bucket === 'opinionated_framing'
                          ? 'rgba(248,113,113,0.06)'
                          : 'transparent',
                      borderLeft: `2px solid ${
                        c.bucket === 'opinionated_framing'
                          ? 'var(--accent-red)'
                          : 'transparent'
                      }`,
                    }}
                  >
                    <div style={{ color: 'var(--text-primary)' }}>{c.claim}</div>
                    <div
                      style={{
                        display: 'flex',
                        gap: 6,
                        marginTop: 4,
                        flexWrap: 'wrap',
                      }}
                    >
                      <span
                        style={{
                          fontSize: 10,
                          padding: '2px 6px',
                          borderRadius: 3,
                          background:
                            c.bucket === 'verified_fact'
                              ? 'rgba(52,211,153,0.15)'
                              : c.bucket === 'attributed_statement'
                              ? 'rgba(96,165,250,0.15)'
                              : c.bucket === 'inference'
                              ? 'rgba(251,191,36,0.15)'
                              : 'rgba(248,113,113,0.15)',
                          color:
                            c.bucket === 'verified_fact'
                              ? 'var(--accent-green)'
                              : c.bucket === 'attributed_statement'
                              ? 'var(--accent-blue)'
                              : c.bucket === 'inference'
                              ? 'var(--accent-yellow)'
                              : 'var(--accent-red)',
                        }}
                      >
                        {claimTypeLabel(c.bucket)}
                      </span>
                      {c.propaganda_flags &&
                        c.propaganda_flags.map(f => (
                          <span key={f} style={{ fontSize: 10, color: 'var(--accent-red)' }}>
                            🚩{biasSignalLabel(f).label}
                          </span>
                        ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Bias & loaded language ────────────────────────────────── */}
      <BiasAnalysis sourceClaims={event.source_claims_layer} />

      {/* ── Full coverage (source articles) ───────────────────────── */}
      <div className="pane" style={{ marginTop: 12 }}>
        <div className="pane-header">
          <span className="pane-icon">📄</span>
          <h3>Full coverage</h3>
          <span style={{ marginLeft: 'auto', fontSize: 13, color: 'var(--text-muted)' }}>
            {event.fact_layer.corroborating_sources} source
            {event.fact_layer.corroborating_sources === 1 ? '' : 's'}
          </span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {Object.entries(poolAnalysis).map(([pool, data]) => (
            <div key={pool}>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: poolColor(pool),
                  marginBottom: 6,
                  marginTop: 10,
                }}
              >
                {POOL_LABELS[pool] || pool} ({data.claims.length})
              </div>
              {[...data.sources].map(source => {
                const sourceClaims = data.claims.filter(c => c.source === source);
                const isExpanded = expandedSources.has(`${pool}-${source}`);
                const articleUrl = sourceClaims.find(c => c.article_url)?.article_url;
                return (
                  <div
                    key={source}
                    style={{
                      fontSize: 13,
                      padding: '6px 10px',
                      background: 'var(--bg-card)',
                      borderRadius: 6,
                      border: '1px solid var(--border)',
                      marginBottom: 4,
                    }}
                  >
                    <div
                      onClick={() => toggleSource(`${pool}-${source}`)}
                      style={{
                        cursor: 'pointer',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
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
                            🔗 read
                          </a>
                        )}
                      </span>
                      <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                        {sourceClaims.length} statement{sourceClaims.length === 1 ? '' : 's'}{' '}
                        {isExpanded ? '▲' : '▼'}
                      </span>
                    </div>
                    {isExpanded && (
                      <div
                        style={{
                          marginTop: 6,
                          paddingLeft: 10,
                          borderLeft: '2px solid var(--border)',
                        }}
                      >
                        {sourceClaims.map((c, i) => (
                          <div
                            key={i}
                            style={{
                              fontSize: 12,
                              color: 'var(--text-secondary)',
                              padding: '3px 0',
                              lineHeight: 1.5,
                            }}
                          >
                            [{claimTypeLabel(c.bucket)}] {c.claim.slice(0, 150)}
                            {c.claim.length > 150 ? '…' : ''}
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
    </div>
  );
}

/** Field-by-field cross-region comparison card */
function CrossPoolField({ field }: { field: FieldAnalysis }) {
  const poolKeys = Object.keys(field.values_by_pool);
  const label = fieldLabel(field.field);
  const isDisputed = field.agreement_level === 'disputed';
  const isAgreed = field.agreement_level === 'agreed';
  const isSingle = field.agreement_level === 'single_source';

  return (
    <div
      style={{
        padding: '14px 16px',
        borderRadius: 8,
        border: `1px solid ${
          isDisputed
            ? 'rgba(248,113,113,0.4)'
            : isAgreed
            ? 'rgba(52,211,153,0.3)'
            : 'var(--border)'
        }`,
        background: isDisputed
          ? 'rgba(248,113,113,0.03)'
          : isAgreed
          ? 'rgba(52,211,153,0.03)'
          : 'var(--bg-card)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>{label}</span>
        {isAgreed && (
          <span className="badge badge-green" style={{ fontSize: 11 }}>
            ✓ {agreementLabel(field.agreement_level).toUpperCase()}
          </span>
        )}
        {!isAgreed && !isDisputed && !isSingle && (
          <span className="badge badge-yellow" style={{ fontSize: 11 }}>
            ~ {agreementLabel(field.agreement_level).toUpperCase()}
          </span>
        )}
        {isDisputed && (
          <span
            className="badge"
            style={{
              fontSize: 11,
              background: 'rgba(248,113,113,0.15)',
              color: 'var(--accent-red)',
            }}
          >
            ⚠ {agreementLabel(field.agreement_level).toUpperCase()}
          </span>
        )}
        {isSingle && (
          <span className="badge badge-gray" style={{ fontSize: 11 }}>
            {agreementLabel(field.agreement_level).toUpperCase()}
          </span>
        )}
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          {poolKeys.length} region{poolKeys.length > 1 ? 's' : ''}
        </span>
      </div>

      <div
        style={{
          fontSize: 14,
          lineHeight: 1.5,
          color: isDisputed ? 'var(--accent-red)' : 'var(--text-secondary)',
          marginBottom: 12,
          padding: '8px 12px',
          background: 'var(--bg-surface)',
          borderRadius: 6,
        }}
      >
        {field.analysis}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {poolKeys.map(poolKey => {
          const values = field.values_by_pool[poolKey];
          return (
            <div
              key={poolKey}
              style={{
                padding: '8px 12px',
                borderRadius: 6,
                borderLeft: `4px solid ${poolColor(poolKey)}`,
                background: 'var(--bg-surface)',
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: poolColor(poolKey),
                  marginBottom: 4,
                }}
              >
                {POOL_LABELS[poolKey] || poolKey}
              </div>
              {values.map((v, i) => (
                <div key={i} style={{ fontSize: 14, lineHeight: 1.5, color: 'var(--text-primary)' }}>
                  “{v.claim}”
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

function BiasAnalysis({ sourceClaims }: { sourceClaims: SourceClaim[] }) {
  const flagCounts: Record<string, { count: number; sources: Set<string>; examples: string[] }> =
    {};
  const opinionClaims: SourceClaim[] = [];

  for (const sc of sourceClaims) {
    if (sc.bucket === 'opinionated_framing') {
      opinionClaims.push(sc);
    }
    for (const flag of sc.propaganda_flags || []) {
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

  const hasBias = Object.keys(flagCounts).length > 0 || opinionClaims.length > 0;
  if (!hasBias) return null;

  return (
    <div
      className="pane"
      style={{
        marginTop: 16,
        borderColor: 'rgba(248,113,113,0.3)',
        background: 'rgba(248,113,113,0.02)',
      }}
    >
      <div className="pane-header">
        <span className="pane-icon">🚩</span>
        <h3>Bias & loaded language</h3>
        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--accent-red)' }}>
          {Object.values(flagCounts).reduce((s, f) => s + f.count, 0)} signal
          {Object.values(flagCounts).reduce((s, f) => s + f.count, 0) === 1 ? '' : 's'} ·{' '}
          {opinionClaims.length} opinion
          {opinionClaims.length === 1 ? '' : 's'}
        </span>
      </div>
      <p
        style={{
          fontSize: 12,
          color: 'var(--text-muted)',
          marginBottom: 12,
          lineHeight: 1.5,
        }}
      >
        These are wording choices that may push the reader toward a particular view rather than
        simply reporting what happened.
      </p>

      {Object.keys(flagCounts).length > 0 && (
        <div style={{ marginBottom: 12 }}>
          {Object.entries(flagCounts).map(([flag, data]) => {
            const info = biasSignalLabel(flag);
            return (
              <div
                key={flag}
                style={{
                  marginBottom: 8,
                  padding: '8px 12px',
                  background: 'rgba(248,113,113,0.06)',
                  borderRadius: 6,
                  border: '1px solid rgba(248,113,113,0.15)',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    marginBottom: 4,
                  }}
                >
                  <span className="badge badge-red" style={{ fontSize: 10 }}>
                    {info.label}
                  </span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {data.count} time{data.count > 1 ? 's' : ''} · {data.sources.size} source
                    {data.sources.size > 1 ? 's' : ''}
                  </span>
                </div>
                <div
                  style={{
                    fontSize: 11,
                    color: 'var(--text-secondary)',
                    marginBottom: 4,
                  }}
                >
                  {info.desc}
                </div>
                {data.examples.slice(0, 2).map((ex, i) => (
                  <div
                    key={i}
                    style={{
                      fontSize: 11,
                      color: 'var(--text-muted)',
                      fontStyle: 'italic',
                      paddingLeft: 8,
                      borderLeft: '2px solid rgba(248,113,113,0.2)',
                    }}
                  >
                    “{ex}”
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      )}

      {opinionClaims.length > 0 && (
        <div>
          <div
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: 'var(--accent-red)',
              marginBottom: 6,
            }}
          >
            Opinionated coverage ({opinionClaims.length})
          </div>
          {opinionClaims.slice(0, 5).map((fc, i) => (
            <div
              key={i}
              style={{
                fontSize: 11,
                color: 'var(--text-secondary)',
                padding: '4px 8px',
                marginBottom: 4,
                background: 'rgba(248,113,113,0.04)',
                borderRadius: 4,
                borderLeft: '3px solid var(--accent-red)',
              }}
            >
              <span style={{ color: 'var(--text-muted)' }}>{fc.source}:</span> “
              {fc.claim.slice(0, 120)}
              {fc.claim.length > 120 ? '…' : ''}”
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
