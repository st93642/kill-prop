import type { DashboardStats, EventSummary } from '../types';
import EventCard from './EventCard';

interface Props {
  events: EventSummary[];
  stats: DashboardStats | null;
  loading: boolean;
  onSelectEvent: (eventId: string) => void;
  onRefresh: () => void;
}

export default function ReviewConsole({ events, stats, loading, onSelectEvent, onRefresh }: Props) {
  const unconfirmedEvents = events.filter(e =>
    e.overall_confidence === 'disputed' || e.overall_confidence === 'unknown'
  );
  const unreviewedEvents = events.filter(e => !e.human_reviewed);

  return (
    <div>
      {stats && (
        <div className="stats-row">
          <div className="stat-card">
            <div className="stat-value blue">{stats.total_events}</div>
            <div className="stat-label">Total Events</div>
          </div>
          <div className="stat-card">
            <div className="stat-value green">{stats.reviewed}</div>
            <div className="stat-label">Reviewed</div>
          </div>
          <div className="stat-card">
            <div className="stat-value yellow">{stats.pending_review}</div>
            <div className="stat-label">Pending Review</div>
          </div>
          <div className="stat-card">
            <div className="stat-value red">{stats.with_disputes}</div>
            <div className="stat-label">With Disputes</div>
          </div>
          <div className="stat-card">
            <div className="stat-value purple">{stats.review_completion}%</div>
            <div className="stat-label">Review Completion</div>
          </div>
        </div>
      )}

      <div className="filters-bar">
        <span style={{ fontSize: 12, color: 'var(--text-muted)', alignSelf: 'center' }}>
          <strong>Pending Review:</strong> {unreviewedEvents.length} events
        </span>
        <button className="btn btn-sm" onClick={onRefresh}>↻ Refresh</button>
      </div>

      {loading ? (
        <div className="loading">
          <div className="spinner" />
          Loading events...
        </div>
      ) : unreviewedEvents.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">✅</div>
          <p>All events have been reviewed. Great work!</p>
        </div>
      ) : (
        <div className="event-feed">
          {unreviewedEvents.map(event => (
            <EventCard
              key={event.event_id}
              event={event}
              onClick={() => onSelectEvent(event.event_id)}
            />
          ))}
        </div>
      )}

      {unconfirmedEvents.length > 0 && (
        <div style={{ marginTop: 32 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
            ⚠ Unconfirmed Events ({unconfirmedEvents.length})
          </h3>
          <div className="event-feed">
            {unconfirmedEvents.map(event => (
              <EventCard
                key={`unc-${event.event_id}`}
                event={event}
                onClick={() => onSelectEvent(event.event_id)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}