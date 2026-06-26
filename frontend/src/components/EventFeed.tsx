import type { EventSummary } from '../types';
import EventCard from './EventCard';
import { POOL_LABELS, POOL_ORDER } from '../labels';

interface Props {
  events: EventSummary[];
  loading: boolean;
  filter: { pool: string; min_confidence: string; topic: string };
  onFilterChange: (f: { pool: string; min_confidence: string; topic: string }) => void;
  onSelectEvent: (eventId: string) => void;
  onRefresh: () => void;
}

export default function EventFeed({
  events,
  loading,
  filter,
  onFilterChange,
  onSelectEvent,
  onRefresh,
}: Props) {
  const confirmedCount = events.filter(e => e.overall_confidence === 'confirmed').length;
  const conflictCount = events.filter(e => e.dispute_count > 0).length;
  const regionCount = new Set(events.flatMap(e => e.pools)).size;

  return (
    <div>
      {events.length > 0 && (
        <div className="stats-row">
          <div className="stat-card">
            <div className="stat-value blue">{events.length}</div>
            <div className="stat-label">Stories</div>
          </div>
          <div className="stat-card">
            <div className="stat-value green">{confirmedCount}</div>
            <div className="stat-label">Confirmed</div>
          </div>
          <div className="stat-card">
            <div className="stat-value yellow">{conflictCount}</div>
            <div className="stat-label">Conflicting reports</div>
          </div>
          <div className="stat-card">
            <div className="stat-value purple">{regionCount}</div>
            <div className="stat-label">Regions covered</div>
          </div>
        </div>
      )}

      <div className="filters-bar">
        <select
          value={filter.pool}
          onChange={e => onFilterChange({ ...filter, pool: e.target.value })}
          aria-label="Filter by region"
        >
          <option value="">All regions</option>
          {POOL_ORDER.map(p => (
            <option key={p} value={p}>
              {POOL_LABELS[p]}
            </option>
          ))}
        </select>
        <select
          value={filter.min_confidence}
          onChange={e => onFilterChange({ ...filter, min_confidence: e.target.value })}
          aria-label="Filter by reliability"
        >
          <option value="">All reliability</option>
          <option value="confirmed">Confirmed</option>
          <option value="probable">Likely true</option>
          <option value="disputed">Conflicting reports</option>
        </select>
        <input
          type="text"
          placeholder="Search stories…"
          value={filter.topic}
          onChange={e => onFilterChange({ ...filter, topic: e.target.value })}
          aria-label="Search stories"
        />
        <button className="btn btn-sm" onClick={onRefresh} title="Reload stories">
          ↻
        </button>
      </div>

      {loading ? (
        <div className="loading">
          <div className="spinner" />
          Loading stories…
        </div>
      ) : events.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📭</div>
          <p>No stories yet. Click “Refresh news” to pull the latest coverage.</p>
        </div>
      ) : (
        <div className="event-feed">
          {events.map(event => (
            <EventCard
              key={event.event_id}
              event={event}
              onClick={() => onSelectEvent(event.event_id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
