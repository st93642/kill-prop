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
        <span>
          {event.corroborating_sources} sources
        </span>
        <span>·</span>
        <span>{event.pool_spread} pools</span>
        {event.dispute_count > 0 && (
          <>
            <span>·</span>
            <span style={{ color: 'var(--accent-yellow)' }}>
              ⚠ {event.dispute_count} dispute{event.dispute_count > 1 ? 's' : ''}
            </span>
          </>
        )}
        <span>·</span>
        <div className="pool-dots">
          {event.pools.map(p => (
            <span key={p} className={`pool-dot ${p}`} title={poolLabels[p] || p} />
          ))}
        </div>
        {event.human_reviewed && (
          <>
            <span>·</span>
            <span style={{ color: 'var(--accent-green)' }}>✓ Reviewed</span>
          </>
        )}
      </div>
    </div>
  );
}