import type { EventSummary } from '../types';
import {
  reliabilityLabel,
  reliabilityBadgeClass,
  poolLabelShort,
} from '../labels';

interface Props {
  event: EventSummary;
  onClick: () => void;
}

export default function EventCard({ event, onClick }: Props) {
  const regionCount = event.pool_count;
  const hasConflicts = event.dispute_count > 0;

  return (
    <div className="event-card" onClick={onClick}>
      <div className="event-card-header">
        <span className="event-title">{event.title}</span>
        <span className={`badge ${reliabilityBadgeClass(event.overall_confidence)}`}>
          {reliabilityLabel(event.overall_confidence)}
        </span>
      </div>
      {event.fact_summary && event.fact_summary !== 'Event reported' && (
        <div className="event-summary">{event.fact_summary}</div>
      )}
      <div className="event-footer">
        <span>
          {event.corroborating_sources} source{event.corroborating_sources === 1 ? '' : 's'} ·{' '}
          {regionCount} region{regionCount === 1 ? '' : 's'}
        </span>
        {hasConflicts && (
          <span style={{ color: 'var(--accent-yellow)', marginLeft: 8 }}>
            ⚠ {event.dispute_count} conflicting point{event.dispute_count === 1 ? '' : 's'}
          </span>
        )}
        <span style={{ marginLeft: 'auto', display: 'flex', gap: 3 }}>
          {event.pools.map(p => (
            <span key={p} className={`pool-dot ${p}`} title={poolLabelShort(p)} />
          ))}
        </span>
      </div>
    </div>
  );
}
