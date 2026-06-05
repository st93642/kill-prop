import type { EventSummary } from '../types';

interface Props {
  event: EventSummary;
  onClick: () => void;
}

export default function EventCard({ event, onClick }: Props) {
  const confidenceColors: Record<string, string> = {
    confirmed: 'badge-green',
    probable: 'badge-blue',
    single_source: 'badge-gray',
    disputed: 'badge-yellow',
    unknown: 'badge-gray',
  };

  const poolLabels: Record<string, string> = {
    western_mainstream: 'Western',
    russian_state: 'Russian State',
    russian_independent: 'Russian Ind.',
    chinese_state: 'Chinese State',
    neutral_wire: 'Wire',
  };

  return (
    <div className="event-card" onClick={onClick}>
      <div className="event-card-header">
        <span className="event-title">{event.title}</span>
        <span className={`badge ${confidenceColors[event.overall_confidence] || 'badge-gray'}`}>
          {event.overall_confidence}
        </span>
      </div>
      <div className="event-summary">{event.fact_summary}</div>
      <div className="event-footer">
        <span>{event.corroborating_sources} sources · {event.pool_count} pools</span>
        {event.dispute_count > 0 && (
          <span style={{ color: 'var(--accent-yellow)', marginLeft: 8 }}>
            ⚠ {event.dispute_count} disputed
          </span>
        )}
        <span style={{ marginLeft: 'auto', display: 'flex', gap: 3 }}>
          {event.pools.map(p => (
            <span key={p} className={`pool-dot ${p}`} title={poolLabels[p] || p} />
          ))}
        </span>
      </div>
    </div>
  );
}