import { useState, useEffect, useCallback, useRef } from 'react';
import './App.css';
import * as api from './api/client';
import type { EventSummary, EventDetail } from './types';
import EventFeed from './components/EventFeed';
import EventDetailView from './components/EventDetail';

type View = 'stories' | 'detail';

function App() {
  const [currentView, setCurrentView] = useState<View>('stories');
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [events, setEvents] = useState<EventSummary[]>([]);
  const [eventDetail, setEventDetail] = useState<EventDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState({ pool: '', min_confidence: '', topic: '' });
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const didInitialLoad = useRef(false);

  const loadEvents = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.listEvents(filter);
      setEvents(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  // Refresh news from sources (runs the analysis pipeline in the background).
  const refreshNews = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      await api.runPipeline(false, false);
      setLastRefreshed(new Date());
      await loadEvents();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setRefreshing(false);
    }
  }, [loadEvents]);

  // On first load: fetch existing stories. If there are none, automatically
  // pull the latest news so the reader sees content without any manual steps.
  useEffect(() => {
    if (didInitialLoad.current) return;
    didInitialLoad.current = true;
    (async () => {
      setLoading(true);
      try {
        const data = await api.listEvents(filter);
        setEvents(data);
        if (data.length === 0) {
          await refreshNews();
        } else {
          setLastRefreshed(new Date());
        }
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSelectEvent = async (eventId: string) => {
    setLoading(true);
    try {
      const detail = await api.getEventDetail(eventId);
      setEventDetail(detail);
      setSelectedEventId(eventId);
      setCurrentView('detail');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    setCurrentView('stories');
    setSelectedEventId(null);
    setEventDetail(null);
    loadEvents();
  };

  // Reload events when switching to stories view
  useEffect(() => {
    if (currentView === 'stories') loadEvents();
  }, [currentView, loadEvents]);

  const refreshLabel = lastRefreshed
    ? `Updated ${formatTimeAgo(lastRefreshed)}`
    : 'Refresh';

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>Balanced News</h1>
          <div className="subtitle">See every side of the story</div>
        </div>
        <nav className="sidebar-nav">
          <button
            className={currentView === 'stories' ? 'active' : ''}
            onClick={() => setCurrentView('stories')}
          >
            <span className="nav-icon">📰</span>
            Stories
          </button>
        </nav>
        <div className="sidebar-footer">
          {events.length} stories · {refreshLabel}
        </div>
      </aside>

      {/* Main content */}
      <main className="main-content">
        <div className="top-header">
          <h2>
            {currentView === 'stories' && 'Latest stories'}
            {currentView === 'detail' && (eventDetail?.title || 'Story')}
          </h2>
          <div className="header-actions">
            {currentView === 'stories' && (
              <button
                className="btn btn-primary btn-sm"
                onClick={refreshNews}
                disabled={refreshing}
                title="Pull the latest stories and re-run the analysis"
              >
                {refreshing ? '⟳ Refreshing…' : '↻ Refresh news'}
              </button>
            )}
            {currentView === 'detail' && (
              <button className="btn btn-sm" onClick={handleBack}>
                ← Back to stories
              </button>
            )}
          </div>
        </div>

        <div className="content-area">
          {error && (
            <div className="pipeline-status" style={{ borderColor: 'var(--accent-red)' }}>
              <span style={{ color: 'var(--accent-red)' }}>⚠️ {error}</span>
              <button className="btn btn-sm btn-danger" onClick={() => setError(null)}>
                Dismiss
              </button>
            </div>
          )}

          {currentView === 'stories' && (
            <>
              {refreshing && events.length === 0 && (
                <div className="loading">
                  <div className="spinner" />
                  Pulling the latest stories from around the world…
                </div>
              )}
              <EventFeed
                events={events}
                loading={loading && !refreshing}
                filter={filter}
                onFilterChange={setFilter}
                onSelectEvent={handleSelectEvent}
                onRefresh={loadEvents}
              />
            </>
          )}

          {currentView === 'detail' && eventDetail && (
            <EventDetailView event={eventDetail} onBack={handleBack} />
          )}
        </div>
      </main>
    </div>
  );
}

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return date.toLocaleDateString();
}

export default App;
