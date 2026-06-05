import type { EventSummary } from '../types';
import EventCard from './EventCard';

interface Props {
  events: EventSummary[];
  loading: boolean;
  filter: { pool: string; min_confidence: string; topic: string };
  onFilterChange: (f: { pool: string; min_confidence: string; topic: string }) => void;
  onSelectEvent: (eventId: string) => void;
  onRefresh: () => void;
}

export default function EventFeed({ events, loading, filter, onFilterChange, onSelectEvent, onRefresh }: Props) {
  return (
    <div>
      {events.length > 0 && (
        <div className="stats-row">
          <div className="stat-card">
            <div className="stat-value blue">{events.length}</div>
            <div className="stat-label">Total Events</div>
          </div>
          <div className="stat-card">
            <div className="stat-value green">
              {events.filter(e => e.overall_confidence === 'confirmed').length}
            </div>
            <div className="stat-label">Confirmed</div>
          </div>
          <div className="stat-card">
            <div className="stat-value yellow">
              {events.filter(e => e.dispute_count > 0).length}
            </div>
            <div className="stat-label">With Disputes</div>
          </div>
          <div className="stat-card">
            <div className="stat-value purple">
              {events.reduce((s, e) => s + e.pool_count, 0)}
            </div>
            <div className="stat-label">Pool Spread</div>
          </div>
        </div>
      )}

      <div className="filters-bar">
        <select
          value={filter.pool}
          onChange={e => onFilterChange({ ...filter, pool: e.target.value })}
        >
          <option value="">All Pools</option>
          <option value="western_mainstream">Western</option>
          <option value="russian_state">Russian State</option>
          <option value="russian_independent">Russian Independent</option>
          <option value="neutral_wire">Neutral Wire</option>
        </select>
        <select
          value={filter.min_confidence}
          onChange={e => onFilterChange({ ...filter, min_confidence: e.target.value })}
        >
          <option value="">All Confidence</option>
          <option value="confirmed">Confirmed</option>
          <option value="probable">Probable</option>
          <option value="disputed">Disputed</option>
        </select>
        <input
          type="text"
          placeholder="Filter by topic..."
          value={filter.topic}
          onChange={e => onFilterChange({ ...filter, topic: e.target.value })}
        />
        <button className="btn btn-sm" onClick={onRefresh}>↻</button>
      </div>

      {loading ? (
        <div className="loading">
          <div className="spinner" />
          Loading events...
        </div>
      ) : events.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📭</div>
          <p>No events yet. Run the pipeline first to ingest and cluster news articles.</p>
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