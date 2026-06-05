import { useState } from 'react';
import type { EventDetail, SourceClaim } from '../types';
import * as api from '../api/client';

interface Props {
  event: EventDetail;
  onBack: () => void;
  onUpdate: (eventId: string) => void;
}

export default function EventDetailView({ event, onBack, onUpdate }: Props) {
  const [reviewNotes, setReviewNotes] = useState('');
  const [saving, setSaving] = useState(false);

  const poolLabels: Record<string, string> = {
    western_mainstream: 'Western',
    russian_state: 'Russian State',
    russian_independent: 'Russian Ind.',
    neutral_wire: 'Wire',
  };

  const bucketLabels: Record<string, string> = {
    verified_fact: 'Verified Fact',
    attributed_statement: 'Attributed Statement',
    inference: 'Inference',
    opinionated_framing: 'Framing',
  };

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

  return (
    <div className="event-detail">
      <div className="event-detail-header">
        <h2>{event.title}</h2>
        <div className="event-meta">
          <span className={`badge ${
            event.overall_confidence === 'confirmed' ? 'badge-green' :
            event.overall_confidence === 'probable' ? 'badge-blue' :
            event.overall_confidence === 'disputed' ? 'badge-yellow' : 'badge-gray'
          }`}>
            {event.overall_confidence}
          </span>
          <span>{event.fact_layer.corroborating_sources} corroborating sources</span>
          <span>{event.fact_layer.pool_spread} pool spread</span>
          <div className="pool-dots">
            {event.source_pools.map(p => (
              <span key={p} className={`pool-dot ${p}`} title={poolLabels[p] || p} />
            ))}
          </div>
          {event.contradiction_state === 'disputed_detail' && (
            <span style={{ color: 'var(--accent-yellow)' }}>⚠ Has disputed fields</span>
          )}
          {event.human_reviewed && (
            <span style={{ color: 'var(--accent-green)' }}>✓ Reviewed</span>
          )}
        </div>
      </div>

      <div className="three-pane">
        {/* Pane 1: Facts agreed across sources */}
        <div className="pane">
          <div className="pane-header">
            <span className="pane-icon">✅</span>
            <h3>Facts Agreed Across Sources</h3>
            <span className={`badge ${
              event.fact_layer.confidence === 'confirmed' ? 'badge-green' :
              event.fact_layer.confidence === 'probable' ? 'badge-blue' : 'badge-yellow'
            }`} style={{ marginLeft: 'auto' }}>
              {event.fact_layer.confidence}
            </span>
          </div>
          <p style={{ fontSize: 14, marginBottom: 12, color: 'var(--text-primary)', lineHeight: 1.6 }}>
            {event.fact_layer.summary}
          </p>
          <div className="fact-fields">
            {Object.entries(event.fact_layer.fields).map(([field, value]) => (
              <span key={field} className="fact-tag">
                {field.replace(/_/g, ' ')}: {value.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        </div>

        {/* Pane 2: Claims still disputed */}
        <div className="pane" style={Object.keys(event.dispute_layer.fields).length === 0 ? {} : { borderColor: 'rgba(251,191,36,0.3)' }}>
          <div className="pane-header">
            <span className="pane-icon">⚡</span>
            <h3>Disputed Details</h3>
            {Object.keys(event.dispute_layer.fields).length > 0 && (
              <span className="badge badge-yellow" style={{ marginLeft: 'auto' }}>
                {Object.keys(event.dispute_layer.fields).length} fields
              </span>
            )}
          </div>
          {Object.keys(event.dispute_layer.fields).length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              No field-level disputes. All core facts are corroborated across sources.
            </p>
          ) : (
            Object.entries(event.dispute_layer.fields).map(([field, resolution]) => (
              <div key={field} className="dispute-item">
                <div className="dispute-field">
                  {field.replace(/_/g, ' ')} — {resolution.status}
                </div>
                <div className="dispute-detail">
                  {resolution.value
                    ? `Abstracted to: ${resolution.value.replace(/_/g, ' ')}`
                    : 'Disputed — no safe abstraction available'}
                </div>
                {resolution.disputed_values.length > 0 && (
                  <div className="dispute-sources">
                    Conflicting values: {resolution.disputed_values.join(', ')}
                  </div>
                )}
                {resolution.top_support && (
                  <div className="dispute-sources">
                    Top: {resolution.top_support.value} (score: {resolution.top_support.score}) from {resolution.top_support.pool_count} pool(s)
                  </div>
                )}
              </div>
            ))
          )}
          {event.dispute_layer.contradictions.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4 style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Contradictions
              </h4>
              {event.dispute_layer.contradictions.map((c, i) => (
                <div key={i} className="dispute-item" style={{ borderColor: 'rgba(248,113,113,0.2)', background: 'rgba(248,113,113,0.03)' }}>
                  <div className="dispute-field" style={{ color: 'var(--accent-red)' }}>
                    {c.description}
                  </div>
                  <div className="dispute-detail">
                    Type: {c.type} · State: {c.state}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Pane 3: Source claims layer */}
        <div className="pane">
          <div className="pane-header">
            <span className="pane-icon">📋</span>
            <h3>Source Claims & Evidence Trail</h3>
            <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-muted)' }}>
              {event.source_claims_layer.length} claims
            </span>
          </div>
          <table className="source-claims-table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Pool</th>
                <th>Claim</th>
                <th>Attribution</th>
                <th>Type</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {event.source_claims_layer.map((sc: SourceClaim) => (
                <tr key={sc.claim_id || `${sc.source}-${sc.claim.slice(0, 20)}`}>
                  <td style={{ fontWeight: 500, whiteSpace: 'nowrap' }}>{sc.source}</td>
                  <td>
                    <span className={`source-pool-label badge-${getPoolBadgeColor(sc.source_pool)}`}>
                      {poolLabels[sc.source_pool] || sc.source_pool}
                    </span>
                  </td>
                  <td style={{ maxWidth: 300, fontSize: 12, lineHeight: 1.4 }}>{sc.claim}</td>
                  <td style={{ fontSize: 11, color: 'var(--text-muted)', maxWidth: 120 }}>
                    {sc.attribution || '—'}
                  </td>
                  <td>
                    <span className={`source-pool-label ${getBucketBadgeColor(sc.bucket)}`}>
                      {bucketLabels[sc.bucket] || sc.bucket}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                    {sc.score.toFixed(3)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Review panel */}
      <div className="review-panel">
        <h4>✏️ Human Review</h4>
        <textarea
          placeholder="Add review notes, observations, or override justifications..."
          value={reviewNotes}
          onChange={e => setReviewNotes(e.target.value)}
        />
        <div className="review-actions">
          <button className="btn btn-success btn-sm" onClick={handleApprove} disabled={saving}>
            {saving ? 'Saving...' : '✓ Approve Event'}
          </button>
          <button
            className="btn btn-sm"
            onClick={handleSaveReview}
            disabled={saving || !reviewNotes}
          >
            {saving ? 'Saving...' : '💾 Save Notes'}
          </button>
        </div>
        {event.human_reviewed && event.human_review_notes && (
          <div style={{ marginTop: 10, padding: 8, background: 'rgba(167,139,250,0.08)', borderRadius: 6, fontSize: 12, color: 'var(--text-secondary)' }}>
            <strong style={{ color: 'var(--accent-purple)' }}>Previous notes:</strong>
            <p style={{ marginTop: 4 }}>{event.human_review_notes}</p>
          </div>
        )}
      </div>
    </div>
  );
}

function getPoolBadgeColor(pool: string): string {
  switch (pool) {
    case 'western_mainstream': return 'blue';
    case 'russian_state': return 'red';
    case 'russian_independent': return 'purple';
    case 'neutral_wire': return 'green';
    default: return 'gray';
  }
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